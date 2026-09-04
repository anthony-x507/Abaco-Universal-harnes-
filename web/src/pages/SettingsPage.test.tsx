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
    expect(await screen.findByRole('option', { name: 'OpenAI (GPT-5.6 Sol)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'webhook' })).toBeEnabled()
    expect(screen.queryByRole('option', { name: /webhook \(later\)/i })).not.toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Check for Updates' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Updates' })).toBeInTheDocument()
    expect(await screen.findByText('Governance')).toBeInTheDocument()
    expect(screen.getByText('no_purchase_without_permission')).toBeInTheDocument()
    expect(screen.getByText('no_dark_web_without_permission')).toBeInTheDocument()
    expect(screen.getByText('navigator_auto_notify')).toBeInTheDocument()
    expect(screen.getByText('memory_share_between_agents')).toBeInTheDocument()
    expect(screen.getByText('strategist_deepseek_tracking')).toBeInTheDocument()
    expect(screen.getByText('sentinel_proof_required')).toBeInTheDocument()
    expect(screen.getByText('improvement_allow_suggestions')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'DeepSeek Insights' })).toBeInTheDocument()
    expect(screen.getAllByText('deepseek-ai/deepseek-harness').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'Scan DeepSeek' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Harness audit' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run audit' })).toBeInTheDocument()
    expect(screen.getByText('VERIFIED')).toBeInTheDocument()
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
