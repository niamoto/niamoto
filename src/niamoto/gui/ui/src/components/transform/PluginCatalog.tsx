import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search, Database, BarChart, Map,
  Calculator, TreePine, Layers, FileText,
  Globe, Package, Loader2
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { cn } from '@/lib/utils'
import { usePlugins, usePluginCategories, type Plugin as APIPlugin, type PluginType } from '@/hooks/usePlugins'

// Map API plugin to internal format with icon
export interface Plugin extends APIPlugin {
  icon: React.ComponentType<{ className?: string }>
  inputs: string[]
  outputs: string[]
}

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
}

// Default icon for unknown categories
const defaultIcon = Package

interface PluginCatalogProps {
  compact?: boolean
  onPluginSelect?: (plugin: Plugin) => void
  onPluginDragStart?: (plugin: Plugin) => void
}

export function PluginCatalog({
  compact = false,
  onPluginSelect,
  onPluginDragStart
}: PluginCatalogProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState<PluginType | 'all'>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // Fetch plugins from API - only loaders and transformers for Transform page
  const { plugins: apiPlugins, loading, error } = usePlugins(
    selectedType === 'all' ? undefined : selectedType
  )

  // Fetch categories
  const { categories } = usePluginCategories()

  // Transform API plugins to internal format with icons
  // Show all plugin types now, as they can all be used in the transform pipeline
  const plugins: Plugin[] = useMemo(() => {
    return apiPlugins
      .map(apiPlugin => ({
        ...apiPlugin,
        icon: categoryIcons[apiPlugin.category || ''] || defaultIcon,
        inputs: apiPlugin.compatible_inputs || [],
        outputs: apiPlugin.output_format ? [apiPlugin.output_format] : [],
      }))
  }, [apiPlugins])

  // Filter plugins based on search and category
  const filteredPlugins = useMemo(() => {
    return plugins.filter(plugin => {
      const matchesSearch = !search ||
        plugin.name.toLowerCase().includes(search.toLowerCase()) ||
        plugin.description.toLowerCase().includes(search.toLowerCase())

      const matchesCategory = selectedCategory === 'all' ||
        plugin.category === selectedCategory

      return matchesSearch && matchesCategory
    })
  }, [plugins, search, selectedCategory])

  const handleDragStart = (e: React.DragEvent, plugin: Plugin) => {
    // Remove icon from plugin data before serializing
    const pluginData = {
      id: plugin.id,
      name: plugin.name,
      description: plugin.description,
      type: plugin.type,
      category: plugin.category,
      inputs: plugin.inputs,
      outputs: plugin.outputs,
      parameters_schema: plugin.parameters_schema,
      compatible_inputs: plugin.compatible_inputs,
      output_format: plugin.output_format,
    }
    // Try both formats for compatibility
    e.dataTransfer.setData('text/plain', JSON.stringify(pluginData))
    e.dataTransfer.setData('application/json', JSON.stringify(pluginData))
    e.dataTransfer.effectAllowed = 'copy'
    onPluginDragStart?.(plugin)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert>
        <AlertDescription>
          {t('transform.plugins.error', 'Failed to load plugins')}: {error}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className={cn("space-y-4", compact && "h-full flex flex-col")}>
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('transform.plugins.search', 'Search plugins...')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>

        {!compact && (
          <Tabs value={selectedType} onValueChange={(v) => setSelectedType(v as PluginType | 'all')}>
            <TabsList className="w-full">
              <TabsTrigger value="all" className="flex-1">
                {t('transform.plugins.all', 'All')}
              </TabsTrigger>
              <TabsTrigger value="loader" className="flex-1">
                {t('transform.plugins.loaders', 'Loaders')}
              </TabsTrigger>
              <TabsTrigger value="transformer" className="flex-1">
                {t('transform.plugins.transformers', 'Transformers')}
              </TabsTrigger>
              <TabsTrigger value="widget" className="flex-1">
                {t('transform.plugins.widgets', 'Widgets')}
              </TabsTrigger>
              <TabsTrigger value="exporter" className="flex-1">
                {t('transform.plugins.exporters', 'Exporters')}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        )}

        {categories.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <Badge
              variant={selectedCategory === 'all' ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setSelectedCategory('all')}
            >
              {t('transform.plugins.allCategories', 'All')}
            </Badge>
            {categories.map(category => (
              <Badge
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <ScrollArea className={cn("", compact ? "flex-1" : "h-[500px]")}>
        <div className="space-y-2 pr-4">
          {filteredPlugins.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t('transform.plugins.noResults', 'No plugins found')}
            </div>
          ) : (
            filteredPlugins.map((plugin) => {
              const Icon = plugin.icon
              return (
                <Card
                  key={plugin.id}
                  className={cn(
                    "cursor-move hover:shadow-md transition-shadow",
                    compact && "p-2"
                  )}
                  draggable
                  onDragStart={(e) => handleDragStart(e, plugin)}
                  onClick={() => onPluginSelect?.(plugin)}
                >
                  <CardHeader className={cn("pb-2", compact && "p-2")}>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <CardTitle className={cn("text-sm", compact && "text-xs")}>
                          {plugin.name}
                        </CardTitle>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        {plugin.type}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className={cn("pt-0", compact && "p-2 pt-0")}>
                    <CardDescription className={cn("text-xs", compact && "line-clamp-2")}>
                      {plugin.description}
                    </CardDescription>
                    {!compact && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {plugin.inputs.map((input) => (
                          <Badge key={input} variant="outline" className="text-xs">
                            ← {input}
                          </Badge>
                        ))}
                        {plugin.outputs.map((output) => (
                          <Badge key={output} variant="outline" className="text-xs">
                            → {output}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
