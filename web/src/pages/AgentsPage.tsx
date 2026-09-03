import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import {
  createAgent,
  deleteAgent,
  listAgents,
  listTemplates,
  startAgent,
  stopAgent,
  type Agent,
  type Template,
} from '../lib/api'

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('general')
  const [channel, setChannel] = useState('cli')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState('')
  const [error, setError] = useState('')

  const refresh = async () => {
    const [rows, tpls] = await Promise.all([listAgents(), listTemplates()])
    setAgents(rows)
    setTemplates(tpls)
    if (tpls.length > 0 && !tpls.some((item) => item.id === template)) {
      setTemplate(tpls[0].id)
    }
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        await refresh()
        if (!cancelled) setError('')
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load agents.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const run = async (label: string, work: () => Promise<void>) => {
    setWorking(label)
    setError('')
    try {
      await work()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed.`)
    } finally {
      setWorking('')
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4 md:p-6">
      <div>
        <h1 className="text-xl font-semibold">Agents</h1>
        <p className="text-sm text-muted">
          Create, start, stop, and delete agents in this server process. There is no pause state.
        </p>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          <span>{error}</span>
          <Button
            size="sm"
            variant="outline"
            disabled={loading}
            onClick={() =>
              void (async () => {
                setLoading(true)
                try {
                  await refresh()
                  setError('')
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Could not load agents.')
                } finally {
                  setLoading(false)
                }
              })()
            }
          >
            Retry
          </Button>
        </div>
      )}

      <Card className="p-4">
        <h2 className="mb-3 text-sm font-medium">Create agent</h2>
        <form
          className="grid gap-3 md:grid-cols-[1fr_10rem_8rem_auto] md:items-end"
          onSubmit={(event) => {
            event.preventDefault()
            void run('create', async () => {
              await createAgent({
                template,
                name: name.trim() || undefined,
                channel,
              })
              setName('')
            })
          }}
        >
          <div className="space-y-1">
            <Label htmlFor="agent-name">Name</Label>
            <Input id="agent-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="optional" />
          </div>
          <div className="space-y-1">
            <Label htmlFor="agent-template">Template</Label>
            <select
              id="agent-template"
              value={template}
              onChange={(event) => setTemplate(event.target.value)}
              className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
            >
              {templates.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="agent-channel">Channel</Label>
            <select
              id="agent-channel"
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
              className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
            >
              <option value="cli">cli</option>
              <option value="webhook" disabled>
                webhook (later)
              </option>
            </select>
          </div>
          <Button type="submit" disabled={working === 'create'}>
            {working === 'create' ? 'Creating…' : 'Create'}
          </Button>
        </form>
      </Card>

      <Card>
        {loading ? (
          <p className="p-4 text-sm text-muted">Loading agents…</p>
        ) : agents.length === 0 ? (
          <p className="p-4 text-sm text-muted">No agents in this process. Create one above.</p>
        ) : (
          <ul className="divide-y divide-border">
            {agents.map((agent) => (
              <li key={agent.id} className="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{agent.name}</span>
                    <Badge className={agent.state === 'running' ? 'border-accent/40 text-accent' : ''}>
                      {agent.state}
                    </Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    {agent.template_id} · {agent.channel} · {agent.id}
                    {agent.plugins.length > 0 ? ` · ${agent.plugins.join(', ')}` : ''}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    to={`/?agent=${agent.id}`}
                    className="inline-flex h-8 items-center rounded-md border border-border px-2.5 text-xs text-ink hover:bg-surface-2"
                  >
                    Open chat
                  </Link>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={working === `start-${agent.id}` || agent.state === 'running'}
                    onClick={() => void run(`start-${agent.id}`, async () => { await startAgent(agent.id) })}
                  >
                    Start
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={working === `stop-${agent.id}` || agent.state !== 'running'}
                    onClick={() => void run(`stop-${agent.id}`, async () => { await stopAgent(agent.id) })}
                  >
                    Stop
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    disabled={working === `delete-${agent.id}`}
                    onClick={() => void run(`delete-${agent.id}`, async () => { await deleteAgent(agent.id) })}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
