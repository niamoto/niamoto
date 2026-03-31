/**
 * CollectionsOverview - Enriched card grid for the Collections module
 *
 * Each card shows: counters, freshness status, configured block badges,
 * last transform date, and direct shortcut buttons to Blocs/Liste/Export.
 */

import { useTranslation } from 'react-i18next'
import {
  usePipelineStatus,
  type EntityStatus,
} from '@/hooks/usePipelineStatus'
import { useConfiguredWidgets } from '@/components/widgets'
import { useApiExportTargets } from '@/features/collections/hooks/useApiExportConfigs'
import type { ReferenceInfo } from '@/hooks/useReferences'
import type { CollectionsSelection } from './CollectionsTree'
import {
  Card,
  CardContent,
  CardHeader,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Layers, LayoutGrid, ListOrdered, FileCode, CheckCircle, AlertTriangle, Clock, Minus } from 'lucide-react'

// =============================================================================
// COLLECTION CARD
// =============================================================================

interface CollectionCardProps {
  reference: ReferenceInfo
  entityStatus?: EntityStatus
  onSelect: (selection: CollectionsSelection, tab?: string) => void
}

function CollectionCard({ reference, entityStatus, onSelect }: CollectionCardProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { configuredIds } = useConfiguredWidgets(reference.name)
  const { data: targets } = useApiExportTargets()

  // Count exports for this collection
  const exportCount = (targets ?? []).filter((target) =>
    target.groups.some((g) => g.group_by === reference.name && g.enabled)
  ).length

  // Freshness
  const status = entityStatus?.status ?? 'never_run'
  const isFresh = status === 'fresh'
  const isStale = status === 'stale'
  const lastRunAt = entityStatus?.last_run_at

  // Kind labels
  const kindLabels: Record<string, string> = {
    hierarchical: t('collectionPanel.kinds.hierarchical'),
    generic: t('collectionPanel.kinds.flat'),
    spatial: t('collectionPanel.kinds.spatial'),
  }

  // Format last run
  const lastRunLabel = lastRunAt ? formatRelativeTime(lastRunAt) : null

  return (
    <Card
      className="cursor-pointer transition-all hover:border-primary hover:shadow-sm"
      onClick={() => onSelect({ type: 'collection', name: reference.name })}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <span className="text-lg font-semibold">{reference.name}</span>
          </div>
          {isFresh ? (
            <Badge variant="outline" className="gap-1 border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400">
              <CheckCircle className="h-3 w-3" />
              {t('collections.overviewFresh', 'Up to date')}
            </Badge>
          ) : isStale ? (
            <Badge variant="outline" className="gap-1 border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              {t('collections.overviewStale', 'Needs recomputing')}
            </Badge>
          ) : (
            <Badge variant="outline" className="gap-1 text-muted-foreground">
              <Minus className="h-3 w-3" />
              {t('collections.overviewNeverRun', 'Never computed')}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="secondary" className="text-[10px]">
            {kindLabels[reference.kind] || reference.kind}
          </Badge>
          <span>{reference.entity_count ?? '?'} {t('reference.entities', 'entities')}</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Counters */}
        <div className="grid grid-cols-3 gap-2">
          <CounterBox
            value={configuredIds.length}
            label={t('collections.overviewBlocks', 'Blocks')}
          />
          <CounterBox
            value={reference.entity_count ?? 0}
            label={t('collections.overviewSheets', 'Sheets')}
          />
          <CounterBox
            value={exportCount}
            label={t('collections.overviewExports', 'Exports')}
          />
        </div>

        {/* Block type badges */}
        {configuredIds.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {configuredIds.slice(0, 5).map((id) => (
              <Badge key={id} variant="outline" className="text-[10px]">
                {id}
              </Badge>
            ))}
            {configuredIds.length > 5 && (
              <Badge variant="outline" className="text-[10px]">
                +{configuredIds.length - 5}
              </Badge>
            )}
          </div>
        )}

        {/* Last run */}
        {lastRunLabel && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {t('collections.overviewLastRun', 'Last computation')}: {lastRunLabel}
          </div>
        )}

        {/* Shortcut buttons */}
        <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
          <Button
            variant="default"
            size="sm"
            className="flex-1 text-xs"
            onClick={() => onSelect({ type: 'collection', name: reference.name }, 'content')}
          >
            <LayoutGrid className="mr-1 h-3 w-3" />
            {t('collectionPanel.tabs.blocks')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1 text-xs"
            onClick={() => onSelect({ type: 'collection', name: reference.name }, 'index')}
          >
            <ListOrdered className="mr-1 h-3 w-3" />
            {t('collectionPanel.tabs.list')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1 text-xs"
            onClick={() => onSelect({ type: 'collection', name: reference.name }, 'export')}
          >
            <FileCode className="mr-1 h-3 w-3" />
            {t('collectionPanel.tabs.export')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// COUNTER BOX
// =============================================================================

function CounterBox({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-md bg-muted/50 p-2 text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
    </div>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

interface CollectionsOverviewProps {
  references: ReferenceInfo[]
  onSelect: (selection: CollectionsSelection, tab?: string) => void
}

export function CollectionsOverview({ references, onSelect }: CollectionsOverviewProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data: pipelineStatus } = usePipelineStatus()

  // Build a map of entity statuses by name
  const statusByName = new Map<string, EntityStatus>()
  if (pipelineStatus?.groups?.items) {
    for (const item of pipelineStatus.groups.items) {
      statusByName.set(item.name, item)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t('collections.title', 'Collections')}</h1>
        <p className="mt-1 text-muted-foreground">
          {t('collections.description', 'Configure blocks and data sources for each collection.')}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {references.map((ref) => (
          <CollectionCard
            key={ref.name}
            reference={ref}
            entityStatus={statusByName.get(ref.name)}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// HELPERS
// =============================================================================

function formatRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return "< 1 min"
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}
