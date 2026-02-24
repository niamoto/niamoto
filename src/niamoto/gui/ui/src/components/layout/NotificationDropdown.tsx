import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { Bell, CheckCircle2, XCircle, AlertTriangle, Loader2, Pause, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useNotificationStore, JOB_TYPE_LABELS, type TrackedJob, type AppNotification } from '@/stores/notificationStore'
import { cn } from '@/lib/utils'

function timeAgo(isoDate: string, t: TFunction): string {
  const seconds = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000)
  if (seconds < 60) return t('notifications.timeAgo.justNow')
  if (seconds < 3600) return t('notifications.timeAgo.minutesAgo', { count: Math.floor(seconds / 60) })
  if (seconds < 86400) return t('notifications.timeAgo.hoursAgo', { count: Math.floor(seconds / 3600) })
  return t('notifications.timeAgo.daysAgo', { count: Math.floor(seconds / 86400) })
}

function ActiveJobItem({ job, t }: { job: TrackedJob; t: TFunction }) {
  const label = t(`notifications.jobTypes.${job.jobType}`, JOB_TYPE_LABELS[job.jobType])

  return (
    <div className="px-3 py-2.5 space-y-1.5">
      <div className="flex items-center gap-2">
        {job.status === 'paused' ? (
          <Pause className="h-3.5 w-3.5 text-amber-500 shrink-0" />
        ) : job.status === 'paused_offline' ? (
          <WifiOff className="h-3.5 w-3.5 text-amber-500 shrink-0" />
        ) : (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500 shrink-0" />
        )}
        <span className="text-sm font-medium truncate">{label}</span>
        <span className="text-xs text-muted-foreground ml-auto">{job.progress}%</span>
      </div>
      <Progress value={job.progress} className="h-1.5" />
      {job.message && (
        <p className="text-xs text-muted-foreground truncate">{job.message}</p>
      )}
    </div>
  )
}

function NotificationItem({
  notification,
  onMarkAsRead,
  t,
}: {
  notification: AppNotification
  onMarkAsRead: (id: string) => void
  t: TFunction
}) {
  const StatusIcon = notification.status === 'completed'
    ? CheckCircle2
    : notification.status === 'failed'
      ? XCircle
      : AlertTriangle

  const iconColor = notification.status === 'completed'
    ? 'text-green-500'
    : notification.status === 'failed'
      ? 'text-red-500'
      : 'text-amber-500'

  return (
    <button
      className={cn(
        'w-full text-left px-3 py-2.5 hover:bg-accent transition-colors',
        !notification.read && 'bg-accent/50'
      )}
      onClick={() => onMarkAsRead(notification.id)}
    >
      <div className="flex items-start gap-2">
        <StatusIcon className={cn('h-4 w-4 mt-0.5 shrink-0', iconColor)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium truncate">
              {notification.title}
            </span>
          </div>
          {notification.message && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {notification.message}
            </p>
          )}
          <p className="text-xs text-muted-foreground mt-0.5">
            {timeAgo(notification.timestamp, t)}
          </p>
        </div>
        {!notification.read && (
          <span className="h-2 w-2 rounded-full bg-blue-500 shrink-0 mt-1.5" />
        )}
      </div>
    </button>
  )
}

export function NotificationDropdown() {
  const { t } = useTranslation('common')
  const trackedJobs = useNotificationStore((s) => s.trackedJobs)
  const notifications = useNotificationStore((s) => s.notifications)
  const markAsRead = useNotificationStore((s) => s.markAsRead)
  const markAllAsRead = useNotificationStore((s) => s.markAllAsRead)
  const clearNotifications = useNotificationStore((s) => s.clearNotifications)

  const unreadCount = notifications.filter((n) => !n.read).length
  const hasActiveJobs = trackedJobs.length > 0
  const showBadge = unreadCount > 0 || hasActiveJobs
  const recentNotifications = notifications.slice(0, 20)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {showBadge && (
            <span
              className={cn(
                'absolute right-1 top-1 flex items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white',
                unreadCount > 0 ? 'h-4 min-w-4 px-0.5' : 'h-2 w-2',
                hasActiveJobs && unreadCount === 0 && 'animate-pulse'
              )}
            >
              {unreadCount > 0 ? (unreadCount > 9 ? '9+' : unreadCount) : ''}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>{t('notifications.title', 'Notifications')}</span>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="text-xs font-normal text-muted-foreground hover:text-foreground"
            >
              {t('notifications.mark_all_read', 'Tout marquer comme lu')}
            </button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Section : Jobs en cours */}
        {hasActiveJobs && (
          <>
            <div className="px-3 py-1.5">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {t('notifications.active_jobs', 'En cours')}
              </span>
            </div>
            {trackedJobs.map((job) => (
              <ActiveJobItem key={job.jobId} job={job} t={t} />
            ))}
            {recentNotifications.length > 0 && <DropdownMenuSeparator />}
          </>
        )}

        {/* Section : Notifications récentes */}
        {recentNotifications.length > 0 ? (
          <>
            {hasActiveJobs && (
              <div className="px-3 py-1.5">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {t('notifications.recent', 'Récents')}
                </span>
              </div>
            )}
            <ScrollArea className={recentNotifications.length > 4 ? 'h-64' : undefined}>
              {recentNotifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onMarkAsRead={markAsRead}
                  t={t}
                />
              ))}
            </ScrollArea>
          </>
        ) : (
          !hasActiveJobs && (
            <div className="px-3 py-6 text-center text-sm text-muted-foreground">
              {t('notifications.no_notifications', 'Aucune notification')}
            </div>
          )
        )}

        {/* Footer */}
        {recentNotifications.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <div className="px-3 py-2 flex justify-center">
              <button
                onClick={clearNotifications}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                {t('notifications.clear_all', 'Effacer')}
              </button>
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
