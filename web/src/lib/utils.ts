import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function pluginCountLabel(count: number) {
  if (count <= 0) return 'no plugins'
  return count === 1 ? '1 plugin' : `${count} plugins`
}

export function laterChannels(available: string[], coming: string[]) {
  return coming.filter((id) => !available.includes(id))
}
