import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

export default function HolidaysPage() {
  const { me } = useAuth()
  const nextYear = useMemo(() => new Date().getFullYear() + 1, [])
  const [year, setYear] = useState(nextYear)
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ day: '', kind: 'Праздник', name: '' })
  const [range, setRange] = useState({ start_day: '', end_day: '', kind: 'Праздник', name: '' })

  const isAdmin = (me?.role || '') === 'admin'

  function _toYmd(d) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${dd}`
  }

  function _parseYmd(s) {
    if (!s) return null
    const [y, m, d] = (s || '').split('-').map((x) => Number(x))
    if (!y || !m || !d) return null
    const dt = new Date(Date.UTC(y, m - 1, d))
    if (Number.isNaN(dt.getTime())) return null
    return dt
  }

  function _daysBetweenInclusive(start, end) {
    const one = 24 * 60 * 60 * 1000
    const a = Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate())
    const b = Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate())
    return Math.floor((b - a) / one) + 1
  }

  function _addDaysUtc(dt, days) {
    const ms = dt.getTime() + days * 24 * 60 * 60 * 1000
    return new Date(ms)
  }

  async function fetchYear(y) {
    setLoading(true)
    setError('')
    try {
      const resp = await api.get('/v1/admin/holidays', { params: { year: y } })
      setRows(resp.data || [])
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка загрузки праздников')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdmin) return
    fetchYear(year)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, isAdmin])

  async function generateRf() {
    setLoading(true)
    setError('')
    try {
      await api.post('/v1/admin/holidays/generate-rf', null, { params: { year } })
      await fetchYear(year)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка генерации праздников')
    } finally {
      setLoading(false)
    }
  }

  async function addOne() {
    setError('')
    if (!form.day) {
      setError('Выберите дату')
      return
    }
    setLoading(true)
    try {
      await api.put('/v1/admin/holidays/bulk', [
        { day: form.day, kind: form.kind, name: form.name || null },
      ])
      setForm({ day: '', kind: 'Праздник', name: '' })
      await fetchYear(year)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка добавления')
    } finally {
      setLoading(false)
    }
  }

  async function addRange() {
    setError('')
    const s = _parseYmd(range.start_day)
    const e = _parseYmd(range.end_day)
    if (!s || !e) {
      setError('Выберите даты диапазона')
      return
    }
    if (s.getTime() > e.getTime()) {
      setError('Дата "с" должна быть раньше или равна дате "по"')
      return
    }
    const total = _daysBetweenInclusive(s, e)
    if (total > 400) {
      setError('Слишком большой диапазон (максимум 400 дней за раз)')
      return
    }
    setLoading(true)
    try {
      const payload = []
      for (let i = 0; i < total; i++) {
        const day = _toYmd(_addDaysUtc(s, i))
        payload.push({ day, kind: range.kind, name: range.name || null })
      }
      await api.put('/v1/admin/holidays/bulk', payload)
      setRange({ start_day: '', end_day: '', kind: 'Праздник', name: '' })
      await fetchYear(year)
    } catch (e2) {
      setError(e2?.response?.data?.detail || 'Ошибка добавления диапазона')
    } finally {
      setLoading(false)
    }
  }

  async function remove(day) {
    setLoading(true)
    setError('')
    try {
      await api.delete(`/v1/admin/holidays/${day}`)
      await fetchYear(year)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка удаления')
    } finally {
      setLoading(false)
    }
  }

  if (!isAdmin) {
    return (
      <div className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h1 className="text-lg font-semibold">Праздники</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Доступно только администратору.</p>
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      <div className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">Праздники</h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Заполните календарь на следующий год одним действием и при необходимости поправьте вручную.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="1970"
              max="2100"
              value={year}
              onChange={(e) => setYear(Number(e.target.value || nextYear))}
              className="h-10 w-28 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
            <button
              onClick={generateRf}
              disabled={loading}
              className="h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400 disabled:opacity-60"
            >
              Сгенерировать РФ
            </button>
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200 ring-1 ring-rose-400/30">
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="grid gap-3 md:grid-cols-[180px_180px_1fr_auto]">
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Дата</span>
            <input
              type="date"
              value={form.day}
              onChange={(e) => setForm((p) => ({ ...p, day: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Вид</span>
            <select
              value={form.kind}
              onChange={(e) => setForm((p) => ({ ...p, kind: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            >
              <option value="Праздник">Праздник</option>
              <option value="Выходной">Выходной</option>
            </select>
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Название (опционально)</span>
            <input
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              placeholder="Напр. День России"
            />
          </label>
          <div className="flex items-end">
            <button
              onClick={addOne}
              disabled={loading}
              className="h-10 rounded-xl bg-slate-900/5 px-4 text-sm font-semibold text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
            >
              Добавить
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-slate-900 dark:text-white">Массовое добавление</div>
            <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Добавляет все даты от "с" до "по" включительно.
            </div>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[180px_180px_180px_1fr_auto]">
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">С</span>
            <input
              type="date"
              value={range.start_day}
              onChange={(e) => setRange((p) => ({ ...p, start_day: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">По</span>
            <input
              type="date"
              value={range.end_day}
              onChange={(e) => setRange((p) => ({ ...p, end_day: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Вид</span>
            <select
              value={range.kind}
              onChange={(e) => setRange((p) => ({ ...p, kind: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            >
              <option value="Праздник">Праздник</option>
              <option value="Выходной">Выходной</option>
            </select>
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Название (опционально)</span>
            <input
              value={range.name}
              onChange={(e) => setRange((p) => ({ ...p, name: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              placeholder="Напр. Корпоративный отпуск"
            />
          </label>
          <div className="flex items-end">
            <button
              onClick={addRange}
              disabled={loading}
              className="h-10 rounded-xl bg-slate-900/5 px-4 text-sm font-semibold text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
            >
              Добавить диапазон
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-3xl bg-white p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="overflow-hidden rounded-2xl bg-slate-100 ring-1 ring-slate-200 dark:bg-slate-950/40 dark:ring-white/10">
          <div className="grid grid-cols-[160px_140px_1fr_120px] gap-0 border-b border-slate-200 px-4 py-3 text-xs font-semibold text-slate-600 dark:border-white/10 dark:text-slate-300">
            <div>Дата</div>
            <div>Вид</div>
            <div>Название</div>
            <div className="text-right">Действия</div>
          </div>
          {loading ? (
            <div className="px-4 py-6 text-sm text-slate-600 dark:text-slate-400">Загрузка…</div>
          ) : rows.length ? (
            rows.map((r) => (
              <div
                key={r.day}
                className="grid grid-cols-[160px_140px_1fr_120px] items-center gap-0 border-b border-slate-200 px-4 py-3 text-sm text-slate-900 dark:border-white/5 dark:text-slate-100"
              >
                <div className="font-mono">{r.day}</div>
                <div>{r.kind}</div>
                <div className="text-slate-700 dark:text-slate-300">{r.name || '—'}</div>
                <div className="text-right">
                  <button
                    onClick={() => remove(r.day)}
                    className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white ring-1 ring-rose-200 hover:bg-rose-500 dark:bg-rose-500/15 dark:text-rose-100 dark:ring-rose-400/30 dark:hover:bg-rose-500/20"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="px-4 py-6 text-sm text-slate-600 dark:text-slate-400">
              Нет праздников за {year} год.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

