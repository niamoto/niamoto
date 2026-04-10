import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export interface DiagnosticInfo {
  working_directory: string
  database: {
    path: string | null
    exists: boolean
    tables: string[]
  }
  config_files: Record<
    string,
    {
      exists: boolean
      path: string
    }
  >
}

export async function getDiagnosticInfo(): Promise<DiagnosticInfo> {
  try {
    const response = await apiClient.get<DiagnosticInfo>('/health/diagnostic')
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to load diagnostics'))
  }
}
