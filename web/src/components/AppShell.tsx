import { Bot, ChevronLeft, ChevronRight, MessageSquare, Settings } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { getHealth } from '../lib/api'
import { useLayout } from '../lib/layout-context'
import { SIZE_LIMITS } from '../lib/layout'
import { cn } from '../lib/utils'
import { DragHandle } from './DragHandle'

const nav = [
  { to: '/', label: 'Chat', icon: MessageSquare, end: true },
  { to: '/agents', label: 'Agents', icon: Bot, end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
]

export function AppShell() {
  const [connected, setConnected] = useState<boolean | null>(null)
  const [demo, setDemo] = useState(false)
  const { layout, updateLayout } = useLayout()

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
    <div className="flex h-svh min-h-0 flex-col bg-bg md:flex-row">
      <aside
        className={cn(
          'flex w-full shrink-0 items-center justify-between border-b border-border bg-surface px-3 py-2 md:h-full md:flex-col md:items-stretch md:border-b-0 md:border-r md:px-2 md:py-4',
          layout.navOpen ? 'md:w-[var(--nav-w)]' : 'md:w-16 md:px-1.5',
        )}
        style={{ ['--nav-w' as string]: `${layout.navWidth}px` }}
      >
        <div className="hidden md:flex md:h-full md:min-h-0 md:w-full md:flex-col">
          <div className="mb-4 flex items-center justify-between gap-2 px-1">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent text-sm font-bold text-bg">
                U
              </div>
              {layout.navOpen && (
                <div className="min-w-0 leading-tight">
                  <div className="truncate text-sm font-semibold">Universal</div>
                  <div className="text-[11px] text-muted">Platform</div>
                </div>
              )}
            </div>
            <button
              type="button"
              className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-ink"
              onClick={() => updateLayout({ navOpen: !layout.navOpen })}
              aria-label={layout.navOpen ? 'Close menu' : 'Open menu'}
              title={layout.navOpen ? 'Close menu' : 'Open menu'}
            >
              {layout.navOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
            </button>
          </div>
          <nav className="flex flex-col gap-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                title={item.label}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-2.5 py-2 text-sm text-muted hover:bg-surface-2 hover:text-ink',
                    !layout.navOpen && 'justify-center px-2',
                    isActive && 'bg-surface-2 text-accent',
                  )
                }
              >
                <item.icon size={16} />
                {layout.navOpen && <span>{item.label}</span>}
              </NavLink>
            ))}
          </nav>
          <div className={cn('mt-auto flex items-center gap-2 text-xs text-muted', !layout.navOpen && 'justify-center')}>
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                connected === null && 'bg-muted',
                connected === true && 'bg-emerald-400',
                connected === false && 'bg-red-400',
              )}
            />
            {layout.navOpen && (connected === false ? 'Server offline' : demo ? 'Demo echo' : 'Connected')}
          </div>
        </div>

        <div className="flex w-full items-center justify-between gap-2 md:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-sm font-bold text-bg">
              U
            </div>
            <div className="text-sm font-semibold">Universal</div>
          </div>
          <nav className="flex gap-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                title={item.label}
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-center rounded-md px-2.5 py-2 text-sm text-muted hover:bg-surface-2 hover:text-ink',
                    isActive && 'bg-surface-2 text-accent',
                  )
                }
              >
                <item.icon size={16} />
                <span className="sr-only">{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>
      {layout.navOpen && (
        <div className="hidden md:block">
          <DragHandle
            axis="x"
            value={layout.navWidth}
            min={SIZE_LIMITS.nav.min}
            max={SIZE_LIMITS.nav.max}
            onValue={(navWidth) => updateLayout({ navWidth })}
            label="Resize menu"
            testId="nav-resize"
          />
        </div>
      )}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
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
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
