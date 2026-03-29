"""Графическая первичная настройка: папка установки, URL портала, ключ, учётные данные."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

import requests


def _default_state_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("PROGRAMDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "ActivityWatchPortal")
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return os.path.join(xdg, "activitywatch-portal")
    return os.path.join(os.path.expanduser("~"), ".local", "state", "activitywatch-portal")


def _default_install_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Programs", "AwPortalUploader")


def _write_state(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _detect_device_id() -> str:
    return os.environ.get("AW_PORTAL_DEVICE_ID") or socket.gethostname()


def _user_desktop_dir() -> str | None:
    home = os.path.expanduser("~")
    for name in ("Desktop", "Рабочий стол"):
        d = os.path.join(home, name)
        if os.path.isdir(d):
            return d
    up = os.environ.get("USERPROFILE", "")
    if up:
        d = os.path.join(up, "Desktop")
        if os.path.isdir(d):
            return d
    return None


def _powershell_single_quoted(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _create_desktop_shortcut_windows(target_exe: str, shortcut_basename: str = "Portal Uploader.lnk") -> None:
    desktop = _user_desktop_dir()
    if not desktop:
        raise RuntimeError("Не удалось найти папку рабочего стола")
    lnk = os.path.join(desktop, shortcut_basename)
    work = os.path.dirname(os.path.abspath(target_exe))
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
        + _powershell_single_quoted(lnk)
        + "); $s.TargetPath="
        + _powershell_single_quoted(os.path.abspath(target_exe))
        + "; $s.WorkingDirectory="
        + _powershell_single_quoted(work)
        + "; $s.Save()"
    )
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
        creationflags=flags,
    )


def main() -> None:
    root = tk.Tk()
    root.title("Установка агента портала")
    root.geometry("600x820")
    root.minsize(560, 760)

    title_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")

    frm = ttk.Frame(root, padding=12)
    frm.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    vars_map: dict[str, tk.Variable] = {
        "install_dir": tk.StringVar(value=_default_install_dir()),
        "portal_url": tk.StringVar(value=os.environ.get("AW_PORTAL_URL") or "http://localhost:8010"),
        "aw_server_url": tk.StringVar(value=os.environ.get("AW_SERVER_URL") or "http://127.0.0.1:5600"),
        "org_id": tk.StringVar(value=os.environ.get("AW_PORTAL_ORG_ID") or "1"),
        "install_secret": tk.StringVar(value=""),
        "device_name": tk.StringVar(value=""),
        "login": tk.StringVar(value=""),
        "password": tk.StringVar(value=""),
        "full_name": tk.StringVar(value=""),
        "job_title": tk.StringVar(value=""),
        "timezone": tk.StringVar(value="Europe/Moscow"),
        "email": tk.StringVar(value=""),
        "screenshots": tk.BooleanVar(value=True),
        "screenshot_ai_server": tk.BooleanVar(value=True),
        "desktop_shortcut": tk.BooleanVar(value=True),
        "launch_after": tk.BooleanVar(value=True),
    }

    row = 0

    def add_row(label: str, widget, colspan: int = 1):
        nonlocal row
        ttk.Label(frm, text=label).grid(row=row, column=0, sticky="nw", pady=4)
        widget.grid(row=row, column=1, sticky="ew", pady=4, columnspan=colspan)
        row += 1

    def add_heading(text: str) -> None:
        nonlocal row
        ttk.Label(frm, text=text, font=title_font).grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4))
        row += 1

    frm.columnconfigure(1, weight=1)

    add_heading("Куда установить")
    install_row = ttk.Frame(frm)
    ent_install = ttk.Entry(install_row, textvariable=vars_map["install_dir"], width=42)

    def browse_install() -> None:
        d = filedialog.askdirectory(initialdir=vars_map["install_dir"].get() or _default_install_dir())
        if d:
            vars_map["install_dir"].set(d)

    ttk.Button(install_row, text="Обзор…", command=browse_install).pack(side=tk.RIGHT, padx=(8, 0))
    ent_install.pack(side=tk.LEFT, fill=tk.X, expand=True)
    add_row("Папка (будет скопирован aw-portal-uploader.exe)", install_row)

    add_heading("Сервер портала")
    add_row("Адрес портала (http://IP или домен:порт)", ttk.Entry(frm, textvariable=vars_map["portal_url"], width=48))
    add_row(
        "Локальный ActivityWatch (aw-server)",
        ttk.Entry(frm, textvariable=vars_map["aw_server_url"], width=48),
    )
    add_row("ID организации", ttk.Entry(frm, textvariable=vars_map["org_id"], width=48))
    add_row(
        "Ключ установки с сервера (админка → организация)",
        ttk.Entry(frm, textvariable=vars_map["install_secret"], width=48, show="*"),
    )
    add_row(
        "Имя устройства (необязательно, иначе имя ПК)",
        ttk.Entry(frm, textvariable=vars_map["device_name"], width=48),
    )

    add_heading("Ваши данные")
    add_row("Логин", ttk.Entry(frm, textvariable=vars_map["login"], width=48))
    add_row("Пароль", ttk.Entry(frm, textvariable=vars_map["password"], width=48, show="*"))
    add_row("ФИО", ttk.Entry(frm, textvariable=vars_map["full_name"], width=48))
    add_row("Должность", ttk.Entry(frm, textvariable=vars_map["job_title"], width=48))
    add_row("Часовой пояс", ttk.Entry(frm, textvariable=vars_map["timezone"], width=48))
    add_row("Email (опционально)", ttk.Entry(frm, textvariable=vars_map["email"], width=48))

    ttk.Separator(frm, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
    row += 1
    ttk.Checkbutton(
        frm,
        text="Отправлять скриншоты на портал",
        variable=vars_map["screenshots"],
    ).grid(row=row, column=0, columnspan=2, sticky="w")
    row += 1
    ttk.Checkbutton(
        frm,
        text="ИИ-анализ непродуктивности по скринам на сервере",
        variable=vars_map["screenshot_ai_server"],
    ).grid(row=row, column=0, columnspan=2, sticky="w")
    row += 1
    ttk.Checkbutton(
        frm,
        text="Ярлык на рабочем столе (после копирования)",
        variable=vars_map["desktop_shortcut"],
    ).grid(row=row, column=0, columnspan=2, sticky="w")
    row += 1
    ttk.Checkbutton(
        frm,
        text="Сразу запустить агент после установки",
        variable=vars_map["launch_after"],
    ).grid(row=row, column=0, columnspan=2, sticky="w")
    row += 1

    status = tk.Text(frm, height=5, width=62, state="disabled", wrap="word")
    status.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=8)
    frm.rowconfigure(row, weight=1)
    row += 1

    def log(msg: str) -> None:
        status.configure(state="normal")
        status.insert("end", msg + "\n")
        status.see("end")
        status.configure(state="disabled")

    def submit() -> None:
        install_dir = (vars_map["install_dir"].get() or "").strip()
        if not install_dir:
            messagebox.showerror("Ошибка", "Укажите папку установки")
            return
        base = (vars_map["portal_url"].get() or "").strip().rstrip("/")
        if not base:
            messagebox.showerror("Ошибка", "Укажите адрес портала")
            return
        try:
            p = urlparse(base)
            if not p.scheme or not p.netloc:
                raise ValueError("нужен полный URL, например http://server:8010")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректный адрес портала: {e}")
            return
        aw_local = (vars_map["aw_server_url"].get() or "").strip().rstrip("/")
        if not aw_local:
            messagebox.showerror("Ошибка", "Укажите адрес локального ActivityWatch")
            return
        try:
            oid = int((vars_map["org_id"].get() or "").strip())
        except ValueError:
            messagebox.showerror("Ошибка", "ID организации должен быть числом")
            return
        try:
            r = requests.get(f"{base}/api/v1/meta/org/{oid}/registration", timeout=15)
            r.raise_for_status()
            meta = r.json()
            if not meta.get("self_registration_enabled"):
                messagebox.showerror("Ошибка", "Саморегистрация для этой организации выключена")
                return
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось связаться с порталом: {e}")
            return

        device_id = (vars_map["device_name"].get() or "").strip() or _detect_device_id()

        payload = {
            "org_id": oid,
            "install_secret": vars_map["install_secret"].get().strip(),
            "login": vars_map["login"].get().strip(),
            "password": vars_map["password"].get(),
            "full_name": vars_map["full_name"].get().strip() or None,
            "job_title": vars_map["job_title"].get().strip() or None,
            "timezone": vars_map["timezone"].get().strip() or "Europe/Moscow",
            "email": vars_map["email"].get().strip() or None,
            "device_id": device_id,
            "hostname": socket.gethostname(),
            "os": f"{os.name}",
        }
        if not payload["login"] or not payload["password"]:
            messagebox.showerror("Ошибка", "Нужны логин и пароль")
            return
        if not payload["install_secret"]:
            messagebox.showerror("Ошибка", "Нужен ключ установки из админки портала")
            return

        try:
            r2 = requests.post(f"{base}/api/v1/devices/enroll-with-user", json=payload, timeout=30)
            if r2.status_code >= 400:
                detail = (
                    r2.json().get("detail", r2.text)
                    if r2.headers.get("content-type", "").startswith("application/json")
                    else r2.text
                )
                messagebox.showerror("Ошибка", str(detail))
                return
            data = r2.json()
            token = data["token"]
            dev_id = data.get("device_id") or device_id
        except Exception as e:
            messagebox.showerror("Ошибка", f"Регистрация не удалась: {e}")
            return

        state_dir = os.environ.get("AW_PORTAL_STATE_DIR") or _default_state_dir()
        state_path = os.path.join(state_dir, "uploader_state.json")
        state = {
            "device_id": dev_id,
            "device_token": token,
            "portal_url": base,
            "aw_server_url": aw_local,
            "seq": 0,
            "bucket_cursors": {},
            "screenshots_local": bool(vars_map["screenshots"].get()),
            "screenshot_ai_server": bool(vars_map["screenshot_ai_server"].get()),
        }
        _write_state(state_path, state)
        log(f"Настройки сохранены: {state_path}")

        target_exe = os.path.abspath(sys.executable)
        if getattr(sys, "frozen", False):
            os.makedirs(install_dir, exist_ok=True)
            target_exe = os.path.join(os.path.abspath(install_dir), "aw-portal-uploader.exe")
            cur = os.path.abspath(sys.executable)
            same = os.path.normcase(cur) == os.path.normcase(target_exe)
            if not same:
                try:
                    shutil.copy2(cur, target_exe)
                    log(f"Программа скопирована: {target_exe}")
                except OSError as e:
                    messagebox.showerror("Ошибка", f"Не удалось скопировать exe в папку установки:\n{e}")
                    return
            else:
                log("Запуск уже из папки установки — копирование не требуется.")
        else:
            log("Режим разработки: exe не копируется, запускайте python -m aw_portal_uploader")

        if os.name == "nt" and vars_map["desktop_shortcut"].get() and getattr(sys, "frozen", False):
            try:
                _create_desktop_shortcut_windows(target_exe)
                log("Ярлык на рабочем столе создан.")
            except Exception as e:
                log(f"Ярлык не создан: {e}")

        messagebox.showinfo("Готово", f"Регистрация выполнена.\n\nСостояние:\n{state_path}")

        if vars_map["launch_after"].get() and getattr(sys, "frozen", False):
            flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen(
                [target_exe],
                cwd=os.path.dirname(target_exe),
                close_fds=True,
                creationflags=flags,
            )
            root.destroy()
            os._exit(0)

    btn = ttk.Button(frm, text="Установить и зарегистрировать", command=submit)
    btn.grid(row=row, column=0, columnspan=2, pady=10)
    row += 1

    ttk.Label(
        frm,
        text="Ключ установки выдаёт администратор в портале (настройки организации).",
        wraplength=540,
    ).grid(row=row, column=0, columnspan=2, sticky="w")

    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except tk.TclError as e:
        print("tkinter недоступен в этой среде:", e, file=sys.stderr)
        sys.exit(1)
