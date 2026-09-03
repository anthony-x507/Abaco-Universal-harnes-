import { useCallback, useEffect, useState } from 'react'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { getHealth, getSettings, updateSettings } from '../lib/api'
import { laterChannels } from '../lib/utils'

export function SettingsPage() {
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [channel, setChannel] = useState('cli')
  const [channels, setChannels] = useState<string[]>(['cli'])
  const [coming, setComing] = useState<string[]>([])
  const [hasKey, setHasKey] = useState(false)
  const [demo, setDemo] = useState(false)
  const [serverOk, setServerOk] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadedOnce, setLoadedOnce] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setMessage('')
    try {
      const [settings, health] = await Promise.all([getSettings(), getHealth()])
      setBaseUrl(settings.llm_base_url)
      setModel(settings.llm_model)
      setChannel(settings.default_channel)
      setChannels(settings.channels.length > 0 ? settings.channels : ['cli'])
      setComing(settings.channels_coming)
      setHasKey(Boolean(settings.llm_api_key))
      setDemo(settings.demo)
      setServerOk(health.status === 'ok')
      setLoadedOnce(true)
      setError('')
    } catch (err) {
      setServerOk(false)
      setError(err instanceof Error ? err.message : 'Could not load settings.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const save = async () => {
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const saved = await updateSettings({
        llm_base_url: baseUrl,
        llm_api_key: apiKey.trim() || undefined,
        llm_model: model,
        default_channel: channel,
      })
      setHasKey(Boolean(saved.llm_api_key))
      setApiKey('')
      setChannels(saved.channels.length > 0 ? saved.channels : ['cli'])
      setComing(saved.channels_coming)
      setMessage('Settings updated in this server process. They are not written to disk.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-muted">
          These settings will be used for new agents. Existing agents keep their current configuration.
          Leave the API key blank to keep the current secret. Nothing is written to disk.
        </p>
      </div>

      {loading && !loadedOnce ? (
        <p className="text-sm text-muted">Loading settings…</p>
      ) : !loadedOnce ? (
        <Card className="space-y-3 p-5">
          <p className="text-sm font-medium">Settings are not available.</p>
          <p className="text-sm text-red-300">{error || 'The factory server did not respond.'}</p>
          <p className="text-xs text-muted">Start `universal serve` and retry. The form stays empty until a load succeeds.</p>
          <Button size="sm" onClick={() => void load()} disabled={loading}>
            {loading ? 'Retrying…' : 'Retry'}
          </Button>
        </Card>
      ) : (
        <Card className="space-y-4 p-5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">API connection</span>
            <span className={serverOk ? 'text-accent' : 'text-red-300'}>
              {serverOk ? (demo ? 'Connected (demo echo)' : 'Connected') : 'Offline'}
            </span>
          </div>
          {error && (
            <div className="flex items-center justify-between gap-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              <span>{error}</span>
              <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
                {loading ? 'Retrying…' : 'Retry'}
              </Button>
            </div>
          )}
          <div className="space-y-1">
            <Label htmlFor="base-url">LLM base URL</Label>
            <Input id="base-url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="api-key">
              {demo ? 'Demo mode — no API key required' : `API key ${hasKey ? '(set)' : '(required for live completions)'}`}
            </Label>
            <Input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              disabled={demo}
              placeholder={
                demo
                  ? 'Demo mode — no API key required'
                  : hasKey
                    ? '••••••••  leave blank to keep'
                    : 'Required for live completions'
              }
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="model">Default model</Label>
            <Input id="model" value={model} onChange={(event) => setModel(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="channel">Default channel for new agents</Label>
            <select
              id="channel"
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
              className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
            >
              {channels.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
              {laterChannels(channels, coming).map((id) => (
                <option key={id} value={id} disabled>
                  {id} (later)
                </option>
              ))}
            </select>
          </div>
          <Button onClick={() => void save()} disabled={saving || !serverOk}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
          {message && <p className="text-sm text-accent">{message}</p>}
        </Card>
      )}
    </div>
  )
}
