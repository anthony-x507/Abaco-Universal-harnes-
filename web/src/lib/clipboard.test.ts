import { describe, expect, it } from 'vitest'
import { textToCopy } from './clipboard'

describe('chat copy payload', () => {
  it('uses the selection when the user highlighted something', () => {
    expect(textToCopy('full message here', '  message  ')).toBe('message')
  })

  it('falls back to the whole message', () => {
    expect(textToCopy('full message here', '')).toBe('full message here')
    expect(textToCopy('full message here', '   ')).toBe('full message here')
  })
})
