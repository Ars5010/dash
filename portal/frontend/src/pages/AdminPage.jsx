import { useEffect, useMemo, useState } from 'react'
import CopyButton from '../components/CopyButton'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function genCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const parts = []
  for (let p = 0; p < 3; p++) {
    let s = ''
    for (let i = 0; i < 4; i++) s += alphabet[Math.floor(Math.random() * alphabet.length)]
    parts.push(s)
  }
  return `PC-${parts.join('-')}`
}

export default function AdminPage() {
  const { me } = useAuth()
  const [users, setUsers] = useState([])
  const [devices, setDevices] = useState([])
  const [code, setCode] = useState(genCode())
  const [userId, setUserId] = useState('')
  const [expiresAt, setExpiresAt] = useState('') // datetime-local
  const [created, setCreated] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [newUser, setNewUser] = useState({
    login: '',
    full_name: '',
    job_title: '',
    timezone: 'Europe/Moscow',
    role: 'user',
    password: '',
  })
  const [selectedUser, setSelectedUser] = useState(null)
  const [editUser, setEditUser] = useState({
    id: null,
    login: '',
    full_name: '',
    job_title: '',
    timezone: 'Europe/Moscow',
    role: 'user',
    is_active: true,
  })
  const [resetPassword, setResetPassword] = useState('')
  const [orgSettings, setOrgSettings] = useState(null)
  const [installSecretOnce, setInstallSecretOnce] = useState('')
  const [shotMediaId, setShotMediaId] = useState('')
  const [shotAnalysis, setShotAnalysis] = useState(null)
  const [shotAnalyses, setShotAnalyses] = useState([])
  const [penaltyForm, setPenaltyForm] = useState(null)
  const [ollamaHealth, setOllamaHealth] = useState(null)
  const [aiSelectedUserIds, setAiSelectedUserIds] = useState([])

  const portalUrl = useMemo(() => window.location.origin, [])
  const agentCommand = useMemo(() => {
    if (!created?.code) return ''
    return [
      'aw-portal-uploader.exe',
      `--portal-url "${portalUrl}"`,
      '--aw-server-url "http://127.0.0.1:5600"',
      `--enrollment-code "${created.code}"`,
    ].join(' ')
  }, [created, portalUrl])

  async function loadUsers() {
    const resp = await api.get('/v1/admin/users')
    setUsers(resp.data || [])
  }

  async function loadDevices() {
    const resp = await api.get('/v1/admin/devices')
    setDevices(resp.data || [])
  }

  async function loadOrgSettings() {
    const resp = await api.get('/v1/admin/org/settings')
    setOrgSettings(resp.data || null)
  }

  async function loadShotAnalyses() {
    const resp = await api.get('/v1/admin/ai/screenshot-analyses', { params: { limit: 40 } })
    setShotAnalyses(resp.data || [])
  }

  async function loadPenaltySettings() {
    try {
      const resp = await api.get('/v1/admin/org/penalty-settings')
      setPenaltyForm(resp.data || null)
    } catch {
      setPenaltyForm(null)
    }
  }

  async function loadOllamaHealth() {
    try {
      const resp = await api.get('/v1/admin/org/ollama-health')
      setOllamaHealth(resp.data || null)
    } catch {
      setOllamaHealth(null)
    }
  }

  useEffect(() => {
    setAiSelectedUserIds(users.filter((u) => u.ai_analyze_screenshots).map((u) => u.id))
  }, [users])

  useEffect(() => {
    loadUsers().catch(() => {})
    loadDevices().catch(() => {})
    loadOrgSettings().catch(() => {})
    loadPenaltySettings().catch(() => {})
    loadOllamaHealth().catch(() => {})
  }, [])

  async function createEnrollment(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    setCreated(null)
    try {
      const payload = {
        code,
        org_id: me?.org_id,
        user_id: userId ? Number(userId) : null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      }
      const resp = await api.post('/v1/devices/enrollment-codes', payload)
      setCreated(resp.data)
      setNotice('Enrollment code создан')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка создания enrollment code')
    } finally {
      setLoading(false)
    }
  }

  async function createUser(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.post('/v1/admin/users', {
        login: newUser.login.trim(),
        full_name: newUser.full_name.trim() || null,
        job_title: newUser.job_title.trim() || null,
        timezone: newUser.timezone.trim() || 'Europe/Moscow',
        role: newUser.role,
        password: newUser.password,
        is_active: true,
      })
      setNotice('Пользователь создан')
      setNewUser({
        login: '',
        full_name: '',
        job_title: '',
        timezone: 'Europe/Moscow',
        role: 'user',
        password: '',
      })
      await loadUsers()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка создания пользователя')
    } finally {
      setLoading(false)
    }
  }

  async function revokeDevice(id) {
    if (!id) return
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/v1/admin/devices/${id}/revoke`)
      setNotice('Устройство отозвано')
      await loadDevices()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка отзыва устройства')
    } finally {
      setLoading(false)
    }
  }

  function openUser(u) {
    setSelectedUser(u)
    setEditUser({
      id: u.id,
      login: u.login,
      full_name: u.full_name || '',
      job_title: u.job_title || '',
      timezone: u.timezone || 'Europe/Moscow',
      role: u.role || 'user',
      is_active: Boolean(u.is_active),
    })
    setResetPassword('')
    setError('')
    setNotice('')
  }

  async function saveUser() {
    if (!editUser?.id) return
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.patch(`/v1/admin/users/${editUser.id}`, {
        full_name: editUser.full_name.trim() || null,
        job_title: editUser.job_title.trim() || null,
        timezone: editUser.timezone.trim() || 'Europe/Moscow',
        role: editUser.role,
        is_active: Boolean(editUser.is_active),
      })
      setNotice('Пользователь обновлён')
      await loadUsers()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка сохранения пользователя')
    } finally {
      setLoading(false)
    }
  }

  async function doResetPassword() {
    if (!editUser?.id) return
    if (!resetPassword) {
      setError('Введите новый пароль')
      return
    }
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/v1/admin/users/${editUser.id}/reset-password`, { password: resetPassword })
      setNotice('Пароль сброшен')
      setResetPassword('')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка сброса пароля')
    } finally {
      setLoading(false)
    }
  }

  async function wipeUser() {
    if (!editUser?.id) return
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/v1/admin/users/${editUser.id}/wipe-data`)
      setNotice('Данные пользователя сброшены')
      await loadUsers()
      await loadDevices()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка сброса данных')
    } finally {
      setLoading(false)
    }
  }

  async function patchOrgSettings(partial) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const resp = await api.patch('/v1/admin/org/settings', partial)
      setOrgSettings(resp.data)
      setNotice('Настройки организации обновлены')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка настроек организации')
    } finally {
      setLoading(false)
    }
  }

  async function setAiPipelineEnabled(checked) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const resp = await api.patch('/v1/admin/org/settings', {
        screenshots_enabled: checked,
        ai_enabled: checked,
      })
      setOrgSettings(resp.data)
      setNotice(checked ? 'Скриншоты и ИИ включены для организации' : 'Скриншоты и ИИ выключены')
      await loadOllamaHealth().catch(() => {})
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка настроек')
    } finally {
      setLoading(false)
    }
  }

  function toggleAiUserSelect(id) {
    setAiSelectedUserIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function saveAiScreenshotUsers() {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.put('/v1/admin/org/ai-screenshot-users', { user_ids: aiSelectedUserIds })
      setNotice('Сохранено: ИИ по скринам только для выбранных сотрудников')
      await loadUsers()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка сохранения списка')
    } finally {
      setLoading(false)
    }
  }

  async function analyzeScreenshot() {
    if (!shotMediaId.trim()) {
      setError('Введите media_id (UUID из ответа загрузки скрина)')
      return
    }
    setLoading(true)
    setError('')
    setNotice('')
    setShotAnalysis(null)
    try {
      const resp = await api.post('/v1/admin/ai/analyze-screenshot', { media_id: shotMediaId.trim() })
      setShotAnalysis(resp.data)
      setNotice('Анализ готов')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка анализа скриншота')
    } finally {
      setLoading(false)
    }
  }

  async function savePenaltySettings(e) {
    e.preventDefault()
    if (!penaltyForm) return
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const payload = {
        ...penaltyForm,
        late_percent: Number(penaltyForm.late_percent),
        early_percent: Number(penaltyForm.early_percent),
        kpi_green_above: Number(penaltyForm.kpi_green_above),
        kpi_yellow_above: Number(penaltyForm.kpi_yellow_above),
        fine_yellow: Number(penaltyForm.fine_yellow),
        fine_red: Number(penaltyForm.fine_red),
      }
      const resp = await api.put('/v1/admin/org/penalty-settings', payload)
      setPenaltyForm(resp.data)
      setNotice('Настройки штрафов сохранены')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка сохранения штрафов')
    } finally {
      setLoading(false)
    }
  }

  async function generateInstallSecret() {
    setLoading(true)
    setError('')
    setNotice('')
    setInstallSecretOnce('')
    try {
      const resp = await api.post('/v1/admin/org/install-secret')
      setInstallSecretOnce(resp.data?.install_secret || '')
      setNotice('Новый ключ установки создан — скопируйте его сейчас (больше не покажем).')
      await loadOrgSettings()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка создания ключа')
    } finally {
      setLoading(false)
    }
  }

  async function deleteUser() {
    if (!editUser?.id) return
    setLoading(true)
    setError('')
    setNotice('')
    try {
      await api.delete(`/v1/admin/users/${editUser.id}`)
      setNotice('Пользователь удалён')
      setSelectedUser(null)
      await loadUsers()
      await loadDevices()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Ошибка удаления пользователя')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-6">
      <div className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h1 className="text-lg font-semibold">Админка</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Устройства: создайте enrollment code и выдайте сотруднику готовую команду подключения агента.
        </p>
      </div>

      {error ? (
        <div className="rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200 ring-1 ring-rose-400/30">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="rounded-2xl bg-emerald-500/10 p-4 text-sm text-emerald-200 ring-1 ring-emerald-400/30">
          {notice}
        </div>
      ) : null}

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">ИИ и скриншоты</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          При <code className="rounded bg-slate-100 px-1 dark:bg-white/10">docker compose up</code> поднимается сервис{' '}
          <code className="rounded bg-slate-100 px-1 dark:bg-white/10">ollama</code>; бэкенд по умолчанию ходит на{' '}
          <code className="rounded bg-slate-100 px-1 dark:bg-white/10">http://ollama:11434</code>. Первый старт долго
          качает модели <code className="rounded bg-slate-100 px-1 dark:bg-white/10">gemma3n:e4b</code> и{' '}
          <code className="rounded bg-slate-100 px-1 dark:bg-white/10">gemma3:4b-it-q4_K_M</code>. Пока pull идёт, в
          проверке ниже будет «список моделей пуст» — это нормально; смотрите{' '}
          <code className="rounded bg-slate-100 px-1 dark:bg-white/10">docker compose logs -f ollama</code>.
        </p>
        <div className="mt-3">
          <button
            type="button"
            disabled={loading}
            onClick={() => loadOllamaHealth().catch(() => {})}
            className="h-9 rounded-xl bg-slate-900/5 px-3 text-xs font-semibold text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10"
          >
            Проверить Ollama
          </button>
        </div>
        {ollamaHealth ? (
          <div
            className={`mt-3 rounded-2xl p-4 text-sm ring-1 ${
              ollamaHealth.reachable && ollamaHealth.vision_model_ready && ollamaHealth.text_model_ready
                ? 'bg-emerald-500/10 text-emerald-900 ring-emerald-300 dark:bg-emerald-500/15 dark:text-emerald-100 dark:ring-emerald-400/35'
                : 'bg-amber-500/10 text-amber-950 ring-amber-300 dark:bg-amber-500/15 dark:text-amber-100 dark:ring-amber-400/35'
            }`}
          >
            <div className="font-semibold">
              {ollamaHealth.configured
                ? ollamaHealth.reachable
                  ? 'Ollama отвечает'
                  : 'Нет связи с Ollama'
                : 'OLLAMA_BASE_URL не задан (для docker-compose обычно уже задан)'}
            </div>
            <div className="mt-1 text-xs opacity-90">
              Vision (скрины): {ollamaHealth.vision_model_ready ? 'готово' : 'нет модели'} · Текст:{' '}
              {ollamaHealth.text_model_ready ? 'готово' : 'нет модели'}
            </div>
            {ollamaHealth.detail ? <div className="mt-2 text-xs opacity-90">{ollamaHealth.detail}</div> : null}
          </div>
        ) : null}

        {orgSettings ? (
          <div className="mt-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-slate-200">
              <input
                type="checkbox"
                checked={Boolean(orgSettings.screenshots_enabled && orgSettings.ai_enabled)}
                onChange={(e) => setAiPipelineEnabled(e.target.checked)}
                disabled={loading}
                className="h-4 w-4 accent-fuchsia-500"
              />
              Включить для организации: скрины с ПК + серверный ИИ
            </label>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Одна галочка включает и загрузку скриншотов, и ИИ. Затем отметьте сотрудников и нажмите «Сохранить список» —
              для этого шага UUID не нужны (в отличие от ручного анализа одного файла по media_id).
            </p>
          </div>
        ) : null}

        <div className="mt-5 border-t border-slate-200 pt-4 dark:border-white/10">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Кого анализировать по скринам</h3>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Только отмеченные. Очередь обрабатывается каждые ~2 мин. ПК должен быть привязан к пользователю (enrollment).
          </p>
          <div className="mt-3 max-h-44 overflow-y-auto rounded-2xl bg-slate-100 p-2 ring-1 ring-slate-200 dark:bg-slate-950/30 dark:ring-white/10">
            {users.length === 0 ? (
              <div className="p-2 text-xs text-slate-500 dark:text-slate-400">Сначала создайте пользователей ниже</div>
            ) : (
              users.map((u) => (
                <label
                  key={u.id}
                  className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-200 dark:hover:bg-white/5"
                >
                  <input
                    type="checkbox"
                    checked={aiSelectedUserIds.includes(u.id)}
                    onChange={() => toggleAiUserSelect(u.id)}
                    disabled={loading}
                    className="accent-fuchsia-500"
                  />
                  <span className="text-slate-800 dark:text-slate-100">{u.full_name || u.login}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">{u.login}</span>
                </label>
              ))
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={loading}
              onClick={() => setAiSelectedUserIds(users.map((u) => u.id))}
              className="h-9 rounded-xl bg-slate-900/5 px-3 text-xs text-slate-900 ring-1 ring-slate-300 dark:bg-white/10 dark:text-white dark:ring-white/10"
            >
              Все
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => setAiSelectedUserIds([])}
              className="h-9 rounded-xl bg-slate-900/5 px-3 text-xs text-slate-900 ring-1 ring-slate-300 dark:bg-white/10 dark:text-white dark:ring-white/10"
            >
              Никого
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => saveAiScreenshotUsers().catch(() => {})}
              className="h-9 rounded-xl bg-fuchsia-600 px-4 text-xs font-semibold text-white hover:bg-fuchsia-500 disabled:opacity-60"
            >
              Сохранить список сотрудников
            </button>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-4 dark:border-white/10">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Последние автоанализы</h4>
          <button
            type="button"
            disabled={loading}
            onClick={() => loadShotAnalyses().catch(() => {})}
            className="h-9 rounded-xl bg-slate-900/5 px-3 text-xs font-semibold text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10"
          >
            Обновить список
          </button>
        </div>
        <div className="mt-2 overflow-auto rounded-xl ring-1 ring-slate-200 dark:ring-white/10">
          <table className="min-w-full text-left text-xs text-slate-700 dark:text-slate-200">
            <thead className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-600 dark:bg-white/5 dark:text-slate-400">
              <tr>
                <th className="px-3 py-2">Время</th>
                <th className="px-3 py-2">Сотрудник</th>
                <th className="px-3 py-2">Балл</th>
                <th className="px-3 py-2">Непродукт.</th>
                <th className="px-3 py-2">Комментарий / ошибка</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-white/5">
              {shotAnalyses.map((r) => (
                <tr key={r.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600 dark:text-slate-400">
                    {r.analyzed_at ? new Date(r.analyzed_at).toLocaleString('ru-RU') : '—'}
                  </td>
                  <td className="px-3 py-2">{r.user_login || r.user_id || '—'}</td>
                  <td className="px-3 py-2 font-mono">{r.productive_score ?? '—'}</td>
                  <td className="px-3 py-2">{r.unproductive == null ? '—' : r.unproductive ? 'да' : 'нет'}</td>
                  <td className="max-w-xs truncate px-3 py-2" title={r.error_text || r.evidence_ru || ''}>
                    {r.error_text || r.evidence_ru || '—'}
                  </td>
                </tr>
              ))}
              {shotAnalyses.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-slate-500 dark:text-slate-400" colSpan={5}>
                    Пока нет записей. Включите галочку выше, сохраните сотрудников, дождитесь скринов с ПК.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <details className="mt-4 rounded-xl bg-slate-100 p-3 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
          <summary className="cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-300">
            Ручной анализ по UUID (отладка)
          </summary>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            Обычно не нужен: автоанализ идёт по очереди. Здесь — принудительно по <code className="rounded bg-white px-1 dark:bg-black/30">media_id</code>.
          </p>
          <div className="mt-2 flex flex-wrap items-end gap-2">
            <label className="grid gap-1">
              <span className="text-xs text-slate-600 dark:text-slate-400">media_id</span>
              <input
                value={shotMediaId}
                onChange={(e) => setShotMediaId(e.target.value)}
                placeholder="UUID"
                className="h-10 w-64 rounded-xl bg-white px-3 font-mono text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              />
            </label>
            <button
              type="button"
              disabled={loading}
              onClick={analyzeScreenshot}
              className="h-10 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60 dark:bg-white dark:text-slate-900"
            >
              Анализировать
            </button>
          </div>
          {shotAnalysis ? (
            <pre className="mt-3 max-h-60 overflow-auto rounded-lg bg-white p-2 text-[10px] text-slate-800 dark:bg-black/40 dark:text-slate-200">
              {JSON.stringify(shotAnalysis, null, 2)}
            </pre>
          ) : null}
        </details>
      </section>

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">Организация и установка на ПК</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          ID организации для мастера регистрации на ПК:{' '}
          <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">{me?.org_id ?? '—'}</span>.
          На ПК: <code className="rounded bg-slate-100 px-1 dark:bg-white/10">aw-portal-uploader --install-wizard</code> или{' '}
          <code className="rounded bg-slate-100 px-1 dark:bg-white/10">aw-portal-install-wizard</code>.
        </p>
        {orgSettings ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={Boolean(orgSettings.self_registration_enabled)}
                onChange={(e) => patchOrgSettings({ self_registration_enabled: e.target.checked })}
                disabled={loading}
              />
              Саморегистрация при установке (ключ + мастер на ПК)
            </label>
            <div className="text-xs text-slate-600 dark:text-slate-400">
              Ключ установки: {orgSettings.install_secret_configured ? 'задан' : 'не создан'}
            </div>
            <p className="md:col-span-2 text-xs text-slate-600 dark:text-slate-400">
              Скриншоты и ИИ — в блоке «ИИ и скриншоты» выше (одна галочка + список сотрудников).
            </p>
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={loading}
            onClick={generateInstallSecret}
            className="h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400 disabled:opacity-60"
          >
            Создать новый ключ установки
          </button>
        </div>
        {installSecretOnce ? (
          <div className="mt-3 rounded-2xl bg-amber-500/15 p-3 text-sm text-amber-100 ring-1 ring-amber-400/30">
            <div className="font-semibold">Сохраните ключ:</div>
            <pre className="mt-2 overflow-auto whitespace-pre-wrap break-all font-mono text-xs">{installSecretOnce}</pre>
            <CopyButton text={installSecretOnce} label="Скопировать ключ" className="mt-2" />
          </div>
        ) : null}
      </section>

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">Штрафы и KPI</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Влияет на расчёт дня в хронологии, сводке и отчётах. Рабочие часы по-прежнему из глобального конфига портала (
          <code className="rounded bg-slate-100 px-1 dark:bg-white/10">portal_config</code>
          ), проценты опоздания/раннего ухода при первом сохранении подтянутся оттуда, если ещё не заданы в организации.
        </p>
        {penaltyForm ? (
          <form onSubmit={savePenaltySettings} className="mt-4 grid gap-4">
            <div className="grid gap-2 md:grid-cols-2">
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={Boolean(penaltyForm.enabled)}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, enabled: e.target.checked }))}
                  disabled={loading}
                />
                Включить штрафы (если выкл. — KPI без вычетов, «штраф дня» = 0)
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={Boolean(penaltyForm.day_fine_enabled)}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, day_fine_enabled: e.target.checked }))}
                  disabled={loading}
                />
                Условные суммы за жёлтый/красный день
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={Boolean(penaltyForm.late_enabled)}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, late_enabled: e.target.checked }))}
                  disabled={loading}
                />
                Штраф за опоздание (первый не-AFK после начала рабочего дня)
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={Boolean(penaltyForm.early_leave_enabled)}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, early_leave_enabled: e.target.checked }))}
                  disabled={loading}
                />
                Штраф за ранний уход (последняя активность до конца рабочего дня)
              </label>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Режим %</span>
                <select
                  value={penaltyForm.mode}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, mode: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                >
                  <option value="binary">Фиксированный % за факт</option>
                  <option value="proportional">Пропорционально окну</option>
                </select>
              </label>
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">% за опоздание</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={penaltyForm.late_percent}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, late_percent: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">% за ранний уход</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={penaltyForm.early_percent}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, early_percent: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Порог KPI → зелёный (&gt;)</span>
                <input
                  type="number"
                  step={0.1}
                  value={penaltyForm.kpi_green_above}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, kpi_green_above: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Порог KPI → жёлтый (&gt;)</span>
                <input
                  type="number"
                  step={0.1}
                  value={penaltyForm.kpi_yellow_above}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, kpi_yellow_above: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Сумма жёлтого дня</span>
                <input
                  type="number"
                  step={1}
                  value={penaltyForm.fine_yellow}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, fine_yellow: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                />
              </label>
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Сумма красного дня</span>
                <input
                  type="number"
                  step={1}
                  value={penaltyForm.fine_red}
                  onChange={(e) => setPenaltyForm((s) => ({ ...s, fine_red: e.target.value }))}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  disabled={loading}
                />
              </label>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={loading}
                className="h-10 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200"
              >
                Сохранить штрафы
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => loadPenaltySettings().catch(() => {})}
                className="h-10 rounded-xl bg-slate-900/5 px-4 text-sm text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10"
              >
                Сбросить из сервера
              </button>
            </div>
          </form>
        ) : (
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Не удалось загрузить настройки штрафов.</p>
        )}
      </section>

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">Пользователи</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Создание пользователей для входа в портал (JWT). ИИ по скринам — в блоке «ИИ и скриншоты» выше.
        </p>

        <form onSubmit={createUser} className="mt-4 grid gap-3 lg:grid-cols-6">
          <label className="grid gap-1 lg:col-span-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Логин</span>
            <input
              value={newUser.login}
              onChange={(e) => setNewUser((s) => ({ ...s, login: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              required
            />
          </label>
          <label className="grid gap-1 lg:col-span-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">ФИО (опц.)</span>
            <input
              value={newUser.full_name}
              onChange={(e) => setNewUser((s) => ({ ...s, full_name: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>
          <label className="grid gap-1 lg:col-span-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Должность (опц.)</span>
            <input
              value={newUser.job_title}
              onChange={(e) => setNewUser((s) => ({ ...s, job_title: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>
          <label className="grid gap-1 lg:col-span-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Таймзона</span>
            <input
              value={newUser.timezone}
              onChange={(e) => setNewUser((s) => ({ ...s, timezone: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            />
          </label>
          <label className="grid gap-1 lg:col-span-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Роль</span>
            <select
              value={newUser.role}
              onChange={(e) => setNewUser((s) => ({ ...s, role: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <label className="grid gap-1 lg:col-span-1">
            <span className="text-xs text-slate-600 dark:text-slate-400">Пароль</span>
            <input
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser((s) => ({ ...s, password: e.target.value }))}
              className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              required
            />
          </label>
          <button
            disabled={loading}
            className="h-10 rounded-xl bg-slate-900/5 px-4 text-sm font-semibold text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15 lg:col-span-6"
          >
            {loading ? 'Сохраняю…' : 'Создать пользователя'}
          </button>
        </form>

        <div className="mt-5 overflow-auto rounded-2xl ring-1 ring-slate-200 dark:ring-white/10">
          <table className="min-w-full text-left text-sm text-slate-700 dark:text-slate-200">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600 dark:bg-white/5 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Логин</th>
                <th className="px-4 py-3">ФИО</th>
                <th className="px-4 py-3">Должность</th>
                <th className="px-4 py-3">Роль</th>
                <th className="px-4 py-3">Статус</th>
                <th className="px-4 py-3 text-right">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-white/5">
              {users.map((u) => (
                <tr key={u.id} className="bg-black/0">
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{u.id}</td>
                  <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">{u.login}</td>
                  <td className="px-4 py-3">{u.full_name || '—'}</td>
                  <td className="px-4 py-3">{u.job_title || '—'}</td>
                  <td className="px-4 py-3">{u.role}</td>
                  <td className="px-4 py-3">{u.is_active ? 'Активен' : 'Выключен'}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => openUser(u)}
                      className="h-9 rounded-xl bg-slate-900/5 px-3 text-xs font-semibold text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
                    >
                      Управлять
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Enrollment code</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Код одноразовый. Можно привязать к пользователю (тогда устройство закрепится за ним).
          </p>

          <form onSubmit={createEnrollment} className="mt-5 grid gap-3">
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <label className="grid gap-1">
                <span className="text-xs text-slate-600 dark:text-slate-400">Code</span>
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                />
              </label>
              <button
                type="button"
                onClick={() => setCode(genCode())}
                className="mt-6 h-10 rounded-xl bg-slate-900/5 px-4 text-sm text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
              >
                Сгенерировать
              </button>
            </div>

            <label className="grid gap-1">
              <span className="text-xs text-slate-600 dark:text-slate-400">Пользователь (опционально)</span>
              <select
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              >
                <option value="">Не привязывать</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name ? `${u.full_name} (${u.login})` : u.login}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1">
              <span className="text-xs text-slate-600 dark:text-slate-400">Истекает (опционально)</span>
              <input
                type="datetime-local"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
              />
            </label>

            <button
              disabled={loading}
              className="mt-2 h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400 disabled:opacity-60"
            >
              {loading ? 'Создаю…' : 'Создать code'}
            </button>
          </form>
        </section>

        <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Подключение ПК</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Передайте сотруднику команду. Она подключит uploader к порталу и начнёт отправку событий ActivityWatch.
          </p>

          <div className="mt-5 grid gap-3 rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200 dark:bg-slate-950/40 dark:ring-white/10">
            <div className="text-xs text-slate-600 dark:text-slate-400">Команда</div>
            <pre className="overflow-auto whitespace-pre-wrap break-words rounded-xl bg-white p-3 text-xs text-slate-900 ring-1 ring-slate-200 dark:bg-black/30 dark:text-slate-100 dark:ring-white/10">
              {agentCommand || 'Сначала создайте enrollment code слева.'}
            </pre>

            <div className="flex flex-wrap items-center gap-2">
              <CopyButton
                text={agentCommand}
                label="Скопировать команду"
                className={!agentCommand ? 'pointer-events-none opacity-50' : ''}
              />
              {created?.code ? (
                <span className="text-xs text-slate-600 dark:text-slate-400">
                  Code: <span className="font-semibold text-slate-900 dark:text-slate-200">{created.code}</span>
                </span>
              ) : null}
            </div>
          </div>

          <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-300 dark:ring-white/10">
            <div className="font-semibold text-slate-900 dark:text-white">Что должно быть на ПК</div>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
              <li>ActivityWatch (aw-server + watchers window/afk)</li>
              <li>Наш uploader.exe (следующий шаг — соберём в один EXE)</li>
              <li>Опционально web watcher (для сайтов)</li>
            </ul>
          </div>
        </section>
      </div>

      <section className="rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">Устройства и токены</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Тут видно, какие ПК подключены и когда последний раз приходили события. Отзыв отключит отправку.
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadDevices().catch(() => {})}
            className="h-10 rounded-xl bg-slate-900/5 px-4 text-sm text-slate-900 ring-1 ring-slate-300 hover:bg-slate-900/10 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
          >
            Обновить
          </button>
        </div>

        <div className="mt-5 overflow-auto rounded-2xl ring-1 ring-slate-200 dark:ring-white/10">
          <table className="min-w-full text-left text-sm text-slate-700 dark:text-slate-200">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600 dark:bg-white/5 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3">Device</th>
                <th className="px-4 py-3">Пользователь</th>
                <th className="px-4 py-3">Host/OS</th>
                <th className="px-4 py-3">Последнее событие</th>
                <th className="px-4 py-3">Статус</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-white/5">
              {devices.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3 font-mono text-xs text-slate-900 dark:text-slate-100">{d.device_id}</td>
                  <td className="px-4 py-3">{d.user_full_name || d.user_login || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="text-slate-900 dark:text-slate-100">{d.hostname || '—'}</div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">{d.os || ''}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                    {d.last_event_at ? new Date(d.last_event_at).toLocaleString('ru-RU') : '—'}
                  </td>
                  <td className="px-4 py-3">{d.revoked_at ? 'Отозвано' : 'Активно'}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      disabled={loading || Boolean(d.revoked_at)}
                      onClick={() => revokeDevice(d.id)}
                      className="h-9 rounded-xl bg-rose-500/15 px-3 text-xs font-semibold text-rose-100 ring-1 ring-rose-400/30 hover:bg-rose-500/20 disabled:opacity-50"
                    >
                      Отозвать
                    </button>
                  </td>
                </tr>
              ))}
              {devices.length === 0 ? (
                <tr>
                  <td className="px-4 py-4 text-sm text-slate-600 dark:text-slate-400" colSpan={6}>
                    Устройств пока нет. Сначала подключите ПК через enrollment code выше.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      {selectedUser ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 dark:bg-black/60"
          onClick={() => setSelectedUser(null)}
        >
          <div
            className="w-full max-w-2xl rounded-3xl bg-white p-5 ring-1 ring-slate-200 dark:bg-slate-950 dark:ring-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-slate-900 dark:text-white">
                  Пользователь: {editUser.login}
                </div>
                <div className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  Можно поменять ФИО/роль/активность, сбросить пароль, сбросить данные (wipe) и удалить.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedUser(null)}
                className="h-9 rounded-xl bg-slate-100 px-3 text-xs font-semibold text-slate-800 ring-1 ring-slate-200 hover:bg-slate-200 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
              >
                Закрыть
              </button>
            </div>

            <div className="mt-4 grid gap-4">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">ФИО</span>
                  <input
                    value={editUser.full_name}
                    onChange={(e) => setEditUser((s) => ({ ...s, full_name: e.target.value }))}
                    className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  />
                </label>
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Должность</span>
                  <input
                    value={editUser.job_title}
                    onChange={(e) => setEditUser((s) => ({ ...s, job_title: e.target.value }))}
                    className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  />
                </label>
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Таймзона</span>
                  <input
                    value={editUser.timezone}
                    onChange={(e) => setEditUser((s) => ({ ...s, timezone: e.target.value }))}
                    className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  />
                </label>
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Роль</span>
                  <select
                    value={editUser.role}
                    onChange={(e) => setEditUser((s) => ({ ...s, role: e.target.value }))}
                    className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                </label>
                <label className="grid gap-1">
                  <span className="text-xs text-slate-600 dark:text-slate-400">Статус</span>
                  <select
                    value={editUser.is_active ? '1' : '0'}
                    onChange={(e) => setEditUser((s) => ({ ...s, is_active: e.target.value === '1' }))}
                    className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                  >
                    <option value="1">Активен</option>
                    <option value="0">Выключен</option>
                  </select>
                </label>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={saveUser}
                  disabled={loading}
                  className="h-10 rounded-xl bg-fuchsia-500 px-4 text-sm font-semibold text-white hover:bg-fuchsia-400 disabled:opacity-60"
                >
                  Сохранить
                </button>
              </div>

              <div className="rounded-2xl bg-slate-100 p-4 ring-1 ring-slate-200 dark:bg-white/5 dark:ring-white/10">
                <div className="text-sm font-semibold text-slate-900 dark:text-white">Сброс пароля</div>
                <div className="mt-3 flex flex-wrap items-end gap-2">
                  <label className="grid flex-1 gap-1">
                    <span className="text-xs text-slate-600 dark:text-slate-400">Новый пароль</span>
                    <input
                      type="password"
                      value={resetPassword}
                      onChange={(e) => setResetPassword(e.target.value)}
                      className="h-10 rounded-xl bg-white px-3 text-sm text-slate-900 ring-1 ring-slate-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-400/40 dark:bg-slate-950/40 dark:text-white dark:ring-white/10"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={doResetPassword}
                    disabled={loading}
                    className="h-10 rounded-xl bg-slate-200 px-4 text-sm font-semibold text-slate-800 ring-1 ring-slate-300 hover:bg-slate-300 disabled:opacity-60 dark:bg-white/10 dark:text-white dark:ring-white/10 dark:hover:bg-white/15"
                  >
                    Сбросить пароль
                  </button>
                </div>
              </div>

              <div className="rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-200 dark:bg-amber-500/10 dark:ring-amber-400/20">
                <div className="text-sm font-semibold text-amber-900 dark:text-amber-100">Сброс данных (wipe)</div>
                <div className="mt-1 text-xs text-amber-800 dark:text-amber-100/80">
                  Удалит события активности, отсутствия, агрегаты и правила продуктивности пользователя, а устройства отвяжет от него.
                </div>
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={wipeUser}
                    disabled={loading}
                    className="h-10 rounded-xl bg-amber-500 px-4 text-sm font-semibold text-black hover:bg-amber-400 disabled:opacity-60"
                  >
                    Сбросить данные
                  </button>
                </div>
              </div>

              <div className="rounded-2xl bg-rose-50 p-4 ring-1 ring-rose-200 dark:bg-rose-500/10 dark:ring-rose-400/30">
                <div className="text-sm font-semibold text-rose-900 dark:text-rose-100">Удаление пользователя</div>
                <div className="mt-1 text-xs text-rose-800 dark:text-rose-100/80">
                  Удаление возможно только если нет связанных данных. Обычно сначала нужно сделать wipe.
                </div>
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={deleteUser}
                    disabled={loading}
                    className="h-10 rounded-xl bg-rose-600 px-4 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-60 dark:bg-rose-500 dark:hover:bg-rose-400"
                  >
                    Удалить пользователя
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

