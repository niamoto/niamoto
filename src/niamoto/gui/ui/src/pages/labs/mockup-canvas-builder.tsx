/**
 * Mockup Option E: Canvas Builder (No-Code / WYSIWYG)
 * Route: /labs/mockup-canvas-builder
 *
 * Paradigme: Design-first — "Je construis ma page visuellement"
 *
 * Features:
 * - Canvas central représentant la page finale
 * - Palette CONTEXTUELLE basée sur les données disponibles
 * - Panneau de propriétés pour le widget sélectionné
 * - WYSIWYG: ce que vous voyez = ce que vous obtenez
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  BarChart3,
  Gauge,
  PieChart,
  MapPin,
  Eye,
  Download,
  Trash2,
  GripVertical,
  Plus,
  ChevronRight,
  ChevronDown,
  LayoutTemplate,
  Move,
  Settings2,
  RefreshCw,
  Table2,
  TrendingUp,
  Activity,
  Hash,
  Database,
  Star,
  Link2,
  Clock,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

// Data field definitions (simulating what would come from the API)
type DataFieldType = 'numeric' | 'categorical' | 'geographic' | 'temporal'

interface DataField {
  id: string
  name: string
  type: DataFieldType
  description: string
  stats?: {
    min?: number
    max?: number
    mean?: number
    uniqueValues?: number
  }
  suggestedWidgets: {
    id: string
    name: string
    icon: typeof BarChart3
    recommended?: boolean
  }[]
}

// Mock data fields (simulating columns from the database)
const dataFields: DataField[] = [
  {
    id: 'dbh',
    name: 'dbh',
    type: 'numeric',
    description: 'Diamètre à hauteur de poitrine (cm)',
    stats: { min: 5, max: 180, mean: 42.5 },
    suggestedWidgets: [
      { id: 'bar_plot', name: 'Histogramme', icon: BarChart3, recommended: true },
      { id: 'gauge', name: 'Jauge (moyenne)', icon: Gauge },
      { id: 'counter', name: 'Compteur', icon: Hash },
    ],
  },
  {
    id: 'height',
    name: 'height',
    type: 'numeric',
    description: 'Hauteur totale (m)',
    stats: { min: 1, max: 35, mean: 12.3 },
    suggestedWidgets: [
      { id: 'bar_plot', name: 'Histogramme', icon: BarChart3, recommended: true },
      { id: 'gauge', name: 'Jauge (moyenne)', icon: Gauge },
      { id: 'line_chart', name: 'Courbe', icon: TrendingUp },
    ],
  },
  {
    id: 'endemic_status',
    name: 'endemic_status',
    type: 'categorical',
    description: 'Statut d\'endémisme',
    stats: { uniqueValues: 3 },
    suggestedWidgets: [
      { id: 'donut', name: 'Donut', icon: PieChart, recommended: true },
      { id: 'bar_plot', name: 'Barres', icon: BarChart3 },
    ],
  },
  {
    id: 'strate',
    name: 'strate',
    type: 'categorical',
    description: 'Strate de végétation',
    stats: { uniqueValues: 5 },
    suggestedWidgets: [
      { id: 'donut', name: 'Donut', icon: PieChart, recommended: true },
      { id: 'bar_plot', name: 'Barres', icon: BarChart3 },
    ],
  },
  {
    id: 'coordinates',
    name: 'coordinates',
    type: 'geographic',
    description: 'Coordonnées géographiques',
    suggestedWidgets: [
      { id: 'map', name: 'Carte', icon: MapPin, recommended: true },
    ],
  },
  {
    id: 'species_count',
    name: 'species_count',
    type: 'numeric',
    description: 'Nombre d\'espèces',
    stats: { min: 1, max: 45, mean: 8.2 },
    suggestedWidgets: [
      { id: 'counter', name: 'Compteur', icon: Hash, recommended: true },
      { id: 'gauge', name: 'Jauge', icon: Gauge },
    ],
  },
]

// Detected patterns (multi-field combinations)
const detectedPatterns = [
  {
    id: 'phenology',
    name: 'Phénologie',
    description: 'Floraison, fructification, feuillaison',
    fields: ['flowering', 'fruiting', 'leafing'],
    icon: Clock,
    confidence: 92,
  },
  {
    id: 'allometry',
    name: 'Allométrie',
    description: 'Relations DBH/hauteur',
    fields: ['dbh', 'height'],
    icon: TrendingUp,
    confidence: 88,
  },
]

// Type icons and colors
const typeConfig: Record<DataFieldType, { icon: typeof BarChart3; color: string; label: string }> = {
  numeric: { icon: Hash, color: 'text-blue-600', label: 'Numérique' },
  categorical: { icon: PieChart, color: 'text-orange-600', label: 'Catégoriel' },
  geographic: { icon: MapPin, color: 'text-purple-600', label: 'Géographique' },
  temporal: { icon: Clock, color: 'text-green-600', label: 'Temporel' },
}

// Initial canvas widgets
const initialCanvasWidgets = [
  {
    id: 'widget_1',
    type: 'bar_plot',
    title: 'Distribution du DBH',
    field: 'dbh',
    colspan: 1,
    color: '#4CAF50',
    row: 0,
    col: 0,
  },
  {
    id: 'widget_2',
    type: 'gauge',
    title: 'Hauteur moyenne',
    field: 'height',
    colspan: 1,
    color: '#2196F3',
    row: 0,
    col: 1,
  },
  {
    id: 'widget_3',
    type: 'map',
    title: 'Distribution spatiale',
    field: 'coordinates',
    colspan: 2,
    color: '#9C27B0',
    row: 1,
    col: 0,
  },
  {
    id: 'widget_4',
    type: 'donut',
    title: 'Endémisme',
    field: 'endemic_status',
    colspan: 1,
    color: '#FF9800',
    row: 2,
    col: 0,
  },
  {
    id: 'widget_5',
    type: 'donut',
    title: 'Strates',
    field: 'strate',
    colspan: 1,
    color: '#8BC34A',
    row: 2,
    col: 1,
  },
]

// Widget icon map
const widgetIcons: Record<string, typeof BarChart3> = {
  bar_plot: BarChart3,
  line_chart: TrendingUp,
  area_chart: Activity,
  gauge: Gauge,
  counter: Hash,
  donut: PieChart,
  pie: PieChart,
  map: MapPin,
  data_table: Table2,
}

// Default colors for new widgets by type
const defaultColors: Record<string, string> = {
  bar_plot: '#4CAF50',
  gauge: '#2196F3',
  donut: '#FF9800',
  map: '#9C27B0',
  counter: '#607D8B',
  line_chart: '#00BCD4',
}

export default function MockupCanvasBuilder() {
  const [canvasWidgets, setCanvasWidgets] = useState(initialCanvasWidgets)
  const [selectedWidget, setSelectedWidget] = useState<string | null>(null)
  const [expandedFields, setExpandedFields] = useState<string[]>(['dbh', 'height', 'endemic_status'])
  const [draggedWidget, setDraggedWidget] = useState<{ fieldId: string; widgetType: string } | null>(null)
  const [dragOverSlot, setDragOverSlot] = useState<{ row: number; col: number } | null>(null)
  const [showPatterns, setShowPatterns] = useState(true)

  const selectedWidgetData = canvasWidgets.find((w) => w.id === selectedWidget)

  // Toggle field expansion
  const toggleField = (fieldId: string) => {
    setExpandedFields(prev =>
      prev.includes(fieldId)
        ? prev.filter(f => f !== fieldId)
        : [...prev, fieldId]
    )
  }

  // Handle drag from palette
  const handlePaletteDragStart = (fieldId: string, widgetType: string) => {
    setDraggedWidget({ fieldId, widgetType })
  }

  // Handle drop on canvas
  const handleCanvasDrop = (row: number, col: number) => {
    if (draggedWidget) {
      const field = dataFields.find(f => f.id === draggedWidget.fieldId)
      const newWidget = {
        id: `widget_${Date.now()}`,
        type: draggedWidget.widgetType,
        title: field ? `${field.name} (${draggedWidget.widgetType})` : 'Nouveau widget',
        field: draggedWidget.fieldId,
        colspan: draggedWidget.widgetType === 'map' ? 2 : 1,
        color: defaultColors[draggedWidget.widgetType] || '#607D8B',
        row,
        col,
      }
      setCanvasWidgets([...canvasWidgets, newWidget])
      setSelectedWidget(newWidget.id)
    }
    setDraggedWidget(null)
    setDragOverSlot(null)
  }

  // Delete widget
  const deleteWidget = (id: string) => {
    setCanvasWidgets(canvasWidgets.filter(w => w.id !== id))
    if (selectedWidget === id) {
      setSelectedWidget(null)
    }
  }

  // Update widget property
  const updateWidget = (id: string, updates: Partial<typeof canvasWidgets[0]>) => {
    setCanvasWidgets(canvasWidgets.map(w =>
      w.id === id ? { ...w, ...updates } : w
    ))
  }

  // Render mini preview based on type
  const renderWidgetPreview = (widget: typeof canvasWidgets[0], size: 'small' | 'large' = 'large') => {
    const scale = size === 'small' ? 0.5 : 1
    const Icon = widgetIcons[widget.type] || BarChart3

    switch (widget.type) {
      case 'bar_plot':
      case 'area_chart':
        return (
          <div className={cn("flex items-end justify-center gap-1", size === 'large' ? 'h-24' : 'h-8')}>
            {[30, 50, 80, 60, 45, 70, 55, 40, 65, 75].map((h, i) => (
              <div
                key={i}
                className="rounded-t transition-all"
                style={{
                  height: `${h * scale}%`,
                  width: size === 'large' ? '8%' : '6px',
                  backgroundColor: widget.color,
                  opacity: 0.8 + (i % 3) * 0.1,
                }}
              />
            ))}
          </div>
        )
      case 'line_chart':
        return (
          <div className={cn("flex items-center justify-center", size === 'large' ? 'h-24' : 'h-8')}>
            <svg viewBox="0 0 100 40" className="w-full h-full">
              <polyline
                points="0,30 15,25 30,35 45,20 60,28 75,15 100,22"
                fill="none"
                stroke={widget.color}
                strokeWidth="2"
              />
            </svg>
          </div>
        )
      case 'gauge':
        return (
          <div className={cn("flex flex-col items-center justify-center", size === 'large' ? 'h-24' : 'h-8')}>
            <div className="relative" style={{ width: size === 'large' ? '80px' : '24px', height: size === 'large' ? '40px' : '12px' }}>
              <div
                className="absolute inset-0 border-t-4 border-l-4 border-r-4 rounded-t-full"
                style={{ borderColor: '#e5e7eb' }}
              />
              <div
                className="absolute inset-0 border-t-4 border-l-4 border-r-4 rounded-t-full"
                style={{
                  borderColor: widget.color,
                  clipPath: 'polygon(0 0, 70% 0, 70% 100%, 0 100%)',
                }}
              />
            </div>
            {size === 'large' && (
              <span className="text-2xl font-bold mt-2" style={{ color: widget.color }}>42.5</span>
            )}
          </div>
        )
      case 'counter':
        return (
          <div className={cn("flex items-center justify-center", size === 'large' ? 'h-24' : 'h-8')}>
            <span
              className={cn("font-bold", size === 'large' ? 'text-4xl' : 'text-sm')}
              style={{ color: widget.color }}
            >
              1,234
            </span>
          </div>
        )
      case 'donut':
      case 'pie':
        return (
          <div className={cn("flex items-center justify-center", size === 'large' ? 'h-24' : 'h-8')}>
            <div
              className="rounded-full"
              style={{
                width: size === 'large' ? '80px' : '24px',
                height: size === 'large' ? '80px' : '24px',
                background: `conic-gradient(${widget.color} 0deg 120deg, #e5e7eb 120deg 200deg, ${widget.color}88 200deg 280deg, #e5e7eb 280deg 360deg)`,
              }}
            >
              {widget.type === 'donut' && (
                <div
                  className="rounded-full bg-background"
                  style={{
                    width: '60%',
                    height: '60%',
                    margin: '20%',
                  }}
                />
              )}
            </div>
          </div>
        )
      case 'map':
        return (
          <div className={cn("flex items-center justify-center relative", size === 'large' ? 'h-24' : 'h-8')}>
            <div className="w-full h-full rounded" style={{ background: 'linear-gradient(135deg, #e8f5e9 25%, #c8e6c9 50%, #a5d6a7 75%)' }}>
              {size === 'large' && (
                <>
                  <MapPin className="absolute" style={{ top: '20%', left: '30%', color: widget.color }} size={16} />
                  <MapPin className="absolute" style={{ top: '50%', left: '60%', color: widget.color }} size={16} />
                  <MapPin className="absolute" style={{ top: '70%', left: '40%', color: widget.color }} size={16} />
                </>
              )}
            </div>
          </div>
        )
      default:
        return (
          <div className={cn("flex items-center justify-center", size === 'large' ? 'h-24' : 'h-8')}>
            <Icon className={cn("text-muted-foreground", size === 'large' ? 'h-12 w-12' : 'h-4 w-4')} />
          </div>
        )
    }
  }

  // Render mini preview for palette item
  const renderPaletteMiniPreview = (widgetType: string, color: string) => {
    switch (widgetType) {
      case 'bar_plot':
        return (
          <div className="flex items-end gap-px h-4">
            {[3, 5, 7, 4, 6].map((h, i) => (
              <div
                key={i}
                className="w-1 rounded-t"
                style={{ height: `${h * 2}px`, backgroundColor: color }}
              />
            ))}
          </div>
        )
      case 'gauge':
        return (
          <div className="relative w-5 h-3">
            <div className="absolute inset-0 border-t-2 border-l-2 border-r-2 rounded-t-full" style={{ borderColor: '#e5e7eb' }} />
            <div className="absolute inset-0 border-t-2 border-l-2 border-r-2 rounded-t-full" style={{ borderColor: color, clipPath: 'polygon(0 0, 70% 0, 70% 100%, 0 100%)' }} />
          </div>
        )
      case 'donut':
        return (
          <div
            className="w-4 h-4 rounded-full"
            style={{
              background: `conic-gradient(${color} 0deg 120deg, #e5e7eb 120deg 240deg, ${color}88 240deg 360deg)`,
            }}
          >
            <div className="w-2 h-2 rounded-full bg-background m-1" />
          </div>
        )
      case 'map':
        return (
          <div className="w-5 h-4 rounded bg-green-100 flex items-center justify-center">
            <MapPin className="h-3 w-3" style={{ color }} />
          </div>
        )
      case 'counter':
        return (
          <span className="text-xs font-bold" style={{ color }}>123</span>
        )
      case 'line_chart':
        return (
          <svg viewBox="0 0 20 12" className="w-5 h-3">
            <polyline
              points="0,10 5,6 10,8 15,3 20,5"
              fill="none"
              stroke={color}
              strokeWidth="1.5"
            />
          </svg>
        )
      default:
        return null
    }
  }

  // Group widgets by row for grid rendering
  const widgetsByRow = canvasWidgets.reduce((acc, widget) => {
    if (!acc[widget.row]) acc[widget.row] = []
    acc[widget.row].push(widget)
    return acc
  }, {} as Record<number, typeof canvasWidgets>)

  const maxRow = Math.max(...canvasWidgets.map(w => w.row), 0)

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
            <h1 className="font-semibold">Option E: Canvas Builder</h1>
            <p className="text-xs text-muted-foreground">
              Palette contextuelle basée sur vos données
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Exporter
          </Button>
          <Badge className="bg-amber-600">Nouveau</Badge>
        </div>
      </div>

      {/* Main content - 3 panels */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel - Contextual Palette */}
        <div className="w-64 border-r flex flex-col bg-muted/10">
          <div className="p-3 border-b">
            <h3 className="font-medium text-sm flex items-center gap-2">
              <Database className="h-4 w-4" />
              Vos données
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              {dataFields.length} champs disponibles
            </p>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {/* Data fields */}
              {dataFields.map((field) => {
                const typeConf = typeConfig[field.type]
                const TypeIcon = typeConf.icon
                const isExpanded = expandedFields.includes(field.id)

                return (
                  <Collapsible
                    key={field.id}
                    open={isExpanded}
                    onOpenChange={() => toggleField(field.id)}
                  >
                    <CollapsibleTrigger className="flex items-center w-full p-2 hover:bg-muted rounded-md text-sm group">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 mr-2 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 mr-2 text-muted-foreground" />
                      )}
                      <TypeIcon className={cn("h-4 w-4 mr-2", typeConf.color)} />
                      <div className="flex-1 text-left">
                        <span className="font-medium">{field.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">({typeConf.label})</span>
                      </div>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <div className="ml-6 pl-2 border-l-2 border-muted space-y-1 mt-1 mb-2">
                        {/* Field stats */}
                        {field.stats && (
                          <div className="text-xs text-muted-foreground px-2 py-1 bg-muted/30 rounded mb-2">
                            {field.stats.mean !== undefined && (
                              <span>Moy: {field.stats.mean}</span>
                            )}
                            {field.stats.min !== undefined && field.stats.max !== undefined && (
                              <span className="ml-2">({field.stats.min} - {field.stats.max})</span>
                            )}
                            {field.stats.uniqueValues !== undefined && (
                              <span>{field.stats.uniqueValues} valeurs</span>
                            )}
                          </div>
                        )}

                        {/* Suggested widgets */}
                        {field.suggestedWidgets.map((widget) => {
                          const color = defaultColors[widget.id] || '#607D8B'

                          return (
                            <div
                              key={widget.id}
                              draggable
                              onDragStart={() => handlePaletteDragStart(field.id, widget.id)}
                              onDragEnd={() => setDraggedWidget(null)}
                              className={cn(
                                "flex items-center gap-2 p-2 rounded-md cursor-grab active:cursor-grabbing border transition-all",
                                widget.recommended
                                  ? "bg-primary/5 border-primary/20 hover:border-primary/40"
                                  : "border-transparent hover:bg-muted hover:border-border"
                              )}
                            >
                              <div className="w-6 flex justify-center">
                                {renderPaletteMiniPreview(widget.id, color)}
                              </div>
                              <span className="text-sm flex-1">{widget.name}</span>
                              {widget.recommended && (
                                <Star className="h-3 w-3 text-amber-500 fill-amber-500" />
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                )
              })}

              {/* Detected patterns section */}
              <Separator className="my-3" />

              <Collapsible open={showPatterns} onOpenChange={setShowPatterns}>
                <CollapsibleTrigger className="flex items-center w-full p-2 hover:bg-muted rounded-md text-sm">
                  {showPatterns ? (
                    <ChevronDown className="h-4 w-4 mr-2 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 mr-2 text-muted-foreground" />
                  )}
                  <Link2 className="h-4 w-4 mr-2 text-purple-600" />
                  <span className="font-medium">Patterns détectés</span>
                  <Badge variant="secondary" className="ml-auto text-[10px]">
                    {detectedPatterns.length}
                  </Badge>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="ml-6 pl-2 border-l-2 border-purple-200 space-y-1 mt-1">
                    {detectedPatterns.map((pattern) => {
                      const PatternIcon = pattern.icon

                      return (
                        <div
                          key={pattern.id}
                          className="p-2 rounded-md hover:bg-muted cursor-pointer border border-transparent hover:border-border transition-all"
                        >
                          <div className="flex items-center gap-2">
                            <PatternIcon className="h-4 w-4 text-purple-600" />
                            <span className="text-sm font-medium">{pattern.name}</span>
                            <Badge variant="outline" className="ml-auto text-[10px]">
                              {pattern.confidence}%
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1 ml-6">
                            {pattern.description}
                          </p>
                          <div className="flex gap-1 mt-1 ml-6">
                            {pattern.fields.map(f => (
                              <Badge key={f} variant="secondary" className="text-[10px]">
                                {f}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          </ScrollArea>

          <div className="p-3 border-t text-xs text-muted-foreground text-center">
            Glisser vers le canvas
          </div>
        </div>

        {/* Center panel - Canvas */}
        <div className="flex-1 flex flex-col bg-[#f8f9fa] dark:bg-zinc-900">
          {/* Canvas toolbar */}
          <div className="p-2 border-b bg-background flex items-center justify-between">
            <div className="flex items-center gap-2">
              <LayoutTemplate className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Canvas</span>
              <Badge variant="outline" className="text-xs">{canvasWidgets.length} widgets</Badge>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Canvas area */}
          <ScrollArea className="flex-1 p-6">
            <div className="max-w-4xl mx-auto space-y-4">
              {/* Render rows */}
              {Array.from({ length: maxRow + 2 }, (_, rowIndex) => {
                const rowWidgets = widgetsByRow[rowIndex] || []
                const hasWidgets = rowWidgets.length > 0

                return (
                  <div
                    key={rowIndex}
                    className={cn(
                      "grid grid-cols-2 gap-4 min-h-[120px]",
                      !hasWidgets && "border-2 border-dashed border-muted-foreground/20 rounded-lg"
                    )}
                    onDragOver={(e) => {
                      e.preventDefault()
                      if (draggedWidget && !hasWidgets) {
                        setDragOverSlot({ row: rowIndex, col: 0 })
                      }
                    }}
                    onDragLeave={() => setDragOverSlot(null)}
                    onDrop={() => {
                      if (draggedWidget && !hasWidgets) {
                        handleCanvasDrop(rowIndex, 0)
                      }
                    }}
                  >
                    {hasWidgets ? (
                      rowWidgets.map((widget) => {
                        const Icon = widgetIcons[widget.type] || BarChart3
                        const isSelected = selectedWidget === widget.id

                        return (
                          <div
                            key={widget.id}
                            className={cn(
                              "bg-background rounded-xl border-2 shadow-sm transition-all cursor-pointer overflow-hidden",
                              widget.colspan === 2 ? 'col-span-2' : 'col-span-1',
                              isSelected
                                ? 'border-primary ring-2 ring-primary/20'
                                : 'border-border hover:border-primary/50'
                            )}
                            onClick={() => setSelectedWidget(widget.id)}
                          >
                            {/* Widget header */}
                            <div className="px-4 py-2 border-b bg-muted/30 flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                                <Icon className="h-4 w-4" style={{ color: widget.color }} />
                                <span className="font-medium text-sm">{widget.title}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Badge variant="outline" className="text-[10px]">{widget.field}</Badge>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    deleteWidget(widget.id)
                                  }}
                                >
                                  <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                                </Button>
                              </div>
                            </div>

                            {/* Widget preview */}
                            <div className="p-4">
                              {renderWidgetPreview(widget)}
                            </div>

                            {/* Widget footer */}
                            <div className="px-4 py-2 border-t bg-muted/10 flex items-center justify-between">
                              <span className="text-xs text-muted-foreground">{widget.type}</span>
                              {widget.colspan === 2 && (
                                <Badge variant="secondary" className="text-[10px]">Pleine largeur</Badge>
                              )}
                            </div>
                          </div>
                        )
                      })
                    ) : (
                      <div
                        className={cn(
                          "col-span-2 flex items-center justify-center text-muted-foreground transition-colors",
                          dragOverSlot?.row === rowIndex && 'bg-primary/5 border-primary/30'
                        )}
                      >
                        <div className="text-center">
                          <Plus className="h-8 w-8 mx-auto mb-2 opacity-30" />
                          <p className="text-sm">Glisser un widget ici</p>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </div>

        {/* Right panel - Properties */}
        <div className="w-72 border-l flex flex-col bg-muted/10">
          <div className="p-3 border-b">
            <h3 className="font-medium text-sm flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              Propriétés
            </h3>
          </div>

          {selectedWidgetData ? (
            <ScrollArea className="flex-1">
              <div className="p-4 space-y-4">
                {/* Widget info */}
                <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                  {(() => {
                    const Icon = widgetIcons[selectedWidgetData.type] || BarChart3
                    return <Icon className="h-5 w-5" style={{ color: selectedWidgetData.color }} />
                  })()}
                  <div>
                    <p className="text-sm font-medium">{selectedWidgetData.title}</p>
                    <p className="text-xs text-muted-foreground">{selectedWidgetData.type}</p>
                  </div>
                </div>

                <Separator />

                {/* Title */}
                <div className="space-y-1.5">
                  <Label className="text-xs">Titre</Label>
                  <Input
                    value={selectedWidgetData.title}
                    onChange={(e) => updateWidget(selectedWidgetData.id, { title: e.target.value })}
                  />
                </div>

                {/* Field */}
                <div className="space-y-1.5">
                  <Label className="text-xs">Champ source</Label>
                  <Select
                    value={selectedWidgetData.field}
                    onValueChange={(value) => updateWidget(selectedWidgetData.id, { field: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {dataFields.map(f => (
                        <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Color */}
                <div className="space-y-1.5">
                  <Label className="text-xs">Couleur</Label>
                  <div className="flex gap-2">
                    <Input
                      type="color"
                      value={selectedWidgetData.color}
                      onChange={(e) => updateWidget(selectedWidgetData.id, { color: e.target.value })}
                      className="w-12 h-9 p-1 cursor-pointer"
                    />
                    <Input
                      value={selectedWidgetData.color}
                      onChange={(e) => updateWidget(selectedWidgetData.id, { color: e.target.value })}
                      className="flex-1 font-mono text-sm"
                    />
                  </div>
                </div>

                {/* Width */}
                <div className="space-y-1.5">
                  <Label className="text-xs">Largeur</Label>
                  <Select
                    value={selectedWidgetData.colspan.toString()}
                    onValueChange={(value) => updateWidget(selectedWidgetData.id, { colspan: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 colonne (50%)</SelectItem>
                      <SelectItem value="2">2 colonnes (100%)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                {/* Quick preview */}
                <div className="space-y-1.5">
                  <Label className="text-xs">Aperçu</Label>
                  <div className="border rounded-lg p-4 bg-background">
                    {renderWidgetPreview(selectedWidgetData)}
                  </div>
                </div>

                <Separator />

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    className="flex-1"
                    onClick={() => deleteWidget(selectedWidgetData.id)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Supprimer
                  </Button>
                </div>
              </div>
            </ScrollArea>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center p-6">
                <Move className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Sélectionnez un widget</p>
                <p className="text-xs mt-1">pour modifier ses propriétés</p>
              </div>
            </div>
          )}

          {/* Footer info */}
          <div className="p-3 border-t text-xs text-muted-foreground text-center">
            Clic = sélectionner • Drag = déplacer
          </div>
        </div>
      </div>
    </div>
  )
}
