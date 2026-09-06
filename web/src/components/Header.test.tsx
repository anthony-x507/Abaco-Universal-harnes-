import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { LayoutProvider } from '../lib/layout-context'
import { installFetchMock } from '../test/fetch'
import { AppShell } from './AppShell'
import { Header } from './Header'

describe('Header brand', () => {
  it('shows the crystal mark next to Abaco Coding Harness', () => {
    render(<Header />)
    expect(screen.getByRole('heading', { name: 'Abaco Coding Harness' })).toBeInTheDocument()
    const mark = screen.getByRole('img', { name: 'Abaco Coding Harness' })
    expect(mark).toHaveAttribute('src')
    expect(String(mark.getAttribute('src'))).toMatch(/logo/)
  })

  it('is the top-left chrome of the app shell', async () => {
    installFetchMock(() => null)
    render(
      <MemoryRouter>
        <LayoutProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<div>chat face</div>} />
            </Route>
          </Routes>
        </LayoutProvider>
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Abaco Coding Harness' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Abaco Coding Harness' })).toBeInTheDocument()
    expect(await screen.findByText('1.2.18')).toBeInTheDocument()
    expect(screen.getByText('chat face')).toBeInTheDocument()
  })
})
