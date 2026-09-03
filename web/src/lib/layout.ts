const STORAGE_KEY = 'universal-layout'

export type PaneId = 'left' | 'middle' | 'right'

export type PaneState = Record<PaneId, boolean>

const defaults: PaneState = { left: true, middle: true, right: true }

export function loadPaneState(): PaneState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw) as Partial<PaneState>
    return {
      left: parsed.left ?? true,
      middle: parsed.middle ?? true,
      right: parsed.right ?? true,
    }
  } catch {
    return { ...defaults }
  }
}

export function savePaneState(state: PaneState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}
