import { describe, expect, it } from 'vitest'
import { laterChannels, pluginCountLabel, pluginListLabel, usageLabel } from './utils'

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

describe('pluginListLabel', () => {
  it('prefers readable plugin names', () => {
    expect(pluginListLabel(['Tools: utc_now'], 1)).toBe('Tools: utc_now')
    expect(pluginListLabel([], 0)).toBe('no plugins')
  })
})

describe('usageLabel', () => {
  it('formats the chat header meter', () => {
    expect(usageLabel({ prompt_tokens: 1000, completion_tokens: 234, estimated_cost: 0.002 })).toBe(
      'Tokens: 1,234 | Cost: $0.002',
    )
    expect(usageLabel()).toBe('Tokens: 0 | Cost: $0.000')
  })
})
