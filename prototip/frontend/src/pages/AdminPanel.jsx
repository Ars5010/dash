import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './AdminPanel.css'

const AdminPanel = () => {
  const [users, setUsers] = useState([])
  const [config, setConfig] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showUserModal, setShowUserModal] = useState(false)
  const [newUser, setNewUser] = useState({
    login: '',
    password: '',
    role_id: 2
  })
  const [roles, setRoles] = useState([
    { id: 1, name: 'Admin' },
    { id: 2, name: 'User' }
  ])

  useEffect(() => {
    fetchUsers()
    fetchConfig()
  }, [])

  const fetchUsers = async () => {
    try {
      const response = await axios.get('/api/v1/admin/users')
      setUsers(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки пользователей')
    }
  }

  const fetchConfig = async () => {
    try {
      const response = await axios.get('/api/v1/admin/config')
      setConfig(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки конфигурации')
    }
  }

  const handleCreateUser = async () => {
    if (!newUser.login || !newUser.password) {
      setError('Заполните все поля')
      return
    }

    setLoading(true)
    setError('')
    try {
      await axios.post('/api/v1/admin/users', newUser)
      setSuccess('Пользователь успешно создан')
      setShowUserModal(false)
      setNewUser({ login: '', password: '', role_id: 2 })
      fetchUsers()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка создания пользователя')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateConfig = async (key, value) => {
    setLoading(true)
    setError('')
    try {
      await axios.put('/api/v1/admin/config', { key, value })
      setSuccess('Конфигурация обновлена')
      fetchConfig()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка обновления конфигурации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-panel">
      <h1>Панель администратора</h1>

      {error && (
        <div className="error card" onClick={() => setError('')}>
          {error}
        </div>
      )}
      {success && (
        <div className="success card" onClick={() => setSuccess('')}>
          {success}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>Пользователи</h2>
          <button
            className="btn btn-primary"
            onClick={() => setShowUserModal(true)}
          >
            Создать пользователя
          </button>
        </div>
        <table className="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Логин</th>
              <th>Роль</th>
              <th>Статус</th>
              <th>Создан</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.login}</td>
                <td>{user.role_name}</td>
                <td>{user.is_active ? 'Активен' : 'Неактивен'}</td>
                <td>
                  {new Date(user.created_at).toLocaleDateString('ru-RU')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Конфигурация подключения к ManicTime</h2>
        <p className="config-description">
          Здесь можно изменить нечувствительные параметры подключения к базе
          данных ManicTime. Пароль и пользователь настраиваются только через
          переменные окружения на сервере.
        </p>
        <div className="config-list">
          {config.map((item) => (
            <div key={item.key} className="config-item">
              <label>{item.key.replace('manictime_', '').toUpperCase()}</label>
              <input
                type="text"
                value={item.value || ''}
                onChange={(e) =>
                  handleUpdateConfig(item.key, e.target.value)
                }
                placeholder="Не задано"
              />
            </div>
          ))}
        </div>
      </div>

      {showUserModal && (
        <div className="modal-overlay" onClick={() => setShowUserModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Создать пользователя</h2>
            <div className="form-group">
              <label>Логин</label>
              <input
                type="text"
                value={newUser.login}
                onChange={(e) =>
                  setNewUser({ ...newUser, login: e.target.value })
                }
                required
              />
            </div>
            <div className="form-group">
              <label>Пароль</label>
              <input
                type="password"
                value={newUser.password}
                onChange={(e) =>
                  setNewUser({ ...newUser, password: e.target.value })
                }
                required
              />
            </div>
            <div className="form-group">
              <label>Роль</label>
              <select
                value={newUser.role_id}
                onChange={(e) =>
                  setNewUser({
                    ...newUser,
                    role_id: parseInt(e.target.value)
                  })
                }
              >
                {roles.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowUserModal(false)}
              >
                Отмена
              </button>
              <button
                className="btn btn-primary"
                onClick={handleCreateUser}
                disabled={loading}
              >
                {loading ? 'Создание...' : 'Создать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminPanel

