import React, { createContext, useState, useContext, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      // Можно добавить запрос для получения информации о пользователе
    } else {
      delete axios.defaults.headers.common['Authorization']
    }
    setLoading(false)
  }, [token])

  const login = async (login, password) => {
    try {
      const response = await axios.post('/api/v1/auth/token', {
        login,
        password
      })
      const newToken = response.data.access_token
      setToken(newToken)
      localStorage.setItem('token', newToken)
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Ошибка входа'
      }
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
  }

  const value = {
    user,
    token,
    login,
    logout,
    loading,
    isAuthenticated: !!token
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

