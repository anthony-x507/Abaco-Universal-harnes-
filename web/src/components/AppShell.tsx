import { Bot, MessageSquare, Settings } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { getHealth } from '../lib/api'
import { cn } from '../lib/utils'

const nav = [
  { to: '/', label: 'Chat', icon: MessageSquare, end: true },
  { to: '/agents', label: 'Agents', icon: Bot, end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
]

export function AppShell() {
  const [connected, setConnected] = useState<boolean | null>(null)
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const health = await getHealth()
        if (!cancelled) {
          setConnected(health.status === 'ok')
          setDemo(health.demo)
        }
      } catch {
        if (!cancelled) setConnected(false)
      }
    }
    void check()
    const timer = window.setInterval(check, 8000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  return (
    <div className="flex min-h-svh flex-col bg-bg md:flex-row">
      <aside className="flex shrink-0 items-center justify-between border-b border-border bg-surface px-3 py-2 md:w-56 md:flex-col md:items-stretch md:border-b-0 md:border-r md:px-3 md:py-4">
        <div className="flex items-center gap-2 md:mb-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-sm font-bold text-bg">
            U
          </div>
          <div className="hidden leading-tight md:block">
            <div className="text-sm font-semibold">Universal</div>
            <div className="text-[11px] text-muted">Platform</div>
          </div>
        </div>
        <nav className="flex gap-1 md:flex-col">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-md px-2.5 py-2 text-sm text-muted hover:bg-surface-2 hover:text-ink',
                  isActive && 'bg-surface-2 text-accent',
                )
              }
            >
              <item.icon size={16} />
              <span className="hidden md:inline">{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="hidden items-center gap-2 text-xs text-muted md:mt-auto md:flex">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              connected === null && 'bg-muted',
              connected === true && 'bg-emerald-400',
              connected === false && 'bg-red-400',
            )}
          />
          {connected === false ? 'Server offline' : demo ? 'Demo echo' : 'Connected'}
        </div>
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-between border-b border-border bg-surface px-4">
          <div className="text-sm text-muted">Universal Platform</div>
          <div className="flex items-center gap-2 text-xs text-muted md:hidden">
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                connected === true && 'bg-emerald-400',
                connected === false && 'bg-red-400',
                connected === null && 'bg-muted',
              )}
            />
            {connected === false ? 'Offline' : demo ? 'Demo' : 'Live'}
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
