import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function isAlreadyBootstrappedMessage(text) {
  if (!text || typeof text !== 'string') return false
  const t = text.toLowerCase()
  return t.includes('bootstrap') || t.includes('already bootstrapped')
}

export default function SetupPage() {
  const nav = useNavigate()
  const { bootstrapped, refreshBootstrapped } = useAuth()
  const [form, setForm] = useState({
    org_name: 'MyCompany',
    login: 'admin',
    password: 'admin123',
    full_name: 'Администратор',
    job_title: '',
    timezone: 'Europe/Moscow',
    role: 'admin',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    refreshBootstrapped().catch(() => {})
  }, [refreshBootstrapped])

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.post('/v1/admin/bootstrap', form)
      await refreshBootstrapped()
      nav('/login')
    } catch (err) {
      const d = err?.response?.data
      const detail = d?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map((x) => x?.msg).filter(Boolean).join('; ') || 'Ошибка инициализации')
      } else {
        setError('Ошибка инициализации')
      }
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10'

  if (bootstrapped === null) {
    return (
      <div className="mx-auto max-w-2xl rounded-3xl bg-white p-6 text-sm text-slate-600 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-400 dark:ring-white/10">
        Проверка состояния портала…
      </div>
    )
  }

  if (bootstrapped === true) {
    return (
      <div className="mx-auto max-w-2xl rounded-3xl bg-white p-6 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">Портал уже настроен</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          В базе уже есть пользователи — повторно пройти этот шаг нельзя. Войдите под своим логином и паролем, которые вы задавали при первом запуске.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            to="/login"
            className="inline-flex h-10 items-center rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400"
          >
            Перейти ко входу
          </Link>
        </div>
        <details className="mt-6 rounded-2xl bg-slate-100 p-4 text-sm text-slate-700 ring-1 ring-slate-200 dark:bg-slate-950/40 dark:text-slate-300 dark:ring-white/10">
          <summary className="cursor-pointer font-medium text-slate-900 dark:text-slate-200">
            Нужна новая «чистая» установка?
          </summary>
          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Это удалит все данные портала в этой базе (организации, пользователи, события).
          </p>
          <p className="mt-2 font-mono text-xs text-slate-600 dark:text-slate-400">
            Из папки <span className="text-slate-800 dark:text-slate-300">portal/</span> — сброс тома PostgreSQL:
          </p>
          <pre className="mt-2 overflow-x-auto rounded-xl bg-slate-800 p-3 text-xs text-slate-100 dark:bg-black/40 dark:text-slate-200">
            docker compose down -v{'\n'}
            docker compose up --build -d
          </pre>
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-500">
            Либо сброс только схемы (без удаления тома): в контейнере backend выполнить{' '}
            <code className="rounded bg-white px-1 ring-1 ring-slate-200 dark:bg-white/10 dark:ring-transparent">
              alembic downgrade base
            </code>{' '}
            затем перезапуск (при старте снова выполнится{' '}
            <code className="rounded bg-white px-1 ring-1 ring-slate-200 dark:bg-white/10 dark:ring-transparent">
              upgrade head
            </code>
            ).
          </p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-500">
            Забыли пароль админа — можно сбросить:{' '}
            <code className="rounded bg-white px-1 text-[10px] ring-1 ring-slate-200 dark:bg-white/10 dark:ring-transparent">
              docker compose exec backend python /app/scripts/reset_user_password.py admin НовыйПароль
            </code>
          </p>
        </details>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl rounded-3xl bg-white p-6 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-white">Первый запуск</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        Создайте организацию и администратора. Это делается один раз.
      </p>

      {error ? (
        <div className="mt-4 rounded-2xl bg-rose-50 p-4 text-sm text-rose-800 ring-1 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-400/30">
          <div>{error}</div>
          {isAlreadyBootstrappedMessage(error) ? (
            <div className="mt-3 border-t border-rose-200 pt-3 text-xs text-rose-900 dark:border-rose-400/20 dark:text-rose-100/90">
              <p className="font-medium text-rose-950 dark:text-rose-50">Портал уже инициализирован ранее.</p>
              <p className="mt-2">
                <Link to="/login" className="font-semibold text-fuchsia-600 underline dark:text-fuchsia-300">
                  Войти
                </Link>
                {' · '}
                чистая установка:{' '}
                <code className="rounded bg-rose-100 px-1 text-rose-900 dark:bg-black/30 dark:text-slate-200">
                  docker compose down -v
                </code>{' '}
                в каталоге portal, затем снова поднять stack.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      <form onSubmit={submit} className="mt-5 grid gap-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Организация</span>
            <input
              value={form.org_name}
              onChange={(e) => setForm((p) => ({ ...p, org_name: e.target.value }))}
              className={inputClass}
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Таймзона (default)</span>
            <input
              value={form.timezone}
              onChange={(e) => setForm((p) => ({ ...p, timezone: e.target.value }))}
              className={inputClass}
            />
          </label>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Логин admin</span>
            <input
              value={form.login}
              onChange={(e) => setForm((p) => ({ ...p, login: e.target.value }))}
              className={inputClass}
            />
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Пароль admin</span>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
              className={inputClass}
            />
          </label>
        </div>

        <label className="grid gap-1">
          <span className="text-xs text-slate-600 dark:text-slate-400">ФИО</span>
          <input
            value={form.full_name}
            onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
            className={inputClass}
          />
        </label>

        <label className="grid gap-1">
          <span className="text-xs text-slate-600 dark:text-slate-400">Должность (опц.)</span>
          <input
            value={form.job_title}
            onChange={(e) => setForm((p) => ({ ...p, job_title: e.target.value }))}
            className={inputClass}
          />
        </label>

        <button
          disabled={loading}
          className="mt-2 h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400 disabled:opacity-60"
        >
          {loading ? 'Создаём…' : 'Инициализировать'}
        </button>
      </form>
    </div>
  )
}
