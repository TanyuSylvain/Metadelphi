import { useState, useEffect } from 'react'
import { modelsApi } from '../api/models'
import type { Model } from '../types/models'

interface UseModelsResult {
  models: Model[]
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useModels(): UseModelsResult {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await modelsApi.list()
      setModels(res.models)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load models')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetch() }, [])

  return { models, loading, error, refetch: fetch }
}
