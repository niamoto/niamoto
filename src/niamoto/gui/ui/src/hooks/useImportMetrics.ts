import { useState, useEffect } from 'react'
import { getImportMetrics } from '@/lib/api/database'

export interface ImportMetrics {
  taxon_ref: number
  occurrences: number
  plot_ref: number
  shape_ref: number
  total_records: number
  unique_species: number
  unique_locations: number
}

interface UseImportMetricsResult {
  metrics: ImportMetrics | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

/**
 * Hook to fetch and manage import metrics from the database
 */
export function useImportMetrics(): UseImportMetricsResult {
  const [metrics, setMetrics] = useState<ImportMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getImportMetrics()
      setMetrics(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch metrics'))
      console.error('Error fetching import metrics:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [])

  return {
    metrics,
    loading,
    error,
    refetch: fetchMetrics
  }
}
