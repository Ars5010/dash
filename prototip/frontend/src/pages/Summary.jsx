import React, { useState, useEffect } from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import axios from 'axios'
import './Summary.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const Summary = () => {
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  )
  const [endDate, setEndDate] = useState(
    new Date().toISOString().split('T')[0]
  )
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchData = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get('/api/v1/summary/histogram', {
        params: { start_date: startDate, end_date: endDate }
      })
      setData(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    fetchData()
  }

  const chartData = data
    ? {
        labels: data.labels,
        datasets: data.datasets.map((dataset) => ({
          label: dataset.label,
          data: dataset.data.map((seconds) => seconds / 3600), // Конвертация в часы
          backgroundColor: dataset.color,
          borderColor: dataset.color,
          borderWidth: 1
        }))
      }
    : null

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top'
      },
      title: {
        display: true,
        text: 'Активность по дням (часы)'
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)} ч`
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Часы'
        }
      }
    }
  }

  return (
    <div className="summary">
      <h1>Сводка активности</h1>
      <div className="card">
        <form onSubmit={handleSubmit} className="date-range-form">
          <div className="form-group">
            <label>Начальная дата</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Конечная дата</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
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
          <Bar data={chartData} options={chartOptions} />
        </div>
      )}
    </div>
  )
}

export default Summary

