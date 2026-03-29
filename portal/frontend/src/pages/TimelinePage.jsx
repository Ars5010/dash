import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import AuthenticatedImage from '../components/AuthenticatedImage'

function badgeClass(indicator) {
  switch (indicator) {
    case 'green':
      return 'bg-emerald-500/10 text-emerald-900 ring-1 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:ring-emerald-400/30'
    case 'yellow':
      return 'bg-amber-500/10 text-amber-950 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:ring-amber-400/30'
    case 'red':
      return 'bg-rose-500/10 text-rose-950 ring-1 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-200 dark:ring-rose-400/30'
    case 'blue':
      return 'bg-sky-500/10 text-sky-950 ring-1 ring-sky-200 dark:bg-sky-500/15 dark:text-sky-200 dark:ring-sky-400/30'
    default:
      return 'bg-slate-900/5 text-slate-800 ring-1 ring-slate-200 dark:bg-white/10 dark:text-slate-200 dark:ring-white/15'
  }
}

function indicatorLabel(indicator) {
  switch (indicator) {
    case 'green':
      return 'Хороший'
    case 'yellow':
      return 'Средний'
    case 'red':
      return 'Плохой'
    case 'blue':
      return 'Отсутствие'
    default:
      return '—'
  }
}

function minutesLabel(mins) {
  if (mins == null) return '—'
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h > 0 ? `${h}ч ${m}м` : `${m}м`
}

