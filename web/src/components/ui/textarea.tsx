import type { TextareaHTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'min-h-[88px] w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none',
        className,
      )}
      {...props}
    />
  )
}
