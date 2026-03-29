from __future__ import annotations

import argparse
import gzip
import json
import os
import socket
import sys
import time

from aw_portal_uploader.extensions.registry import run_sync_hooks
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests
from urllib.parse import urlencode, urlparse


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _gzip_ingest_enabled() -> bool:
    """По умолчанию без gzip: прокси часто снимает Content-Encoding, тело остаётся gzip → FastAPI: «parsing the body»."""
    return os.environ.get("AW_PORTAL_GZIP_INGEST", "").lower() in ("1", "true", "yes")


def _default_portal_url() -> str:
    # Как в install_wizard и типичном docker-compose портала (внешний порт 8010).
    return "http://localhost:8010"


def _cli_gave_arg(flag: str) -> bool:
    prefix = flag + "="
    for a in sys.argv[1:]:
        if a == flag or a.startswith(prefix):
            return True
    return False


def _should_auto_first_run_wizard(args: argparse.Namespace) -> bool:
    """Первый запуск собранного exe на Windows: графический мастер вместо консоли."""
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return False
    if args.no_first_run_wizard:
        return False
    if _cli_gave_arg("--enrollment-code") or os.environ.get("AW_PORTAL_ENROLLMENT_CODE"):
        return False
    early_state = os.path.join(_default_state_dir(), "uploader_state.json")
    if (_read_json(early_state).get("device_token") or "").strip():
        return False
    return True


