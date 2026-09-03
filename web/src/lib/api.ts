export type AgentState = 'created' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error'

export type HistoryTurn = {
  role: string
  content: string
}

export type Agent = {
  id: string
  name: string
  template_id: string
  state: AgentState
  channel: string
  plugins: string[]
  created_at: string
  model: string
  history?: HistoryTurn[]
  answer?: string
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

export async function askAgent(id: string, prompt: string): Promise<Agent> {
  return request(`/v1/agents/${id}/ask`, {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}
