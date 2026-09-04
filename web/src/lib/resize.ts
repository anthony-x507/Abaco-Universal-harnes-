export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

type Axis = 'x' | 'y'

export function startResize(
  event: { clientX: number; clientY: number; preventDefault(): void },
  options: {
    startValue: number
    min: number
    max: number
    axis: Axis
    invert?: boolean
    onValue: (next: number) => void
    onEnd?: (next: number) => void
  },
) {
  event.preventDefault()
  const origin = options.axis === 'x' ? event.clientX : event.clientY
  let last = options.startValue

  const move = (ev: PointerEvent) => {
    const pos = options.axis === 'x' ? ev.clientX : ev.clientY
    const delta = options.invert ? origin - pos : pos - origin
    last = clamp(options.startValue + delta, options.min, options.max)
    options.onValue(last)
  }

  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    options.onEnd?.(last)
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}
