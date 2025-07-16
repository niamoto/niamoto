import axios from 'axios'

// Estimate import duration based on type and data size
function calculateEstimatedDuration(importType: string, dataSize: number): number {
  // Base durations in milliseconds per 1000 records
  // Adjusted for more realistic progress display
  const baseDurations: Record<string, number> = {
    taxonomy: 8000,      // ~8s per 1000 taxa
    occurrences: 10000,  // ~10s per 1000 occurrences
    plots: 8000,         // ~8s per 1000 plots
    shapes: 6000         // ~6s per 1000 features (actually fast)
  }

  const baseTime = baseDurations[importType] || 8000
  const estimatedTime = (dataSize / 1000) * baseTime

  // Minimum duration to show progress (at least 3 seconds)
  const minDuration = 3000

  // Add some buffer time for initialization and finalization
  return Math.max(minDuration, estimatedTime) + 1000 // +1s buffer
}

export interface FileAnalysis {
  rowCount: number
  columns: string[]
  encoding: string
  preview: any[]
  suggestions: Record<string, string[]>
  uniqueTaxonCount?: number
  error?: string
}

export interface ImportRequest {
  import_type: string
  file_name: string
  field_mappings: Record<string, string>
  advanced_options?: Record<string, any>
}

export async function analyzeFile(file: File, importType: string): Promise<FileAnalysis> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('import_type', importType)

  const response = await axios.post<FileAnalysis>('/api/files/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  return response.data
}

export async function executeImport(request: ImportRequest, file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('import_type', request.import_type)
  formData.append('file_name', request.file_name)
  formData.append('field_mappings', JSON.stringify(request.field_mappings))
  if (request.advanced_options) {
    formData.append('advanced_options', JSON.stringify(request.advanced_options))
  }

  const response = await axios.post('/api/imports/execute', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  return response.data
}

export async function getImportStatus(jobId: string): Promise<any> {
  const response = await axios.get(`/api/imports/jobs/${jobId}`)
  return response.data
}

export async function executeImportAndWait(
  request: ImportRequest,
  file: File,
  pollInterval: number = 500, // Poll every 500ms for smoother progress
  maxWaitTime: number = 300000, // 5 minutes max
  onProgress?: (progress: number) => void,
  dataSize?: number // Number of rows or features to process
): Promise<any> {
  // Start the import and get the job ID
  const importResponse = await executeImport(request, file)
  const jobId = importResponse.job_id

  // Poll for completion
  const startTime = Date.now()
  let pollCount = 0
  let currentProgress = 0

  // Estimate processing speed based on import type and data size
  const estimatedDuration = calculateEstimatedDuration(request.import_type, dataSize || 1000)

  while (Date.now() - startTime < maxWaitTime) {
    const status = await getImportStatus(jobId)

    // Calculate estimated progress based on time elapsed and expected duration
    if (onProgress && status.status === 'running') {
      const elapsed = Date.now() - startTime

      // Calculate raw progress percentage
      const rawProgress = (elapsed / estimatedDuration) * 100

      // Use a logarithmic curve for more visible progress
      // This gives: 0->0%, 25->50%, 50->70%, 75->85%, 100->95%
      const logProgress = Math.log(rawProgress + 1) / Math.log(101) * 95

      // Ensure progress is always increasing and capped at 95%
      currentProgress = Math.max(currentProgress, Math.min(95, logProgress))
      onProgress(Math.round(currentProgress))
    }

    if (status.status === 'completed') {
      onProgress?.(100)
      return {
        ...status,
        count: status.processed_records || status.total_records || status.count || status.imported_count || status.result?.count || 0
      }
    } else if (status.status === 'failed') {
      throw new Error(status.errors?.join(', ') || 'Import failed')
    }

    // Wait before polling again
    await new Promise(resolve => setTimeout(resolve, pollInterval))
    pollCount++
  }

  throw new Error('Import timed out')
}
