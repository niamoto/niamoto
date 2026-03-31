/**
 * CollectionsTree - Sidebar navigation for the Collections module
 *
 * Flat list: "Vue d'ensemble" button followed by each collection
 * with a status dot (green/orange) and entity count.
 */

import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { Layers, Loader2 } from 'lucide-react'
import { usePipelineStatus, type EntityStatus } from '@/hooks/usePipelineStatus'
import type { ReferenceInfo } from '@/hooks/useReferences'

// =============================================================================
// TYPES
// =============================================================================

export type CollectionsSelection =
  | { type: 'overview' }
  | { type: 'api-settings' }
  | { type: 'collection'; name: string }

interface CollectionsTreeProps {
  references: ReferenceInfo[]
  referencesLoading: boolean
  selection: CollectionsSelection
  onSelect: (selection: CollectionsSelection) => void
}

// =============================================================================
// COMPONENT
// =============================================================================

export function CollectionsTree({
  references,
  referencesLoading,
  selection,
  onSelect,
}: CollectionsTreeProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data: pipelineStatus } = usePipelineStatus()

  // Build status map
  const statusByName = new Map<string, EntityStatus>()
  if (pipelineStatus?.groups?.items) {
    for (const item of pipelineStatus.groups.items) {
      statusByName.set(item.name, item)
    }
  }

  const isSelected = (type: CollectionsSelection['type'], name?: string) => {
    if (selection.type !== type) return false
    if (type === 'collection' && name !== undefined) {
      return selection.type === 'collection' && selection.name === name
    }
    return true
  }

  return (
    <div className="flex h-full flex-col">
      {/* Vue d'ensemble */}
      <div className="px-2 pt-2">
        <button
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-4 py-2 text-sm transition-colors',
            isSelected('overview')
              ? 'bg-primary/10 text-primary'
              : 'hover:bg-muted/50'
          )}
          onClick={() => onSelect({ type: 'overview' })}
        >
          <Layers className="h-4 w-4" />
          {t('collections.overview', 'Overview')}
        </button>
      </div>

      {/* Separator */}
      <div className="mx-4 my-2 h-px bg-border" />

      {/* Flat collection list */}
      <div className="space-y-0.5 px-2">
        {referencesLoading ? (
          <div className="flex items-center gap-2 px-4 py-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('common:status.loading')}
          </div>
        ) : references.length === 0 ? (
          <p className="px-4 py-2 text-xs italic text-muted-foreground">
            {t('collections.noCollections', 'No collections')}
          </p>
        ) : (
          references.map((ref) => {
            const status = statusByName.get(ref.name)?.status
            return (
              <button
                key={ref.name}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-4 py-2 text-sm transition-colors',
                  isSelected('collection', ref.name)
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'hover:bg-muted/50'
                )}
                onClick={() => onSelect({ type: 'collection', name: ref.name })}
              >
                <span
                  className={cn(
                    'h-1.5 w-1.5 shrink-0 rounded-full',
                    status === 'fresh' && 'bg-green-500',
                    status === 'stale' && 'bg-amber-500',
                    status === 'never_run' && 'bg-muted-foreground/30',
                    !status && 'bg-muted-foreground/30'
                  )}
                />
                <span className="flex-1 truncate text-left">
                  {ref.name}
                </span>
                {ref.entity_count !== undefined && (
                  <span className="text-[10px] text-muted-foreground tabular-nums">
                    {ref.entity_count}
                  </span>
                )}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