export default function TimelinePage() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [q, setQ] = useState('')
  const [users, setUsers] = useState([])
  const [selectedUserIds, setSelectedUserIds] = useState([])
  const [activities, setActivities] = useState([])
  const [periodStats, setPeriodStats] = useState(null)
  const [ssByUser, setSsByUser] = useState({})
  const [shotModal, setShotModal] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const selectedPrimaryUserId = selectedUserIds[0] ?? null

  const dayStart = useMemo(() => new Date(`${date}T00:00:00Z`), [date])
  const dayEnd = useMemo(() => new Date(`${date}T23:59:59Z`), [date])

  function leftPct(startIso) {
    const t = new Date(startIso).getTime()
    const a = dayStart.getTime()
    const b = dayEnd.getTime()
    const pct = ((t - a) / (b - a)) * 100
    return Math.max(0, Math.min(100, pct))
  }

  function widthPct(startIso, endIso) {
    const s = new Date(startIso).getTime()
    const e = new Date(endIso).getTime()
    const a = dayStart.getTime()
    const b = dayEnd.getTime()
    const pct = ((e - s) / (b - a)) * 100
    return Math.max(0.5, Math.min(100, pct))
  }

  function segColor(type) {
    switch (type) {
      case 'Active':
        return 'bg-emerald-400/60'
      case 'Away':
        return 'bg-rose-400/60'
      case 'Productive':
        return 'bg-amber-300/70'
      default:
        return 'bg-white/30'
    }
  }

  async function fetchUsers() {
    const resp = await api.get('/v1/timeline/users', { params: { q: q || undefined } })
    setUsers(resp.data || [])
  }

  async function fetchActivities() {
    if (selectedUserIds.length === 0) {
      setActivities([])
      return
    }
    setLoading(true)
    setError('')
    try {
      const resp = await api.get('/v1/timeline/user-activity', {
        params: { date, user_ids: selectedUserIds },
      })
      setActivities(resp.data.activities || [])
    } catch (e) {
      const d = e?.response?.data
      const detail = d?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map((x) => x?.msg).filter(Boolean).join('; ') || 'Ошибка загрузки данных')
      } else {
        setError('Ошибка загрузки данных')
      }
    } finally {
      setLoading(false)
    }
  }

  async function fetchPeriodStats() {
    if (!selectedPrimaryUserId) {
      setPeriodStats(null)
      return
    }
    try {
      const resp = await api.get('/v1/timeline/period-stats', {
        params: { user_id: selectedPrimaryUserId, date },
      })
      setPeriodStats(resp.data)
    } catch {
      // не блокируем основной UI
    }
  }

  async function fetchDayScreenshots() {
    if (selectedUserIds.length === 0) {
      setSsByUser({})
      return
    }
    try {
      const resp = await api.get('/v1/timeline/day-screenshots', {
        params: { date, user_ids: selectedUserIds },
      })
      const m = {}
      for (const block of resp.data.users || []) {
        m[block.user_id] = block.screenshots || []
      }
      setSsByUser(m)
    } catch {
      setSsByUser({})
    }
  }

  useEffect(() => {
    fetchUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    fetchActivities()
    fetchPeriodStats()
    fetchDayScreenshots()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, selectedUserIds.join(',')])

  function toggleUser(id) {
    setSelectedUserIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">Хронология</h1>
          <span className="text-xs text-slate-500 dark:text-slate-400">UTC MVP</span>
        </div>

        <div className="mt-4 grid gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Дата</span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>

          <div className="grid gap-2">
            <div className="flex items-end gap-2">
              <label className="grid flex-1 gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Пользователи</span>
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Поиск по логину/ФИО…"
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                />
              </label>
              <button
                onClick={fetchUsers}
                className="h-10 rounded-xl bg-slate-900/5 px-4 text-sm text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
              >
                Найти
              </button>
            </div>

            {selectedPrimaryUserId ? (
              <Link
                to={`/employee/${selectedPrimaryUserId}`}
                className="inline-flex text-xs font-semibold text-fuchsia-600 hover:text-fuchsia-500 dark:text-fuchsia-400"
              >
                Профиль сотрудника (первый в списке выбранных) →
              </Link>
            ) : null}

            <div className="max-h-[52vh] overflow-auto rounded-2xl bg-slate-100 p-2 ring-1 ring-slate-200 dark:bg-slate-950/30 dark:ring-white/10">
              {users.length === 0 ? (
                <div className="p-3 text-sm text-slate-500 dark:text-slate-400">Нет пользователей</div>
              ) : (
                users.map((u) => (
                  <label
                    key={u.id}
                    className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 hover:bg-slate-200 dark:hover:bg-white/5"
                  >
                    <input
                      type="checkbox"
                      checked={selectedUserIds.includes(u.id)}
                      onChange={() => toggleUser(u.id)}
                      className="h-4 w-4 accent-fuchsia-400"
                    />
                    <div className="min-w-0">
                      <div className="truncate text-sm text-slate-900 dark:text-slate-100">
                        {u.full_name || u.login}
                      </div>
                      <div className="truncate text-xs text-slate-600 dark:text-slate-500">{u.login}</div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Лента дня</h2>
          <div className="text-xs text-slate-600 dark:text-slate-400">
            Active / Away / Productive
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200 ring-1 ring-rose-400/30">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="mt-4 rounded-2xl bg-slate-100 p-4 text-sm text-slate-600 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-300 dark:ring-white/10">
            Загрузка…
          </div>
        ) : null}

        <div className="mt-4 grid gap-4">
          {activities.map((a) => (
            <div
              key={a.user_id}
              className="grid gap-3 rounded-2xl bg-slate-100 p-4 ring-1 ring-slate-200 dark:bg-slate-950/25 dark:ring-white/10 lg:grid-cols-[220px_1fr_320px]"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {a.display_name}
                  </div>
                  <Link
                    to={`/employee/${a.user_id}`}
                    className="shrink-0 text-xs font-semibold text-fuchsia-600 hover:text-fuchsia-500 dark:text-fuchsia-400"
                  >
                    Профиль
                  </Link>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs ${badgeClass(a.metrics.indicator)}`}>
                    KPI {a.metrics.kpi_percent}% · {indicatorLabel(a.metrics.indicator)}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-1 text-xs text-slate-800 ring-1 ring-slate-300 dark:bg-white/10 dark:text-slate-200 dark:ring-white/15">
                    Штраф {a.metrics.day_fine}
                  </span>
                </div>
              </div>

              <div className="relative h-10 overflow-hidden rounded-xl bg-slate-200 ring-1 ring-slate-300 dark:bg-white/5 dark:ring-white/10">
                {a.segments.map((s, idx) => (
                  <div
                    key={idx}
                    className={`absolute top-0 h-full ${segColor(s.type)}`}
                    style={{
                      left: `${leftPct(s.start)}%`,
                      width: `${widthPct(s.start, s.end)}%`,
                    }}
                    title={`${s.type}: ${new Date(s.start).toISOString()} → ${new Date(s.end).toISOString()}`}
                  />
                ))}
              </div>

              <div className={`rounded-2xl p-4 ${badgeClass(a.metrics.indicator)}`}>
                <div className="grid gap-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-700 dark:text-slate-200/90">Активное</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {minutesLabel(a.metrics.active_minutes)} · {a.metrics.active_percent}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-700 dark:text-slate-200/90">Неактивное</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {minutesLabel(a.metrics.inactive_minutes)} · {a.metrics.inactive_percent}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-700 dark:text-slate-200/90">Продуктивное</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {minutesLabel(a.metrics.productive_minutes)} · {a.metrics.productive_percent}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-700 dark:text-slate-200/90">Непродуктивное</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {minutesLabel(a.metrics.unproductive_minutes)} · {a.metrics.unproductive_percent}%
                    </span>
                  </div>
                  <div className="mt-2 grid gap-1 rounded-xl bg-slate-200 p-3 text-slate-800 ring-1 ring-slate-300 dark:bg-slate-950/30 dark:text-slate-200 dark:ring-white/10">
                    <div>Опоздал: {a.metrics.late ? `да (-${a.metrics.late_penalty_percent}%)` : 'нет'}</div>
                    <div>Ушёл раньше: {a.metrics.early_leave ? `да (-${a.metrics.early_leave_penalty_percent}%)` : 'нет'}</div>
                  </div>
                </div>
              </div>

              <div className="lg:col-span-3 border-t border-slate-200 pt-3 dark:border-white/10">
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Скриншоты за выбранный день (по времени на сервере)
                </div>
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                  {(ssByUser[a.user_id] || []).length === 0 ? (
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      Нет загрузок за этот день или устройство не привязано к пользователю.
                    </div>
                  ) : (
                    (ssByUser[a.user_id] || []).map((s) => (
                      <button
                        key={s.media_file_id}
                        type="button"
                        onClick={() => setShotModal({ userId: a.user_id, item: s })}
                        className="w-28 shrink-0 overflow-hidden rounded-xl ring-1 ring-slate-300 hover:ring-fuchsia-400/50 dark:ring-white/10 dark:hover:ring-fuchsia-400/40"
                      >
                        <AuthenticatedImage
                          mediaId={s.media_file_id}
                          className="h-20 w-full object-cover object-top"
                          alt=""
                        />
                        <div className="bg-white px-1 py-1 text-[10px] text-slate-700 dark:bg-slate-950/80 dark:text-slate-200">
                          {new Date(s.created_at).toLocaleTimeString('ru-RU', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                          {s.productive_score != null ? (
                            <span className="ml-1 font-mono font-semibold">· {s.productive_score}</span>
                          ) : s.error_text ? (
                            <span className="ml-1 text-rose-600 dark:text-rose-300">· err</span>
                          ) : (
                            <span className="ml-1 text-slate-400">· …</span>
                          )}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {periodStats?.month && periodStats?.year ? (
          <div className="mt-6 rounded-3xl bg-slate-100 p-5 ring-1 ring-slate-200 dark:bg-slate-950/25 dark:ring-white/10">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">Показатели за период</div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              {['month', 'year'].map((k) => (
                <div key={k} className="rounded-2xl bg-white p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {k === 'month' ? 'Месяц' : 'Год'}
                  </div>
                  <div className="mt-3 grid gap-2 text-xs text-slate-700 dark:text-slate-200">
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200 dark:bg-white/10 dark:ring-white/15">
                        Рабочих дней: {periodStats[k].working_days}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200 dark:bg-white/10 dark:ring-white/15">
                        Выходных: {periodStats[k].weekend_days}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200 dark:bg-white/10 dark:ring-white/15">
                        Праздник/выходной: {periodStats[k].holiday_days}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-950 ring-1 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:ring-emerald-400/30">
                        Хороших: {periodStats[k].good_days}
                      </span>
                      <span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-950 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:ring-amber-400/30">
                        Средних: {periodStats[k].medium_days}
                      </span>
                      <span className="rounded-full bg-rose-500/10 px-2 py-1 text-rose-950 ring-1 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-200 dark:ring-rose-400/30">
                        Плохих: {periodStats[k].bad_days}
                      </span>
                      <span className="rounded-full bg-sky-500/10 px-2 py-1 text-sky-950 ring-1 ring-sky-200 dark:bg-sky-500/15 dark:text-sky-200 dark:ring-sky-400/30">
                        Отсутствий: {periodStats[k].absence_days}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {shotModal ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 dark:bg-black/70"
          onClick={() => setShotModal(null)}
          role="presentation"
        >
          <div
            className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-4 ring-1 ring-slate-200 dark:bg-slate-950 dark:ring-white/10"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-semibold text-slate-900 dark:text-white">Скриншот</div>
              <button
                type="button"
                onClick={() => setShotModal(null)}
                className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-800 ring-1 ring-slate-200 hover:bg-slate-200 dark:bg-white/10 dark:font-normal dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
              >
                Закрыть
              </button>
            </div>
            <AuthenticatedImage
              mediaId={shotModal.item.media_file_id}
              className="mt-3 max-h-[65vh] w-full rounded-xl object-contain ring-1 ring-slate-200 dark:ring-white/10"
              alt="Скриншот"
            />
            <div className="mt-3 grid gap-2 text-xs text-slate-700 dark:text-slate-200">
              <div className="font-mono text-slate-500 dark:text-slate-400">{shotModal.item.media_file_id}</div>
              {shotModal.item.productive_score != null ? (
                <div>
                  Балл:{' '}
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {shotModal.item.productive_score}
                  </span>
                  {shotModal.item.unproductive != null ? (
                    <span className="ml-2">
                      Непродуктивно: {shotModal.item.unproductive ? 'да' : 'нет'}
                    </span>
                  ) : null}
                </div>
              ) : null}
              {shotModal.item.evidence_ru ? (
                <div className="rounded-xl bg-slate-100 p-3 text-slate-800 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-200 dark:ring-white/10">
                  {shotModal.item.evidence_ru}
                </div>
              ) : null}
              {shotModal.item.error_text ? (
                <div className="rounded-xl bg-rose-50 p-3 text-rose-800 ring-1 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-100 dark:ring-rose-400/30">
                  {shotModal.item.error_text}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

