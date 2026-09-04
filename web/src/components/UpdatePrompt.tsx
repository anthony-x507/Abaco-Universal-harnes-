import { useCallback, useEffect, useState } from 'react'
import { applyUpdate, getUpdateStatus, type UpdateStatus } from '../lib/api'
import { Button } from './ui/button'
import { Card } from './ui/card'

type Props = {
  /** launch: silent check, prompt only if an update exists. */
  mode?: 'launch'
}

export function UpdatePrompt({ mode = 'launch' }: Props) {
  const [status, setStatus] = useState<UpdateStatus | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (mode !== 'launch') return
    let cancelled = false
    void getUpdateStatus()
      .then((next) => {
        if (cancelled) return
        setStatus(next)
        if (next.available) setOpen(true)
      })
      .catch(() => {
        /* silent on launch */
      })
    return () => {
      cancelled = true
    }
  }, [mode])

  const download = useCallback(async () => {
    setBusy(true)
    setError('')
    try {
      await applyUpdate()
      setOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed.')
    } finally {
      setBusy(false)
    }
  }, [])

  if (!open || !status?.available) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-md space-y-3 p-5">
        <h2 className="text-base font-semibold">Update available</h2>
        <p className="text-sm text-muted">
          Version {status.latest} is available (you have {status.current}). Download now?
        </p>
        {status.install_warning && <p className="text-sm text-amber-200">{status.install_warning}</p>}
        {error && <p className="text-sm text-red-300">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => setOpen(false)} disabled={busy}>
            Later
          </Button>
          <Button size="sm" onClick={() => void download()} disabled={busy}>
            {busy ? 'Downloading…' : 'Download now'}
          </Button>
        </div>
      </Card>
    </div>
  )
}
