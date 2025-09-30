import { useState, useMemo, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Package,
  Upload,
  Settings,
  Download,
  BarChart,
  Database,
  FileCode,
  Layers,
  ArrowRight,
  Loader2
} from 'lucide-react'
import { useShowcaseStore } from '@/stores/showcaseStore'

interface ArchitectureSectionProps {}

const pluginTypeConfig = {
  loader: {
    title: 'Loaders',
    icon: Upload,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    description: 'Chargement et validation des données'
  },
  transformer: {
    title: 'Transformers',
    icon: Settings,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    description: 'Transformation et analyse des données'
  },
  exporter: {
    title: 'Exporters',
    icon: Download,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    description: 'Génération de sites et exports'
  },
  widget: {
    title: 'Widgets',
    icon: BarChart,
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    description: 'Composants de visualisation'
  }
}

export function ArchitectureSection({}: ArchitectureSectionProps) {
  const [selectedType, setSelectedType] = useState<keyof typeof pluginTypeConfig>('loader')
  const [hoveredPlugin, setHoveredPlugin] = useState<string | null>(null)
  const [selectedPlugin, setSelectedPlugin] = useState<any>(null)

  // Récupérer les plugins depuis le store partagé
  const { plugins, pluginsLoading: loading, loadPlugins } = useShowcaseStore()

  // Charger les plugins au montage si pas déjà chargés
  useEffect(() => {
    if (!plugins || plugins.length === 0) {
      loadPlugins()
    }
  }, [])

  // Organiser les plugins par type
  const pluginsByType = useMemo(() => {
    if (!plugins) return {}

    const grouped: Record<string, any[]> = {
      loader: [],
      transformer: [],
      exporter: [],
      widget: []
    }

    plugins.forEach(plugin => {
      if (grouped[plugin.type]) {
        grouped[plugin.type].push({
          ...plugin,  // Garder toutes les données du plugin
          category: plugin.category || 'general'
        })
      }
    })

    return grouped
  }, [plugins])

  // Regrouper les plugins par catégorie pour l'affichage
  const groupPluginsByCategory = (pluginList: any[]) => {
    const byCategory: Record<string, any[]> = {}

    pluginList.forEach(plugin => {
      const category = plugin.category || 'general'
      if (!byCategory[category]) {
        byCategory[category] = []
      }
      byCategory[category].push(plugin)
    })

    // Trier les catégories pour avoir 'general' en premier
    const sortedCategories = Object.keys(byCategory).sort((a, b) => {
      if (a === 'general') return -1
      if (b === 'general') return 1
      return a.localeCompare(b)
    })

    const result: Record<string, any[]> = {}
    sortedCategories.forEach(cat => {
      result[cat] = byCategory[cat]
    })

    return result
  }

  // Créer la structure complète avec les données de l'API
  const pluginTypes = useMemo(() => {
    const types: Record<string, any> = {}

    Object.entries(pluginTypeConfig).forEach(([key, config]) => {
      types[key] = {
        ...config,
        plugins: pluginsByType[key] || [],
        count: pluginsByType[key]?.length || 0
      }
    })

    return types
  }, [pluginsByType])

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Architecture Plugin</h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Système modulaire extensible permettant d'ajouter facilement de nouvelles fonctionnalités
        </p>
      </div>

      {/* Plugin Flow Visualization */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {Object.entries(pluginTypes).map(([key, type]: [string, any], index) => {
            const Icon = type.icon
            return (
              <div key={key} className="relative">
                <Card
                  className={`cursor-pointer transition-all hover:scale-105 ${
                    selectedType === key ? 'ring-2 ring-primary' : ''
                  }`}
                  onClick={() => setSelectedType(key as keyof typeof pluginTypeConfig)}
                >
                  <CardHeader className="text-center">
                    <div className={`w-16 h-16 mx-auto rounded-full ${type.bgColor} flex items-center justify-center`}>
                      <Icon className={`w-8 h-8 ${type.color}`} />
                    </div>
                    <CardTitle className="text-lg">{type.title}</CardTitle>
                    <CardDescription className="text-xs">
                      {loading ? (
                        <span className="animate-pulse">Chargement...</span>
                      ) : (
                        <span className="font-semibold">{type.count} plugins</span>
                      )}
                    </CardDescription>
                  </CardHeader>
                </Card>
                {index < Object.keys(pluginTypes).length - 1 && (
                  <ArrowRight className="absolute -right-6 top-1/2 transform -translate-y-1/2 text-muted-foreground hidden md:block" />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Plugin Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {(() => {
              const Icon = pluginTypes[selectedType].icon
              return (
                <>
                  <Icon className={`w-5 h-5 ${pluginTypes[selectedType].color}`} />
                  {pluginTypes[selectedType].title}
                </>
              )
            })()}
          </CardTitle>
          <CardDescription>
            {pluginTypes[selectedType].description}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          ) : pluginTypes[selectedType].plugins.length > 0 ? (
            <div className="space-y-6">
              {Object.entries(groupPluginsByCategory(pluginTypes[selectedType].plugins)).map(
                ([category, categoryPlugins]: [string, any]) => (
                  <div key={category}>
                    <div className="flex items-center gap-2 mb-3">
                      <h4 className="text-sm font-semibold uppercase text-muted-foreground">
                        {category === 'general' ? 'Général' : category}
                      </h4>
                      <div className="h-px flex-1 bg-border" />
                      <span className="text-xs text-muted-foreground">
                        {categoryPlugins.length} plugin{categoryPlugins.length > 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {categoryPlugins.map((plugin: any) => (
                        <div
                          key={plugin.id || plugin.name}
                          className={`p-4 rounded-lg border bg-card hover:bg-accent transition-colors cursor-pointer ${
                            selectedPlugin?.id === plugin.id ? 'ring-2 ring-primary bg-accent' : ''
                          }`}
                          onMouseEnter={() => setHoveredPlugin(plugin.name)}
                          onMouseLeave={() => setHoveredPlugin(null)}
                          onClick={() => setSelectedPlugin(plugin)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h4 className="font-medium">{plugin.name}</h4>
                              <p className="text-sm text-muted-foreground">
                                {plugin.description}
                              </p>
                            </div>
                            <Package className={`w-4 h-4 ml-2 flex-shrink-0 ${
                              hoveredPlugin === plugin.name ? pluginTypes[selectedType].color : 'text-muted-foreground'
                            }`} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Aucun plugin de ce type disponible
            </div>
          )}
        </CardContent>
      </Card>

      {/* Code Example */}
      <Tabs defaultValue="usage" className="w-full">
        <TabsList>
          <TabsTrigger value="usage">Utilisation</TabsTrigger>
          <TabsTrigger value="creation">Créer un plugin</TabsTrigger>
        </TabsList>
        <TabsContent value="usage">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                {selectedPlugin ? `Configuration pour ${selectedPlugin.name}` : 'Configuration YAML simple'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="p-4 bg-muted rounded-lg overflow-x-auto">
                <code>{selectedPlugin ?
                  `# ${selectedPlugin.type === 'transformer' ? 'transform' : selectedPlugin.type === 'loader' ? 'import' : 'export'}.yml
${selectedPlugin.type === 'transformer' ? 'widgets_data' : selectedPlugin.type === 'loader' ? 'sources' : 'exports'}:
  ${selectedPlugin.name.toLowerCase().replace(/\s+/g, '_')}:
    plugin: ${selectedPlugin.id}
    ${selectedPlugin.example_config ?
      `params:\n${Object.entries(selectedPlugin.example_config).map(([k, v]) =>
        `      ${k}: ${JSON.stringify(v)}`).join('\n')}` :
      selectedPlugin.parameters_schema && selectedPlugin.parameters_schema.length > 0 ?
      `params:\n${selectedPlugin.parameters_schema.slice(0, 3).map((param: any) =>
        `      ${param.name}: ${param.default !== undefined ? JSON.stringify(param.default) :
          param.type === 'string' ? '"value"' :
          param.type === 'number' ? '0' :
          param.type === 'boolean' ? 'true' : '{}'}  # ${param.description || ''}`).join('\n')}` :
      'params: {}'}
${selectedPlugin.compatible_inputs && selectedPlugin.compatible_inputs.length > 0 ?
  `    # Compatible avec: ${selectedPlugin.compatible_inputs.join(', ')}` : ''}`
                  :
                  `# Sélectionnez un plugin pour voir sa configuration
# transform.yml
widgets_data:
  general_info:
    plugin: field_aggregator
    params:
      fields:
        - source: taxon_ref
          field: full_name
          target: name`}</code>
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="creation">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Créer votre propre plugin</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="p-4 bg-muted rounded-lg overflow-x-auto">
                <code>{`from niamoto.core.plugins import TransformerPlugin, register

@register("mon_plugin", PluginType.TRANSFORMER)
class MonPlugin(TransformerPlugin):
    def transform(self, data, config):
        # Votre logique ici
        return result`}</code>
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Benefits */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <Layers className="w-8 h-8 mb-2 text-primary" />
            <h3 className="font-semibold mb-1">Modulaire</h3>
            <p className="text-sm text-muted-foreground">
              {plugins ? `${plugins.length} plugins disponibles` : 'Système extensible'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <Database className="w-8 h-8 mb-2 text-primary" />
            <h3 className="font-semibold mb-1">Réutilisable</h3>
            <p className="text-sm text-muted-foreground">
              Partagez vos plugins avec la communauté
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <FileCode className="w-8 h-8 mb-2 text-primary" />
            <h3 className="font-semibold mb-1">Simple</h3>
            <p className="text-sm text-muted-foreground">
              Configuration YAML, pas besoin de coder
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
