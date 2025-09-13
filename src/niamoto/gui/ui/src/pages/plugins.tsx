import { useTranslation } from 'react-i18next'
import { Package, Download, Settings, Check, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

export function Plugins() {
  const { t } = useTranslation()

  // Mock plugin data
  const plugins = [
    {
      id: 'nested_set',
      name: 'Nested Set',
      description: 'Hierarchical data structure for taxonomic trees',
      version: '1.0.0',
      type: 'transformer',
      status: 'active',
      author: 'Niamoto Core'
    },
    {
      id: 'stats_loader',
      name: 'Statistics Loader',
      description: 'Load and aggregate statistical data',
      version: '1.0.0',
      type: 'transformer',
      status: 'active',
      author: 'Niamoto Core'
    },
    {
      id: 'bar_plot',
      name: 'Bar Plot Widget',
      description: 'Interactive bar chart visualization',
      version: '1.0.0',
      type: 'widget',
      status: 'active',
      author: 'Niamoto Core'
    },
    {
      id: 'donut_chart',
      name: 'Donut Chart Widget',
      description: 'Donut chart for categorical data',
      version: '1.0.0',
      type: 'widget',
      status: 'active',
      author: 'Niamoto Core'
    },
    {
      id: 'interactive_map',
      name: 'Interactive Map',
      description: 'Leaflet-based map visualization',
      version: '1.0.0',
      type: 'widget',
      status: 'active',
      author: 'Niamoto Core'
    }
  ]

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'transformer':
        return 'bg-blue-500/10 text-blue-500'
      case 'widget':
        return 'bg-green-500/10 text-green-500'
      case 'exporter':
        return 'bg-purple-500/10 text-purple-500'
      default:
        return 'bg-gray-500/10 text-gray-500'
    }
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
            {t('plugins.description', 'Manage and configure Niamoto plugins')}
          </p>
        </div>
        <Badge variant="secondary">
          {t('common.coming_soon', 'Coming Soon')}
        </Badge>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-4">
        <Input
          placeholder={t('plugins.search_placeholder', 'Search plugins...')}
          className="max-w-sm"
        />
        <Button variant="outline">
          <Package className="mr-2 h-4 w-4" />
          {t('plugins.install_new', 'Install New Plugin')}
        </Button>
      </div>

      {/* Plugin Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {plugins.map((plugin) => (
          <Card key={plugin.id} className="relative">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-lg">{plugin.name}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={getTypeColor(plugin.type)}>
                      {plugin.type}
                    </Badge>
                    <span className="text-xs text-muted-foreground">v{plugin.version}</span>
                  </div>
                </div>
                {plugin.status === 'active' ? (
                  <div className="rounded-full bg-green-500/10 p-1">
                    <Check className="h-4 w-4 text-green-500" />
                  </div>
                ) : (
                  <div className="rounded-full bg-yellow-500/10 p-1">
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                  </div>
                )}
              </div>
              <CardDescription className="mt-2">
                {plugin.description}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{plugin.author}</span>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm">
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

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
    </div>
  )
}
