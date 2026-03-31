/**
 * GroupsTree - Sidebar tree navigation for the Groups module
 *
 * Displays a "Vue d'ensemble" overview button followed by an accordion
 * listing all reference groups with kind badges and entity counts.
 * Follows the SiteTree pattern from SiteBuilder.tsx.
 */

import { useTranslation } from 'react-i18next'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Layers, Loader2, ArrowRight, FileCode } from 'lucide-react'
import type { ReferenceInfo } from '@/hooks/useReferences'

// =============================================================================
// TYPES
// =============================================================================

export type GroupsSelection =
  | { type: 'overview' }
  | { type: 'api-settings' }
  | { type: 'group'; name: string }

interface GroupsTreeProps {
  references: ReferenceInfo[]
  referencesLoading: boolean
  selection: GroupsSelection
  onSelect: (selection: GroupsSelection) => void
}

// =============================================================================
// COMPONENT
// =============================================================================

export function GroupsTree({
  references,
  referencesLoading,
  selection,
  onSelect,
}: GroupsTreeProps) {
  const { t } = useTranslation(['sources', 'common'])

  const isSelected = (type: GroupsSelection['type'], name?: string) => {
    if (selection.type !== type) return false
    if (type === 'group' && name !== undefined) {
      return selection.type === 'group' && selection.name === name
    }
    return true
  }

  return (
    <div className="flex h-full flex-col">
      {/* Vue d'ensemble button */}
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
          {t('groups.overview', 'Overview')}
        </button>
      </div>

      {/* Groups accordion */}
      <Accordion
        type="multiple"
        defaultValue={['groups']}
        className="px-2 py-2"
      >
        <AccordionItem value="groups" className="border-none">
          <AccordionTrigger className="py-2 text-sm hover:no-underline">
            <span className="flex items-center gap-2">
              <Layers className="h-4 w-4" />
              {t('groups.title', 'Groups')}
              {referencesLoading ? (
                <Loader2 className="ml-auto h-3 w-3 animate-spin" />
              ) : (
                <Badge variant="secondary" className="ml-auto text-[10px]">
                  {references.length}
                </Badge>
              )}
            </span>
          </AccordionTrigger>
          <AccordionContent className="pb-2">
            <div className="space-y-1 pl-6">
              {referencesLoading ? (
                <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {t('common:status.loading')}
                </div>
              ) : references.length === 0 ? (
                <p className="px-2 py-1.5 text-xs italic text-muted-foreground">
                  {t('groups.noGroups', 'No groups')}
                </p>
              ) : (
                references.map((ref, index) => (
                  <button
                    key={`${ref.name}-${index}`}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                      isSelected('group', ref.name)
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-muted/50'
                    )}
                    onClick={() => onSelect({ type: 'group', name: ref.name })}
                  >
                    <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                    <span className="flex-1 truncate text-left">
                      {ref.name}
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {ref.kind}
                    </Badge>
                    {ref.entity_count !== undefined && (
                      <Badge variant="secondary" className="text-[10px]">
                        {ref.entity_count}
                      </Badge>
                    )}
                  </button>
                ))
              )}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <div className="mt-auto px-2 pb-3">
        <button
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-4 py-2 text-sm transition-colors',
            isSelected('api-settings')
              ? 'bg-primary/10 text-primary'
              : 'hover:bg-muted/50'
          )}
          onClick={() => onSelect({ type: 'api-settings' })}
        >
          <FileCode className="h-4 w-4" />
          {t('groups.apiSettings', 'API settings')}
        </button>
      </div>
    </div>
  )
}
