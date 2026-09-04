export type AgentState = 'created' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error'

export type HistoryTurn = {
  role: string
  content: string
  failed?: boolean
}

export type Usage = {
  prompt_tokens: number
  completion_tokens: number
  estimated_cost: number
  last_model: string
  last_latency_ms: number
  calls: number
}

export type Agent = {
  id: string
  name: string
  template_id: string
  state: AgentState
  channel: string
  plugins: string[]
  plugin_labels?: string[]
  created_at: string
  model: string
  history?: HistoryTurn[]
  answer?: string
  outbound_url?: string
  usage?: Usage
}

export type ModelPreset = {
  name: string
  base_url: string
  default_model: string
  docs: string
  requires_api_key: boolean
}

export type Template = {
  id: string
  name: string
  description: string
}

export type Settings = {
  llm_base_url: string
  llm_api_key: string
  llm_model: string
  demo: boolean
  default_channel: string
  channels: string[]
  channels_coming: string[]
}

export const PROVIDER_ERROR_COPY: Record<number, string> = {
  401: 'Invalid API key. Please check Settings.',
  408: 'Request timed out. Try again.',
  429: 'Rate limit exceeded. Wait a moment.',
  503: 'Cannot reach LLM service. Check your connection.',
}

export function friendlyError(err: unknown): string {
  if (err instanceof ApiError) {
    return PROVIDER_ERROR_COPY[err.status] ?? err.message
  }
  if (err instanceof Error) return err.message
  return 'Something went wrong. Try again.'
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function parseError(response: Response): Promise<string> {
  const text = await response.text()
  try {
    const json = JSON.parse(text) as { error?: string; detail?: string }
    return json.error || json.detail || text || response.statusText
  } catch {
    return text || response.statusText
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response))
  }
  return response.json() as Promise<T>
}

export async function getHealth(): Promise<{ status: string; demo: boolean; agents: number }> {
  return request('/health')
}

export async function listModels(): Promise<ModelPreset[]> {
  const data = await request<{ models: ModelPreset[] }>('/v1/models')
  return data.models
}

export async function listTemplates(): Promise<Template[]> {
  const data = await request<{ templates: Template[] }>('/v1/templates')
  return data.templates
}

export async function getSettings(): Promise<Settings> {
  return request('/v1/settings')
}

export async function updateSettings(body: {
  llm_base_url?: string
  llm_api_key?: string
  llm_model?: string
  default_channel?: string
}): Promise<Settings> {
  return request('/v1/settings', { method: 'PUT', body: JSON.stringify(body) })
}

export async function listAgents(): Promise<Agent[]> {
  const data = await request<{ agents: Agent[] }>('/v1/agents')
  return data.agents
}

export async function getAgent(id: string): Promise<Agent> {
  return request(`/v1/agents/${id}`)
}

export async function createAgent(body: {
  template: string
  name?: string
  channel?: string
  outbound_url?: string
  provider?: string
}): Promise<Agent> {
  return request('/v1/agents', { method: 'POST', body: JSON.stringify(body) })
}

export async function startAgent(id: string): Promise<Agent> {
  return request(`/v1/agents/${id}/start`, { method: 'POST' })
}

export async function stopAgent(id: string): Promise<Agent> {
  return request(`/v1/agents/${id}/stop`, { method: 'POST' })
}

export async function deleteAgent(id: string): Promise<void> {
  await request(`/v1/agents/${id}`, { method: 'DELETE' })
}

export async function resetAgent(id: string): Promise<Agent> {
  return request(`/v1/agents/${id}/reset`, { method: 'POST' })
}

export async function askAgent(id: string, prompt: string): Promise<Agent> {
  return request(`/v1/agents/${id}/ask`, {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}

export async function downloadAgentZip(id: string): Promise<void> {
  const response = await fetch(`/v1/agents/${id}/deploy`, { method: 'POST' })
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response))
  }
  const blob = await response.blob()
  const header = response.headers.get('content-disposition') || ''
  const match = header.match(/filename="?([^"]+)"?/i)
  const filename = match?.[1] || `agent-${id}.zip`
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export type StreamStatusEvent = {
  type: 'tool_execution' | 'delegating'
  tool?: string
  target?: string
}

function parseSseBlock(
  part: string,
  onDelta: (text: string) => void,
  onStatus?: (event: StreamStatusEvent) => void,
): (Agent & { done?: boolean }) | null {
  const line = part
    .split('\n')
    .filter((row) => row.startsWith('data:'))
    .map((row) => row.slice(5).trim())
    .join('')
  if (!line) return null
  const event = JSON.parse(line) as Agent & {
    type?: string
    text?: string
    tool?: string
    target?: string
    done?: boolean
    error?: string
    status?: number
  }
  if (event.error) {
    throw new ApiError(event.status ?? 502, event.error)
  }
  if (event.type === 'tool_execution' || event.type === 'delegating') {
    onStatus?.({ type: event.type, tool: event.tool, target: event.target })
    return null
  }
  if (event.text) {
    onDelta(event.text)
  }
  if (event.done) {
    return event
  }
  return null
}

export async function askAgentStream(
  id: string,
  prompt: string,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
  onStatus?: (event: StreamStatusEvent) => void,
  options?: { autonomous?: boolean; maxIterations?: number },
): Promise<Agent> {
  const path = options?.autonomous ? `/v1/agents/${id}/run` : `/v1/agents/${id}/ask`
  const body: { prompt: string; stream: boolean; max_iterations?: number } = {
    prompt,
    stream: true,
  }
  if (options?.autonomous) {
    body.max_iterations = options.maxIterations ?? 5
  }
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response))
  }
  if (!response.body) {
    throw new ApiError(502, 'Stream had no body')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let donePayload: Agent | null = null
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const event = parseSseBlock(part, onDelta, onStatus)
      if (event) donePayload = event
    }
  }
  if (buffer.trim()) {
    const event = parseSseBlock(buffer, onDelta, onStatus)
    if (event) donePayload = event
  }
  if (!donePayload) {
    throw new ApiError(502, 'Stream ended without a final agent payload')
  }
  return donePayload
}
