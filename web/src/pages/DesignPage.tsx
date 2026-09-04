import {
  Bot,
  Circle,
  Code2,
  FileText,
  Globe,
  Layers,
  LayoutGrid,
  PencilRuler,
  Puzzle,
  Square,
  Wrench,
} from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { CreateAgentForm } from '../components/CreateAgentForm'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Textarea } from '../components/ui/textarea'
import { useActivity } from '../lib/activity'
import { useAskSession } from '../lib/ask-session'
import { addSkill, loadSkills, makeSkillId, type Skill, type SkillStep } from '../lib/skills'
import { cn } from '../lib/utils'

type ToolId =
  | 'agent'
  | 'pdf'
  | 'system'
  | 'website'
  | 'platform'
  | 'code'
  | 'plugins'
  | 'modify'
  | 'skill'

type ToolTile = {
  id: ToolId
  title: string
  hint: string
  icon: ReactNode
}

const TILES: ToolTile[] = [
  { id: 'agent', title: 'Create an agent', hint: 'Face, name, template', icon: <Bot size={22} /> },
  { id: 'pdf', title: 'Create a PDF', hint: 'Brief → document draft', icon: <FileText size={22} /> },
  { id: 'system', title: 'Create a system', hint: 'Name the parts first', icon: <Layers size={22} /> },
  { id: 'website', title: 'Create a website', hint: 'Pages and purpose', icon: <Globe size={22} /> },
  { id: 'platform', title: 'Create a platform', hint: 'Who it serves', icon: <LayoutGrid size={22} /> },
  { id: 'code', title: 'Create code', hint: 'Language and outcome', icon: <Code2 size={22} /> },
  { id: 'plugins', title: 'Plugins', hint: 'Tools agents already have', icon: <Puzzle size={22} /> },
  { id: 'modify', title: 'Modify systems', hint: 'Change an existing setup', icon: <Wrench size={22} /> },
  { id: 'skill', title: 'Teach skill', hint: 'Record the steps once', icon: <Circle size={22} className="fill-red-400 text-red-400" /> },
]

const STEP_PRESETS = ['Click', 'Type', 'Scroll', 'Wait', 'Open menu', 'Submit']

