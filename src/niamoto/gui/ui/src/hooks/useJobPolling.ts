import { useEffect, useRef, useCallback } from 'react'
import { useNotificationStore, JOB_TYPE_LABELS, type TrackedJob, type JobType } from '@/stores/notificationStore'
import { getActiveTransformJob, type TransformStatus } from '@/lib/api/transform'
import { getActiveExportJob, type ExportStatus } from '@/lib/api/export'
import { apiClient } from '@/shared/lib/api/client'

const ACTIVE_POLL_INTERVAL = 1_000  // 1s quand un job est traqué
const DISCOVERY_POLL_INTERVAL = 5_000 // 5s en mode découverte

/** Statuts terminaux pour les différents systèmes de jobs */
const TERMINAL_STATUSES = new Set([
  'completed', 'failed', 'cancelled', 'interrupted',
])

/**
 * Hook de polling global pour détecter et suivre les jobs du pipeline.
 *
 * Deux modes :
 * - Découverte (5s) : interroge transform/active, export/active, imports/jobs
 *   pour détecter des jobs en cours non encore traqués
 * - Actif (1s) : suit la progression des jobs traqués et détecte les transitions
 *   vers des statuts terminaux — démarré uniquement quand des jobs sont traqués
 */
export function useJobPolling() {
  const discoveryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const activeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const discoveryGuard = useRef(false)
  const activeGuard = useRef(false)

  const store = useNotificationStore

  // --- Découverte de jobs non traqués ---

  const discoverJobs = useCallback(async () => {
    if (discoveryGuard.current || document.hidden) return
    discoveryGuard.current = true

    try {
      await Promise.allSettled([
        discoverTransformJob(),
        discoverExportJob(),
        discoverImportJobs(),
        pollTrackedEnrichmentJobs(),
      ])
    } finally {
      discoveryGuard.current = false
    }
  }, [])

  // --- Polling actif des jobs traqués ---

  const pollActiveJobs = useCallback(async () => {
    if (activeGuard.current || document.hidden) return
    const { trackedJobs } = store.getState()
    if (trackedJobs.length === 0) return

    activeGuard.current = true
    try {
      await Promise.allSettled(trackedJobs.map(pollSingleJob))
    } finally {
      activeGuard.current = false
    }
  }, [])

  // Timer de découverte (5s) — toujours actif
  useEffect(() => {
    discoverJobs()
    discoveryTimerRef.current = setInterval(discoverJobs, DISCOVERY_POLL_INTERVAL)

    return () => {
      if (discoveryTimerRef.current) clearInterval(discoveryTimerRef.current)
    }
  }, [discoverJobs])

  // Timer actif (1s) — conditionnel sur les jobs traqués
  useEffect(() => {
    const startActive = () => {
      if (!activeTimerRef.current) {
        pollActiveJobs()
        activeTimerRef.current = setInterval(pollActiveJobs, ACTIVE_POLL_INTERVAL)
      }
    }
    const stopActive = () => {
      if (activeTimerRef.current) {
        clearInterval(activeTimerRef.current)
        activeTimerRef.current = null
      }
    }

    // Vérifier état initial
    if (store.getState().trackedJobs.length > 0) startActive()

    const unsub = store.subscribe((state, prevState) => {
      const had = prevState.trackedJobs.length > 0
      const has = state.trackedJobs.length > 0
      if (has && !had) startActive()
      else if (!has && had) stopActive()
    })

    return () => {
      unsub()
      stopActive()
    }
  }, [pollActiveJobs])

  // Relancer immédiatement au retour de visibilité
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) return
      discoverJobs()
      if (store.getState().trackedJobs.length > 0) pollActiveJobs()
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [discoverJobs, pollActiveJobs])
}

// --- Fonctions de découverte par type ---

async function discoverTransformJob() {
  try {
    const job = await getActiveTransformJob()
    if (!job || TERMINAL_STATUSES.has(job.status)) return
    autoTrackJob(job.job_id, 'transform', 'running', job.progress, job.message, job.started_at, job.phase)
  } catch {
    // Endpoint indisponible — ignorer silencieusement
  }
}

async function discoverExportJob() {
  try {
    const job = await getActiveExportJob()
    if (!job || TERMINAL_STATUSES.has(job.status)) return
    autoTrackJob(job.job_id, 'export', 'running', job.progress, job.message, job.started_at, job.phase)
  } catch {
    // Ignorer
  }
}

async function discoverImportJobs() {
  try {
    const response = await apiClient.get('/imports/jobs', {
      params: { limit: 10, status: 'running' },
    })
    const jobs = response.data?.jobs || []
    for (const job of jobs) {
      if (job.status === 'running') {
        autoTrackJob(job.id, 'import', 'running', job.progress ?? 0, job.message ?? '', job.started_at ?? new Date().toISOString())
      }
    }
  } catch {
    // Ignorer
  }
}

