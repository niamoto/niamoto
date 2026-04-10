export interface TableInfo {
  name: string
  count: number
  description: string
  columns: string[]
}

export interface QueryRequest {
  table: string
  columns?: string[]
  where?: string
  order_by?: string
  limit?: number
  offset?: number
}

export interface QueryResponse {
  columns: string[]
  rows: Array<Record<string, unknown>>
  total_count: number
  page_count: number
}

export interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  default: string | null
}
