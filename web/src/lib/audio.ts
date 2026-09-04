function writeString(view: DataView, offset: number, value: string) {
  for (let i = 0; i < value.length; i += 1) {
    view.setUint8(offset + i, value.charCodeAt(i))
  }
}

function encodeWav(buffer: AudioBuffer): Blob {
  const samples = buffer.getChannelData(0)
  const bytes = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(bytes)
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, buffer.sampleRate, true)
  view.setUint32(28, buffer.sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(view, 36, 'data')
  view.setUint32(40, samples.length * 2, true)
  let cursor = 44
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i] ?? 0))
    view.setInt16(cursor, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
    cursor += 2
  }
  return new Blob([bytes], { type: 'audio/wav' })
}

export async function blobToWav(blob: Blob, sampleRate = 16000): Promise<Blob> {
  const context = new AudioContext()
  const decoded = await context.decodeAudioData(await blob.arrayBuffer())
  const frameCount = Math.max(1, Math.ceil(decoded.duration * sampleRate))
  const offline = new OfflineAudioContext(1, frameCount, sampleRate)
  const mono = offline.createBuffer(1, decoded.length, decoded.sampleRate)
  const mixed = mono.getChannelData(0)
  for (let channel = 0; channel < decoded.numberOfChannels; channel += 1) {
    const data = decoded.getChannelData(channel)
    for (let i = 0; i < data.length; i += 1) {
      mixed[i] += data[i] / decoded.numberOfChannels
    }
  }
  const source = offline.createBufferSource()
  source.buffer = mono
  source.connect(offline.destination)
  source.start()
  const rendered = await offline.startRendering()
  await context.close()
  return encodeWav(rendered)
}

export function getUserMedia(): ((constraints: MediaStreamConstraints) => Promise<MediaStream>) | undefined {
  if (typeof navigator === 'undefined') return undefined
  const devices = navigator.mediaDevices
  if (devices && typeof devices.getUserMedia === 'function') {
    return (constraints) => devices.getUserMedia(constraints)
  }
  const legacy = navigator as Navigator & {
    getUserMedia?: (c: MediaStreamConstraints, ok: (s: MediaStream) => void, err: (e: Error) => void) => void
    webkitGetUserMedia?: (c: MediaStreamConstraints, ok: (s: MediaStream) => void, err: (e: Error) => void) => void
    mozGetUserMedia?: (c: MediaStreamConstraints, ok: (s: MediaStream) => void, err: (e: Error) => void) => void
  }
  const fn = legacy.getUserMedia || legacy.webkitGetUserMedia || legacy.mozGetUserMedia
  if (typeof fn !== 'function') return undefined
  return (constraints) =>
    new Promise((resolve, reject) => {
      fn.call(navigator, constraints, resolve, reject)
    })
}

export function speechRecognitionCtor(): (new () => SpeechRecognitionLike) | undefined {
  if (typeof window === 'undefined') return undefined
  const host = window as Window & {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
  return host.SpeechRecognition || host.webkitSpeechRecognition
}

export type SpeechRecognitionLike = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null
  onerror: (() => void) | null
}

export const MIC_UNAVAILABLE =
  'Microphone is not available in this window. On a Mac, allow Microphone for Universal in System Settings → Privacy & Security, then restart the app.'

export function wordCount(text: string) {
  const parts = text.trim().split(/\s+/).filter(Boolean)
  return parts.length
}
