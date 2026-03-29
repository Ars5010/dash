import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('portal_jwt') || '')
  const [me, setMe] = useState(null)
  const [bootstrapped, setBootstrapped] = useState(null) // null=loading

  async function refreshBootstrapped() {
    const resp = await api.get('/v1/meta/status')
    setBootstrapped(Boolean(resp.data?.bootstrapped))
  }

  async function refreshMe() {
    if (!token) {
      setMe(null)
      return
    }
    const resp = await api.get('/v1/meta/me')
    setMe(resp.data)
  }

  async function login(login, password) {
    const resp = await api.post('/v1/auth/token', { login, password })
    const t = resp.data?.access_token
    localStorage.setItem('portal_jwt', t)
    setToken(t)
    await refreshMe()
  }

  function logout() {
    localStorage.removeItem('portal_jwt')
    setToken('')
    setMe(null)
  }

  const value = useMemo(
    () => ({
      token,
      me,
      bootstrapped,
      refreshBootstrapped,
      refreshMe,
      login,
      logout,
    }),
    [token, me, bootstrapped]
  )

  useEffect(() => {
    refreshBootstrapped().catch(() => setBootstrapped(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    refreshMe().catch(() => setMe(null))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

