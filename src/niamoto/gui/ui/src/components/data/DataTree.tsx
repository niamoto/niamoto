/**
 * DataTree - Sidebar tree navigation for the Data (Sources) module
 *
 * Sections:
 * - Datasets: list of imported datasets with entity counts
 * - References: list of references with kind badges and entity counts
 * - Import: action button to launch the import wizard
 */

import { useTranslation } from 'react-i18next'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Database, BookOpen, Upload, Loader2, Table2 } from 'lucide-react'
import type { DatasetInfo } from '@/hooks/useDatasets'
import type { ReferenceInfo } from '@/hooks/useReferences'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DataSelection =
  | { type: 'overview' }
  | { type: 'dataset'; name: string }
  | { type: 'reference'; name: string }
  | { type: 'import' }

interface DataTreeProps {
  datasets: DatasetInfo[]
  references: ReferenceInfo[]
  datasetsLoading: boolean
  referencesLoading: boolean
  selection: DataSelection
  onSelect: (selection: DataSelection) => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DataTree({
  datasets,
  references,
  datasetsLoading,
  referencesLoading,
  selection,
  onSelect,
}: DataTreeProps) {
  const { t } = useTranslation(['sources', 'common'])

  const isSelected = (type: DataSelection['type'], name?: string) => {
    if (selection.type !== type) return false
    if (name !== undefined && 'name' in selection) return selection.name === name
    return name === undefined
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <Accordion
          type="multiple"
          defaultValue={['datasets', 'references', 'import']}
          className="px-2 py-2"
        >
          {/* Datasets Section */}
          <AccordionItem value="datasets" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <Database className="h-4 w-4" />
                {t('tree.datasets', 'Datasets')}
                {datasetsLoading ? (
                  <Loader2 className="ml-auto h-3 w-3 animate-spin" />
                ) : (
                  <Badge variant="secondary" className="ml-auto text-[10px]">
                    {datasets.length}
                  </Badge>
                )}
              </span>
            </AccordionTrigger>
            <AccordionContent className="pb-2">
              <div className="space-y-1 pl-6">
                {datasetsLoading ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground italic">
                    {t('tree.loading', 'Loading...')}
                  </p>
                ) : datasets.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground italic">
                    {t('tree.noDatasets', 'No imported datasets')}
                  </p>
                ) : (
                  datasets.map((dataset) => (
                    <button
                      key={dataset.name}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                        isSelected('dataset', dataset.name)
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-muted/50'
                      )}
                      onClick={() => onSelect({ type: 'dataset', name: dataset.name })}
                    >
                      <Table2 className="h-4 w-4 shrink-0" />
                      <span className="truncate flex-1 text-left">{dataset.name}</span>
                      {dataset.entity_count != null && (
                        <Badge variant="outline" className="text-[10px]">
                          {dataset.entity_count.toLocaleString()}
                        </Badge>
                      )}
                    </button>
                  ))
                )}
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* References Section */}
          <AccordionItem value="references" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                {t('tree.references', 'References')}
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
                  <p className="px-2 py-1.5 text-xs text-muted-foreground italic">
                    {t('tree.loading', 'Loading...')}
                  </p>
                ) : references.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground italic">
                    {t('tree.noReferences', 'No imported references')}
                  </p>
                ) : (
                  references.map((reference) => (
                    <button
                      key={reference.name}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                        isSelected('reference', reference.name)
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-muted/50'
                      )}
                      onClick={() => onSelect({ type: 'reference', name: reference.name })}
                    >
                      <BookOpen className="h-4 w-4 shrink-0" />
                      <span className="truncate flex-1 text-left">{reference.name}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {reference.kind}
                      </Badge>
                      {reference.entity_count != null && (
                        <Badge variant="outline" className="ml-1 text-[10px]">
                          {reference.entity_count.toLocaleString()}
                        </Badge>
                      )}
                    </button>
                  ))
                )}
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Import Section */}
          <AccordionItem value="import" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <Upload className="h-4 w-4" />
                {t('tree.import', 'Import')}
              </span>
            </AccordionTrigger>
            <AccordionContent className="pb-2">
              <div className="space-y-1 pl-6">
                <Button
                  variant={isSelected('import') ? 'secondary' : 'ghost'}
                  size="sm"
                  className={cn(
                    'w-full justify-start text-sm',
                    isSelected('import') && 'bg-primary/10 text-primary'
                  )}
                  onClick={() => onSelect({ type: 'import' })}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {t('tree.importData', 'Import data')}
                </Button>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </ScrollArea>
    </div>
  )
}
