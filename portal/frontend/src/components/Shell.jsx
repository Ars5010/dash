import { NavLink, Outlet } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext.jsx'

const navItems = [
  { to: '/timeline', label: 'Хронология' },
  { to: '/summary', label: 'Сводка' },
  { to: '/absence', label: 'Отсутствие' },
  { to: '/holidays', label: 'Праздники' },
  { to: '/admin', label: 'Админка' },
]

export default function Shell() {
  const { theme, toggleTheme } = useTheme()

  const isDark = theme === 'dark'

  return (
    <div className="min-h-dvh">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-cyan-400 via-fuchsia-500 to-amber-400 p-[1px]">
              <div className="h-full w-full rounded-2xl bg-white dark:bg-slate-950" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-wide text-slate-900 dark:text-slate-100">
                Portal
              </div>
              <div className="text-xs text-slate-600 dark:text-slate-400">
                ActivityWatch → Дашборды
              </div>
            </div>
          </div>

          <div className="hidden items-center gap-2 md:flex">
            <nav className="flex items-center gap-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'rounded-full px-4 py-2 text-sm transition',
                      isActive
                        ? 'bg-slate-900/5 text-slate-900 ring-1 ring-slate-900/10 dark:bg-white/10 dark:text-white dark:ring-white/15'
                        : 'text-slate-700 hover:bg-slate-900/5 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white',
                    ].join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={isDark ? 'Переключить на светлую тему' : 'Переключить на тёмную тему'}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900/5 text-slate-700 ring-1 ring-slate-900/10 hover:bg-slate-900/10 dark:bg-white/10 dark:text-slate-200 dark:ring-white/15 dark:hover:bg-white/20"
            >
              {isDark ? (
                // Луна
                <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
                  <path
                    d="M21 12.79A9 9 0 0 1 12.21 3 7 7 0 1 0 21 12.79z"
                    fill="currentColor"
                  />
                </svg>
              ) : (
                // Солнце
                <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
                  <circle cx="12" cy="12" r="4" fill="currentColor" />
                  <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                    <line x1="12" y1="2" x2="12" y2="5" />
                    <line x1="12" y1="19" x2="12" y2="22" />
                    <line x1="4.22" y1="4.22" x2="6.34" y2="6.34" />
                    <line x1="17.66" y1="17.66" x2="19.78" y2="19.78" />
                    <line x1="2" y1="12" x2="5" y2="12" />
                    <line x1="19" y1="12" x2="22" y2="12" />
                    <line x1="4.22" y1="19.78" x2="6.34" y2="17.66" />
                    <line x1="17.66" y1="6.34" x2="19.78" y2="4.22" />
                  </g>
                </svg>
              )}
            </button>
          </div>
        </header>

        <main className="mt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