export function DesignPage() {
  const navigate = useNavigate()
  const { showToast } = useAskSession()
  const { pushActivity } = useActivity()
  const [selected, setSelected] = useState<ToolId | null>(null)
  const [intent, setIntent] = useState('')
  const [skills, setSkills] = useState<Skill[]>(() => loadSkills())

  const selectedTile = TILES.find((tile) => tile.id === selected) ?? null

  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-8 md:py-12">
        <header className="flex items-end justify-between gap-4">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted">Herramientas</p>
            <h1 className="font-serif text-3xl tracking-tight text-ink md:text-4xl">Design</h1>
          </div>
          <p className="max-w-xs text-right text-xs text-muted">
            Creation lives here. Chat stays quiet. Pick a model when you create the agent.
          </p>
        </header>

        <section className="text-center">
          <h2 className="font-serif text-3xl text-ink md:text-[2.6rem]">What should we create?</h2>
          <div className="glass-panel mx-auto mt-6 max-w-2xl rounded-[28px] p-3 text-left">
            <Textarea
              value={intent}
              onChange={(event) => setIntent(event.target.value)}
              placeholder="Describe an idea, or pick a tile below."
              rows={2}
              className="min-h-[4.5rem] resize-none border-0 bg-transparent px-3 py-2 shadow-none focus-visible:ring-0"
            />
          </div>
        </section>

        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {TILES.map((tile) => (
            <li key={tile.id}>
              <button
                type="button"
                onClick={() => setSelected(tile.id)}
                className={cn(
                  'flex h-full w-full flex-col items-start gap-3 rounded-2xl border px-3 py-4 text-left transition-colors',
                  selected === tile.id
                    ? 'border-accent/50 bg-white/8'
                    : 'border-white/8 bg-white/4 hover:border-white/16 hover:bg-white/7',
                )}
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-black/30 text-ink">
                  {tile.icon}
                </span>
                <span className="text-sm font-medium">{tile.title}</span>
                <span className="text-[11px] leading-snug text-muted">{tile.hint}</span>
              </button>
            </li>
          ))}
        </ul>

        {selectedTile && (
          <section className="glass-panel space-y-5 rounded-[28px] p-5 md:p-6">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted">Design</p>
              <h3 className="mt-1 font-serif text-2xl">{selectedTile.title}</h3>
            </div>
            {selected === 'agent' && (
              <CreateAgentForm
                submitLabel="Create agent"
                onCreated={(agent) => {
                  pushActivity(`Created agent ${agent.emoji || '💬'} ${agent.name}`, 'team')
                  showToast(`${agent.name} is ready. Open Chat to talk to it.`)
                  navigate(`/?agent=${agent.id}`)
                }}
              />
            )}
            {selected === 'skill' && (
              <SkillRecorder
                intent={intent}
                onCreated={(skill) => {
                  setSkills(loadSkills())
                  pushActivity(`Skill ready: ${skill.title} (${skill.steps.length} steps)`, 'skill')
                }}
              />
            )}
            {selected === 'pdf' && (
              <DraftTool
                titleLabel="PDF title"
                bodyLabel="What should the document cover?"
                action="Create PDF draft"
                onSubmit={(title, body) => {
                  pushActivity(`PDF draft started: ${title}`, 'design')
                  showToast(`PDF draft “${title}” is on the board. Open Chat to finish it with an agent.`)
                  void body
                }}
              />
            )}
            {selected === 'system' && (
              <DraftTool
                titleLabel="System name"
                bodyLabel="Parts, owners, and what must stay true"
                action="Create system outline"
                onSubmit={(title) => {
                  pushActivity(`System outline: ${title}`, 'design')
                  showToast(`System “${title}” is outlined. Chat can take the next pass.`)
                }}
              />
            )}
            {selected === 'website' && (
              <DraftTool
                titleLabel="Site name"
                bodyLabel="Audience, pages, and the first action"
                action="Create website brief"
                onSubmit={(title) => {
                  pushActivity(`Website brief: ${title}`, 'design')
                  showToast(`Website brief “${title}” is ready for an agent.`)
                }}
              />
            )}
            {selected === 'platform' && (
              <DraftTool
                titleLabel="Platform name"
                bodyLabel="Who uses it, and what they do on day one"
                action="Create platform brief"
                onSubmit={(title) => {
                  pushActivity(`Platform brief: ${title}`, 'design')
                  showToast(`Platform “${title}” is sketched.`)
                }}
              />
            )}
            {selected === 'code' && (
              <DraftTool
                titleLabel="What to build"
                bodyLabel="Language, constraints, and the first file"
                action="Create code brief"
                onSubmit={(title) => {
                  pushActivity(`Code brief: ${title}`, 'design')
                  showToast(`Code brief “${title}” is ready.`)
                }}
              />
            )}
            {selected === 'plugins' && (
              <div className="space-y-3 text-sm text-muted">
                <p>
                  Every agent already carries terminal, speech, vision, search, and scrape. Plugin work is not a
                  second factory — it is a request you send from Chat.
                </p>
                <Button
                  onClick={() => {
                    pushActivity('Opened plugin notes from Design', 'design')
                    showToast('Plugin changes go through Chat or Agents. Nothing extra is installed here.')
                  }}
                >
                  Note it and return to Chat
                </Button>
              </div>
            )}
            {selected === 'modify' && (
              <DraftTool
                titleLabel="What to change"
                bodyLabel="Current behavior, and the change you want"
                action="Create change note"
                onSubmit={(title) => {
                  pushActivity(`Modify systems: ${title}`, 'design')
                  showToast(`Change note “${title}” is waiting under the write bar in Chat.`)
                }}
              />
            )}
          </section>
        )}

        {skills.length > 0 && (
          <section>
            <div className="mb-3 flex items-center gap-2 text-sm text-muted">
              <PencilRuler size={14} />
              Skills taught in this browser
            </div>
            <ul className="space-y-2">
              {skills.map((skill) => (
                <li key={skill.id} className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3">
                  <div className="text-sm font-medium">{skill.title}</div>
                  <p className="text-xs text-muted">
                    {skill.steps.length} steps
                    {skill.url ? ` · ${skill.url}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  )
}

function DraftTool({
  titleLabel,
  bodyLabel,
  action,
  onSubmit,
}: {
  titleLabel: string
  bodyLabel: string
  action: string
  onSubmit: (title: string, body: string) => void
}) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault()
        const nextTitle = title.trim()
        if (!nextTitle) return
        onSubmit(nextTitle, body.trim())
        setTitle('')
        setBody('')
      }}
    >
      <div>
        <Label htmlFor={`draft-${titleLabel}`}>{titleLabel}</Label>
        <Input
          id={`draft-${titleLabel}`}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={titleLabel}
        />
      </div>
      <div>
        <Label htmlFor={`draft-body-${titleLabel}`}>{bodyLabel}</Label>
        <Textarea
          id={`draft-body-${titleLabel}`}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder={bodyLabel}
          rows={4}
        />
      </div>
      <Button type="submit" disabled={!title.trim()}>
        {action}
      </Button>
    </form>
  )
}

function SkillRecorder({
  intent,
  onCreated,
}: {
  intent: string
  onCreated: (skill: Skill) => void
}) {
  const { showToast } = useAskSession()
  const { pushActivity } = useActivity()
  const [url, setUrl] = useState('https://example.com')
  const [frameUrl, setFrameUrl] = useState('')
  const [recording, setRecording] = useState(false)
  const [steps, setSteps] = useState<SkillStep[]>([])
  const [note, setNote] = useState('')
  const [pending, setPending] = useState(false)
  const [title, setTitle] = useState(intent.trim() || '')

  const addStep = (action: string) => {
    const clean = action.trim()
    if (!clean) return
    setSteps((current) => [
      ...current,
      { id: makeSkillId(), at: Date.now(), action: clean },
    ])
    setNote('')
  }

  const openUrl = (next = url, record = recording) => {
    const target = next.trim()
    if (!target) return
    setFrameUrl(target)
    if (record) addStep(`Opened ${target}`)
  }

  const startRecording = () => {
    setPending(false)
    setRecording(true)
    const target = (frameUrl || url).trim()
    if (target) openUrl(target, true)
    else addStep('Started recording')
    pushActivity('Skill recording started. Do the steps in the browser frame.', 'skill')
    showToast('Recording. Do the steps, then stop.')
  }

  const stopRecording = () => {
    setRecording(false)
    setPending(true)
    pushActivity('Recording stopped. Create a skill from those steps.', 'skill')
    showToast('Recording stopped. Create the skill below.')
  }

  const createSkill = () => {
    const skill: Skill = {
      id: makeSkillId(),
      title: title.trim() || `Skill from ${new Date().toLocaleString()}`,
      url: frameUrl || url,
      steps,
      createdAt: new Date().toISOString(),
    }
    addSkill(skill)
    onCreated(skill)
    setPending(false)
    setSteps([])
    setTitle('')
    showToast(`Skill “${skill.title}” is saved. People can run those steps next.`)
  }

  const previewSrc = useMemo(() => {
    if (!frameUrl) return ''
    try {
      const parsed = new URL(frameUrl)
      return parsed.href
    } catch {
      return frameUrl.startsWith('http') ? frameUrl : `https://${frameUrl}`
    }
  }, [frameUrl])

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Press record, work in the browser frame, add the clicks you take, then stop. Universal turns that pass into a
        skill the team can reuse.
      </p>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/40">
        <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
          <span className={cn('h-2.5 w-2.5 rounded-full', recording ? 'bg-red-400' : 'bg-muted')} />
          <Input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                openUrl()
              }
            }}
            placeholder="https://"
            aria-label="Browser address"
            className="h-8 bg-black/30"
          />
          <Button size="sm" variant="outline" onClick={() => openUrl()}>
            Go
          </Button>
          <Button
            size="sm"
            variant={recording ? 'danger' : 'default'}
            onClick={() => (recording ? stopRecording() : startRecording())}
            aria-pressed={recording}
          >
            {recording ? <Square size={14} /> : <Circle size={14} className="fill-current" />}
            {recording ? 'Stop' : 'Record'}
          </Button>
        </div>
        <div className="relative min-h-[280px] bg-[#07090d]">
          {previewSrc ? (
            <iframe title="Skill recording browser" src={previewSrc} className="h-[280px] w-full bg-white" />
          ) : (
            <div className="flex h-[280px] flex-col items-center justify-center gap-2 px-6 text-center">
              <Circle size={36} className={recording ? 'fill-red-400 text-red-400' : 'text-muted'} />
              <p className="text-sm font-medium">Browser for teaching a skill</p>
              <p className="text-xs text-muted">
                Enter a URL, press Record, then do the steps. Some sites refuse to load in a frame — keep adding the
                steps yourself.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {STEP_PRESETS.map((label) => (
          <Button
            key={label}
            size="sm"
            variant="outline"
            disabled={!recording}
            onClick={() => addStep(label)}
          >
            {label}
          </Button>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder={recording ? 'Describe the step you just took' : 'Start recording to add steps'}
          disabled={!recording}
          aria-label="Skill step"
        />
        <Button size="sm" variant="outline" disabled={!recording || !note.trim()} onClick={() => addStep(note)}>
          Add step
        </Button>
      </div>

      <ol className="space-y-1 text-sm">
        {steps.length === 0 ? (
          <li className="text-muted">No steps yet.</li>
        ) : (
          steps.map((step, index) => (
            <li key={step.id} className="rounded-lg bg-white/4 px-3 py-1.5">
              <span className="mr-2 text-xs text-muted">{index + 1}</span>
              {step.action}
            </li>
          ))
        )}
      </ol>

      {pending && (
        <div
          role="status"
          className="space-y-3 rounded-2xl border border-accent/30 bg-accent/10 p-4"
        >
          <p className="text-sm">
            Recording stopped. Create a skill from these {steps.length} step{steps.length === 1 ? '' : 's'}?
          </p>
          <div>
            <Label htmlFor="skill-title">Skill name</Label>
            <Input
              id="skill-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Name this skill"
            />
          </div>
          <div className="flex gap-2">
            <Button onClick={createSkill} disabled={steps.length === 0}>
              Create skill
            </Button>
            <Button variant="outline" onClick={() => setPending(false)}>
              Not now
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
