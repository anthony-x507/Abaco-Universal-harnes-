import { startResize } from '../lib/resize'
import { cn } from '../lib/utils'

type Props = {
  axis: 'x' | 'y'
  invert?: boolean
  value: number
  min: number
  max: number
  onValue: (next: number) => void
  label: string
  testId?: string
}

export function DragHandle({ axis, invert, value, min, max, onValue, label, testId }: Props) {
  const vertical = axis === 'x'
  return (
    <button
      type="button"
      data-testid={testId}
      aria-label={label}
      title={label}
      className={cn(
        'shrink-0 touch-none bg-border/80 hover:bg-accent focus-visible:bg-accent focus-visible:outline-none',
        vertical ? 'w-1.5 cursor-col-resize self-stretch' : 'h-1.5 cursor-row-resize w-full',
      )}
      onPointerDown={(event) => {
        startResize(event, {
          startValue: value,
          min,
          max,
          axis,
          invert,
          onValue,
        })
      }}
    />
  )
}
