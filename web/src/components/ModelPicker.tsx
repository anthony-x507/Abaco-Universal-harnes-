import { Label } from './ui/label'
import type { ModelPreset } from '../lib/api'
import { cn } from '../lib/utils'

export function matchPreset(models: ModelPreset[], modelId: string): string {
  const hit = models.find((row) => row.default_model === modelId)
  return hit?.name || ''
}

export function ModelPicker({
  id,
  label = 'Models',
  value,
  onChange,
  models,
  currentModel,
  disabled,
  compact,
}: {
  id: string
  label?: string
  value: string
  onChange: (name: string) => void
  models: ModelPreset[]
  currentModel?: string
  disabled?: boolean
  compact?: boolean
}) {
  const selected = models.find((row) => row.name === value)
  const shown = selected?.default_model || currentModel || ''
  return (
    <div className={cn(compact ? 'flex min-w-0 items-center gap-2' : 'space-y-1')}>
      <Label htmlFor={id} className={compact ? 'text-xs text-muted' : undefined}>
        {label}
      </Label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          'rounded-md border border-border bg-surface-2 px-2 text-sm text-ink',
          compact ? 'h-8 max-w-[14rem] rounded-full border-white/10 bg-white/5' : 'mt-1 h-9 w-full',
        )}
      >
        {!value && currentModel ? (
          <option value="">
            {currentModel}
          </option>
        ) : null}
        {models.map((row) => (
          <option key={row.name} value={row.name}>
            {row.name}
          </option>
        ))}
      </select>
      {shown ? (
        <span className={cn('truncate text-[11px] text-muted', compact ? 'max-w-[10rem]' : 'block')} title={shown}>
          {shown}
        </span>
      ) : null}
    </div>
  )
}
