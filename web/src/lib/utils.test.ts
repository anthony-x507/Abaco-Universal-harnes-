import { describe, expect, it } from 'vitest'
import { laterChannels, pluginCountLabel } from './utils'

describe('laterChannels', () => {
  it('does not disable webhook once the catalog lists it', () => {
    expect(laterChannels(['cli', 'webhook'], [])).toEqual([])
    expect(laterChannels(['cli', 'webhook'], ['webhook'])).toEqual([])
    expect(laterChannels(['cli'], ['telegram'])).toEqual(['telegram'])
  })
})

describe('pluginCountLabel', () => {
  it('hides plugin ids', () => {
    expect(pluginCountLabel(0)).toBe('no plugins')
    expect(pluginCountLabel(1)).toBe('1 plugin')
    expect(pluginCountLabel(2)).toBe('2 plugins')
  })
})
