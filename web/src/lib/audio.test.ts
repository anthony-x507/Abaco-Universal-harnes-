import { describe, expect, it, vi } from 'vitest'
import { getUserMedia } from './audio'

describe('getUserMedia', () => {
  it('returns undefined when mediaDevices is missing', () => {
    vi.stubGlobal('navigator', {})
    expect(getUserMedia()).toBeUndefined()
    vi.unstubAllGlobals()
  })

  it('uses mediaDevices.getUserMedia when present', async () => {
    const stream = {} as MediaStream
    const get = vi.fn().mockResolvedValue(stream)
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia: get } })
    const fn = getUserMedia()
    expect(fn).toBeTypeOf('function')
    await expect(fn?.({ audio: true })).resolves.toBe(stream)
    vi.unstubAllGlobals()
  })
})
