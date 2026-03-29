import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './Metrics.css'

const Metrics = () => {
  const [period, setPeriod] = useState('quarter')
  const [year, setYear] = useState(new Date().getFullYear())
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchData()
  }, [period, year])

  const fetchData = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get('/api/v1/metrics/aggregate', {
        params: { period, year }
      })
      setData(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  const getPeriodLabel = (key) => {
    if (period === 'week') {
      return `Неделя ${key.replace('W', '')}`
    } else if (period === 'month') {
      const months = [
        'Январь',
        'Февраль',
        'Март',
        'Апрель',
        'Май',
        'Июнь',
        'Июль',
        'Август',
        'Сентябрь',
        'Октябрь',
        'Ноябрь',
        'Декабрь'
      ]
      return months[parseInt(key.replace('M', '')) - 1]
    } else if (period === 'quarter') {
      return `Квартал ${key.replace('Q', '')}`
    } else {
      return 'Год'
    }
  }

  const getAllPeriodKeys = () => {
    if (!data || !data.data || data.data.length === 0) return []
    const allKeys = new Set()
    data.data.forEach((row) => {
      Object.keys(row.data).forEach((key) => allKeys.add(key))
    })
    return Array.from(allKeys).sort()
  }

  return (
    <div className="metrics">
      <h1>Метрики эффективности</h1>

      <div className="card">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            fetchData()
          }}
          className="metrics-controls"
        >
          <div className="form-group">
            <label>Период</label>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="week">Неделя</option>
              <option value="month">Месяц</option>
              <option value="quarter">Квартал</option>
              <option value="year">Год</option>
            </select>
          </div>
          <div className="form-group">
            <label>Год</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(parseInt(e.target.value))}
              min="2000"
              max="2100"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Загрузка...' : 'Обновить'}
          </button>
        </form>
      </div>

      {error && <div className="error card">{error}</div>}

      {data && !loading && (
        <div className="card">
          <h2>
            Агрегированные метрики за {year} год ({period === 'week' ? 'по неделям' : period === 'month' ? 'по месяцам' : period === 'quarter' ? 'по кварталам' : 'за год'})
          </h2>
          <div className="table-container">
            <table className="metrics-table">
              <thead>
                <tr>
                  <th>Пользователь</th>
                  {getAllPeriodKeys().map((key) => (
                    <th key={key}>{getPeriodLabel(key)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.data.map((row, idx) => (
                  <tr key={idx}>
                    <td className="user-name">{row.user}</td>
                    {getAllPeriodKeys().map((key) => (
                      <td key={key}>
                        {row.data[key] ? `${row.data[key]} ч` : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default Metrics

