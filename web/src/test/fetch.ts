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
  emoji: '🤖',
  system_prompt: 'Be helpful.',
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
    health: {
      status: 'ok',
      demo: true,
      agents: 1,
      whisper: true,
      runtime: { ok: false, url: 'http://127.0.0.1:43126', dir: '', plugins: [] },
    },
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
    rules: {
      version: '1.0',
      file: '/tmp/abaco_rules.json',
      rules: [
        { id: 'no_system_delete', description: 'Do not delete system files without confirmation.', enforced: true },
        { id: 'ask_before_self_modify', description: 'Ask before changing the evolvable runtime.', enforced: true },
        { id: 'no_external_sharing', description: 'Do not share user data with third parties.', enforced: true },
        { id: 'no_ui_modification', description: 'Do not change the signed UI without consent.', enforced: true },
        { id: 'no_purchase_without_permission', description: 'Never spend stored card details without an explicit allow.', enforced: true },
        { id: 'no_dark_web_without_permission', description: 'Use Tor only after the user allows that fetch.', enforced: true },
        { id: 'navigator_auto_notify', description: 'Notify the user when a mission is blocked.', enforced: true },
        { id: 'navigator_allow_deviations', description: 'Ask before a planned step is replaced.', enforced: true },
        { id: 'navigator_no_false_promises', description: 'Do not claim a result you did not produce.', enforced: true },
        { id: 'memory_share_between_agents', description: 'Share team notes only after an explicit allow.', enforced: false },
        { id: 'strategist_deepseek_tracking', description: 'Scan official DeepSeek Harness repos and keep a comparison report.', enforced: true },
        { id: 'sentinel_proof_required', description: 'Last mission step stays verifying until a Sentinel Proof is sealed.', enforced: false },
      ],
    },
    deepseek: {
      ok: true,
      blocked: false,
      scanned: true,
      scanned_at: '2026-09-04T12:00:00+00:00',
      harness: {
        full_name: 'deepseek-ai/deepseek-harness',
        stars: 111894,
        updated_at: '2026-09-01T00:00:00Z',
        description: 'Everything is a plugin.',
        url: 'https://github.com/deepseek-ai/deepseek-harness',
      },
      new_releases: [
        {
          repo: 'harness',
          tag: 'v0.1.0',
          name: 'Developer preview',
          body: 'Everything is a plugin.',
          published_at: '2026-08-13T00:00:00Z',
        },
      ],
      comparisons: [
        {
          feature: 'plugin_surface',
          status: 'DSH makes the UI and agent loop plugins. Universal keeps a signed factory.',
          recommendation: 'Watch sandbox and schedule ideas. Do not move the factory into Node.',
        },
      ],
      popularity: { mention_count: 2, twitter: 'not_available' },
    },
    situation: {
      agent_id: 'a1',
      agent: 'alpha',
      phase: 'idle',
      objective: '',
      current_step: '',
      steps_remaining: [] as string[],
      steps_completed: [] as string[],
      steps_blocked: [] as string[],
      obstacles: [] as { step?: string; obstacle?: string }[],
      deviations: [] as unknown[],
      alternatives: [] as { step?: string; path?: string }[],
      attempts: 0,
      max_attempts: 3,
      team: null,
      last_checkpoint: null,
      proof_id: null,
    },
    proof: { proof: null as null },
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
    if (path === '/v1/rules') return jsonResponse(catalog.rules)
    if (path === '/v1/notifications') return jsonResponse({ notifications: [] })
    if (path === '/v1/templates') return jsonResponse(catalog.templates)
    if (path === '/v1/agents') return jsonResponse(catalog.agents)
    if (path === `/v1/agents/${agentFixture.id}`) return jsonResponse(catalog.agent)
    if (path === `/v1/agents/${agentFixture.id}/situation`) return jsonResponse(catalog.situation)
    if (path === `/v1/agents/${agentFixture.id}/proof`) return jsonResponse(catalog.proof)
    if (path === '/v1/strategist/deepseek' || path === '/v1/strategist/deepseek/scan') {
      return jsonResponse(catalog.deepseek)
    }
    return jsonResponse({ error: `unmocked ${path}` }, 404)
  }
  globalThis.fetch = fetchMock as typeof fetch
  return { calls, catalog }
}
