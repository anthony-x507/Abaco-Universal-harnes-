import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ActivityProvider } from '../lib/activity'
import { AskSessionProvider } from '../lib/ask-session'
import { loadSkills } from '../lib/skills'
import { agentFixture, installFetchMock, jsonResponse } from '../test/fetch'
import { DesignPage } from './DesignPage'

function renderDesign() {
  return render(
    <MemoryRouter>
      <AskSessionProvider>
        <ActivityProvider>
          <DesignPage />
        </ActivityProvider>
      </AskSessionProvider>
    </MemoryRouter>,
  )
}

describe('Design page', () => {
  it('opens Herramientas / Design tiles and creates an agent', async () => {
    const user = userEvent.setup()
    const { calls } = installFetchMock((path, init) => {
      if (path === '/v1/agents' && init?.method === 'POST') {
        return jsonResponse({ ...agentFixture, name: 'Nova', emoji: '🤖' })
      }
      return null
    })

    renderDesign()
    expect(screen.getByText('Herramientas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Design' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Create an agent/ }))
    expect(await screen.findByRole('heading', { name: 'Templates' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Create agent' }))
    await screen.findByText(/Nova is ready/)
    expect(calls.some((call) => call.path === '/v1/agents' && call.init?.method === 'POST')).toBe(true)
  })

  it('records steps and asks to create a skill', async () => {
    const user = userEvent.setup()
    installFetchMock(() => null)
    renderDesign()
    await user.click(screen.getByRole('button', { name: /Teach skill/ }))
    await user.click(screen.getByRole('button', { name: 'Record' }))
    await user.type(screen.getByLabelText('Skill step'), 'Open invoices')
    await user.click(screen.getByRole('button', { name: 'Add step' }))
    await user.click(screen.getByRole('button', { name: 'Stop' }))
    expect(screen.getByText(/Create a skill from these 1 step/)).toBeInTheDocument()
    await user.clear(screen.getByLabelText('Skill name'))
    await user.type(screen.getByLabelText('Skill name'), 'Invoice walkthrough')
    await user.click(screen.getByRole('button', { name: 'Create skill' }))
    expect(loadSkills()[0]?.title).toBe('Invoice walkthrough')
    expect(loadSkills()[0]?.steps[0]?.action).toBe('Open invoices')
  })

  it('PDF tile responds instead of sitting dead', async () => {
    const user = userEvent.setup()
    installFetchMock(() => null)
    renderDesign()
    await user.click(screen.getByRole('button', { name: /Create a PDF/ }))
    await user.type(screen.getByLabelText('PDF title'), 'Q3 brief')
    await user.click(screen.getByRole('button', { name: 'Create PDF draft' }))
    expect(await screen.findByText(/PDF draft “Q3 brief”/)).toBeInTheDocument()
  })
})
