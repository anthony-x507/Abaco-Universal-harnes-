import type { InputHTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-9 w-full rounded-md border border-border bg-surface-2 px-3 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none',
        className,
      )}
      {...props}
    />
  )
}
