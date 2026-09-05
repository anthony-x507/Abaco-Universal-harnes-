import { describe, expect, it } from 'vitest'
import { ThinkStreamFilter, stripThinkTags } from './thinkFilter'

describe('think tag filter', () => {
  it('strips complete and unclosed blocks', () => {
    expect(stripThinkTags('hello')).toBe('hello')
    expect(stripThinkTags('<think>secret</think>visible')).toBe('visible')
    expect(stripThinkTags('pre<THINK>x</Think>post')).toBe('prepost')
    expect(stripThinkTags('keep <think>hidden')).toBe('keep ')
  })

  it('does not leak split tags across SSE chunks', () => {
    const filter = new ThinkStreamFilter()
    const pieces = ['hello <th', 'ink>secret</th', 'ink> world']
    const visible = pieces.map((piece) => filter.feed(piece)).join('') + filter.flush()
    expect(visible).toBe('hello  world')
    expect(visible.toLowerCase()).not.toContain('<think>')
    expect(visible).not.toContain('secret')
  })
})
