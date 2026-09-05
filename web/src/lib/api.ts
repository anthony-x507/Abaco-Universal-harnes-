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
  emoji?: string
  system_prompt?: string
  situation?: Situation
  has_api_key?: boolean
  llm_provider?: string
}

export type Situation = {
  agent_id: string
  agent: string
  phase: string
  objective: string
  current_step: string
  steps_remaining: string[]
  steps_completed: string[]
  steps_blocked: string[]
  obstacles: { step?: string; obstacle?: string }[]
  deviations: unknown[]
  alternatives: { step?: string; path?: string }[]
  attempts: number
  max_attempts: number
  team: string | null
  last_checkpoint: string | null
  proof_id?: string | null
}

export type Notice = {
  id: string
  agent_id: string
  kind: string
  message: string
  at: string
  acked?: boolean
}

export type ModelPreset = {
  company?: string
  name: string
  base_url: string
  default_model: string
  docs: string
  requires_api_key: boolean
  region?: string
  adapter?: string
}

export type Template = {
  id: string
  name: string
  description: string
  emoji?: string
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

export type RuntimePlugin = {
  name: string
  version?: string
  description?: string
}

export type RuntimeStatus = {
  ok: boolean
  url: string
  dir: string
  node?: string
  plugins: RuntimePlugin[]
}

export async function getHealth(): Promise<{
  status: string
  demo: boolean
  agents: number
  version?: string
  whisper?: boolean
  runtime?: RuntimeStatus
}> {
  return request('/health')
}

export async function getRuntime(): Promise<RuntimeStatus> {
  return request('/v1/runtime')
}

export type GovernanceRule = {
  id: string
  description: string
  enforced: boolean
}

export async function getRules(): Promise<{ version: string; file: string; rules: GovernanceRule[] }> {
  return request('/v1/rules')
}

export type UpdateStatus = {
  current: string
  latest: string | null
  available: boolean
  url: string | null
  release_notes: string
  repo: string
  reason: string
  can_apply: boolean
  in_applications: boolean
  install_warning: string
}

export async function getUpdateStatus(): Promise<UpdateStatus> {
  return request('/v1/update')
}

export async function applyUpdate(): Promise<{ ok: boolean; message: string }> {
  return request('/v1/update', { method: 'POST' })
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

export type ChatAttachment = {
  name: string
  mime: string
  data: string
  kind: 'file' | 'audio' | 'image'
  transcript?: string
}

export async function transcribeAudio(body: {
  name: string
  mime: string
  data: string
  model?: string
}): Promise<{ text: string }> {
  return request('/v1/transcribe', { method: 'POST', body: JSON.stringify({ model: 'tiny', ...body }) })
}

export async function startHostRecording(): Promise<{ status: string }> {
  return request('/v1/record/start', { method: 'POST', body: '{}' })
}

export async function stopHostRecording(): Promise<{ name: string; mime: string; data: string }> {
  return request('/v1/record/stop', { method: 'POST', body: '{}' })
}

export async function updateAgent(
  id: string,
  body: {
    name?: string
    emoji?: string
    channel?: string
    outbound_url?: string
    system_prompt?: string
    provider?: string
    llm_model?: string
    llm_api_key?: string
  },
): Promise<Agent> {
  return request(`/v1/agents/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
}

export async function createAgent(body: {
  template: string
  name?: string
  channel?: string
  outbound_url?: string
  provider?: string
  emoji?: string
  llm_model?: string
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

export async function getSituation(id: string): Promise<Situation> {
  return request(`/v1/agents/${id}/situation`)
}

export async function resetSituation(id: string): Promise<Situation> {
  return request(`/v1/agents/${id}/situation/reset`, { method: 'POST' })
}

export type ProofRequirement = {
  id: string
  text: string
}

export type ProofOracle = {
  requirement_id: string
  passed: boolean
  evidence: string
  oracle?: string
  at?: string
}

export type ProofChallenge = {
  requirement_id: string
  mutation: string
  still_holds: boolean
  at?: string
}

export type ProofSummary = {
  id: string
  agent_id?: string
  objective: string
  status: string
  requirements: ProofRequirement[]
  oracles: ProofOracle[]
  challenges: ProofChallenge[]
  sealed_at: string | null
  signature: string | null
  payload_hash: string | null
  verified: boolean
  quantum: boolean
  engine?: string
  updated_at?: string
}

export async function getAgentProof(id: string): Promise<ProofSummary | null> {
  const data = await request<{ proof: ProofSummary | null }>(`/v1/agents/${id}/proof`)
  return data.proof
}

export async function draftAgentProof(
  id: string,
  body: { objective: string; requirements: string[] },
): Promise<ProofSummary> {
  return request(`/v1/agents/${id}/proof`, { method: 'POST', body: JSON.stringify(body) })
}

export async function recordProofOracle(
  proofId: string,
  body: { requirement_id: string; passed: boolean; evidence: string },
): Promise<ProofSummary> {
  return request(`/v1/proofs/${proofId}/oracle`, { method: 'POST', body: JSON.stringify(body) })
}

export async function challengeProof(
  proofId: string,
  body: { requirement_id: string; mutation: string; still_holds: boolean },
): Promise<ProofSummary> {
  return request(`/v1/proofs/${proofId}/challenge`, { method: 'POST', body: JSON.stringify(body) })
}

export async function sealProof(proofId: string): Promise<ProofSummary> {
  return request(`/v1/proofs/${proofId}/seal`, { method: 'POST' })
}

export async function listNotifications(): Promise<Notice[]> {
  const data = await request<{ notifications: Notice[] }>('/v1/notifications')
  return data.notifications
}

export async function ackNotification(id: string): Promise<Notice> {
  return request(`/v1/notifications/${id}/ack`, { method: 'POST' })
}

export type DeepSeekRepo = {
  key?: string
  repo?: string
  name?: string
  full_name?: string
  description?: string
  stars?: number
  forks?: number
  updated_at?: string | null
  url?: string
  language?: string
  missing?: boolean
  error?: string
}

export type DeepSeekRelease = {
  repo: string
  tag: string
  name?: string
  body?: string
  published_at?: string | null
  url?: string
}

export type DeepSeekComparison = {
  feature: string
  status: string
  recommendation: string
  priority?: string
}

export type DeepSeekReport = {
  ok: boolean
  blocked?: boolean
  reason?: string
  scanned?: boolean
  scanned_at?: string | null
  harness: DeepSeekRepo | null
  coder?: DeepSeekRepo | null
  chat?: DeepSeekRepo | null
  new_releases: DeepSeekRelease[]
  updated_at?: string | null
  changes_detected?: { type?: string; message?: string }[]
  popularity?: { stars?: number; mention_count?: number; twitter?: string; source?: string } | null
  comparisons: DeepSeekComparison[]
  product?: string
}

export async function getDeepSeekReport(): Promise<DeepSeekReport> {
  return request('/v1/strategist/deepseek')
}

export async function scanDeepSeek(): Promise<DeepSeekReport> {
  return request('/v1/strategist/deepseek/scan', { method: 'POST' })
}

export type AuditSummary = {
  id?: string
  verdict?: string | null
  status?: string
  verified?: boolean
  quantum?: boolean
  signature?: string | null
  sealed_at?: string | null
  contract_id?: string
  objective?: string
  engine?: string
}

export async function getAudit(): Promise<AuditSummary | null> {
  const data = await request<{ audit: AuditSummary | null }>('/v1/audit')
  return data.audit
}

export async function runAudit(): Promise<AuditSummary> {
  return request('/v1/audit/run', { method: 'POST' })
}

export type Improvement = {
  id: string
  agent_id: string
  task: string
  original_plan?: string
  proposed_plan: string
  status: string
  created_at?: string
  updated_at?: string
}

export type NervousEvent = {
  at?: string
  kind: string
  message?: string
  agent_id?: string
}

export type NervousHealth = {
  bus?: string
  redis?: boolean
  nats?: boolean
  events?: number
  circuit?: { name?: string; state?: string; failures?: number }
  store?: string
}

export async function listImprovements(agentId: string): Promise<Improvement[]> {
  const data = await request<{ improvements: Improvement[] }>(`/v1/agents/${agentId}/improvements`)
  return data.improvements
}

export async function proposeImprovement(
  agentId: string,
  body: { task: string; proposed_plan: string; original_plan?: string },
): Promise<Improvement> {
  return request(`/v1/agents/${agentId}/improvements`, { method: 'POST', body: JSON.stringify(body) })
}

export async function acceptImprovement(id: string): Promise<Improvement> {
  return request(`/v1/improvements/${id}/accept`, { method: 'POST' })
}

export async function rejectImprovement(id: string): Promise<Improvement> {
  return request(`/v1/improvements/${id}/reject`, { method: 'POST' })
}

export async function listEvents(): Promise<{ events: NervousEvent[]; nervous: NervousHealth }> {
  return request('/v1/events')
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
  options?: { autonomous?: boolean; maxIterations?: number; attachments?: ChatAttachment[] },
): Promise<Agent> {
  const path = options?.autonomous ? `/v1/agents/${id}/run` : `/v1/agents/${id}/ask`
  const body: {
    prompt: string
    stream: boolean
    max_iterations?: number
    attachments?: ChatAttachment[]
  } = {
    prompt,
    stream: true,
  }
  if (options?.autonomous) {
    body.max_iterations = options.maxIterations ?? 5
  }
  if (options?.attachments?.length) {
    body.attachments = options.attachments
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
