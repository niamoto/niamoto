import { useEffect, useRef, useCallback } from 'react'
import { useNotificationStore, type TrackedJob, type JobType } from '@/stores/notificationStore'
import { getActiveTransformJob } from '@/lib/api/transform'
import { getActiveExportJob } from '@/lib/api/export'
import { apiClient } from '@/lib/api/client'

const ACTIVE_POLL_INTERVAL = 1_000  // 1s quand un job est traqué
const DISCOVERY_POLL_INTERVAL = 5_000 // 5s en mode découverte

/** Statuts terminaux pour les différents systèmes de jobs */
const TERMINAL_STATUSES = new Set([
  'completed', 'failed', 'cancelled', 'interrupted',
])

/** Labels FR pour les types de jobs */
const JOB_TYPE_LABELS: Record<JobType, string> = {
  import: 'Import',
  enrichment: 'Enrichissement',
  transform: 'Transformation',
  export: 'Export',
}

/**
 * Hook de polling global pour détecter et suivre les jobs du pipeline.
 *
 * Deux modes :
 * - Découverte (5s) : interroge transform/active, export/active, imports/jobs
 *   pour détecter des jobs en cours non encore traqués
 * - Actif (1s) : suit la progression des jobs traqués et détecte les transitions
 *   vers des statuts terminaux
 */
export function useJobPolling() {
  const discoveryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const activeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollingRef = useRef(false) // guard contre les overlaps async

  const store = useNotificationStore

  // --- Découverte de jobs non traqués ---

  const discoverJobs = useCallback(async () => {
    if (pollingRef.current) return
    pollingRef.current = true

    try {
      await Promise.allSettled([
        discoverTransformJob(),
        discoverExportJob(),
        discoverImportJobs(),
        pollTrackedEnrichmentJobs(),
      ])
    } finally {
      pollingRef.current = false
    }
  }, [])

  // --- Polling actif des jobs traqués ---

  const pollActiveJobs = useCallback(async () => {
    const { trackedJobs } = store.getState()
    if (trackedJobs.length === 0) return

    await Promise.allSettled(
      trackedJobs.map((job) => pollSingleJob(job))
    )
  }, [])

  // --- Gestion des timers ---

  useEffect(() => {
    // Purger les vieilles notifications au montage
    store.getState().clearOldNotifications()

    // Découverte immédiate au montage
    discoverJobs()

    // Timer de découverte (5s)
    discoveryTimerRef.current = setInterval(discoverJobs, DISCOVERY_POLL_INTERVAL)

    // Timer actif (1s)
    activeTimerRef.current = setInterval(pollActiveJobs, ACTIVE_POLL_INTERVAL)

    return () => {
      if (discoveryTimerRef.current) clearInterval(discoveryTimerRef.current)
      if (activeTimerRef.current) clearInterval(activeTimerRef.current)
    }
  }, [discoverJobs, pollActiveJobs])
}

// --- Fonctions de découverte par type ---

async function discoverTransformJob() {
  try {
    const job = await getActiveTransformJob()
    if (!job || TERMINAL_STATUSES.has(job.status)) return
    autoTrackJob(job.job_id, 'transform', job.status === 'running' ? 'running' : 'running', job.progress, job.message, job.started_at, job.phase)
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

  for (const tracked of enrichmentJobs) {
    const ref = tracked.meta?.referenceName
    if (!ref) continue

    try {
      const response = await apiClient.get(`/enrichment/job/${ref}`)
      const job = response.data

      if (!job) {
        handleJobTerminal(tracked.jobId, 'enrichment', 'completed', '')
        continue
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
  }
}

// --- Polling d'un job traqué individuel ---

async function pollSingleJob(tracked: TrackedJob) {
  if (tracked.jobType === 'enrichment') return // Géré par pollTrackedEnrichmentJobs

  try {
    if (tracked.jobType === 'transform') {
      const job = await getActiveTransformJob()
      if (!job || job.job_id !== tracked.jobId) {
        // Job disparu → probablement terminé
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
    // Déjà traqué → mettre à jour
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
    // Notification déjà créée → juste retirer du tracking
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

function formatTransformResult(job: any): string {
  if (!job.result?.metrics) return ''
  const m = job.result.metrics
  return `${m.completed_transformations ?? 0} transformations, ${m.total_widgets ?? 0} widgets`
}

function formatExportResult(job: any): string {
  if (!job.result?.metrics) return ''
  const m = job.result.metrics
  return `${m.generated_pages ?? 0} pages générées`
}
