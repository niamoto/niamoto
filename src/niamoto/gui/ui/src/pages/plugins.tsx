import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Download,
  Settings,
  Check,
  Search,
  Filter,
  Loader2,
  Database,
  Layers,
  BarChart,
  FileJson,
  Calculator,
  Map,
  TreePine,
  Package,
  FileText,
  Globe,
  Binary,
  Shuffle,
  Eye
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { usePlugins } from '@/hooks/usePlugins'
import { PluginDetailView } from '@/components/plugins/PluginDetailView'

export function Plugins() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [selectedPlugin, setSelectedPlugin] = useState<any>(null)

  // Fetch plugins from API
  const { plugins: apiPlugins, loading, error } = usePlugins()

  // Extract unique types and categories
  const pluginTypes = useMemo(() => {
    const types = new Set<string>()
    apiPlugins.forEach(plugin => {
      types.add(plugin.type)
    })
    return Array.from(types).sort()
  }, [apiPlugins])

  const categories = useMemo(() => {
    const cats = new Set<string>()
    apiPlugins.forEach(plugin => {
      if (plugin.category) cats.add(plugin.category)
    })
    return Array.from(cats).sort()
  }, [apiPlugins])

  // Filter plugins based on search and filters
  const filteredPlugins = useMemo(() => {
    return apiPlugins.filter(plugin => {
      const matchesSearch = search === '' ||
        plugin.name.toLowerCase().includes(search.toLowerCase()) ||
        plugin.description?.toLowerCase().includes(search.toLowerCase()) ||
        plugin.id.toLowerCase().includes(search.toLowerCase())

      const matchesType = typeFilter === 'all' || plugin.type === typeFilter
      const matchesCategory = categoryFilter === 'all' || plugin.category === categoryFilter

      return matchesSearch && matchesType && matchesCategory
    })
  }, [apiPlugins, search, typeFilter, categoryFilter])

  // Group plugins by type for stats
  const stats = useMemo(() => {
    const grouped = apiPlugins.reduce((acc, plugin) => {
      acc[plugin.type] = (acc[plugin.type] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    return {
      total: apiPlugins.length,
      loader: grouped.loader || 0,
      transformer: grouped.transformer || 0,
      widget: grouped.widget || 0,
      exporter: grouped.exporter || 0
    }
  }, [apiPlugins])

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'transformer':
        return 'bg-blue-500/10 text-blue-500'
      case 'widget':
        return 'bg-green-500/10 text-green-500'
      case 'exporter':
        return 'bg-purple-500/10 text-purple-500'
      case 'loader':
        return 'bg-orange-500/10 text-orange-500'
      default:
        return 'bg-gray-500/10 text-gray-500'
    }
  }

  const getCategoryIcon = (category: string) => {
    const IconComponent = (() => {
      switch (category?.toLowerCase()) {
        case 'aggregation':
        case 'aggregator':
          return Layers
        case 'visualization':
        case 'widget':
          return BarChart
        case 'data':
        case 'database':
          return Database
        case 'geo':
        case 'geospatial':
        case 'spatial':
          return Map
        case 'ecological':
        case 'ecology':
          return TreePine
        case 'statistics':
        case 'stats':
          return Calculator
        case 'file':
        case 'files':
          return FileText
        case 'export':
        case 'exporter':
          return FileJson
        case 'web':
        case 'api':
          return Globe
        case 'binary':
          return Binary
        case 'chain':
        case 'chains':
          return Shuffle
        default:
          return Package
      }
    })()

    return IconComponent
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center text-red-500">
          {t('plugins.error', 'Failed to load plugins')}: {error}
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('plugins.title', 'Plugins')}
          </h1>
          <p className="text-muted-foreground">
            {t('plugins.description', 'Explore and manage Niamoto plugins')}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-xs text-muted-foreground">{t('plugins.total', 'Total plugins')}</div>
          </div>
          <div className="flex gap-2">
            {stats.loader > 0 && (
              <Badge variant="outline" className="bg-orange-500/10">
                {stats.loader} Loaders
              </Badge>
            )}
            {stats.transformer > 0 && (
              <Badge variant="outline" className="bg-blue-500/10">
                {stats.transformer} Transformers
              </Badge>
            )}
            {stats.widget > 0 && (
              <Badge variant="outline" className="bg-green-500/10">
                {stats.widget} Widgets
              </Badge>
            )}
            {stats.exporter > 0 && (
              <Badge variant="outline" className="bg-purple-500/10">
                {stats.exporter} Exporters
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('plugins.search_placeholder', 'Search plugins...')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('plugins.all_types', 'All types')}</SelectItem>
            {pluginTypes.map(type => (
              <SelectItem key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}s
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('plugins.all_categories', 'All categories')}</SelectItem>
            {categories.map(cat => {
              const Icon = getCategoryIcon(cat)
              return (
                <SelectItem key={cat} value={cat}>
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    {cat}
                  </span>
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
      </div>

      {/* Results count */}
      {(search || typeFilter !== 'all' || categoryFilter !== 'all') && (
        <div className="text-sm text-muted-foreground">
          {t('plugins.showing', 'Showing')} {filteredPlugins.length} {t('plugins.of', 'of')} {apiPlugins.length} {t('plugins.plugins', 'plugins')}
        </div>
      )}

      {/* Plugin Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredPlugins.map((plugin) => (
          <Card
            key={plugin.id}
            className="relative hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => setSelectedPlugin(plugin)}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-1 flex-1">
                  <CardTitle className="text-lg">{plugin.name}</CardTitle>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className={getTypeColor(plugin.type)}>
                      {plugin.type}
                    </Badge>
                    {plugin.category && (() => {
                      const Icon = getCategoryIcon(plugin.category)
                      return (
                        <Badge variant="secondary" className="flex items-center gap-1">
                          <Icon className="h-3 w-3" />
                          {plugin.category}
                        </Badge>
                      )
                    })()}
                    <span className="text-xs text-muted-foreground">v{plugin.version || '1.0.0'}</span>
                  </div>
                </div>
                <div className="rounded-full bg-green-500/10 p-1">
                  <Check className="h-4 w-4 text-green-500" />
                </div>
              </div>
              <CardDescription className="mt-2 line-clamp-2">
                {plugin.description || t('plugins.no_description', 'No description available')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span className="text-xs">{plugin.id}</span>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    title={t('plugins.view_details', 'View Details')}
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedPlugin(plugin)
                    }}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="sm" title={t('plugins.view_schema', 'View Schema')}>
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredPlugins.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          {t('plugins.no_results', 'No plugins found matching your criteria')}
        </div>
      )}

      {/* Info Section */}
      <Card>
        <CardHeader>
          <CardTitle>{t('plugins.develop_title', 'Develop Your Own Plugins')}</CardTitle>
          <CardDescription>
            {t('plugins.develop_description', 'Extend Niamoto with custom functionality')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t('plugins.develop_info', 'Create custom transformers, widgets, and exporters to suit your specific needs.')}
          </p>
          <div className="flex gap-2">
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              {t('plugins.download_template', 'Download Template')}
            </Button>
            <Button variant="outline">
              {t('plugins.view_docs', 'View Documentation')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Plugin Detail View */}
      {selectedPlugin && (
        <PluginDetailView
          plugin={selectedPlugin}
          onClose={() => setSelectedPlugin(null)}
        />
      )}
    </div>
  )
}
