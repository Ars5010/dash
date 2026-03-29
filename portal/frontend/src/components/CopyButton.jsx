import { useState } from 'react'

export default function CopyButton({ text, label = 'Скопировать', className = '' }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  return (
    <button
      type="button"
      onClick={copy}
      className={[
        'h-10 rounded-xl bg-white/10 px-4 text-sm text-white ring-1 ring-white/10 hover:bg-white/15',
        className,
      ].join(' ')}
      title={text}
    >
      {copied ? 'Скопировано' : label}
    </button>
  )
}
