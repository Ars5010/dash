import React from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import axios from 'axios'
import './Layout.css'

const Layout = () => {
  const { logout, user } = useAuth()
  const location = useLocation()
  const [manicTimeUrl, setManicTimeUrl] = React.useState(null)

  const isActive = (path) => location.pathname === path

  React.useEffect(() => {
    const load = async () => {
      try {
        const response = await axios.get('/api/v1/admin/config')
        const items = response.data || []
        const web = items.find((i) => i.key === 'manictime_web_url')?.value
        setManicTimeUrl(web || null)
      } catch (e) {
        // не критично
      }
    }
    load()
  }, [])

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="navbar-brand">
          <h2>ManicTime Dashboard</h2>
          {manicTimeUrl && (
            <a
              className="nav-link"
              href={manicTimeUrl}
              target="_blank"
              rel="noreferrer"
              style={{ marginLeft: 12 }}
            >
              ManicTime
            </a>
          )}
        </div>
        <div className="navbar-menu">
          <Link
            to="/summary"
            className={`nav-link ${isActive('/summary') ? 'active' : ''}`}
          >
            Сводка
          </Link>
          <Link
            to="/timeline"
            className={`nav-link ${isActive('/timeline') ? 'active' : ''}`}
          >
            Хронология
          </Link>
          <Link
            to="/metrics"
            className={`nav-link ${isActive('/metrics') ? 'active' : ''}`}
          >
            Метрика
          </Link>
          <Link
            to="/leave"
            className={`nav-link ${isActive('/leave') ? 'active' : ''}`}
          >
            Отсутствие
          </Link>
          <Link
            to="/admin"
            className={`nav-link ${isActive('/admin') ? 'active' : ''}`}
          >
            Администрирование
          </Link>
        </div>
        <div className="navbar-actions">
          <span className="user-info">{user?.login || 'Пользователь'}</span>
          <button onClick={logout} className="btn btn-secondary">
            Выход
          </button>
        </div>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout

