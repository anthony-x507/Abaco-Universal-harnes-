import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

export function Badge({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted',
        className,
      )}
    >
      {children}
    </span>
  )
}
