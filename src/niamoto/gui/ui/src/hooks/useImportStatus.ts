import { useEffect, useState } from 'react'
import axios from 'axios'

export interface ImportStatus {
  import_type: string
  is_imported: boolean
  row_count: number
  dependencies_met: boolean
  missing_dependencies: string[]
}

export interface ImportStatusResponse {
  taxonomy: ImportStatus
  occurrences: ImportStatus
  plots: ImportStatus
  shapes: ImportStatus
}

export function useImportStatus() {
  const [status, setStatus] = useState<ImportStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      setLoading(true)
      const response = await axios.get<ImportStatusResponse>('/api/imports/status')
      setStatus(response.data)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch import status:', err)
      setError('Failed to fetch import status')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  return { status, loading, error, refetch: fetchStatus }
}
