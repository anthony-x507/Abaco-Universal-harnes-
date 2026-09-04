export type Json = Record<string, unknown>

export const agentFixture = {
  id: 'a1',
  name: 'alpha',
  template_id: 'general',
  state: 'running',
  channel: 'cli',
  plugins: [] as string[],
  plugin_labels: [] as string[],
  created_at: '2026-09-03T00:00:00+00:00',
  model: 'demo-echo',
  history: [] as { role: string; content: string; failed?: boolean }[],
  usage: {
    prompt_tokens: 0,
    completion_tokens: 0,
    estimated_cost: 0,
    last_model: '',
    last_latency_ms: 0,
    calls: 0,
  },
}

export function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function sseResponse(blocks: string[]) {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      for (const block of blocks) {
        controller.enqueue(encoder.encode(block.endsWith('\n\n') ? block : `${block}\n\n`))
      }
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

export function defaultCatalog() {
  return {
    health: { status: 'ok', demo: true, agents: 1 },
    settings: {
      llm_base_url: 'https://api.openai.com/v1',
      llm_api_key: '',
      llm_model: 'gpt-4o-mini',
      demo: true,
      default_channel: 'cli',
      channels: ['cli', 'webhook'],
      channels_coming: [] as string[],
    },
    templates: {
      templates: [
        { id: 'general', name: 'General', description: 'Everyday questions.', emoji: '💬' },
        { id: 'researcher', name: 'Researcher', description: 'Research face.', emoji: '🔎' },
        { id: 'coder', name: 'Coder', description: 'Code face.', emoji: '💻' },
      ],
    },
    agents: { agents: [{ ...agentFixture }] },
    agent: { ...agentFixture },
    update: {
      current: '1.0.0',
      latest: null,
      available: false,
      url: null,
      release_notes: '',
      repo: 'anthony-x507/Abaco-Universal-harnes-',
      reason: 'Already up to date.',
      can_apply: false,
      in_applications: true,
      install_warning: '',
    },
    models: {
      models: [
        {
          name: 'OpenAI (GPT-5.6 Sol)',
          company: 'OpenAI',
          base_url: 'https://api.openai.com/v1',
          default_model: 'gpt-5.6-sol',
          docs: 'https://platform.openai.com/docs/models',
          requires_api_key: true,
        },
        {
          name: 'DeepSeek (V4 Pro)',
          company: 'DeepSeek',
          base_url: 'https://api.deepseek.com/v1',
          default_model: 'deepseek-v4-pro',
          docs: 'https://api-docs.deepseek.com/',
          requires_api_key: true,
        },
        {
          name: 'Custom (URL)',
          base_url: '',
          default_model: 'custom-model',
          docs: '',
          requires_api_key: true,
        },
      ],
    },
  }
}

export function installFetchMock(
  route: (path: string, init: RequestInit | undefined) => Response | Promise<Response> | null,
) {
  const calls: { path: string; init?: RequestInit }[] = []
  const catalog = defaultCatalog()
  const fetchMock = async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input), 'http://127.0.0.1').pathname
    calls.push({ path, init })
    const custom = await route(path, init)
    if (custom) return custom
    if (path === '/health') return jsonResponse(catalog.health)
    if (path === '/v1/settings') return jsonResponse(catalog.settings)
    if (path === '/v1/models') return jsonResponse(catalog.models)
    if (path === '/v1/update') return jsonResponse(catalog.update)
    if (path === '/v1/templates') return jsonResponse(catalog.templates)
    if (path === '/v1/agents') return jsonResponse(catalog.agents)
    if (path === `/v1/agents/${agentFixture.id}`) return jsonResponse(catalog.agent)
    return jsonResponse({ error: `unmocked ${path}` }, 404)
  }
  globalThis.fetch = fetchMock as typeof fetch
  return { calls, catalog }
}
