import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { agentFixture, installFetchMock, jsonResponse } from '../test/fetch'

const abortAsk = vi.fn()

vi.mock('../lib/ask-session', () => ({
  useAskSession: () => ({
    askingId: 'a1',
    toast: '',
    showToast: vi.fn(),
    clearToast: vi.fn(),
    beginAsk: vi.fn(),
    endAsk: vi.fn(),
    abortAsk,
  }),
}))

import { AgentsPage } from './AgentsPage'

describe('Agents page quality tests', () => {
  beforeEach(() => {
    abortAsk.mockReset()
  })

  it('shows readable plugin labels and downloads a ZIP', async () => {
    const user = userEvent.setup()
    const { calls, catalog } = installFetchMock((path, init) => {
      if (path === `/v1/agents/${agentFixture.id}/deploy` && init?.method === 'POST') {
        return new Response(new Blob(['PK']), {
          status: 200,
          headers: {
            'Content-Type': 'application/zip',
            'Content-Disposition': 'attachment; filename="alpha-a1.zip"',
          },
        })
      }
      return null
    })
    catalog.agents = {
      agents: [{ ...agentFixture, plugins: ['tools'], plugin_labels: ['Tools: utc_now'] }],
    }

    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/Tools: utc_now/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Download ZIP' }))
    await vi.waitFor(() => {
      expect(calls.some((call) => call.path === `/v1/agents/${agentFixture.id}/deploy` && call.init?.method === 'POST')).toBe(
        true,
      )
    })
  })

  it('W05 enables webhook in the create selector', async () => {
    installFetchMock(() => null)
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )
    expect(await screen.findByLabelText('LLM company (latest model)')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'OpenAI (GPT-5.6 Sol)' })).toBeInTheDocument()
    const option = await screen.findByRole('option', { name: 'webhook' })
    expect(option).toBeEnabled()
    expect(screen.queryByRole('option', { name: /webhook \(later\)/i })).not.toBeInTheDocument()
  })

  it('T07 shows a cancel-then-delete modal while the agent is answering', async () => {
    const user = userEvent.setup()
    const { calls } = installFetchMock((path, init) => {
      if (path === `/v1/agents/${agentFixture.id}` && init?.method === 'DELETE') {
        return jsonResponse({ deleted: agentFixture })
      }
      return null
    })

    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('alpha')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(screen.getByRole('heading', { name: /Delete alpha/ })).toBeInTheDocument()
    expect(screen.getByText(/Deleting will cancel the response/)).toBeInTheDocument()
    const deletes = screen.getAllByRole('button', { name: 'Delete' })
    await user.click(deletes[deletes.length - 1])
    expect(abortAsk).toHaveBeenCalled()
    await vi.waitFor(() => {
      expect(calls.some((call) => call.path === `/v1/agents/${agentFixture.id}` && call.init?.method === 'DELETE')).toBe(
        true,
      )
    })
  })
})
