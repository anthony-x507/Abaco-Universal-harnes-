import { useCallback, useEffect, useState } from 'react'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { useModels } from '../hooks/useModels'
import {
  applyUpdate,
  getHealth,
  getRules,
  getSettings,
  getUpdateStatus,
  updateSettings,
  type GovernanceRule,
  type RuntimeStatus,
} from '../lib/api'
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
  const [updateNote, setUpdateNote] = useState('')
  const [updateWarn, setUpdateWarn] = useState('')
  const [checkingUpdate, setCheckingUpdate] = useState(false)
  const [applyingUpdate, setApplyingUpdate] = useState(false)
  const [pendingUpdate, setPendingUpdate] = useState<{ latest: string; current: string } | null>(null)
  const [preset, setPreset] = useState('OpenAI (GPT-5.6 Sol)')
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null)
  const [rules, setRules] = useState<GovernanceRule[]>([])
  const { models } = useModels()

  const load = useCallback(async () => {
    setLoading(true)
    setMessage('')
    try {
      const [settings, health, update, governance] = await Promise.all([
        getSettings(),
        getHealth(),
        getUpdateStatus().catch(() => null),
        getRules().catch(() => null),
      ])
      if (update?.install_warning) setUpdateWarn(update.install_warning)
      else setUpdateWarn('')
      setBaseUrl(settings.llm_base_url)
      setModel(settings.llm_model)
      setChannel(settings.default_channel)
      setChannels(settings.channels.length > 0 ? settings.channels : ['cli'])
      setComing(settings.channels_coming)
      setHasKey(Boolean(settings.llm_api_key))
      setDemo(settings.demo)
      setServerOk(health.status === 'ok')
      setRuntime(health.runtime ?? null)
      setRules(governance?.rules ?? [])
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

  useEffect(() => {
    if (models.length === 0 || !baseUrl) return
    const match = models.find(
      (row) =>
        row.base_url.replace(/\/$/, '') === baseUrl.replace(/\/$/, '') && row.default_model === model,
    )
    setPreset(match?.name || 'Custom (URL)')
  }, [models, baseUrl, model])

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
    <div className="h-full min-h-0 overflow-y-auto">
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
            <Label htmlFor="llm-preset">LLM company (latest model)</Label>
            <select
              id="llm-preset"
              value={preset}
              onChange={(event) => {
                const name = event.target.value
                setPreset(name)
                const row = models.find((item) => item.name === name)
                if (!row) return
                if (row.base_url) setBaseUrl(row.base_url)
                if (row.default_model) setModel(row.default_model)
              }}
              className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
            >
              {(models.length > 0 ? models : [{ name: preset, base_url: '', default_model: '', docs: '', requires_api_key: true }]).map(
                (row) => (
                  <option key={row.name} value={row.name}>
                    {row.name}
                  </option>
                ),
              )}
            </select>
            {models.find((row) => row.name === preset)?.docs && (
              <p className="text-[11px] text-muted">
                <a
                  href={models.find((row) => row.name === preset)?.docs}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                >
                  Provider docs
                </a>
              </p>
            )}
          </div>
          <div className="space-y-1">
            <Label htmlFor="base-url">LLM base URL</Label>
            <Input id="base-url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="api-key">
              {demo ? 'Demo mode — no API key required' : `API key ${hasKey ? '(set)' : '(required for live completions)'}`}
            </Label>
            <div
              onClick={() => {
                if (demo) setMessage('Demo mode does not use an API key.')
              }}
            >
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

      {loadedOnce && (
        <Card className="space-y-3 p-5">
          <h2 className="text-sm font-semibold">Governance</h2>
          <p className="text-sm text-muted">
            The signed core enforces these rules. Flip <code>enforced</code> in the rules file to relax one. Purchases
            are simulated. Tor fetches need an allow when that rule is on.
          </p>
          {rules.length ? (
            <ul className="space-y-2 text-sm">
              {rules.map((rule) => (
                <li key={rule.id}>
                  <span className={rule.enforced ? 'text-accent' : 'text-muted'}>
                    {rule.enforced ? 'On' : 'Off'}
                  </span>
                  <span className="text-ink"> {rule.id}</span>
                  <div className="text-muted">{rule.description}</div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">Rules are not available.</p>
          )}
        </Card>
      )}

      {loadedOnce && (
        <Card className="space-y-3 p-5">
          <h2 className="text-sm font-semibold">Evolvable runtime</h2>
          <p className="text-sm text-muted">
            Node.js lives in your user data. The signed app never writes plugin files until you allow it in
            the macOS dialog.
          </p>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">Runtime</span>
            <span className={runtime?.ok ? 'text-accent' : 'text-muted'}>
              {runtime?.ok ? 'Online' : 'Offline'}
            </span>
          </div>
          {runtime?.plugins?.length ? (
            <ul className="space-y-1 text-sm text-ink">
              {runtime.plugins.map((plugin) => (
                <li key={plugin.name}>
                  {plugin.name}
                  {plugin.description ? <span className="text-muted"> — {plugin.description}</span> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">No runtime plugins loaded yet.</p>
          )}
        </Card>
      )}

      {loadedOnce && (
        <Card className="space-y-3 p-5">
          <h2 className="text-sm font-semibold">Updates</h2>
          <p className="text-sm text-muted">
            Official install is Universal.dmg → /Applications/Universal.app. Updates replace that copy only.
          </p>
          {updateWarn && <p className="text-sm text-amber-200">{updateWarn}</p>}
          <Button
            size="sm"
            variant="outline"
            disabled={checkingUpdate || applyingUpdate}
            onClick={async () => {
              setCheckingUpdate(true)
              setUpdateNote('')
              setPendingUpdate(null)
              try {
                const status = await getUpdateStatus()
                setUpdateWarn(status.install_warning || '')
                if (status.available && status.latest) {
                  setPendingUpdate({ latest: status.latest, current: status.current })
                } else {
                  setUpdateNote('No updates available')
                }
              } catch (err) {
                setUpdateNote(err instanceof Error ? err.message : 'Could not check for updates.')
              } finally {
                setCheckingUpdate(false)
              }
            }}
          >
            {checkingUpdate ? 'Checking…' : 'Check for Updates'}
          </Button>
          {updateNote && <p className="text-sm text-accent">{updateNote}</p>}
          {pendingUpdate && (
            <div className="space-y-2 rounded-md border border-border p-3">
              <p className="text-sm">
                Update available. Version {pendingUpdate.latest} (you have {pendingUpdate.current}). Download now?
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setPendingUpdate(null)} disabled={applyingUpdate}>
                  Later
                </Button>
                <Button
                  size="sm"
                  disabled={applyingUpdate}
                  onClick={async () => {
                    setApplyingUpdate(true)
                    try {
                      await applyUpdate()
                      setUpdateNote('Update installed. The app is relaunching…')
                      setPendingUpdate(null)
                    } catch (err) {
                      setUpdateNote(err instanceof Error ? err.message : 'Update failed.')
                    } finally {
                      setApplyingUpdate(false)
                    }
                  }}
                >
                  {applyingUpdate ? 'Downloading…' : 'Download now'}
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
    </div>
  )
}
