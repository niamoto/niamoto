import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getAutoConfigureJob,
  startAutoConfigureJob,
  subscribeToAutoConfigureJobEvents,
  type AutoConfigureProgressEvent,
  type AutoConfigureJobStatusResponse,
  type AutoConfigureResponse,
} from '@/features/import/api/smart-config'

type AutoConfigureJobStatus = 'idle' | 'running' | 'completed' | 'failed'

interface UseAutoConfigureJobOptions {
  timeoutMs?: number
  pollIntervalMs?: number
}

interface UseAutoConfigureJobResult {
  status: AutoConfigureJobStatus
  error: string | null
  result: AutoConfigureResponse | null
  events: AutoConfigureProgressEvent[]
  stage: string | null
  start: (
    paths: string[],
    messages?: { failed?: string; timedOut?: string }
  ) => Promise<AutoConfigureResponse>
  reset: () => void
}

function latestStage(events: AutoConfigureProgressEvent[]): string | null {
  return [...events].reverse().find((event) => event.kind === 'stage')?.message ?? null
}

function latestProgressMessage(events: AutoConfigureProgressEvent[]): string | null {
  return [...events]
    .reverse()
    .find((event) => ['stage', 'detail', 'finding'].includes(event.kind))?.message ??
    null
}

function buildTimeoutMessage(
  fallback: string,
  current: AutoConfigureJobStatusResponse
): string {
  const details: string[] = []
  if (typeof current.elapsed_seconds === 'number') {
    details.push(`${Math.round(current.elapsed_seconds)}s`)
  }
  const latestMessage = latestProgressMessage(current.events ?? [])
  if (latestMessage) {
    details.push(latestMessage)
  }
  return details.length > 0 ? `${fallback} (${details.join(' - ')})` : fallback
}

export function useAutoConfigureJob({
  timeoutMs = 600000,
  pollIntervalMs = 400,
}: UseAutoConfigureJobOptions = {}): UseAutoConfigureJobResult {
  const [status, setStatus] = useState<AutoConfigureJobStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AutoConfigureResponse | null>(null)
  const [events, setEvents] = useState<AutoConfigureProgressEvent[]>([])
  const [stage, setStage] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const closeStream = useCallback(() => {
    eventSourceRef.current?.close()
    eventSourceRef.current = null
  }, [])

  const reset = useCallback(() => {
    closeStream()
    setStatus('idle')
    setError(null)
    setResult(null)
    setEvents([])
    setStage(null)
  }, [closeStream])

  const start = useCallback(
    async (paths: string[], messages?: { failed?: string; timedOut?: string }) => {
      closeStream()
      setStatus('running')
      setError(null)
      setResult(null)
      setEvents([])
      setStage(null)

      try {
        const job = await startAutoConfigureJob({ files: paths })
        const eventSource = subscribeToAutoConfigureJobEvents(job.job_id, (event) => {
          setEvents((previous) => [...previous, event].slice(-30))
          if (event.kind === 'stage') {
            setStage(event.message)
          }
        })
        eventSourceRef.current = eventSource

        const startTime = Date.now()
        while (Date.now() - startTime < timeoutMs) {
          const current = await getAutoConfigureJob(job.job_id)
          if (current.events?.length > 0) {
            setEvents(current.events.slice(-30))
            const currentStage = latestStage(current.events)
            if (currentStage) {
              setStage(currentStage)
            }
          }

          if (current.status === 'completed' && current.result) {
            closeStream()
            setResult(current.result)
            setStatus('completed')
            return current.result
          }

          if (current.status === 'failed') {
            throw new Error(
              current.error || messages?.failed || 'Auto-configuration failed'
            )
          }

          await new Promise((resolve) => setTimeout(resolve, pollIntervalMs))
        }

        const current = await getAutoConfigureJob(job.job_id)
        if (current.events?.length > 0) {
          setEvents(current.events.slice(-30))
          const currentStage = latestStage(current.events)
          if (currentStage) {
            setStage(currentStage)
          }
        }

        if (current.status === 'completed' && current.result) {
          closeStream()
          setResult(current.result)
          setStatus('completed')
          return current.result
        }

        if (current.status === 'failed') {
          throw new Error(
            current.error || messages?.failed || 'Auto-configuration failed'
          )
        }

        throw new Error(
          buildTimeoutMessage(
            messages?.timedOut || 'Auto-configuration timed out',
            current
          )
        )
      } catch (err) {
        closeStream()
        const message =
          err instanceof Error
            ? err.message
            : messages?.failed || 'Auto-configuration failed'
        setError(message)
        setStatus('failed')
        throw err
      }
    },
    [closeStream, pollIntervalMs, timeoutMs]
  )

  useEffect(() => () => closeStream(), [closeStream])

  return {
    status,
    error,
    result,
    events,
    stage,
    start,
    reset,
  }
}
