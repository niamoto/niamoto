import { useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Circle,
  Database,
  FileText,
  Globe2,
  Layers,
  Loader2,
  Map,
  Network,
  Table2,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type {
  ImportInventoryItem,
  ImportInventoryQuality,
  ImportInventoryRole,
  ImportInventoryStatus,
} from './importInventory'
import { importInventoryStatuses } from './importInventory'

interface ImportInventoryListProps {
  items: ImportInventoryItem[]
  selectedItemId?: string | null
  onSelectItem?: (item: ImportInventoryItem) => void
  emptyState?: ReactNode
  compact?: boolean
}

const roleOrder: ImportInventoryRole[] = [
  'occurrences',
  'sites',
  'class_values',
  'spatial_layer',
  'raster_layer',
  'reference',
  'dataset',
  'auxiliary',
  'supporting_table',
  'unknown',
]

function statusTone(status: ImportInventoryStatus) {
  switch (status) {
    case 'ready':
    case 'analysed':
    case 'imported':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200'
    case 'needs_attention':
      return 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'
    case 'not_configured':
      return 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-950/30 dark:text-slate-300'
    case 'failed':
      return 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200'
    case 'checking':
    case 'uploading':
    case 'importing':
      return 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200'
    default:
      return 'border-border bg-muted/60 text-muted-foreground'
  }
}

function statusIcon(status: ImportInventoryStatus) {
  switch (status) {
    case 'ready':
    case 'analysed':
    case 'imported':
      return <CheckCircle2 className="h-3.5 w-3.5" />
    case 'needs_attention':
    case 'failed':
      return <AlertCircle className="h-3.5 w-3.5" />
    case 'checking':
    case 'uploading':
    case 'importing':
      return <Loader2 className="h-3.5 w-3.5 animate-spin" />
    default:
      return <Circle className="h-3.5 w-3.5" />
  }
}

function roleIcon(role: ImportInventoryRole) {
  switch (role) {
    case 'occurrences':
      return <Table2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
    case 'sites':
      return <Map className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
    case 'class_values':
      return <Database className="h-4 w-4 text-amber-600 dark:text-amber-400" />
    case 'spatial_layer':
      return <Layers className="h-4 w-4 text-teal-600 dark:text-teal-400" />
    case 'raster_layer':
      return <Globe2 className="h-4 w-4 text-orange-600 dark:text-orange-400" />
    case 'reference':
      return <Network className="h-4 w-4 text-green-600 dark:text-green-400" />
    case 'dataset':
      return <Table2 className="h-4 w-4 text-sky-600 dark:text-sky-400" />
    case 'auxiliary':
      return <Database className="h-4 w-4 text-violet-600 dark:text-violet-400" />
    default:
      return <FileText className="h-4 w-4 text-muted-foreground" />
  }
}

function qualityDot(quality: ImportInventoryQuality) {
  return cn(
    'h-2 w-2 rounded-full',
    quality === 'good' && 'bg-emerald-500',
    quality === 'info' && 'bg-blue-500',
    quality === 'review' && 'bg-amber-500',
    quality === 'error' && 'bg-red-500'
  )
}

function displayMessage(
  message: string | undefined,
  t: (key: string, options?: Record<string, unknown>) => string
) {
  if (message && importInventoryStatuses.includes(message as ImportInventoryStatus)) {
    return t(`cockpit.status.${message}`)
  }
  if (message === 'not_configured') {
    return t('cockpit.messages.not_configured')
  }
  return message
}

export function ImportInventoryList({
  items,
  selectedItemId,
  onSelectItem,
  emptyState,
  compact = false,
}: ImportInventoryListProps) {
  const { t } = useTranslation(['sources'])
  const [collapsedGroups, setCollapsedGroups] = useState<Set<ImportInventoryRole>>(new Set())

  const groups = useMemo(() => {
    const byRole = items.reduce(
      (acc, item) => {
        const group = acc[item.role] ?? []
        group.push(item)
        acc[item.role] = group
        return acc
      },
      {} as Partial<Record<ImportInventoryRole, ImportInventoryItem[]>>
    )

    return roleOrder
      .map((role) => ({ role, items: byRole[role] ?? [] }))
      .filter((group) => group.items.length > 0)
  }, [items])

  const toggleGroup = (role: ImportInventoryRole) => {
    setCollapsedGroups((current) => {
      const next = new Set(current)
      if (next.has(role)) {
        next.delete(role)
      } else {
        next.add(role)
      }
      return next
    })
  }

  if (items.length === 0) {
    return <>{emptyState}</>
  }

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const isCollapsed = collapsedGroups.has(group.role)
        const attentionCount = group.items.filter(
          (item) => item.quality === 'review' || item.quality === 'error'
        ).length

        return (
          <section key={group.role} className="rounded-lg border bg-background/80">
            <button
              type="button"
              className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
              onClick={() => toggleGroup(group.role)}
            >
              <ChevronDown
                className={cn('h-4 w-4 text-muted-foreground transition-transform', isCollapsed && '-rotate-90')}
              />
              {roleIcon(group.role)}
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">
                  {t(`cockpit.roles.${group.role}`)}
                </div>
              </div>
              <Badge variant="outline" className="text-[10px]">
                {t('cockpit.inventory.fileCount', { count: group.items.length })}
              </Badge>
              {attentionCount > 0 && (
                <Badge className="border-amber-200 bg-amber-50 text-[10px] text-amber-800">
                  {t('cockpit.inventory.attentionCount', { count: attentionCount })}
                </Badge>
              )}
            </button>

            {!isCollapsed && (
              <div className="border-t">
                {group.items.map((item) => {
                  const isSelected = selectedItemId === item.id

                  return (
                    <Button
                      key={item.id}
                      type="button"
                      variant="ghost"
                      className={cn(
                        'h-auto w-full justify-start rounded-none border-b px-3 py-2 text-left last:border-b-0 hover:bg-muted/60',
                        'text-foreground hover:text-foreground',
                        isSelected && 'bg-primary/5 hover:bg-primary/10',
                        compact && 'py-1.5'
                      )}
                      onClick={() => onSelectItem?.(item)}
                    >
                      <div className="flex min-w-0 flex-1 items-center gap-3">
                        <span className={qualityDot(item.quality)} />
                        <div className="min-w-0 flex-1">
                          <div className="flex min-w-0 items-center gap-2">
                            <span className="truncate text-sm font-medium">{item.name}</span>
                            {item.detectedEntityName && item.detectedEntityName !== item.name && (
                              <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                                {item.detectedEntityName}
                              </span>
                            )}
                          </div>
                          {!compact && (
                            <div className="mt-0.5 truncate text-xs text-muted-foreground">
                              {displayMessage(item.primaryMessage, t) || item.summary || t(`cockpit.roles.${item.role}`)}
                            </div>
                          )}
                        </div>
                        {item.summary && !compact && (
                          <span className="hidden max-w-[12rem] truncate text-xs text-muted-foreground md:inline">
                            {item.summary}
                          </span>
                        )}
                        <Badge className={cn('gap-1 text-[10px]', statusTone(item.status))} variant="outline">
                          {statusIcon(item.status)}
                          {t(`cockpit.status.${item.status}`)}
                        </Badge>
                      </div>
                    </Button>
                  )
                })}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}
