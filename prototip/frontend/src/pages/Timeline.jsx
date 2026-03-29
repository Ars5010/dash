import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './Timeline.css'

const Timeline = () => {
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  )
  const [users, setUsers] = useState([])
  const [selectedUserIds, setSelectedUserIds] = useState([])
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [userQuery, setUserQuery] = useState('')
  const [periodStats, setPeriodStats] = useState(null)

  useEffect(() => {
    fetchUsers()
  }, [])

  useEffect(() => {
    if (selectedUserIds.length > 0) {
      fetchActivities()
      fetchPeriodStats()
    } else {
      setActivities([])
      setPeriodStats(null)
    }
  }, [selectedDate, selectedUserIds])

  const fetchUsers = async () => {
    try {
      const response = await axios.get('/api/v1/timeline/users', {
        params: { q: userQuery || undefined }
      })
      setUsers(
        (response.data || []).map((u) => ({ id: u.user_id, name: u.display_name }))
      )
    } catch (err) {
      console.error('Ошибка загрузки пользователей:', err)
    }
  }

  const fetchActivities = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get('/api/v1/timeline/user-activity', {
        params: {
          date: selectedDate,
          user_ids: selectedUserIds
        }
      })
      setActivities(response.data.activities || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  const fetchPeriodStats = async () => {
    try {
      // Для периода показываем статистику по первому выбранному пользователю
      const userId = selectedUserIds[0]
      if (!userId) return
      const response = await axios.get('/api/v1/timeline/period-stats', {
        params: { user_id: userId, date: selectedDate }
      })
      setPeriodStats(response.data)
    } catch (err) {
      // статистика — второстепенная, не блокируем основной UI
      console.error('Ошибка загрузки статистики периода:', err)
    }
  }

  const toggleUser = (userId) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    )
  }

  const getSegmentColor = (type) => {
    switch (type) {
      case 'Active':
        return '#28a745'
      case 'Away':
        return '#dc3545'
      case 'Session Locked':
      case 'Power Off':
        return '#ffc107'
      case 'Productive':
        return '#fd7e14'
      default:
        return '#6c757d'
    }
  }

  const formatTime = (isoString) => {
    return new Date(isoString).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const calculatePosition = (start, dayStart, dayEnd) => {
    const startTime = new Date(start).getTime()
    const dayStartTime = new Date(dayStart).getTime()
    const dayEndTime = new Date(dayEnd).getTime()
    const totalDuration = dayEndTime - dayStartTime
    const position = ((startTime - dayStartTime) / totalDuration) * 100
    return Math.max(0, Math.min(100, position))
  }

  const calculateWidth = (start, end, dayStart, dayEnd) => {
    const startTime = new Date(start).getTime()
    const endTime = new Date(end).getTime()
    const dayStartTime = new Date(dayStart).getTime()
    const dayEndTime = new Date(dayEnd).getTime()
    const totalDuration = dayEndTime - dayStartTime
    const segmentDuration = endTime - startTime
    const width = (segmentDuration / totalDuration) * 100
    return Math.max(1, Math.min(100, width))
  }

  const dayStart = new Date(`${selectedDate}T00:00:00`)
  const dayEnd = new Date(`${selectedDate}T23:59:59`)

  const formatMinutes = (m) => {
    if (m == null) return '—'
    const h = Math.floor(m / 60)
    const mm = m % 60
    return h > 0 ? `${h}ч ${mm}м` : `${mm}м`
  }

  const indicatorLabel = (indicator) => {
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

  return (
    <div className="timeline">
      <h1>Хронология активности</h1>

      <div className="card">
        <div className="form-group">
          <label>Дата</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Пользователи</label>
          <input
            type="text"
            placeholder="Поиск по имени…"
            value={userQuery}
            onChange={(e) => setUserQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') fetchUsers()
            }}
          />
          <button type="button" className="btn" onClick={fetchUsers}>
            Обновить список
          </button>
          <div className="user-checklist">
            {users.map((user) => (
              <label key={user.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedUserIds.includes(user.id)}
                  onChange={() => toggleUser(user.id)}
                />
                {user.name}
              </label>
            ))}
            {users.length === 0 && (
              <p className="text-muted">
                Выберите дату и загрузите данные для отображения пользователей
              </p>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error card">{error}</div>}

      {loading && <div className="card">Загрузка...</div>}

      {activities.length > 0 && (
        <div className="card">
          <h2>Активность за {selectedDate}</h2>
          <div className="timeline-container">
            {activities.map((activity) => (
              <div key={activity.user_id} className="timeline-row">
                <div className="timeline-label">{activity.display_name}</div>
                <div className="timeline-ruler">
                  {activity.segments.map((segment, idx) => {
                    const left = calculatePosition(
                      segment.start,
                      dayStart.toISOString(),
                      dayEnd.toISOString()
                    )
                    const width = calculateWidth(
                      segment.start,
                      segment.end,
                      dayStart.toISOString(),
                      dayEnd.toISOString()
                    )
                    return (
                      <div
                        key={idx}
                        className="timeline-segment"
                        style={{
                          left: `${left}%`,
                          width: `${width}%`,
                          backgroundColor: getSegmentColor(segment.type),
                          title: `${segment.type}: ${formatTime(
                            segment.start
                          )} - ${formatTime(segment.end)}`
                        }}
                      />
                    )
                  })}
                </div>
                {activity.metrics && (
                  <div
                    className={`timeline-metrics timeline-metrics--${activity.metrics.indicator}`}
                    title={`KPI: ${activity.metrics.kpi_percent}%`}
                  >
                    <div className="timeline-metrics__kpi">
                      <div className="timeline-metrics__kpiValue">
                        {activity.metrics.kpi_percent}%
                      </div>
                      <div className="timeline-metrics__kpiLabel">
                        {indicatorLabel(activity.metrics.indicator)}
                      </div>
                    </div>

                    <div className="timeline-metrics__grid">
                      <div>
                        Активное: {formatMinutes(activity.metrics.active_minutes)} (
                        {activity.metrics.active_percent}%)
                      </div>
                      <div>
                        Неактивное: {formatMinutes(activity.metrics.inactive_minutes)} (
                        {activity.metrics.inactive_percent}%)
                      </div>
                      <div>
                        Продуктивное: {formatMinutes(activity.metrics.productive_minutes)} (
                        {activity.metrics.productive_percent}%)
                      </div>
                      <div>
                        Непродуктивное: {formatMinutes(activity.metrics.unproductive_minutes)} (
                        {activity.metrics.unproductive_percent}%)
                      </div>
                    </div>

                    <div className="timeline-metrics__penalties">
                      <div>
                        Опоздал:{' '}
                        {activity.metrics.late
                          ? `да (-${activity.metrics.late_penalty_percent}%)`
                          : 'нет'}
                      </div>
                      <div>
                        Ушёл раньше:{' '}
                        {activity.metrics.early_leave
                          ? `да (-${activity.metrics.early_leave_penalty_percent}%)`
                          : 'нет'}
                      </div>
                      <div className="timeline-metrics__fine">
                        Штраф за день: {activity.metrics.day_fine}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="timeline-legend">
            <div className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: '#28a745' }}
              />
              Активный
            </div>
            <div className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: '#dc3545' }}
              />
              Неактивный
            </div>
            <div className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: '#ffc107' }}
              />
              Не у ПК
            </div>
            <div className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: '#fd7e14' }}
              />
              Продуктивность
            </div>
          </div>
        </div>
      )}

      {periodStats?.month && periodStats?.year && (
        <div className="card">
          <h2>Показатели за период</h2>
          <div className="period-stats">
            <div className="period-stats__block">
              <h3>Месяц</h3>
              <div className="period-stats__row">
                <span className="badge badge-gray">
                  Рабочих дней: {periodStats.month.working_days}
                </span>
                <span className="badge badge-gray">
                  Выходных: {periodStats.month.weekend_days}
                </span>
                <span className="badge badge-gray">
                  Праздников/выходных (в календаре): {periodStats.month.holiday_days}
                </span>
              </div>
              <div className="period-stats__row">
                <span className="badge badge-green">
                  Хороших: {periodStats.month.good_days}
                </span>
                <span className="badge badge-yellow">
                  Средних: {periodStats.month.medium_days}
                </span>
                <span className="badge badge-red">Плохих: {periodStats.month.bad_days}</span>
                <span className="badge badge-blue">
                  Отсутствий: {periodStats.month.absence_days}
                </span>
              </div>
            </div>

            <div className="period-stats__block">
              <h3>Год</h3>
              <div className="period-stats__row">
                <span className="badge badge-gray">
                  Рабочих дней: {periodStats.year.working_days}
                </span>
                <span className="badge badge-gray">
                  Выходных: {periodStats.year.weekend_days}
                </span>
                <span className="badge badge-gray">
                  Праздников/выходных (в календаре): {periodStats.year.holiday_days}
                </span>
              </div>
              <div className="period-stats__row">
                <span className="badge badge-green">
                  Хороших: {periodStats.year.good_days}
                </span>
                <span className="badge badge-yellow">
                  Средних: {periodStats.year.medium_days}
                </span>
                <span className="badge badge-red">Плохих: {periodStats.year.bad_days}</span>
                <span className="badge badge-blue">
                  Отсутствий: {periodStats.year.absence_days}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Timeline