async function pollTrackedEnrichmentJobs() {
  const { trackedJobs } = useNotificationStore.getState()
  const enrichmentJobs = trackedJobs.filter((j) => j.jobType === 'enrichment')
  if (enrichmentJobs.length === 0) return

  await Promise.allSettled(enrichmentJobs.map(async (tracked) => {
    const ref = tracked.meta?.referenceName
    if (!ref) return

    try {
      const response = await apiClient.get(`/enrichment/job/${ref}`)
      const job = response.data

      if (!job) {
        handleJobTerminal(tracked.jobId, 'enrichment', 'completed', '')
        return
      }

      if (TERMINAL_STATUSES.has(job.status)) {
        const msg = job.status === 'completed'
          ? `${job.processed ?? 0} entités enrichies`
          : job.error || ''
        handleJobTerminal(tracked.jobId, 'enrichment', job.status as 'completed' | 'failed', msg)
      } else {
        const progress = job.total > 0 ? Math.round((job.processed / job.total) * 100) : 0
        useNotificationStore.getState().updateTrackedJob(tracked.jobId, {
          status: job.status === 'paused' ? 'paused' : job.status === 'paused_offline' ? 'paused_offline' : 'running',
          progress,
          message: job.current_entity || `${job.processed ?? 0}/${job.total ?? 0}`,
        })
      }
    } catch {
      // 404 = pas de job → ignorer
    }
  }))
}

// --- Polling d'un job traqué individuel ---

async function pollSingleJob(tracked: TrackedJob) {
  if (tracked.jobType === 'enrichment') return // Géré par pollTrackedEnrichmentJobs

  try {
    if (tracked.jobType === 'transform') {
      const job = await getActiveTransformJob()
      if (!job || job.job_id !== tracked.jobId) {
        handleJobTerminal(tracked.jobId, 'transform', 'completed', '')
        return
      }
      if (TERMINAL_STATUSES.has(job.status)) {
        const msg = job.status === 'completed'
          ? formatTransformResult(job)
          : job.error || ''
        handleJobTerminal(tracked.jobId, 'transform', job.status as 'completed' | 'failed' | 'interrupted', msg)
      } else {
        useNotificationStore.getState().updateTrackedJob(tracked.jobId, {
          progress: job.progress,
          message: job.message,
          phase: job.phase,
        })
      }
    } else if (tracked.jobType === 'export') {
      const job = await getActiveExportJob()
      if (!job || job.job_id !== tracked.jobId) {
        handleJobTerminal(tracked.jobId, 'export', 'completed', '')
        return
      }
      if (TERMINAL_STATUSES.has(job.status)) {
        const msg = job.status === 'completed'
          ? formatExportResult(job)
          : job.error || ''
        handleJobTerminal(tracked.jobId, 'export', job.status as 'completed' | 'failed' | 'interrupted', msg)
      } else {
        useNotificationStore.getState().updateTrackedJob(tracked.jobId, {
          progress: job.progress,
          message: job.message,
          phase: job.phase,
        })
      }
    } else if (tracked.jobType === 'import') {
      const response = await apiClient.get(`/imports/jobs/${tracked.jobId}`)
      const job = response.data
      if (!job) {
        handleJobTerminal(tracked.jobId, 'import', 'completed', '')
        return
      }
      if (TERMINAL_STATUSES.has(job.status)) {
        const msg = job.status === 'completed'
          ? job.message || ''
          : job.error || ''
        handleJobTerminal(tracked.jobId, 'import', job.status as 'completed' | 'failed', msg)
      } else {
        useNotificationStore.getState().updateTrackedJob(tracked.jobId, {
          progress: job.progress ?? 0,
          message: job.message ?? '',
        })
      }
    }
  } catch {
    // Erreur réseau ou 404 — garder le job en l'état
  }
}

// --- Helpers ---

function autoTrackJob(
  jobId: string,
  jobType: JobType,
  status: TrackedJob['status'],
  progress: number,
  message: string,
  startedAt: string,
  phase?: string | null
) {
  const state = useNotificationStore.getState()
  if (state.isJobKnown(jobId)) {
    state.updateTrackedJob(jobId, { progress, message, phase })
    return
  }
  state.trackJob({
    jobId,
    jobType,
    status,
    progress,
    message,
    phase,
    startedAt,
  })
}

function handleJobTerminal(
  jobId: string,
  jobType: JobType,
  status: 'completed' | 'failed' | 'interrupted',
  message: string
) {
  const state = useNotificationStore.getState()
  if (state.notifications.some((n) => n.jobId === jobId)) {
    state.removeTrackedJob(jobId)
    return
  }

  const label = JOB_TYPE_LABELS[jobType]
  const titleMap = {
    completed: `${label} terminé`,
    failed: `${label} échoué`,
    interrupted: `${label} interrompu`,
  }

  state.completeJob(jobId, {
    jobId,
    jobType,
    status,
    title: titleMap[status],
    message,
  })
}

function formatTransformResult(job: TransformStatus): string {
  if (!job.result?.metrics) return ''
  const m = job.result.metrics
  return `${m.completed_transformations ?? 0} transformations, ${m.total_widgets ?? 0} widgets`
}

function formatExportResult(job: ExportStatus): string {
  if (!job.result?.metrics) return ''
  const m = job.result.metrics
  return `${m.generated_pages ?? 0} pages générées`
}
