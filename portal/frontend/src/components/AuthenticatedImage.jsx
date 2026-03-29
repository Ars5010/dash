import { useEffect, useState } from 'react'
import { api } from '../lib/api'

/**
 * Загружает бинарь скрина с Authorization (обычный <img src> токен не передаёт).
 */
export default function AuthenticatedImage({ mediaId, className = '', alt = '' }) {
  const [url, setUrl] = useState('')
  const [err, setErr] = useState(false)

  useEffect(() => {
    const hold = { objectUrl: '' }
    let cancelled = false
    setErr(false)
    setUrl('')
    api
      .get(`/v1/media/${mediaId}`, { responseType: 'blob' })
      .then((r) => {
        if (cancelled) return
        hold.objectUrl = URL.createObjectURL(r.data)
        setUrl(hold.objectUrl)
      })
      .catch(() => {
        if (!cancelled) setErr(true)
      })
    return () => {
      cancelled = true
      if (hold.objectUrl) URL.revokeObjectURL(hold.objectUrl)
    }
  }, [mediaId])

  if (err) {
    return (
      <div
        className={`flex items-center justify-center bg-slate-200 text-[10px] text-slate-600 dark:bg-white/10 dark:text-slate-400 ${className}`}
      >
        Нет файла
      </div>
    )
  }
  if (!url) {
    return <div className={`animate-pulse bg-slate-200 dark:bg-white/10 ${className}`} />
  }
  return <img src={url} alt={alt} className={className} />
}
