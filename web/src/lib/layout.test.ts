import { afterEach, describe, expect, it } from 'vitest'
import { LAYOUT_DEFAULTS, loadLayout, loadPaneState, saveLayout, savePaneState } from './layout'
import { clamp } from './resize'

describe('layout persistence', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('returns defaults and ignores a bad payload', () => {
    expect(loadLayout()).toEqual(LAYOUT_DEFAULTS)
    localStorage.setItem('universal-layout', '{not json')
    expect(loadLayout()).toEqual(LAYOUT_DEFAULTS)
  })

  it('round-trips pane open/close and sizes', () => {
    saveLayout({
      ...LAYOUT_DEFAULTS,
      navOpen: false,
      left: false,
      composerHeight: 200,
    })
    const next = loadLayout()
    expect(next.navOpen).toBe(false)
    expect(next.left).toBe(false)
    expect(next.composerHeight).toBe(200)
    savePaneState({ left: true, middle: true, right: false })
    expect(loadPaneState()).toEqual({ left: true, middle: true, right: false })
  })

  it('clamps resize values', () => {
    expect(clamp(10, 20, 40)).toBe(20)
    expect(clamp(50, 20, 40)).toBe(40)
    expect(clamp(30, 20, 40)).toBe(30)
  })
})
