import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Database,
  FileText,
  FileSpreadsheet,
  Map,
  Layers,
  Settings2,
  Globe,
  FileJson,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { usePipelineStore } from '../store'
import type { CatalogItem } from '../types'

// Import catalog items
const importItems: CatalogItem[] = [
  {
    type: 'import',
    subType: 'taxonomy',
    label: 'Taxonomy',
    description: 'Import taxonomic hierarchy',
    icon: Database,
  },
  {
    type: 'import',
    subType: 'occurrences',
    label: 'Occurrences',
    description: 'Import occurrence data',
    icon: FileText,
  },
  {
    type: 'import',
    subType: 'plots',
    label: 'Plots',
    description: 'Import plot data',
    icon: FileSpreadsheet,
  },
  {
    type: 'import',
    subType: 'shapes',
    label: 'Shapes',
    description: 'Import geographic shapes',
    icon: Map,
  },
  {
    type: 'import',
    subType: 'layers',
    label: 'Layers',
    description: 'Import raster/vector layers',
    icon: Layers,
  },
]

// Transform catalog items (simplified for now)
const transformItems: CatalogItem[] = [
  {
    type: 'transform',
    label: 'Field Aggregator',
    description: 'Aggregate fields from sources',
    icon: Layers,
    pluginId: 'field_aggregator',
  },
  {
    type: 'transform',
    label: 'Top Ranking',
    description: 'Calculate top rankings',
    icon: Settings2,
    pluginId: 'top_ranking',
  },
  {
    type: 'transform',
    label: 'Geospatial Extractor',
    description: 'Extract geospatial data',
    icon: Map,
    pluginId: 'geospatial_extractor',
  },
]

// Export catalog items
const exportItems: CatalogItem[] = [
  {
    type: 'export',
    label: 'HTML Export',
    description: 'Export as HTML pages',
    icon: Globe,
    format: 'html',
  },
  {
    type: 'export',
    label: 'JSON Export',
    description: 'Export as JSON data',
    icon: FileJson,
    format: 'json',
  },
  {
    type: 'export',
    label: 'CSV Export',
    description: 'Export as CSV file',
    icon: FileText,
    format: 'csv',
  },
]

interface CategoryProps {
  title: string
  items: CatalogItem[]
  defaultExpanded?: boolean
}

function Category({ title, items, defaultExpanded = true }: CategoryProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  const onDragStart = (event: React.DragEvent, item: CatalogItem) => {
    event.dataTransfer.setData('application/json', JSON.stringify(item))
    event.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div className="mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full p-2 text-sm font-medium hover:bg-accent rounded-lg"
      >
        {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        {title}
        <Badge variant="secondary" className="ml-auto">
          {items.length}
        </Badge>
      </button>

      {expanded && (
        <div className="mt-2 space-y-1">
          {items.map((item, index) => {
            const Icon = item.icon || Settings2
            return (
              <div
                key={`${item.type}-${item.subType || item.label}-${index}`}
                draggable
                onDragStart={(e) => onDragStart(e, item)}
                className="flex items-center gap-2 p-2 rounded-lg border bg-card hover:bg-accent cursor-move transition-colors"
              >
                <Icon className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1 text-left">
                  <div className="text-sm font-medium">{item.label}</div>
                  {item.description && (
                    <div className="text-xs text-muted-foreground">{item.description}</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function NodeCatalog() {
  const { t } = useTranslation()
  const { catalogFilter, setCatalogFilter } = usePipelineStore()
  const [search, setSearch] = useState('')

  // Filter items based on search
  const filterItems = (items: CatalogItem[]) => {
    if (!search) return items
    const searchLower = search.toLowerCase()
    return items.filter(
      item =>
        item.label.toLowerCase().includes(searchLower) ||
        item.description?.toLowerCase().includes(searchLower)
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b">
        <h3 className="font-semibold text-lg mb-3">
          {t('pipeline.catalog.title', 'Node Catalog')}
        </h3>

        {/* Search */}
        <Input
          placeholder={t('pipeline.catalog.search', 'Search nodes...')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mb-3"
        />

        {/* Filter Toggle */}
        <div className="flex items-center space-x-2">
          <Switch
            id="show-all"
            checked={catalogFilter === 'all'}
            onCheckedChange={(checked) => setCatalogFilter(checked ? 'all' : 'compatible')}
          />
          <Label htmlFor="show-all" className="text-sm">
            {t('pipeline.catalog.showAll', 'Show all nodes')}
          </Label>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        <Category
          title={t('pipeline.catalog.import', 'Import')}
          items={filterItems(importItems)}
        />
        <Category
          title={t('pipeline.catalog.transform', 'Transform')}
          items={filterItems(transformItems)}
        />
        <Category
          title={t('pipeline.catalog.export', 'Export')}
          items={filterItems(exportItems)}
        />
      </ScrollArea>

      <div className="p-4 border-t text-xs text-muted-foreground">
        {t('pipeline.catalog.help', 'Drag nodes to the canvas to add them to your pipeline')}
      </div>
    </div>
  )
}
