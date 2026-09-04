import { useEffect, useState } from 'react'
import { listModels, type ModelPreset } from '../lib/api'

export function useModels() {
  const [models, setModels] = useState<ModelPreset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const rows = await listModels()
        if (!cancelled) {
          setModels(rows)
          setError('')
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load models.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return { models, loading, error }
}
