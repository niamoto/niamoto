import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, Database, BarChart, Map, Table as TableIcon, Calculator, TreePine, Layers, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

export interface Plugin {
  id: string
  name: string
  description: string
  type: 'loader' | 'transformer' | 'aggregator' | 'calculator'
  category: string
  icon: React.ComponentType<{ className?: string }>
  inputs: string[]
  outputs: string[]
  config?: any
}

const availablePlugins: Plugin[] = [
  // Loaders
  {
    id: 'nested_set',
    name: 'Nested Set',
    description: 'Load hierarchical tree structure data',
    type: 'loader',
    category: 'Structure',
    icon: TreePine,
    inputs: ['table'],
    outputs: ['hierarchy'],
  },
  {
    id: 'stats_loader',
    name: 'Statistics Loader',
    description: 'Load and prepare statistical data',
    type: 'loader',
    category: 'Statistics',
    icon: BarChart,
    inputs: ['csv', 'table'],
    outputs: ['stats'],
  },
  {
    id: 'direct_attribute',
    name: 'Direct Attribute',
    description: 'Direct field mapping from source',
    type: 'loader',
    category: 'Mapping',
    icon: Database,
    inputs: ['any'],
    outputs: ['attributes'],
  },

  // Transformers
  {
    id: 'field_aggregator',
    name: 'Field Aggregator',
    description: 'Aggregate fields by grouping',
    type: 'aggregator',
    category: 'Aggregation',
    icon: Layers,
    inputs: ['table', 'grouping_field'],
    outputs: ['aggregated_data'],
  },
  {
    id: 'sum_aggregator',
    name: 'Sum Aggregator',
    description: 'Sum numeric fields by group',
    type: 'aggregator',
    category: 'Aggregation',
    icon: Calculator,
    inputs: ['numeric_field', 'grouping'],
    outputs: ['sum'],
  },
  {
    id: 'count_aggregator',
    name: 'Count Aggregator',
    description: 'Count occurrences by group',
    type: 'aggregator',
    category: 'Aggregation',
    icon: TableIcon,
    inputs: ['table', 'grouping'],
    outputs: ['count'],
  },

  // Calculators
  {
    id: 'top_ranking',
    name: 'Top Ranking',
    description: 'Calculate top N items',
    type: 'calculator',
    category: 'Analysis',
    icon: BarChart,
    inputs: ['data', 'rank_field'],
    outputs: ['top_items'],
  },
  {
    id: 'geo_extractor',
    name: 'Geo Extractor',
    description: 'Extract geographic data',
    type: 'calculator',
    category: 'Geographic',
    icon: Map,
    inputs: ['geometry_field'],
    outputs: ['geo_data'],
  },
  {
    id: 'filter_plugin',
    name: 'Filter',
    description: 'Filter data based on conditions',
    type: 'transformer',
    category: 'Processing',
    icon: Filter,
    inputs: ['data', 'conditions'],
    outputs: ['filtered_data'],
  },
]

interface PluginCatalogProps {
  onPluginDragStart?: (plugin: Plugin) => void
  onPluginSelect?: (plugin: Plugin) => void
  compact?: boolean
}

export function PluginCatalog({ onPluginDragStart, onPluginSelect, compact = false }: PluginCatalogProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')

  const categories = ['all', 'Structure', 'Statistics', 'Mapping', 'Aggregation', 'Analysis', 'Geographic', 'Processing']

  const filteredPlugins = availablePlugins.filter(plugin => {
    const matchesSearch = plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          plugin.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || plugin.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'loader': return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
      case 'transformer': return 'bg-green-500/10 text-green-500 border-green-500/20'
      case 'aggregator': return 'bg-purple-500/10 text-purple-500 border-purple-500/20'
      case 'calculator': return 'bg-orange-500/10 text-orange-500 border-orange-500/20'
      default: return 'bg-gray-500/10 text-gray-500 border-gray-500/20'
    }
  }

  const handleDragStart = (e: React.DragEvent, plugin: Plugin) => {
    // Don't serialize the icon component, just pass the plugin data
    const pluginData = {
      id: plugin.id,
      name: plugin.name,
      description: plugin.description,
      type: plugin.type,
      category: plugin.category,
      inputs: plugin.inputs,
      outputs: plugin.outputs,
      config: plugin.config,
    }
    e.dataTransfer.setData('application/reactflow', JSON.stringify(pluginData))
    e.dataTransfer.effectAllowed = 'move'
    onPluginDragStart?.(plugin)
  }

  if (compact) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t('transform.plugins.title', 'Plugin Catalog')}</CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          <ScrollArea className="h-[400px]">
            <div className="space-y-2">
              {filteredPlugins.map(plugin => {
                const Icon = plugin.icon
                return (
                  <div
                    key={plugin.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, plugin)}
                    onClick={() => onPluginSelect?.(plugin)}
                    className="flex items-center gap-2 p-2 rounded-lg border cursor-move hover:bg-accent transition-colors"
                  >
                    <Icon className="h-4 w-4" />
                    <span className="text-sm font-medium">{plugin.name}</span>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">
          {t('transform.plugins.title', 'Plugin Catalog')}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t('transform.plugins.description', 'Drag plugins to the canvas to build your transformation pipeline')}
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={t('transform.plugins.search', 'Search plugins...')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Categories */}
      <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
        <TabsList className="grid grid-cols-4 h-auto">
          {categories.slice(0, 4).map(cat => (
            <TabsTrigger key={cat} value={cat} className="text-xs">
              {t(`transform.plugins.category.${cat.toLowerCase()}`, cat)}
            </TabsTrigger>
          ))}
        </TabsList>
        {categories.length > 4 && (
          <TabsList className="grid grid-cols-4 h-auto mt-1">
            {categories.slice(4).map(cat => (
              <TabsTrigger key={cat} value={cat} className="text-xs">
                {t(`transform.plugins.category.${cat.toLowerCase()}`, cat)}
              </TabsTrigger>
            ))}
          </TabsList>
        )}
      </Tabs>

      {/* Plugin Grid */}
      <ScrollArea className="h-[500px]">
        <div className="grid gap-3 md:grid-cols-2">
          {filteredPlugins.map(plugin => {
            const Icon = plugin.icon
            return (
              <Card
                key={plugin.id}
                draggable
                onDragStart={(e) => handleDragStart(e, plugin)}
                onClick={() => onPluginSelect?.(plugin)}
                className="cursor-move hover:shadow-md transition-all"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className="rounded-lg bg-primary/10 p-2">
                        <Icon className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-sm">{plugin.name}</CardTitle>
                        <Badge
                          variant="outline"
                          className={cn('mt-1 text-xs', getTypeColor(plugin.type))}
                        >
                          {plugin.type}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  <CardDescription className="mt-2 text-xs">
                    {plugin.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span>In:</span>
                      <div className="flex gap-1">
                        {plugin.inputs.map(input => (
                          <Badge key={input} variant="secondary" className="text-[10px] px-1">
                            {input}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>Out:</span>
                      <div className="flex gap-1">
                        {plugin.outputs.map(output => (
                          <Badge key={output} variant="secondary" className="text-[10px] px-1">
                            {output}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </ScrollArea>
    </div>
  )
}
