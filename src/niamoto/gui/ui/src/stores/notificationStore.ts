import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type JobType = 'import' | 'enrichment' | 'transform' | 'export'

export type TrackedJobStatus = 'running' | 'paused' | 'paused_offline'

/** Labels pour les types de jobs (utilisés dans les titres de notifications) */
export const JOB_TYPE_LABELS: Record<JobType, string> = {
  import: 'Import',
  enrichment: 'Enrichissement',
  transform: 'Transformation',
  export: 'Export',
}

export interface TrackedJob {
  jobId: string
  jobType: JobType
  status: TrackedJobStatus
  progress: number
  message: string
  phase?: string | null
  startedAt: string
  /** Pour enrichment : le reference_name nécessaire au polling */
  meta?: { referenceName?: string }
}

export interface AppNotification {
  id: string
  jobId: string
  jobType: JobType
  status: 'completed' | 'failed' | 'interrupted'
  title: string
  message: string
  timestamp: string
  read: boolean
}

const MAX_NOTIFICATIONS = 50

interface NotificationState {
  trackedJobs: TrackedJob[]
  notifications: AppNotification[]

  // Actions — jobs en cours
  trackJob: (job: TrackedJob) => void
  updateTrackedJob: (jobId: string, updates: Partial<TrackedJob>) => void
  removeTrackedJob: (jobId: string) => void

  // Actions — notifications
  completeJob: (
    jobId: string,
    notification: Omit<AppNotification, 'id' | 'timestamp' | 'read'>
  ) => void
  markAsRead: (notificationId: string) => void
  markAllAsRead: () => void
  clearNotifications: () => void

  // Sélecteurs
  isJobKnown: (jobId: string) => boolean
}

const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      trackedJobs: [],
      notifications: [],

      trackJob: (job) => {
        set((state) => {
          if (state.trackedJobs.some((j) => j.jobId === job.jobId)) {
            return state
          }
          return { trackedJobs: [...state.trackedJobs, job] }
        })
      },

      updateTrackedJob: (jobId, updates) => {
        set((state) => {
          const idx = state.trackedJobs.findIndex((j) => j.jobId === jobId)
          if (idx === -1) return state

          const current = state.trackedJobs[idx]
          const hasChange = (Object.keys(updates) as (keyof TrackedJob)[]).some(
            (k) => current[k] !== updates[k]
          )
          if (!hasChange) return state

          const updated = [...state.trackedJobs]
          updated[idx] = { ...current, ...updates }
          return { trackedJobs: updated }
        })
      },

      removeTrackedJob: (jobId) => {
        set((state) => ({
          trackedJobs: state.trackedJobs.filter((j) => j.jobId !== jobId),
        }))
      },

      completeJob: (jobId, notification) => {
        set((state) => {
          if (state.notifications.some((n) => n.jobId === jobId)) {
            return { trackedJobs: state.trackedJobs.filter((j) => j.jobId !== jobId) }
          }

          const newNotification: AppNotification = {
            ...notification,
            id: generateId(),
            timestamp: new Date().toISOString(),
            read: false,
          }

          return {
            trackedJobs: state.trackedJobs.filter((j) => j.jobId !== jobId),
            notifications: [newNotification, ...state.notifications].slice(
              0,
              MAX_NOTIFICATIONS
            ),
          }
        })
      },

      markAsRead: (notificationId) => {
        set((state) => {
          const n = state.notifications.find((n) => n.id === notificationId)
          if (!n || n.read) return state
          return {
            notifications: state.notifications.map((n) =>
              n.id === notificationId ? { ...n, read: true } : n
            ),
          }
        })
      },

      markAllAsRead: () => {
        set((state) => {
          if (state.notifications.every((n) => n.read)) return state
          return {
            notifications: state.notifications.map((n) =>
              n.read ? n : { ...n, read: true }
            ),
          }
        })
      },

      clearNotifications: () => {
        set({ notifications: [] })
      },

      isJobKnown: (jobId) => {
        const { trackedJobs, notifications } = get()
        return (
          trackedJobs.some((j) => j.jobId === jobId) ||
          notifications.some((n) => n.jobId === jobId)
        )
      },
    }),
    {
      name: 'niamoto-notifications',
      partialize: (state) => ({
        notifications: state.notifications,
      }),
    }
  )
)
