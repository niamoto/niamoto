import { useState, useEffect } from 'react'
import { API_BASE_URL } from '@/lib/api-config'

export interface TableInfo {
  name: string
  row_count: number
  columns: string[]
  hasGeometry?: boolean
}

export function useDatabaseTables() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTables = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(`${API_BASE_URL}/database/schema`)
        if (!response.ok) {
          throw new Error('Failed to fetch database schema')
        }

        const data = await response.json()

        // Extract table info from the schema
        const tableList: TableInfo[] = data.tables.map((table: any) => ({
          name: table.name,
          row_count: table.row_count,
          columns: table.columns.map((col: any) => col.name),
          hasGeometry: table.columns.some((col: any) =>
            col.type?.toLowerCase().includes('geom') ||
            col.type?.toLowerCase().includes('point') ||
            col.name?.toLowerCase().includes('geom') ||
            col.name?.toLowerCase().includes('location')
          )
        }))

        setTables(tableList)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchTables()
  }, [])

  return { tables, loading, error }
}
