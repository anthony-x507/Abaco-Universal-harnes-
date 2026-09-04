import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { SettingsPage } from './SettingsPage'
import { installFetchMock, jsonResponse } from '../test/fetch'

describe('T10 Settings demo mode', () => {
  it('disables the API key field and shows demo copy', async () => {
    installFetchMock((path) => {
      if (path === '/v1/settings') {
        return jsonResponse({
          llm_base_url: 'https://api.openai.com/v1',
          llm_api_key: '',
          llm_model: 'gpt-4o-mini',
          demo: true,
          default_channel: 'cli',
          channels: ['cli', 'webhook'],
          channels_coming: [],
        })
      }
      return null
    })

    render(<SettingsPage />)

    expect(await screen.findByText('Demo mode — no API key required')).toBeInTheDocument()
    const key = screen.getByLabelText('Demo mode — no API key required')
    expect(key).toBeDisabled()
    expect(key).toHaveAttribute('placeholder', 'Demo mode — no API key required')
    expect(await screen.findByRole('option', { name: 'OpenAI (GPT-4o-mini)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'webhook' })).toBeEnabled()
    expect(screen.queryByRole('option', { name: /webhook \(later\)/i })).not.toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Check for Updates' })).toBeInTheDocument()
  })

  it('Check for Updates shows no-updates copy', async () => {
    const user = userEvent.setup()
    installFetchMock(() => null)
    render(<SettingsPage />)
    const button = await screen.findByRole('button', { name: 'Check for Updates' })
    await user.click(button)
    expect(await screen.findByText('No updates available')).toBeInTheDocument()
  })
})
