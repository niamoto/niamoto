import React, { useState, useMemo } from 'react'
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
  BarChart,
  Calculator,
  TreePine,
  Package,
  Loader2,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { usePipelineStore } from '../store'
import type { CatalogItem } from '../types'
import { usePlugins } from '@/hooks/usePlugins'

// Icon mapping for plugin categories
const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  file: FileText,
  geo: Map,
  aggregation: Layers,
  statistics: Calculator,
  hierarchy: TreePine,
  web: Globe,
  data: Database,
  visualization: BarChart,
  database: Database,
  relation: Layers,
  export: FileJson,
}

// Default icon for unknown categories
const defaultIcon = Package

// Import catalog items (hardcoded as they're not plugins)
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
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set())

  // Fetch plugins from API
  const { plugins: apiPlugins, loading, error } = usePlugins()

  // Extract unique categories
  const availableCategories = useMemo(() => {
    const categories = new Set<string>()
    apiPlugins.forEach(plugin => {
      if (plugin.category) {
        categories.add(plugin.category)
      }
    })
    return Array.from(categories).sort()
  }, [apiPlugins])

  // Transform API plugins to CatalogItems with category filtering
  const { loaderItems, transformItems, widgetItems, exportItems } = useMemo(() => {
    const loaders: CatalogItem[] = []
    const transformers: CatalogItem[] = []
    const widgets: CatalogItem[] = []
    const exporters: CatalogItem[] = []

    apiPlugins.forEach(plugin => {
      // Filter by category if any are selected
      if (selectedCategories.size > 0 && plugin.category && !selectedCategories.has(plugin.category)) {
        return
      }

      const icon = categoryIcons[plugin.category || ''] || defaultIcon

      const item: CatalogItem = {
        type: plugin.type === 'loader' ? 'transform' :
              plugin.type === 'exporter' ? 'export' : 'transform',
        label: plugin.name,
        description: plugin.description,
        icon: icon,
        pluginId: plugin.id,
        category: plugin.category,
      }

      // Sort plugins by type
      switch (plugin.type) {
        case 'loader':
          loaders.push(item)
          break
        case 'transformer':
          transformers.push(item)
          break
        case 'widget':
          widgets.push(item)
          break
        case 'exporter':
          exporters.push(item)
          break
      }
    })

    return {
      loaderItems: loaders,
      transformItems: transformers,
      widgetItems: widgets,
      exportItems: exporters,
    }
  }, [apiPlugins, selectedCategories])

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

  const toggleCategory = (category: string) => {
    const newCategories = new Set(selectedCategories)
    if (newCategories.has(category)) {
      newCategories.delete(category)
    } else {
      newCategories.add(category)
    }
    setSelectedCategories(newCategories)
  }

  const clearCategories = () => {
    setSelectedCategories(new Set())
  }

  return (
    <div className="h-full flex flex-col">
      <div className="border-b flex-shrink-0">
        <div className="p-4">
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

          {/* Category Filter Tags */}
          {availableCategories.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center justify-between mb-2">
                <Label className="text-xs text-muted-foreground">
                  {t('pipeline.catalog.filterByCategory', 'Filter by category')}
                </Label>
                {selectedCategories.size > 0 && (
                  <button
                    onClick={clearCategories}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    {t('pipeline.catalog.clearFilters', 'Clear')}
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {availableCategories.map(category => (
                  <Badge
                    key={category}
                    variant={selectedCategories.has(category) ? 'default' : 'outline'}
                    className="cursor-pointer text-xs"
                    onClick={() => toggleCategory(category)}
                  >
                    {category}
                  </Badge>
                ))}
              </div>
            </div>
          )}

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
      </div>

      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="p-4">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        )}

        {error && (
          <Alert className="mb-4">
            <AlertDescription>
              {t('pipeline.catalog.error', 'Failed to load plugins')}: {error}
            </AlertDescription>
          </Alert>
        )}

        {!loading && !error && (
          <>
            <Category
              title={t('pipeline.catalog.import', 'Import')}
              items={filterItems(importItems)}
            />
            <Category
              title={t('pipeline.catalog.loaders', 'Loaders')}
              items={filterItems(loaderItems)}
            />
            <Category
              title={t('pipeline.catalog.transform', 'Transform')}
              items={filterItems(transformItems)}
            />
            <Category
              title={t('pipeline.catalog.widgets', 'Widgets')}
              items={filterItems(widgetItems)}
            />
            <Category
              title={t('pipeline.catalog.export', 'Export')}
              items={filterItems(exportItems)}
            />
          </>
        )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t text-xs text-muted-foreground">
        {t('pipeline.catalog.help', 'Drag nodes to the canvas to add them to your pipeline')}
      </div>
    </div>
  )
}
