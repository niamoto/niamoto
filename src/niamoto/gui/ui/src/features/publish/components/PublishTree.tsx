/**
 * PublishTree - Sidebar tree navigation for the Publish module
 *
 * Flat list of clickable items (no accordion needed since it's a short list):
 * - Vue d'ensemble
 * - Build + status badge
 * - Deploy + status badge
 * - Historique + count badge
 */

import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { LayoutDashboard, Package, Send, History } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PublishSelection =
  | { type: 'overview' }
  | { type: 'build' }
  | { type: 'deploy' }
  | { type: 'history' }

interface PublishTreeProps {
  selection: PublishSelection
  lastBuildStatus?: string
  lastDeployStatus?: string
  buildCount: number
  deployCount: number
  onSelect: (selection: PublishSelection) => void
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function StatusDot({ status }: { status?: string }) {
  if (!status) return null

  switch (status) {
    case 'completed':
      return <span className="h-2 w-2 shrink-0 rounded-full bg-green-500" />
    case 'failed':
      return <span className="h-2 w-2 shrink-0 rounded-full bg-destructive" />
    case 'running':
      return <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-primary" />
    default:
      return null
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PublishTree({
  selection,
  lastBuildStatus,
  lastDeployStatus,
  buildCount,
  deployCount,
  onSelect,
}: PublishTreeProps) {
  const { t } = useTranslation('publish')

  const items: {
    type: PublishSelection['type']
    label: string
    icon: typeof LayoutDashboard
    badge?: React.ReactNode
  }[] = [
    {
      type: 'overview',
      label: t('tree.overview', 'Overview'),
      icon: LayoutDashboard,
    },
    {
      type: 'build',
      label: t('tree.build', 'Build'),
      icon: Package,
      badge: <StatusDot status={lastBuildStatus} />,
    },
    {
      type: 'deploy',
      label: t('tree.deploy', 'Deploy'),
      icon: Send,
      badge: <StatusDot status={lastDeployStatus} />,
    },
    {
      type: 'history',
      label: t('tree.history', 'History'),
      icon: History,
      badge:
        buildCount + deployCount > 0 ? (
          <Badge variant="secondary" className="text-[10px]">
            {buildCount + deployCount}
          </Badge>
        ) : null,
    },
  ]

  return (
    <div className="flex h-full flex-col px-2 py-2 space-y-1">
      {items.map(({ type, label, icon: Icon, badge }) => {
        const isSelected = selection.type === type
        return (
          <button
            key={type}
            className={cn(
              'flex w-full items-center justify-between rounded-md px-4 py-2 text-sm transition-colors',
              isSelected
                ? 'bg-primary/10 text-primary'
                : 'hover:bg-muted/50'
            )}
            onClick={() => onSelect({ type })}
          >
            <span className="flex items-center gap-2">
              <Icon className="h-4 w-4" />
              {label}
            </span>
            {badge}
          </button>
        )
      })}
    </div>
  )
}
