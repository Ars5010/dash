import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'

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
      return indicator || '—'
  }
}

function rowClass(indicator) {
  switch (indicator) {
    case 'green':
      return 'bg-emerald-500/10 text-emerald-900 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:ring-emerald-400/30'
    case 'yellow':
      return 'bg-amber-500/10 text-amber-950 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:ring-amber-400/30'
    case 'red':
      return 'bg-rose-500/10 text-rose-950 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-200 dark:ring-rose-400/30'
    case 'blue':
      return 'bg-sky-500/10 text-sky-950 ring-sky-200 dark:bg-sky-500/15 dark:text-sky-200 dark:ring-sky-400/30'
    default:
      return 'bg-slate-100 text-slate-800 ring-slate-200 dark:bg-white/10 dark:text-slate-200 dark:ring-white/15'
  }
}

export default function EmployeeProfilePage() {
  const { userId } = useParams()
  const id = Number(userId)
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError('Некорректный ID')
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    api
      .get('/v1/timeline/user-profile', { params: { user_id: id, days: 14 } })
      .then((r) => setProfile(r.data))
      .catch((e) => {
        setError(e?.response?.data?.detail || 'Не удалось загрузить профиль')
        setProfile(null)
      })
      .finally(() => setLoading(false))
  }, [id])

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            to="/timeline"
            className="text-xs font-semibold text-fuchsia-600 hover:text-fuchsia-500 dark:text-fuchsia-400"
          >
            ← Хронология
          </Link>
          <h1 className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
            {loading ? 'Загрузка…' : profile ? profile.full_name || profile.login : 'Сотрудник'}
          </h1>
          {profile ? (
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              @{profile.login}
              {profile.job_title ? ` · ${profile.job_title}` : ''}
              {profile.is_active ? '' : ' · неактивен'}
            </p>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200 ring-1 ring-rose-400/30">{error}</div>
      ) : null}

      {profile ? (
        <>
          <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Продуктивность по дням</h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Последние 14 дней (UTC, как в хронологии): KPI и индикатор дня.
            </p>
            <div className="mt-4 overflow-auto rounded-2xl ring-1 ring-slate-200 dark:ring-white/10">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600 dark:bg-white/5 dark:text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Дата</th>
                    <th className="px-3 py-2">KPI</th>
                    <th className="px-3 py-2">Индикатор</th>
                    <th className="px-3 py-2">Штраф дня</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-white/5">
                  {profile.recent_days.map((row) => (
                    <tr key={row.date}>
                      <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-800 dark:text-slate-200">
                        {row.date}
                      </td>
                      <td className="px-3 py-2 font-semibold">{Math.round(row.kpi_percent)}%</td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs ring-1 ${rowClass(row.indicator)}`}
                        >
                          {indicatorLabel(row.indicator)}
                        </span>
                      </td>
                      <td className="px-3 py-2">{row.day_fine}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Скриншоты и ИИ (30 дней)</h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Сводка по записям анализа скринов за последние 30 дней для этого сотрудника.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-100 p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
                <div className="text-xs text-slate-600 dark:text-slate-400">Разобрано скринов</div>
                <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">
                  {profile.screenshots_analyzed_30d}
                </div>
              </div>
              <div className="rounded-2xl bg-slate-100 p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
                <div className="text-xs text-slate-600 dark:text-slate-400">Средний балл (ИИ)</div>
                <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">
                  {profile.screenshots_avg_score_30d != null
                    ? profile.screenshots_avg_score_30d.toFixed(1)
                    : '—'}
                </div>
              </div>
              <div className="rounded-2xl bg-slate-100 p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
                <div className="text-xs text-slate-600 dark:text-slate-400">Отмечено непродуктивными</div>
                <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">
                  {profile.screenshots_unproductive_30d}
                </div>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  )
}
