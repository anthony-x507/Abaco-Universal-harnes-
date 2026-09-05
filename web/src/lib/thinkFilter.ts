const OPEN_TAG = '<think>'
const CLOSE_TAG = '</think>'

function findCi(haystack: string, needle: string): number {
  return haystack.toLowerCase().indexOf(needle.toLowerCase())
}

function holdbackLen(buffer: string, tag: string): number {
  const lowered = buffer.toLowerCase()
  const target = tag.toLowerCase()
  const maxN = Math.min(lowered.length, target.length - 1)
  for (let size = maxN; size > 0; size -= 1) {
    if (lowered.endsWith(target.slice(0, size))) return size
  }
  return 0
}

/** Incremental ``<think>`` stripper for SSE token deltas. */
export class ThinkStreamFilter {
  private buf = ''
  private hidden = false
  private visible = ''

  get text(): string {
    return this.visible
  }

  feed(chunk: string): string {
    if (!chunk) return ''
    this.buf += chunk
    const next = this.drain(false)
    this.visible += next
    return next
  }

  flush(): string {
    const next = this.drain(true)
    this.visible += next
    return next
  }

  private drain(finalize: boolean): string {
    const out: string[] = []
    while (this.buf) {
      if (this.hidden) {
        const idx = findCi(this.buf, CLOSE_TAG)
        if (idx >= 0) {
          this.buf = this.buf.slice(idx + CLOSE_TAG.length)
          this.hidden = false
          continue
        }
        if (finalize) {
          this.buf = ''
          break
        }
        const keep = holdbackLen(this.buf, CLOSE_TAG)
        this.buf = keep ? this.buf.slice(-keep) : ''
        break
      }
      const idx = findCi(this.buf, OPEN_TAG)
      if (idx >= 0) {
        out.push(this.buf.slice(0, idx))
        this.buf = this.buf.slice(idx + OPEN_TAG.length)
        this.hidden = true
        continue
      }
      if (finalize) {
        out.push(this.buf)
        this.buf = ''
        break
      }
      const keep = holdbackLen(this.buf, OPEN_TAG)
      if (keep) {
        out.push(this.buf.slice(0, -keep))
        this.buf = this.buf.slice(-keep)
      } else {
        out.push(this.buf)
        this.buf = ''
      }
      break
    }
    return out.join('')
  }
}

export function stripThinkTags(text: string): string {
  if (!text || !text.includes('<')) return text
  const filter = new ThinkStreamFilter()
  return filter.feed(text) + filter.flush()
}
