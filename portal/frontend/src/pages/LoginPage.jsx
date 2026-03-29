import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const nav = useNavigate()
  const { login: doLogin, bootstrapped } = useAuth()
  const [login, setLogin] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await doLogin(login.trim(), password)
      nav('/timeline')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10'

  return (
    <div className="mx-auto max-w-lg rounded-3xl bg-white p-6 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-white">Вход</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Войдите, чтобы открыть дашборды.</p>

      {bootstrapped === false ? (
        <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-100 dark:ring-amber-400/30">
          Первый запуск: сначала создайте организацию и администратора на странице{' '}
          <Link to="/setup" className="font-semibold text-amber-800 underline dark:text-amber-50">
            /setup
          </Link>
          . Логин и пароль задаёте вы сами — подставленные «admin» / «admin123» в форме ниже только пример.
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-2xl bg-rose-50 p-4 text-sm text-rose-800 ring-1 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-400/30">
          {error}
        </div>
      ) : null}

      <form onSubmit={submit} className="mt-5 grid gap-3">
        <label className="grid gap-1">
          <span className="text-xs text-slate-600 dark:text-slate-400">Логин</span>
          <input
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs text-slate-600 dark:text-slate-400">Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
          />
        </label>
        <button
          disabled={loading}
          className="mt-2 h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400 disabled:opacity-60"
        >
          {loading ? 'Входим…' : 'Войти'}
        </button>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Забыли пароль? Админ может сбросить его в разделе «Админка» → пользователь → сброс пароля.
        </p>
      </form>
    </div>
  )
}
