import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AskSessionProvider } from '../lib/ask-session'
import { ChatPage } from './ChatPage'
import { agentFixture, installFetchMock, jsonResponse, sseResponse } from '../test/fetch'

function renderChat() {
  return render(
    <MemoryRouter initialEntries={['/?agent=a1']}>
      <AskSessionProvider>
        <ChatPage />
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
    const box = await screen.findByPlaceholderText('Write in the middle column…')
    await user.type(box, 'hello')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(calls.some((call) => call.path === '/v1/agents/a1/ask')).toBe(true)
    })
    const ask = calls.find((call) => call.path === '/v1/agents/a1/ask' && call.init?.method === 'POST')
    expect(ask).toBeTruthy()
    expect(askBody(ask?.init)).toEqual({ prompt: 'hello', stream: true })
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
    await user.type(await screen.findByPlaceholderText('Write in the middle column…'), 'hi')
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
    await user.type(await screen.findByPlaceholderText('Write in the middle column…'), 'again')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Agent is already answering')
    expect(screen.getByText('again')).toBeInTheDocument()
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
    await user.type(await screen.findByPlaceholderText('Write in the middle column…'), 'keep-me')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(screen.getByText('keep-me')).toBeInTheDocument()
  })
})
