import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ActivityProvider } from '../lib/activity'
import { AskSessionProvider } from '../lib/ask-session'
import { ChatPage } from './ChatPage'
import { agentFixture, installFetchMock, jsonResponse, sseResponse } from '../test/fetch'

function renderChat() {
  return render(
    <MemoryRouter initialEntries={['/?agent=a1']}>
      <AskSessionProvider>
        <ActivityProvider>
          <ChatPage />
        </ActivityProvider>
      </AskSessionProvider>
    </MemoryRouter>,
  )
}

function askBody(init?: RequestInit) {
  return JSON.parse(String(init?.body ?? '{}')) as { prompt?: string; stream?: boolean }
}

describe('Chat page quality tests', () => {
  it('T14 Send posts /v1/agents/{id}/ask with stream true', async () => {
    const user = userEvent.setup()
    const { calls } = installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/ask' && init?.method === 'POST') {
        return sseResponse([
          'data: {"text":"ok"}',
          `data: ${JSON.stringify({ ...agentFixture, history: [{ role: 'user', content: 'hello' }, { role: 'assistant', content: 'ok' }], answer: 'ok', done: true })}`,
        ])
      }
      return null
    })

    renderChat()
    const box = await screen.findByPlaceholderText('How can I help you today?')
    await user.type(box, 'hello')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(calls.some((call) => call.path === '/v1/agents/a1/ask')).toBe(true)
    })
    const ask = calls.find((call) => call.path === '/v1/agents/a1/ask' && call.init?.method === 'POST')
    expect(ask).toBeTruthy()
    expect(askBody(ask?.init)).toEqual({ prompt: 'hello', stream: true })
    expect(screen.getByTestId('usage-meter')).toHaveTextContent('Tokens: 0 | Cost: $0.000')
  })

  it('Auto toggle posts /v1/agents/{id}/run', async () => {
    const user = userEvent.setup()
    const { calls } = installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/run' && init?.method === 'POST') {
        return sseResponse([
          'data: {"text":"ok"}',
          `data: ${JSON.stringify({
            ...agentFixture,
            history: [
              { role: 'user', content: 'investigate and summarize' },
              { role: 'assistant', content: 'ok' },
            ],
            answer: 'ok',
            done: true,
            usage: {
              prompt_tokens: 1000,
              completion_tokens: 234,
              estimated_cost: 0.002,
              last_model: 'demo-echo',
              last_latency_ms: 1,
              calls: 1,
            },
          })}`,
        ])
      }
      return null
    })

    renderChat()
    const auto = await screen.findByRole('button', { name: 'Auto' })
    expect(auto).toHaveAttribute('aria-pressed', 'false')
    await user.click(auto)
    expect(auto).toHaveAttribute('aria-pressed', 'true')
    await user.type(await screen.findByPlaceholderText('How can I help you today?'), 'investigate and summarize')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => {
      expect(calls.some((call) => call.path === '/v1/agents/a1/run')).toBe(true)
    })
    const run = calls.find((call) => call.path === '/v1/agents/a1/run' && call.init?.method === 'POST')
    expect(JSON.parse(String(run?.init?.body))).toEqual({
      prompt: 'investigate and summarize',
      stream: true,
      max_iterations: 5,
    })
    expect(await screen.findByTestId('usage-meter')).toHaveTextContent('Tokens: 1,234 | Cost: $0.002')
  })

  it('shows an ephemeral tool banner that is not a chat turn', async () => {
    const user = userEvent.setup()
    let releaseToken: (() => void) | undefined
    const hold = new Promise<void>((resolve) => {
      releaseToken = resolve
    })
    installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/ask' && init?.method === 'POST') {
        const encoder = new TextEncoder()
        const stream = new ReadableStream({
          async start(controller) {
            controller.enqueue(encoder.encode('data: {"type":"tool_execution","tool":"utc_now"}\n\n'))
            await hold
            controller.enqueue(encoder.encode('data: {"type":"token","text":"now"}\n\n'))
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  ...agentFixture,
                  history: [
                    { role: 'user', content: 'time' },
                    { role: 'assistant', content: 'now' },
                  ],
                  answer: 'now',
                  done: true,
                })}\n\n`,
              ),
            )
            controller.close()
          },
        })
        return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
      }
      return null
    })

    renderChat()
    await user.type(await screen.findByPlaceholderText('How can I help you today?'), 'time')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('🔧 Executing tool: utc_now...')).toBeInTheDocument()
    releaseToken?.()
    expect(await screen.findByText('now')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText('🔧 Executing tool: utc_now...')).not.toBeInTheDocument()
    })
    expect(screen.queryByText('🔧 Executing tool: utc_now...', { selector: '.whitespace-pre-wrap' })).not.toBeInTheDocument()
  })

  it('T15 assembles SSE tokens into the assistant turn', async () => {
    const user = userEvent.setup()
    installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/ask' && init?.method === 'POST') {
        return sseResponse([
          'data: {"text":"Hel"}',
          'data: {"text":"lo"}',
          `data: ${JSON.stringify({
            ...agentFixture,
            history: [
              { role: 'user', content: 'hi' },
              { role: 'assistant', content: 'Hello' },
            ],
            answer: 'Hello',
            done: true,
          })}`,
        ])
      }
      return null
    })

    renderChat()
    await user.type(await screen.findByPlaceholderText('How can I help you today?'), 'hi')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('Hello')).toBeInTheDocument()
    expect(screen.getByText('hi')).toBeInTheDocument()
  })

  it('T16 shows the already-answering toast on HTTP 409', async () => {
    const user = userEvent.setup()
    installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/ask' && init?.method === 'POST') {
        return jsonResponse({ detail: 'Agent is already answering' }, 409)
      }
      return null
    })

    renderChat()
    await user.type(await screen.findByPlaceholderText('How can I help you today?'), 'again')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText(/Agent is already answering/)).toBeInTheDocument()
    expect(screen.getByText('again')).toBeInTheDocument()
  })

  it('clears history after confirm', async () => {
    const user = userEvent.setup()
    const { calls } = installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/reset' && init?.method === 'POST') {
        return jsonResponse({ ...agentFixture, history: [] })
      }
      return null
    })

    renderChat()
    expect(await screen.findByRole('button', { name: 'Clear history' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear history' }))
    expect(screen.getByText('Are you sure? This will delete the conversation history.')).toBeInTheDocument()
    const confirms = screen.getAllByRole('button', { name: 'Clear history' })
    await user.click(confirms[confirms.length - 1])
    await waitFor(() => {
      expect(calls.some((call) => call.path === '/v1/agents/a1/reset' && call.init?.method === 'POST')).toBe(true)
    })
  })

  it('keeps Chat free of create-agent chrome and shows a glass composer', async () => {
    const user = userEvent.setup()
    installFetchMock(() => null)
    renderChat()
    expect(await screen.findByPlaceholderText('How can I help you today?')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Templates' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agents' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Messages' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('LLM company (latest model)')).not.toBeInTheDocument()
    expect(await screen.findByLabelText('Models')).toBeInTheDocument()
    expect(screen.getByLabelText('Models').closest('form')).toBeTruthy()
    expect(screen.getByTitle('demo-echo')).toHaveTextContent('demo-echo')
    expect(screen.queryByLabelText('Channel')).not.toBeInTheDocument()
    expect(screen.getByTestId('thinking-status')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Workspace' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Workspace' }))
    expect(screen.queryByText('No screen connected')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Workspace' }))
    expect(screen.getByText('No screen connected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Mission' }))
    expect(await screen.findByText('None yet')).toBeInTheDocument()
    expect(screen.getByText('idle')).toBeInTheDocument()
  })

  it('shows a mission notice and dismisses it', async () => {
    const user = userEvent.setup()
    let unread = true
    const { calls } = installFetchMock((path, init) => {
      if (path === '/v1/notifications' && init?.method !== 'POST') {
        return jsonResponse({
          notifications: unread
            ? [
                {
                  id: 'n1',
                  agent_id: 'a1',
                  kind: 'blocked',
                  message: 'alpha is blocked on “research”: paywall.',
                  at: '2026-09-04T00:00:00+00:00',
                  acked: false,
                },
              ]
            : [],
        })
      }
      if (path === '/v1/notifications/n1/ack' && init?.method === 'POST') {
        unread = false
        return jsonResponse({
          id: 'n1',
          agent_id: 'a1',
          kind: 'blocked',
          message: 'alpha is blocked on “research”: paywall.',
          at: '2026-09-04T00:00:00+00:00',
          acked: true,
        })
      }
      if (path === '/v1/agents/a1/situation') {
        return jsonResponse({
          agent_id: 'a1',
          agent: 'alpha',
          phase: 'blocked',
          objective: 'Finish the report',
          current_step: 'research',
          steps_remaining: ['research', 'write'],
          steps_completed: [],
          steps_blocked: ['research'],
          obstacles: [{ step: 'research', obstacle: 'paywall' }],
          deviations: [],
          alternatives: [],
          attempts: 1,
          max_attempts: 3,
          team: null,
          last_checkpoint: null,
        })
      }
      return null
    })
    renderChat()
    expect(await screen.findByTestId('mission-notice')).toHaveTextContent('alpha is blocked on “research”: paywall.')
    await user.click(screen.getByRole('button', { name: 'Dismiss notice' }))
    await waitFor(() => {
      expect(calls.some((call) => call.path === '/v1/notifications/n1/ack' && call.init?.method === 'POST')).toBe(true)
    })
    expect(screen.queryByTestId('mission-notice')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Mission' }))
    expect(await screen.findByText('Finish the report')).toBeInTheDocument()
    expect(screen.getByText('blocked')).toBeInTheDocument()
  })

  it('shows an API key field on the composer when the model needs one', async () => {
    const user = userEvent.setup()
    installFetchMock((path, init) => {
      if (path === '/v1/settings') {
        return jsonResponse({
          llm_base_url: 'https://api.openai.com/v1',
          llm_api_key: init?.method === 'PUT' ? '***' : '',
          llm_model: 'gpt-4o-mini',
          demo: false,
          default_channel: 'cli',
          channels: ['cli', 'webhook'],
          channels_coming: [],
        })
      }
      if (path === '/v1/agents/a1' && init?.method === 'PATCH') {
        return jsonResponse({ ...agentFixture, model: 'gpt-5.6-sol' })
      }
      return null
    })
    renderChat()
    const picker = await screen.findByLabelText('Models')
    await user.selectOptions(picker, 'OpenAI (GPT-5.6 Sol)')
    expect(await screen.findByPlaceholderText('API key')).toBeInTheDocument()
    expect(screen.queryByLabelText('LLM company (latest model)')).not.toBeInTheDocument()
  })

  it('keeps a long note in the composer and accepts a dropped document', async () => {
    installFetchMock(() => null)
    renderChat()
    const box = await screen.findByPlaceholderText('How can I help you today?')
    expect(box).not.toHaveAttribute('maxLength')
    const long = Array.from({ length: 240 }, (_, index) => `word${index}`).join(' ')
    fireEvent.change(box, { target: { value: long } })
    expect(box).toHaveValue(long)
    expect(screen.getByText(/240 \/ 5,000 words/)).toBeInTheDocument()
    const form = box.closest('form')
    expect(form).toBeTruthy()
    const file = new File(['# Brief\nDo the steps.'], 'brief.md', { type: 'text/markdown' })
    fireEvent.drop(form as HTMLFormElement, { dataTransfer: { files: [file] } })
    expect(await screen.findByText('brief.md')).toBeInTheDocument()
  })

  it('T17 keeps the user turn and shows Retry when the stream dies', async () => {
    const user = userEvent.setup()
    installFetchMock((path, init) => {
      if (path === '/v1/agents/a1/ask' && init?.method === 'POST') {
        const encoder = new TextEncoder()
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"text":"x"}\n\n'))
            controller.close()
          },
        })
        return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
      }
      return null
    })

    renderChat()
    await user.type(await screen.findByPlaceholderText('How can I help you today?'), 'keep-me')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(screen.getByText('keep-me')).toBeInTheDocument()
  })

  it('Audio falls back to host record when the window has no microphone', async () => {
    const user = userEvent.setup()
    const { calls } = installFetchMock((path) => {
      if (path === '/v1/record/start') return jsonResponse({ status: 'recording' })
      if (path === '/v1/record/stop') {
        return jsonResponse({ name: 'clip.wav', mime: 'audio/wav', data: 'QQ==' })
      }
      if (path === '/v1/transcribe') return jsonResponse({ text: 'hello from the mac' })
      return null
    })
    const original = globalThis.navigator
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: { language: 'en-US' },
    })
    try {
      renderChat()
      await user.click(await screen.findByRole('button', { name: 'Audio' }))
      await waitFor(() => {
        expect(calls.some((call) => call.path === '/v1/record/start')).toBe(true)
      })
      await user.click(screen.getByRole('button', { name: 'Stop audio' }))
      await waitFor(() => {
        expect(calls.some((call) => call.path === '/v1/record/stop')).toBe(true)
        expect(calls.some((call) => call.path === '/v1/transcribe')).toBe(true)
      })
      expect(await screen.findByText('hello from the mac')).toBeInTheDocument()
    } finally {
      Object.defineProperty(globalThis, 'navigator', { configurable: true, value: original })
    }
  })
})
