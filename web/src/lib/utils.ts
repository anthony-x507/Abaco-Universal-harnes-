import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function pluginCountLabel(count: number) {
  if (count <= 0) return 'no plugins'
  return count === 1 ? '1 plugin' : `${count} plugins`
}

export function pluginListLabel(labels?: string[], count = 0) {
  if (labels && labels.length > 0) return labels.join(' · ')
  return pluginCountLabel(count)
}

export function usageLabel(usage?: {
  prompt_tokens: number
  completion_tokens: number
  estimated_cost: number
}) {
  const tokens = (usage?.prompt_tokens ?? 0) + (usage?.completion_tokens ?? 0)
  const cost = usage?.estimated_cost ?? 0
  return `Tokens: ${tokens.toLocaleString('en-US')} | Cost: $${cost.toFixed(3)}`
}

export function laterChannels(available: string[], coming: string[]) {
  return coming.filter((id) => !available.includes(id))
}
