/**
 * Flow Sidebar Component
 *
 * Secondary sidebar with three sections:
 * - Données (Data): Import status and sources
 * - Groupes (Groups): Dynamic list of references from import.yml
 * - Site: Structure, static pages, API config
 */

import { cn } from '@/lib/utils'
import {
  Database,
  Layers,
  Globe,
  Plus,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  Loader2,
} from 'lucide-react'
import * as Collapsible from '@radix-ui/react-collapsible'
import { useState } from 'react'
import type { ReferenceInfo } from '@/hooks/useReferences'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

type FlowSection = 'data' | 'groups' | 'site'
type ActivePanel =
  | { type: 'data' }
  | { type: 'dataset'; name: string }
  | { type: 'reference-view'; name: string }
  | { type: 'group'; name: string }
  | { type: 'site'; subSection: 'structure' | 'pages' | 'api' }

interface DatasetInfo {
  name: string
  connector_type: string
  path?: string
}

interface FlowSidebarProps {
  references: ReferenceInfo[]
  datasets: DatasetInfo[]
  isLoading: boolean
  hasImported: boolean
  activePanel: ActivePanel
  onPanelChange: (panel: ActivePanel) => void
  className?: string
}

export function FlowSidebar({
  references,
  datasets,
  isLoading,
  hasImported,
  activePanel,
  onPanelChange,
  className,
}: FlowSidebarProps) {
  const [expandedSections, setExpandedSections] = useState<FlowSection[]>([
    'data',
    'groups',
  ])

  const toggleSection = (section: FlowSection) => {
    setExpandedSections((prev) =>
      prev.includes(section)
        ? prev.filter((s) => s !== section)
        : [...prev, section]
    )
  }

  const isExpanded = (section: FlowSection) => expandedSections.includes(section)

  // Count configured widgets per reference (placeholder for now)
  const getWidgetCount = (_refName: string) => 0

  return (
    <div
      className={cn(
        'flex h-full w-64 flex-col border-r bg-muted/30',
        className
      )}
    >
      {/* Section: Données */}
      <Collapsible.Root
        open={isExpanded('data')}
        onOpenChange={() => toggleSection('data')}
      >
        <Collapsible.Trigger asChild>
          <button
            className={cn(
              'flex w-full items-center gap-2 border-b px-4 py-3 text-sm font-medium',
              'hover:bg-accent/50 transition-colors'
            )}
          >
            <Database className="h-4 w-4 text-primary" />
            <span className="flex-1 text-left">Données</span>
            <Badge variant={hasImported ? 'default' : 'secondary'} className="text-xs">
              {hasImported ? 'Importé' : 'À importer'}
            </Badge>
            {isExpanded('data') ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </Collapsible.Trigger>
        <Collapsible.Content>
          <div className="space-y-1 p-2">
            {/* Import management */}
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                'hover:bg-accent transition-colors',
                activePanel.type === 'data' && 'bg-accent font-medium'
              )}
              onClick={() => onPanelChange({ type: 'data' })}
            >
              {hasImported ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground" />
              )}
              <span>Gestion imports</span>
            </button>

            {/* Datasets */}
            {datasets.length > 0 && (
              <>
                <div className="px-3 pt-2 text-xs font-medium uppercase text-muted-foreground">
                  Datasets
                </div>
                {datasets.map((ds) => (
                  <button
                    key={ds.name}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                      'hover:bg-accent transition-colors',
                      activePanel.type === 'dataset' &&
                        activePanel.name === ds.name &&
                        'bg-accent font-medium'
                    )}
                    onClick={() => onPanelChange({ type: 'dataset', name: ds.name })}
                  >
                    <Database className="h-4 w-4 text-blue-500" />
                    <span className="flex-1 text-left">{ds.name}</span>
                  </button>
                ))}
              </>
            )}

            {/* References for viewing */}
            {references.length > 0 && (
              <>
                <div className="px-3 pt-2 text-xs font-medium uppercase text-muted-foreground">
                  References
                </div>
                {references.map((ref) => (
                  <button
                    key={ref.name}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                      'hover:bg-accent transition-colors',
                      activePanel.type === 'reference-view' &&
                        activePanel.name === ref.name &&
                        'bg-accent font-medium'
                    )}
                    onClick={() => onPanelChange({ type: 'reference-view', name: ref.name })}
                  >
                    <Layers className="h-4 w-4 text-green-500" />
                    <span className="flex-1 text-left">{ref.name}</span>
                    <span className="text-xs text-muted-foreground">
                      ({ref.entity_count ?? '?'})
                    </span>
                  </button>
                ))}
              </>
            )}
          </div>
        </Collapsible.Content>
      </Collapsible.Root>

      {/* Section: Groupes */}
      <Collapsible.Root
        open={isExpanded('groups')}
        onOpenChange={() => toggleSection('groups')}
      >
        <Collapsible.Trigger asChild>
          <button
            className={cn(
              'flex w-full items-center gap-2 border-b px-4 py-3 text-sm font-medium',
              'hover:bg-accent/50 transition-colors'
            )}
          >
            <Layers className="h-4 w-4 text-primary" />
            <span className="flex-1 text-left">Groupes</span>
            <Badge variant="outline" className="text-xs">
              {references.length}
            </Badge>
            {isExpanded('groups') ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </Collapsible.Trigger>
        <Collapsible.Content>
          <div className="space-y-1 p-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : references.length === 0 ? (
              <p className="px-3 py-2 text-sm text-muted-foreground">
                {hasImported
                  ? 'Aucun groupe défini'
                  : 'Importez des données pour voir les groupes'}
              </p>
            ) : (
              references.map((ref) => (
                <button
                  key={ref.name}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                    'hover:bg-accent transition-colors',
                    activePanel.type === 'group' &&
                      activePanel.name === ref.name &&
                      'bg-accent font-medium'
                  )}
                  onClick={() => onPanelChange({ type: 'group', name: ref.name })}
                >
                  <span className="flex-1 text-left">{ref.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({ref.entity_count ?? '?'})
                  </span>
                  {getWidgetCount(ref.name) > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {getWidgetCount(ref.name)} widgets
                    </Badge>
                  )}
                </button>
              ))
            )}
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-muted-foreground"
              disabled={!hasImported}
            >
              <Plus className="h-4 w-4" />
              Ajouter un groupe
            </Button>
          </div>
        </Collapsible.Content>
      </Collapsible.Root>

      {/* Section: Site */}
      <Collapsible.Root
        open={isExpanded('site')}
        onOpenChange={() => toggleSection('site')}
      >
        <Collapsible.Trigger asChild>
          <button
            className={cn(
              'flex w-full items-center gap-2 border-b px-4 py-3 text-sm font-medium',
              'hover:bg-accent/50 transition-colors'
            )}
          >
            <Globe className="h-4 w-4 text-primary" />
            <span className="flex-1 text-left">Site</span>
            <Badge variant="outline" className="text-xs">
              0 pages
            </Badge>
            {isExpanded('site') ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </Collapsible.Trigger>
        <Collapsible.Content>
          <div className="space-y-1 p-2">
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                'hover:bg-accent transition-colors',
                activePanel.type === 'site' &&
                  activePanel.subSection === 'structure' &&
                  'bg-accent font-medium'
              )}
              onClick={() =>
                onPanelChange({ type: 'site', subSection: 'structure' })
              }
            >
              Structure & Navigation
            </button>
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                'hover:bg-accent transition-colors',
                activePanel.type === 'site' &&
                  activePanel.subSection === 'pages' &&
                  'bg-accent font-medium'
              )}
              onClick={() => onPanelChange({ type: 'site', subSection: 'pages' })}
            >
              Pages statiques
            </button>
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm',
                'hover:bg-accent transition-colors',
                activePanel.type === 'site' &&
                  activePanel.subSection === 'api' &&
                  'bg-accent font-medium'
              )}
              onClick={() => onPanelChange({ type: 'site', subSection: 'api' })}
            >
              API
            </button>
          </div>
        </Collapsible.Content>
      </Collapsible.Root>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer status */}
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">
          {hasImported
            ? `${references.length} groupe(s) configuré(s)`
            : 'En attente des données...'}
        </p>
      </div>
    </div>
  )
}