def _default_state_dir() -> str:
    # Windows service-friendly default
    if os.name == "nt":
        base = os.environ.get("PROGRAMDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "ActivityWatchPortal")
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return os.path.join(xdg, "activitywatch-portal")
    return os.path.join(os.path.expanduser("~"), ".local", "state", "activitywatch-portal")


@dataclass
class UrlPolicy:
    mode: str  # drop|host_only|full
    allow: List[str]
    deny: List[str]

    def apply_to_url(self, url: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not url:
            return None, None
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
        except Exception:
            return None, None

        if not host:
            return None, None

        def _domain_match(hostname: str, rule: str) -> bool:
            rule = rule.lstrip(".").lower()
            return hostname == rule or hostname.endswith("." + rule)

        if self.allow:
            if not any(_domain_match(host, r) for r in self.allow):
                return None, None

        if self.deny and any(_domain_match(host, r) for r in self.deny):
            if self.mode == "drop":
                return None, None
            if self.mode == "host_only":
                return host, host

        if self.mode == "host_only":
            return host, host

        return url, host


class HttpClient:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def request_json(self, method: str, path: str, body: Optional[dict] = None, gzip_body: bool = False) -> Any:
        url = self.base_url + path
        headers = {"Accept": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = None
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
            if gzip_body:
                raw = gzip.compress(raw)
                headers["Content-Encoding"] = "gzip"
            data = raw

        try:
            resp = requests.request(method=method, url=url, data=data, headers=headers, timeout=self.timeout)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            if not resp.content:
                return None
            return resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Network error: {e}") from e

    def post_multipart_file(self, path: str, filename: str, content: bytes, content_type: str = "image/png") -> Any:
        url = self.base_url + path
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        files = {"file": (filename, content, content_type)}
        try:
            resp = requests.post(url, files=files, headers=headers, timeout=max(60, self.timeout * 3))
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json() if resp.content else {}
        except requests.RequestException as e:
            raise RuntimeError(f"Network error: {e}") from e


def _detect_device_id() -> str:
    return os.environ.get("AW_PORTAL_DEVICE_ID") or socket.gethostname()


def _detect_os() -> str:
    return f"{os.name}"


def enroll_if_needed(portal: HttpClient, state_path: str, portal_url: str) -> Tuple[str, str]:
    state = _read_json(state_path)
    device_id = state.get("device_id") or _detect_device_id()
    token = os.environ.get("AW_PORTAL_DEVICE_TOKEN") or state.get("device_token")

    if token:
        return device_id, token

    enrollment_code = os.environ.get("AW_PORTAL_ENROLLMENT_CODE")
    if not enrollment_code:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "Нужен enrollment code: запустите из cmd с параметром "
                "--enrollment-code \"...\" или задайте AW_PORTAL_ENROLLMENT_CODE, "
                "либо используйте aw-portal-uploader.exe --install-wizard"
            )
        print("Введите enrollment code (полученный в портале): ", end="", flush=True)
        enrollment_code = input().strip()

    req = {
        "enrollment_code": enrollment_code,
        "device_id": device_id,
        "hostname": socket.gethostname(),
        "os": _detect_os(),
    }
    resp = portal.request_json("POST", "/api/v1/devices/enroll", req)
    token = resp["token"]
    state["device_id"] = resp.get("device_id") or device_id
    state["device_token"] = token
    state["portal_url"] = portal_url
    _write_json(state_path, state)
    return state["device_id"], token


def _aw_list_buckets(aw: HttpClient) -> List[str]:
    buckets = aw.request_json("GET", "/api/0/buckets") or {}
    return list(buckets.keys())


def _aw_get_events(aw: HttpClient, bucket_id: str, start_iso: Optional[str]) -> List[dict]:
    qs = {}
    if start_iso:
        qs["start"] = start_iso
    path = f"/api/0/buckets/{bucket_id}/events"
    if qs:
        path += "?" + urlencode(qs)
    data = aw.request_json("GET", path)
    return data or []


def _event_ts(ev: dict) -> Optional[datetime]:
    ts = ev.get("timestamp") or ev.get("ts")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _event_duration_seconds(ev: dict) -> Optional[int]:
    # ActivityWatch events usually have duration in seconds in ev["duration"].
    d = ev.get("duration")
    if d is None:
        return None
    try:
        # duration may be float
        sec = int(float(d))
        return sec if sec > 0 else None
    except Exception:
        return None


def _normalize(bucket_id: str, ev: dict, policy: UrlPolicy) -> Optional[Tuple[str, datetime, Optional[int], Dict[str, Any]]]:
    dt = _event_ts(ev)
    if not dt:
        return None

    dur = _event_duration_seconds(ev)
    data = ev.get("data") or {}

    if bucket_id.startswith("aw-watcher-window"):
        return "window", dt, dur, {"app": data.get("app"), "title": data.get("title")}

    if bucket_id.startswith("aw-watcher-afk"):
        status = data.get("status")
        return "afk", dt, dur, {"status": status, "is_afk": status == "afk"}

    if bucket_id.startswith("aw-watcher-web"):
        url = data.get("url")
        title = data.get("title")
        browser = data.get("browser")
        filtered_url, host = policy.apply_to_url(url)
        if filtered_url is None and host is None:
            return None
        return "web", dt, dur, {"url": filtered_url, "host": host, "title": title, "browser": browser}

    return "raw", dt, dur, data


def _interactive_setup_choices(state_path: str) -> None:
    if not sys.stdin.isatty():
        print("[uploader] --setup-prompts: нет TTY, пропуск.")
        return

    def _yn(prompt: str, default: bool) -> bool:
        suf = "Y/n" if default else "y/N"
        s = input(f"{prompt} [{suf}]: ").strip().lower()
        if not s:
            return default
        return s in ("y", "yes", "д", "да")

    state = _read_json(state_path)
    print("[uploader] Локальные опции (организация на сервере тоже должна разрешить скриншоты/ИИ).")
    state["screenshots_local"] = _yn("Отправлять скриншоты с этого ПК?", bool(state.get("screenshots_local", True)))
    state["screenshot_ai_server"] = _yn(
        "Учитывать ИИ-анализ непродуктивности на сервере (Ollama)?",
        bool(state.get("screenshot_ai_server", True)),
    )
    _write_json(state_path, state)
    print(f"[uploader] Сохранено: {state_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="aw-portal-uploader")
    parser.add_argument(
        "--portal-url",
        default=os.environ.get("AW_PORTAL_URL") or _default_portal_url(),
        help=f"Базовый URL портала (по умолчанию {_default_portal_url()} или AW_PORTAL_URL)",
    )
    parser.add_argument("--aw-server-url", default=os.environ.get("AW_SERVER_URL") or "http://127.0.0.1:5600")
    parser.add_argument("--state-dir", default=os.environ.get("AW_PORTAL_STATE_DIR") or _default_state_dir())
    parser.add_argument("--device-id", default=os.environ.get("AW_PORTAL_DEVICE_ID"))
    parser.add_argument("--enrollment-code", default=os.environ.get("AW_PORTAL_ENROLLMENT_CODE"))
    parser.add_argument(
        "--install-wizard",
        action="store_true",
        help="Только графический мастер установки (папка, URL, ключ, учётная запись)",
    )
    parser.add_argument(
        "--no-first-run-wizard",
        action="store_true",
        help="Не открывать мастер при первом запуске exe (enrollment через --enrollment-code / переменные)",
    )
    parser.add_argument(
        "--setup-prompts",
        action="store_true",
        help="После регистрации: в терминале спросить скриншоты и ИИ-анализ (только интерактивный режим)",
    )
    args = parser.parse_args()

    if args.install_wizard:
        from aw_portal_uploader.install_wizard import main as wizard_main

        wizard_main()
        return

    if _should_auto_first_run_wizard(args):
        from aw_portal_uploader.install_wizard import main as wizard_main

        wizard_main()
        state_path_early = os.path.join(_default_state_dir(), "uploader_state.json")
        if not (_read_json(state_path_early).get("device_token") or "").strip():
            return

    if args.device_id:
        os.environ["AW_PORTAL_DEVICE_ID"] = args.device_id
    if args.enrollment_code:
        os.environ["AW_PORTAL_ENROLLMENT_CODE"] = args.enrollment_code

    state_dir = (args.state_dir or "").strip()
    state_path = os.path.join(state_dir, "uploader_state.json")
    disk_state = _read_json(state_path)

    portal_arg = (args.portal_url or "").strip()
    aw_arg = (args.aw_server_url or "").strip()

    # CLI и переменные окружения важнее сохранённого state; иначе при двойном клике по exe
    # каждый раз сбрасывалось на localhost и ломалась работа после первой регистрации.
    if _cli_gave_arg("--portal-url"):
        portal_url = portal_arg
    elif os.environ.get("AW_PORTAL_URL"):
        portal_url = portal_arg
    elif (disk_state.get("portal_url") or "").strip():
        portal_url = (disk_state.get("portal_url") or "").strip()
    else:
        portal_url = portal_arg

    if _cli_gave_arg("--aw-server-url"):
        aw_server_url = aw_arg
    elif os.environ.get("AW_SERVER_URL"):
        aw_server_url = aw_arg
    elif (disk_state.get("aw_server_url") or "").strip():
        aw_server_url = (disk_state.get("aw_server_url") or "").strip()
    else:
        aw_server_url = aw_arg

    if (
        sys.stdin.isatty()
        and not (getattr(sys, "frozen", False) and os.name == "nt")
        and not _cli_gave_arg("--portal-url")
        and not os.environ.get("AW_PORTAL_URL")
        and not (disk_state.get("portal_url") or "").strip()
    ):
        print(
            f"Адрес портала (Enter = {_default_portal_url()}): ",
            end="",
            flush=True,
        )
        try:
            line = input().strip()
        except (EOFError, KeyboardInterrupt):
            line = ""
        if line:
            portal_url = line.rstrip("/")

    print(f"[uploader] Портал: {portal_url} | ActivityWatch (локально): {aw_server_url}", flush=True)

    portal = HttpClient(portal_url)
    device_id, token = enroll_if_needed(portal, state_path, portal_url)
    portal.token = token

    if args.setup_prompts:
        _interactive_setup_choices(state_path)

    aw = HttpClient(aw_server_url)

    state = _read_json(state_path)
    seq = int(state.get("seq") or 0)
    cursors: Dict[str, str] = state.get("bucket_cursors") or {}

    backoff = 1.0
    while True:
        try:
            pol = portal.request_json("GET", "/api/v1/devices/policy") or {}
            policy = UrlPolicy(
                mode=str(pol.get("url_policy_mode") or "full"),
                allow=list(pol.get("allow_domains") or []),
                deny=list(pol.get("deny_domains") or []),
            )
            interval = int(pol.get("sync_interval_seconds") or 120)

            bucket_ids = _aw_list_buckets(aw)
            wanted = [b for b in bucket_ids if b.startswith(("aw-watcher-window", "aw-watcher-afk", "aw-watcher-web"))]

            batch: List[dict] = []
            max_per_sync = int(os.environ.get("AW_PORTAL_MAX_EVENTS_PER_SYNC") or "2000")

            for bucket_id in wanted:
                start_iso = cursors.get(bucket_id)
                events = _aw_get_events(aw, bucket_id, start_iso)
                latest_dt: Optional[datetime] = None

                for raw in events:
                    norm = _normalize(bucket_id, raw, policy)
                    if not norm:
                        continue
                    ev_type, ts, dur, data = norm
                    seq += 1
                    rid = raw.get("id")
                    batch.append(
                        {
                            "seq": seq,
                            "type": ev_type,
                            "ts": _iso(ts),
                            "duration_seconds": dur,
                            "data": data,
                            "raw_bucket": bucket_id,
                            "raw_event_id": str(rid) if rid is not None else None,
                        }
                    )
                    latest_dt = ts if (latest_dt is None or ts > latest_dt) else latest_dt
                    if len(batch) >= max_per_sync:
                        break

                if latest_dt is not None:
                    cursors[bucket_id] = _iso(latest_dt)
                if len(batch) >= max_per_sync:
                    break

            if batch:
                payload = {"device_id": device_id, "sent_at": _iso(_utcnow()), "events": batch}
                portal.request_json("POST", "/api/v1/ingest/batch", payload, gzip_body=_gzip_ingest_enabled())

            run_sync_hooks(
                {
                    "portal": portal,
                    "device_id": device_id,
                    "state_path": state_path,
                    "state": state,
                    "policy": pol,
                }
            )

            last_cap = float(state.get("last_screenshot_at") or 0)
            now_ts = time.time()
            shot_iv = int(pol.get("screenshot_interval_seconds") or 300)
            if (
                bool(pol.get("screenshots_enabled"))
                and bool(state.get("screenshots_local"))
                and portal.token
                and (now_ts - last_cap >= shot_iv)
            ):
                from aw_portal_uploader.screenshots_win import capture_screen_png

                png = capture_screen_png()
                if png:
                    try:
                        up = portal.post_multipart_file("/api/v1/devices/screenshots", "screen.png", png, "image/png")
                        mid = up.get("media_id")
                        if mid:
                            seq += 1
                            portal.request_json(
                                "POST",
                                "/api/v1/ingest/batch",
                                {
                                    "device_id": device_id,
                                    "sent_at": _iso(_utcnow()),
                                    "events": [
                                        {
                                            "seq": seq,
                                            "type": "screenshot",
                                            "ts": _iso(_utcnow()),
                                            "duration_seconds": None,
                                            "data": {"media_id": mid},
                                        }
                                    ],
                                },
                                gzip_body=_gzip_ingest_enabled(),
                            )
                            state["last_screenshot_at"] = now_ts
                    except Exception as e:
                        print(f"[uploader] screenshot: {e}")

            state["device_id"] = device_id
            state["device_token"] = token
            state["portal_url"] = portal_url
            state["aw_server_url"] = aw_server_url
            state["seq"] = seq
            state["bucket_cursors"] = cursors
            _write_json(state_path, state)

            backoff = 1.0
            time.sleep(max(30, min(interval, 3600)))
        except Exception as e:
            print(f"[uploader] error: {e}")
            time.sleep(min(300, backoff))
            backoff = min(300, backoff * 2)


def _pause_console_on_frozen() -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        input("\nОшибка — нажмите Enter, чтобы закрыть окно… ")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback

        tb = traceback.format_exc()
        print(tb, flush=True)
        err_path = os.path.join(_default_state_dir(), "uploader_last_error.log")
        try:
            with open(err_path, "w", encoding="utf-8") as ef:
                ef.write(tb)
            print(f"[uploader] Подробности записаны в: {err_path}", flush=True)
        except OSError:
            pass
        _pause_console_on_frozen()
        raise

