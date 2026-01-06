/**
 * Mockup Option C: Expansion inline (Accordion)
 * Route: /labs/mockup-widgets-inline
 *
 * 4 onglets avec expansion inline dans la liste.
 * Clic sur un widget = expansion accordéon pour preview/édition.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  Plus,
  GripVertical,
  BarChart3,
  Gauge,
  PieChart,
  MapPin,
  Search,
  ChevronDown,
  ChevronRight,
  Trash2,
  Copy,
  RefreshCw,
  Sparkles,
  Link2,
  Settings2,
  Eye,
  FileCode,
  Palette,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

// Mock data for widgets
const mockWidgets = [
  {
    id: 'dbh_distribution',
    title: 'Distribution du DBH',
    transformer: 'binned_distribution',
    widget: 'bar_plot',
    icon: BarChart3,
  },
  {
    id: 'height_gauge',
    title: 'Hauteur moyenne',
    transformer: 'stats_aggregator',
    widget: 'gauge',
    icon: Gauge,
  },
  {
    id: 'endemic_donut',
    title: 'Répartition endémisme',
    transformer: 'categorical_distribution',
    widget: 'donut',
    icon: PieChart,
  },
  {
    id: 'distribution_map',
    title: 'Carte de distribution',
    transformer: 'geo_aggregator',
    widget: 'map',
    icon: MapPin,
  },
]

export default function MockupWidgetsInline() {
  const [expandedWidget, setExpandedWidget] = useState<string | null>('height_gauge')
  const [mainTab, setMainTab] = useState('widgets')
  const [searchQuery, setSearchQuery] = useState('')

  const toggleWidget = (id: string) => {
    setExpandedWidget(expandedWidget === id ? null : id)
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/labs">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour
            </Link>
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <div>
            <h1 className="font-semibold">Option C: Expansion inline</h1>
            <p className="text-xs text-muted-foreground">
              Accordéon - tout dans une seule colonne
            </p>
          </div>
        </div>
        <Badge variant="outline">Expérimental</Badge>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Simulated top-level tabs */}
        <div className="border-b px-4">
          <Tabs value={mainTab} onValueChange={setMainTab}>
            <TabsList className="h-10">
              <TabsTrigger value="sources" className="text-xs">
                Sources
              </TabsTrigger>
              <TabsTrigger value="widgets" className="text-xs">
                Widgets
              </TabsTrigger>
              <TabsTrigger value="layout" className="text-xs">
                Mise en page
              </TabsTrigger>
              <TabsTrigger value="index" className="text-xs">
                Index
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Widgets tab content - Single column with accordions */}
        {mainTab === 'widgets' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Header with search and add */}
            <div className="p-4 border-b flex items-center gap-3">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Rechercher un widget..."
                  className="pl-8 h-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Ajouter un widget
                    <ChevronDown className="h-4 w-4 ml-2" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem>
                    <Sparkles className="h-4 w-4 mr-2 text-amber-500" />
                    Depuis les suggestions
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Link2 className="h-4 w-4 mr-2 text-blue-500" />
                    Widget combiné
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Settings2 className="h-4 w-4 mr-2 text-gray-500" />
                    Widget personnalisé
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Widget list with inline expansion */}
            <ScrollArea className="flex-1">
              <div className="p-4 max-w-4xl mx-auto space-y-2">
                {mockWidgets.map((widget) => {
                  const Icon = widget.icon
                  const isExpanded = expandedWidget === widget.id

                  return (
                    <Collapsible
                      key={widget.id}
                      open={isExpanded}
                      onOpenChange={() => toggleWidget(widget.id)}
                    >
                      <div
                        className={cn(
                          'border rounded-lg overflow-hidden transition-all',
                          isExpanded ? 'ring-2 ring-primary/30' : ''
                        )}
                      >
                        {/* Widget header - always visible */}
                        <CollapsibleTrigger asChild>
                          <div
                            className={cn(
                              'flex items-center gap-3 p-3 cursor-pointer transition-colors',
                              isExpanded ? 'bg-muted/50' : 'hover:bg-muted/30'
                            )}
                          >
                            <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            )}
                            <Icon className="h-5 w-5 text-muted-foreground" />
                            <div className="flex-1">
                              <div className="font-medium">{widget.title}</div>
                              <div className="text-xs text-muted-foreground flex items-center gap-2">
                                <Badge variant="outline" className="text-[10px]">
                                  {widget.transformer}
                                </Badge>
                                <span>→</span>
                                <Badge variant="outline" className="text-[10px]">
                                  {widget.widget}
                                </Badge>
                              </div>
                            </div>
                            <div
                              className="flex items-center gap-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <Copy className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive hover:text-destructive"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </CollapsibleTrigger>

                        {/* Expanded content */}
                        <CollapsibleContent>
                          <div className="border-t">
                            <Tabs defaultValue="preview" className="w-full">
                              <div className="px-4 border-b bg-muted/30">
                                <TabsList className="h-9 bg-transparent">
                                  <TabsTrigger
                                    value="preview"
                                    className="text-xs data-[state=active]:bg-background"
                                  >
                                    <Eye className="h-3.5 w-3.5 mr-1.5" />
                                    Preview
                                  </TabsTrigger>
                                  <TabsTrigger
                                    value="params"
                                    className="text-xs data-[state=active]:bg-background"
                                  >
                                    <Settings2 className="h-3.5 w-3.5 mr-1.5" />
                                    Paramètres
                                  </TabsTrigger>
                                  <TabsTrigger
                                    value="yaml"
                                    className="text-xs data-[state=active]:bg-background"
                                  >
                                    <FileCode className="h-3.5 w-3.5 mr-1.5" />
                                    YAML
                                  </TabsTrigger>
                                </TabsList>
                              </div>

                              <TabsContent value="preview" className="m-0 p-4">
                                <div className="flex items-center justify-between mb-3">
                                  <span className="text-sm text-muted-foreground">
                                    Aperçu du widget
                                  </span>
                                  <Button variant="outline" size="sm">
                                    <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                                    Actualiser
                                  </Button>
                                </div>
                                <div className="h-48 border rounded-lg bg-muted/30 flex items-center justify-center">
                                  <div className="text-center text-muted-foreground">
                                    <Icon className="h-12 w-12 mx-auto mb-2 opacity-30" />
                                    <p className="text-sm">Preview iframe</p>
                                  </div>
                                </div>
                              </TabsContent>

                              <TabsContent value="params" className="m-0 p-4">
                                <div className="grid grid-cols-2 gap-4">
                                  {/* Transform params */}
                                  <Card>
                                    <CardHeader className="py-2 px-3">
                                      <CardTitle className="text-sm flex items-center gap-2">
                                        <Settings2 className="h-4 w-4 text-amber-600" />
                                        Transformation
                                        <Badge variant="secondary" className="text-xs ml-auto">
                                          {widget.transformer}
                                        </Badge>
                                      </CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-3 pt-0 space-y-3">
                                      <div>
                                        <label className="text-xs text-muted-foreground">
                                          Source
                                        </label>
                                        <Input defaultValue="occurrences" className="h-8 mt-1" />
                                      </div>
                                      <div>
                                        <label className="text-xs text-muted-foreground">
                                          Field
                                        </label>
                                        <Input defaultValue="height" className="h-8 mt-1" />
                                      </div>
                                    </CardContent>
                                  </Card>

                                  {/* Widget params */}
                                  <Card>
                                    <CardHeader className="py-2 px-3">
                                      <CardTitle className="text-sm flex items-center gap-2">
                                        <Palette className="h-4 w-4 text-emerald-600" />
                                        Visualisation
                                        <Badge variant="secondary" className="text-xs ml-auto">
                                          {widget.widget}
                                        </Badge>
                                      </CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-3 pt-0 space-y-3">
                                      <div>
                                        <label className="text-xs text-muted-foreground">
                                          Titre
                                        </label>
                                        <Input defaultValue={widget.title} className="h-8 mt-1" />
                                      </div>
                                      <div>
                                        <label className="text-xs text-muted-foreground">
                                          Color
                                        </label>
                                        <Input defaultValue="#4CAF50" className="h-8 mt-1" />
                                      </div>
                                    </CardContent>
                                  </Card>
                                </div>

                                {/* Save buttons */}
                                <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
                                  <Button variant="outline" size="sm">
                                    Annuler
                                  </Button>
                                  <Button size="sm">Sauvegarder</Button>
                                </div>
                              </TabsContent>

                              <TabsContent value="yaml" className="m-0 p-4">
                                <div className="grid grid-cols-2 gap-4">
                                  <Card>
                                    <CardHeader className="py-2 px-3">
                                      <CardTitle className="text-xs">transform.yml</CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-3 pt-0">
                                      <pre className="text-xs bg-muted rounded p-2">
                                        {`${widget.id}:
  plugin: ${widget.transformer}
  params:
    source: occurrences
    field: height`}
                                      </pre>
                                    </CardContent>
                                  </Card>
                                  <Card>
                                    <CardHeader className="py-2 px-3">
                                      <CardTitle className="text-xs">export.yml</CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-3 pt-0">
                                      <pre className="text-xs bg-muted rounded p-2">
                                        {`- plugin: ${widget.widget}
  data: ${widget.id}
  params:
    title: "${widget.title}"`}
                                      </pre>
                                    </CardContent>
                                  </Card>
                                </div>
                              </TabsContent>
                            </Tabs>
                          </div>
                        </CollapsibleContent>
                      </div>
                    </Collapsible>
                  )
                })}
              </div>
            </ScrollArea>

            {/* Footer */}
            <div className="p-3 border-t text-sm text-muted-foreground text-center">
              {mockWidgets.length} widgets configurés
            </div>
          </div>
        )}

        {/* Other tabs placeholder */}
        {mainTab !== 'widgets' && (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p className="text-lg font-medium mb-1">Onglet {mainTab}</p>
              <p className="text-sm">Contenu non implémenté dans ce mockup</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
