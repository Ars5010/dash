import React from 'react'
import { Link } from 'react-router-dom'
import './Dashboard.css'

const Dashboard = () => {
  return (
    <div className="dashboard">
      <h1>Главная панель</h1>
      <div className="dashboard-grid">
        <Link to="/summary" className="dashboard-card">
          <h3>Сводка</h3>
          <p>Агрегированная гистограмма активности по категориям</p>
        </Link>
        <Link to="/timeline" className="dashboard-card">
          <h3>Хронология</h3>
          <p>Индивидуальные линейки активности пользователей</p>
        </Link>
        <Link to="/metrics" className="dashboard-card">
          <h3>Метрика</h3>
          <p>Числовые показатели эффективности в динамике</p>
        </Link>
        <Link to="/leave" className="dashboard-card">
          <h3>Отсутствие</h3>
          <p>Календарь отсутствий сотрудников</p>
        </Link>
      </div>
    </div>
  )
}

export default Dashboard

