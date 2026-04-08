import { useCallback, useRef, useState } from 'react'
import {
  createEntitiesBulk,
  type AutoConfigureResponse,
} from '@/features/import/api/smart-config'
import {
  executeImportAll,
  type ImportErrorDetails,
  getImportStatus,
  type ImportJobEvent,
} from '@/features/import/api/import'

type ImportJobStatus = 'idle' | 'running' | 'completed' | 'failed'

export interface ImportJobState {
  status: ImportJobStatus
  error: string | null
  totalEntities: number
  processedEntities: number
  currentEntity?: string
  currentEntityType?: string
  phase?: string | null
  message?: string
  progress?: number
  events: ImportJobEvent[]
  errorDetails?: ImportErrorDetails | null
}

interface UseImportJobOptions {
  timeoutMs?: number
  pollIntervalMs?: number
}

interface UseImportJobResult {
  state: ImportJobState
  start: (
    config: AutoConfigureResponse,
    messages?: {
      writingImportYml?: string
      importJobStarting?: string
      savingConfigDone?: string
      importFailed?: string
      importTimedOut?: string
    }
  ) => Promise<void>
  reset: () => void
}

const INITIAL_STATE: ImportJobState = {
  status: 'idle',
  error: null,
  totalEntities: 0,
  processedEntities: 0,
  events: [],
  errorDetails: null,
}

export function useImportJob({
  timeoutMs = 600000,
  pollIntervalMs = 500,
}: UseImportJobOptions = {}): UseImportJobResult {
  const [state, setState] = useState<ImportJobState>(INITIAL_STATE)
  const startedRef = useRef(false)

  const reset = useCallback(() => {
    startedRef.current = false
    setState(INITIAL_STATE)
  }, [])

  const start = useCallback(
    async (
      config: AutoConfigureResponse,
      messages?: {
        writingImportYml?: string
        importJobStarting?: string
        savingConfigDone?: string
        importFailed?: string
        importTimedOut?: string
      }
    ) => {
      if (startedRef.current) return
      startedRef.current = true
      let latestErrorDetails: ImportErrorDetails | null = null

      try {
        setState({
          status: 'running',
          error: null,
          totalEntities: 0,
          processedEntities: 0,
          phase: 'saving',
          message: messages?.writingImportYml || 'Writing import.yml',
          progress: 0,
          currentEntity: undefined,
          currentEntityType: undefined,
          events: [
            {
              timestamp: new Date().toISOString(),
              kind: 'stage' as const,
              message: messages?.writingImportYml || 'Writing import.yml',
              phase: 'saving',
            },
          ],
          errorDetails: null,
        })

        await createEntitiesBulk({
          entities: config.entities,
          auxiliary_sources: config.auxiliary_sources || [],
        })

        setState((previous) => ({
          ...previous,
          phase: 'importing',
          message: messages?.importJobStarting || 'Starting import job',
          events: [
            ...previous.events,
            {
              timestamp: new Date().toISOString(),
              kind: 'finding' as const,
              message: messages?.savingConfigDone || 'Import configuration saved',
              phase: 'saving',
            },
            {
              timestamp: new Date().toISOString(),
              kind: 'detail' as const,
              message: messages?.importJobStarting || 'Starting import job',
              phase: 'importing',
            },
          ].slice(-30),
        }))

        const importResponse = await executeImportAll(false)
        const jobId = importResponse.job_id
        const startTime = Date.now()

        while (Date.now() - startTime < timeoutMs) {
          const current = await getImportStatus(jobId)
          setState({
            status: 'running',
            error: null,
            totalEntities: current.total_entities || 0,
            processedEntities: current.processed_entities || 0,
            currentEntity: current.current_entity || undefined,
            currentEntityType: current.current_entity_type || undefined,
            phase: current.phase,
            message: current.message,
            progress: current.progress,
            events: current.events || [],
            errorDetails: current.error_details || null,
          })

          if (current.status === 'completed') {
            setState((previous) => ({
              ...previous,
              status: 'completed',
            }))
            return
          }

          if (current.status === 'failed') {
            latestErrorDetails = current.error_details || null
            throw new Error(current.errors?.join(', ') || messages?.importFailed || 'Import failed')
          }

          await new Promise((resolve) => setTimeout(resolve, pollIntervalMs))
        }

        throw new Error(messages?.importTimedOut || 'Import timed out')
      } catch (err) {
        const message =
          err instanceof Error ? err.message : messages?.importFailed || 'Import failed'
        startedRef.current = false
        setState((previous) => ({
          ...previous,
          status: 'failed',
          error: message,
          errorDetails: latestErrorDetails ?? previous.errorDetails ?? null,
        }))
        throw err
      }
    },
    [pollIntervalMs, timeoutMs]
  )

  return {
    state,
    start,
    reset,
  }
}
