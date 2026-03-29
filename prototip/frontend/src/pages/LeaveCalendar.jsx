import React, { useState, useEffect } from 'react'
import { Calendar, momentLocalizer } from 'react-big-calendar'
import moment from 'moment'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import axios from 'axios'
import './LeaveCalendar.css'

const localizer = momentLocalizer(moment)

const LeaveCalendar = () => {
  const absenceTypes = [
    'Отпуск',
    'Больничный',
    'Праздник',
    'Выходной',
    'Прогул',
    'Отгул'
  ]

  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [selectedRange, setSelectedRange] = useState(null)
  const [newEvent, setNewEvent] = useState({
    user_id: '',
    start_date: '',
    end_date: '',
    leave_type: 'Отпуск'
  })
  const [users, setUsers] = useState([])

  useEffect(() => {
    const currentDate = new Date()
    const startDate = new Date(currentDate.getFullYear(), 0, 1)
    const endDate = new Date(currentDate.getFullYear(), 11, 31)
    fetchEvents(startDate, endDate)
    fetchUsers()
  }, [])

  const fetchEvents = async (startDate, endDate) => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get('/api/v1/leave/events', {
        params: {
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString()
        }
      })
      const formattedEvents = response.data.map((event) => ({
        id: event.id,
        title: `${event.user_login || `User ${event.user_id}`} - ${event.leave_type}`,
        start: new Date(event.start_date),
        end: new Date(event.end_date),
        resource: event
      }))
      setEvents(formattedEvents)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  const fetchUsers = async () => {
    try {
      const response = await axios.get('/api/v1/admin/users')
      setUsers(response.data)
    } catch (err) {
      console.error('Ошибка загрузки пользователей:', err)
    }
  }

  const handleSelectSlot = ({ start, end }) => {
    setSelectedRange({ start, end })
    setNewEvent({
      user_id: '',
      start_date: start.toISOString().slice(0, 16),
      end_date: end.toISOString().slice(0, 16),
      leave_type: 'Отпуск'
    })
    setShowModal(true)
  }

  const handleCreateEvent = async () => {
    if (!newEvent.user_id || !newEvent.start_date || !newEvent.end_date) {
      setError('Заполните все поля')
      return
    }

    try {
      await axios.post('/api/v1/leave/events', {
        user_id: parseInt(newEvent.user_id),
        start_date: new Date(newEvent.start_date).toISOString(),
        end_date: new Date(newEvent.end_date).toISOString(),
        leave_type: newEvent.leave_type
      })
      setShowModal(false)
      const startDate = new Date(newEvent.start_date)
      const endDate = new Date(newEvent.end_date)
      fetchEvents(
        new Date(startDate.getFullYear(), 0, 1),
        new Date(endDate.getFullYear(), 11, 31)
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка создания события')
    }
  }

  const eventStyleGetter = (event) => {
    const leaveType = event.resource?.leave_type
    let backgroundColor = '#007bff' // default blue
    if (leaveType === 'Праздник' || leaveType === 'Выходной') {
      backgroundColor = '#6c757d' // gray
    } else if (leaveType === 'Прогул') {
      backgroundColor = '#dc3545' // red
    } else {
      // Отпуск/Больничный/Отгул: blue
      backgroundColor = '#007bff'
    }
    return {
      style: {
        backgroundColor,
        borderRadius: '5px',
        opacity: 0.8,
        color: 'white',
        border: '0px',
        display: 'block'
      }
    }
  }

  return (
    <div className="leave-calendar">
      <h1>Отсутствие</h1>

      {error && <div className="error card">{error}</div>}

      <div className="card" style={{ height: '600px' }}>
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          onSelectSlot={handleSelectSlot}
          selectable
          eventPropGetter={eventStyleGetter}
          culture="ru"
          messages={{
            next: 'Вперед',
            previous: 'Назад',
            today: 'Сегодня',
            month: 'Месяц',
            week: 'Неделя',
            day: 'День',
            agenda: 'Повестка дня',
            date: 'Дата',
            time: 'Время',
            event: 'Событие',
            noEventsInRange: 'Нет событий в выбранном диапазоне'
          }}
        />
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Добавить событие</h2>
            <div className="form-group">
              <label>Пользователь</label>
              <select
                value={newEvent.user_id}
                onChange={(e) =>
                  setNewEvent({ ...newEvent, user_id: e.target.value })
                }
                required
              >
                <option value="">Выберите пользователя</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.login}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Начало</label>
              <input
                type="datetime-local"
                value={newEvent.start_date}
                onChange={(e) =>
                  setNewEvent({ ...newEvent, start_date: e.target.value })
                }
                required
              />
            </div>
            <div className="form-group">
              <label>Конец</label>
              <input
                type="datetime-local"
                value={newEvent.end_date}
                onChange={(e) =>
                  setNewEvent({ ...newEvent, end_date: e.target.value })
                }
                required
              />
            </div>
            <div className="form-group">
              <label>Тип отсутствия</label>
              <select
                value={newEvent.leave_type}
                onChange={(e) =>
                  setNewEvent({ ...newEvent, leave_type: e.target.value })
                }
              >
                {absenceTypes.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowModal(false)}
              >
                Отмена
              </button>
              <button
                className="btn btn-primary"
                onClick={handleCreateEvent}
              >
                Создать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LeaveCalendar

