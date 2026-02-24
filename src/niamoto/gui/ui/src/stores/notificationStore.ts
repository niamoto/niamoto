import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type JobType = 'import' | 'enrichment' | 'transform' | 'export'

export type TrackedJobStatus = 'running' | 'paused' | 'paused_offline'

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
  path?: string
}

const MAX_NOTIFICATIONS = 50
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000 // 7 jours

interface NotificationState {
  trackedJobs: TrackedJob[]
  notifications: AppNotification[]
  unreadCount: number

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
  clearOldNotifications: () => void

  // Sélecteurs
  hasRunningJob: (jobType?: JobType) => boolean
  isJobKnown: (jobId: string) => boolean
}

const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      trackedJobs: [],
      notifications: [],
      unreadCount: 0,

      trackJob: (job) => {
        set((state) => {
          // Éviter les doublons
          if (state.trackedJobs.some((j) => j.jobId === job.jobId)) {
            return state
          }
          return { trackedJobs: [...state.trackedJobs, job] }
        })
      },

      updateTrackedJob: (jobId, updates) => {
        set((state) => ({
          trackedJobs: state.trackedJobs.map((j) =>
            j.jobId === jobId ? { ...j, ...updates } : j
          ),
        }))
      },

      removeTrackedJob: (jobId) => {
        set((state) => ({
          trackedJobs: state.trackedJobs.filter((j) => j.jobId !== jobId),
        }))
      },

      completeJob: (jobId, notification) => {
        set((state) => {
          // Éviter les doublons de notification
          if (state.notifications.some((n) => n.jobId === jobId)) {
            return { trackedJobs: state.trackedJobs.filter((j) => j.jobId !== jobId) }
          }

          const newNotification: AppNotification = {
            ...notification,
            id: generateId(),
            timestamp: new Date().toISOString(),
            read: false,
          }

          const updated = [newNotification, ...state.notifications].slice(
            0,
            MAX_NOTIFICATIONS
          )

          return {
            trackedJobs: state.trackedJobs.filter((j) => j.jobId !== jobId),
            notifications: updated,
            unreadCount: state.unreadCount + 1,
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
            unreadCount: Math.max(0, state.unreadCount - 1),
          }
        })
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        }))
      },

      clearNotifications: () => {
        set({ notifications: [], unreadCount: 0 })
      },

      clearOldNotifications: () => {
        const now = Date.now()
        set((state) => {
          const fresh = state.notifications.filter(
            (n) => now - new Date(n.timestamp).getTime() < MAX_AGE_MS
          )
          const removedUnread = state.notifications.filter(
            (n) => !n.read && now - new Date(n.timestamp).getTime() >= MAX_AGE_MS
          ).length
          return {
            notifications: fresh,
            unreadCount: Math.max(0, state.unreadCount - removedUnread),
          }
        })
      },

      hasRunningJob: (jobType) => {
        const { trackedJobs } = get()
        if (jobType) {
          return trackedJobs.some(
            (j) => j.jobType === jobType && j.status === 'running'
          )
        }
        return trackedJobs.some((j) => j.status === 'running')
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
        unreadCount: state.unreadCount,
      }),
    }
  )
)
