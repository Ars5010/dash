import { useEffect, useMemo, useState } from 'react'
import { Calendar, momentLocalizer } from 'react-big-calendar'
import moment from 'moment'
import { api } from '../lib/api'
import 'react-big-calendar/lib/css/react-big-calendar.css'

const localizer = momentLocalizer(moment)

const absenceTypes = [
  { key: 'Отпуск', color: '#3b82f6' },
  { key: 'Больничный', color: '#3b82f6' },
  { key: 'Отгул', color: '#3b82f6' },
  { key: 'Праздник', color: '#64748b' },
  { key: 'Выходной', color: '#64748b' },
  { key: 'Прогул', color: '#ef4444' },
]

export default function AbsencePage() {
  const [events, setEvents] = useState([])
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [range, setRange] = useState(null)
  const [selected, setSelected] = useState(null) // calendar event
  const [form, setForm] = useState({
    user_id: '',
    start_at: '',
    end_at: '',
    absence_type: 'Отпуск',
  })

  const colorMap = useMemo(() => {
    const m = new Map()
    absenceTypes.forEach((t) => m.set(t.key, t.color))
    return m
  }, [])

  async function fetchUsers() {
    const resp = await api.get('/v1/admin/users')
    setUsers(resp.data || [])
  }

  async function fetchEvents(start, end) {
    const resp = await api.get('/v1/absence/events', {
      params: { start_at: start.toISOString(), end_at: end.toISOString() },
    })
    const formatted = (resp.data || []).map((e) => ({
      id: e.id,
      title: `${e.user_full_name || e.user_login || `User ${e.user_id}`} · ${e.absence_type}`,
      start: new Date(e.start_at),
      end: new Date(e.end_at),
      resource: e,
    }))
    setEvents(formatted)
  }

  useEffect(() => {
    const now = new Date()
    const start = new Date(now.getFullYear(), 0, 1)
    const end = new Date(now.getFullYear(), 11, 31, 23, 59, 59)
    fetchEvents(start, end).catch(() => setError('Ошибка загрузки отсутствий'))
    fetchUsers().catch(() => {})
  }, [])

  function onSelectSlot({ start, end }) {
    setSelected(null)
    setRange({ start, end })
    setForm({
      user_id: '',
      start_at: new Date(start).toISOString().slice(0, 16),
      end_at: new Date(end).toISOString().slice(0, 16),
      absence_type: 'Отпуск',
    })
    setShowModal(true)
  }

  function onSelectEvent(ev) {
    setSelected(ev)
    setRange({ start: ev.start, end: ev.end })
    setForm({
      user_id: String(ev?.resource?.user_id || ''),
      start_at: new Date(ev.start).toISOString().slice(0, 16),
      end_at: new Date(ev.end).toISOString().slice(0, 16),
      absence_type: ev?.resource?.absence_type || 'Отпуск',
    })
    setShowModal(true)
  }

  async function createEvent() {
    setError('')
    if (!form.user_id || !form.start_at || !form.end_at) {
      setError('Заполните все поля')
      return
    }
    try {
      const payload = {
        user_id: Number(form.user_id),
        start_at: new Date(form.start_at).toISOString(),
        end_at: new Date(form.end_at).toISOString(),
        absence_type: form.absence_type,
      }
      if (selected?.resource?.id) {
        await api.patch(`/v1/absence/events/${selected.resource.id}`, {
          start_at: payload.start_at,
          end_at: payload.end_at,
          absence_type: payload.absence_type,
        })
      } else {
        await api.post('/v1/absence/events', payload)
      }
      setShowModal(false)
      setSelected(null)
      const start = range?.start || new Date()
      const end = range?.end || new Date()
      await fetchEvents(
        new Date(start.getFullYear(), 0, 1),
        new Date(end.getFullYear(), 11, 31, 23, 59, 59)
      )
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка создания события')
    }
  }

  async function deleteEvent() {
    if (!selected?.resource?.id) return
    setError('')
    try {
      await api.delete(`/v1/absence/events/${selected.resource.id}`)
      setShowModal(false)
      const start = range?.start || new Date()
      const end = range?.end || new Date()
      await fetchEvents(
        new Date(start.getFullYear(), 0, 1),
        new Date(end.getFullYear(), 11, 31, 23, 59, 59)
      )
    } catch (e) {
      setError(e?.response?.data?.detail || 'Ошибка удаления события')
    } finally {
      setSelected(null)
    }
  }

  function eventPropGetter(event) {
    const t = event?.resource?.absence_type
    const c = colorMap.get(t) || '#3b82f6'
    return {
      style: {
        backgroundColor: c,
        borderRadius: '10px',
        border: '0px',
        opacity: 0.95,
        color: 'white',
        padding: '2px 6px',
      },
    }
  }

  const inputClass =
    'h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10'

  return (
    <div className="grid gap-6">
      <div className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">Отсутствие</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Диапазон выбирается с датой и временем. Типы подсвечиваются (синий/серый/красный).
        </p>
      </div>

      {error ? (
        <div className="rounded-2xl bg-rose-50 p-4 text-sm text-rose-800 ring-1 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-400/30">
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl bg-white p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="h-[72vh] overflow-hidden rounded-2xl bg-slate-50 p-2 text-slate-900 ring-1 ring-slate-200 dark:bg-slate-900/90 dark:text-slate-100 dark:ring-white/10">
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            onSelectSlot={onSelectSlot}
            onSelectEvent={onSelectEvent}
            selectable
            eventPropGetter={eventPropGetter}
            culture="ru"
            messages={{
              next: 'Вперед',
              previous: 'Назад',
              today: 'Сегодня',
              month: 'Месяц',
              week: 'Неделя',
              day: 'День',
              agenda: 'Повестка',
              date: 'Дата',
              time: 'Время',
              event: 'Событие',
              noEventsInRange: 'Нет событий',
            }}
          />
        </div>
      </div>

      {showModal ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 dark:bg-black/60"
          onClick={() => setShowModal(false)}
        >
          <div
            className="w-full max-w-lg rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-slate-950 dark:ring-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-base font-semibold text-slate-900 dark:text-white">
              {selected ? 'Редактировать отсутствие' : 'Добавить отсутствие'}
            </div>
            <div className="mt-4 grid gap-3">
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Пользователь</span>
                <select
                  value={form.user_id}
                  onChange={(e) => setForm((p) => ({ ...p, user_id: e.target.value }))}
                  className={inputClass}
                >
                  <option value="">Выберите пользователя</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name ? `${u.full_name} (${u.login})` : u.login}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Начало</span>
                  <input
                    type="datetime-local"
                    value={form.start_at}
                    onChange={(e) => setForm((p) => ({ ...p, start_at: e.target.value }))}
                    className={inputClass}
                  />
                </label>
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Конец</span>
                  <input
                    type="datetime-local"
                    value={form.end_at}
                    onChange={(e) => setForm((p) => ({ ...p, end_at: e.target.value }))}
                    className={inputClass}
                  />
                </label>
              </div>

              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Тип</span>
                <select
                  value={form.absence_type}
                  onChange={(e) => setForm((p) => ({ ...p, absence_type: e.target.value }))}
                  className={inputClass}
                >
                  {absenceTypes.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.key}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              {selected ? (
                <button
                  onClick={deleteEvent}
                  className="mr-auto h-10 rounded-xl bg-rose-50 px-4 text-sm font-semibold text-rose-700 ring-1 ring-rose-200 hover:bg-rose-100 dark:bg-rose-500/15 dark:text-rose-100 dark:ring-rose-400/30 dark:hover:bg-rose-500/20"
                >
                  Удалить
                </button>
              ) : null}
              <button
                onClick={() => {
                  setShowModal(false)
                  setSelected(null)
                }}
                className="h-10 rounded-xl bg-slate-100 px-4 text-sm font-semibold text-slate-800 ring-1 ring-slate-200 hover:bg-slate-200 dark:bg-white/10 dark:font-normal dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
              >
                Отмена
              </button>
              <button
                onClick={createEvent}
                className="h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400"
              >
                {selected ? 'Сохранить' : 'Создать'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

