const STORAGE_KEY = 'universal-layout'

export type PaneId = 'left' | 'middle' | 'right'

export type LayoutState = {
  navOpen: boolean
  navWidth: number
  left: boolean
  leftWidth: number
  middle: boolean
  right: boolean
  rightWidth: number
  composerOpen: boolean
  composerHeight: number
}

export type PaneState = Pick<LayoutState, 'left' | 'middle' | 'right'>

export const LAYOUT_DEFAULTS: LayoutState = {
  navOpen: true,
  navWidth: 224,
  left: true,
  leftWidth: 320,
  middle: true,
  right: true,
  rightWidth: 320,
  composerOpen: true,
  composerHeight: 148,
}

const NAV_MIN = 176
const NAV_MAX = 360
const PANE_MIN = 220
const PANE_MAX = 520
const COMPOSER_MIN = 96
const COMPOSER_MAX = 420

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function asBool(value: unknown, fallback: boolean) {
  return typeof value === 'boolean' ? value : fallback
}

function asNumber(value: unknown, fallback: number, min: number, max: number) {
  return typeof value === 'number' && Number.isFinite(value) ? clamp(value, min, max) : fallback
}

export function loadLayout(): LayoutState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...LAYOUT_DEFAULTS }
    const parsed = JSON.parse(raw) as Partial<LayoutState>
    return {
      navOpen: asBool(parsed.navOpen, LAYOUT_DEFAULTS.navOpen),
      navWidth: asNumber(parsed.navWidth, LAYOUT_DEFAULTS.navWidth, NAV_MIN, NAV_MAX),
      left: asBool(parsed.left, LAYOUT_DEFAULTS.left),
      leftWidth: asNumber(parsed.leftWidth, LAYOUT_DEFAULTS.leftWidth, PANE_MIN, PANE_MAX),
      middle: asBool(parsed.middle, LAYOUT_DEFAULTS.middle),
      right: asBool(parsed.right, LAYOUT_DEFAULTS.right),
      rightWidth: asNumber(parsed.rightWidth, LAYOUT_DEFAULTS.rightWidth, PANE_MIN, PANE_MAX),
      composerOpen: asBool(parsed.composerOpen, LAYOUT_DEFAULTS.composerOpen),
      composerHeight: asNumber(parsed.composerHeight, LAYOUT_DEFAULTS.composerHeight, COMPOSER_MIN, COMPOSER_MAX),
    }
  } catch {
    return { ...LAYOUT_DEFAULTS }
  }
}

export function saveLayout(state: LayoutState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function loadPaneState(): PaneState {
  const layout = loadLayout()
  return { left: layout.left, middle: layout.middle, right: layout.right }
}

export function savePaneState(state: PaneState) {
  saveLayout({ ...loadLayout(), ...state })
}

export const SIZE_LIMITS = {
  nav: { min: NAV_MIN, max: NAV_MAX },
  pane: { min: PANE_MIN, max: PANE_MAX },
  composer: { min: COMPOSER_MIN, max: COMPOSER_MAX },
}
