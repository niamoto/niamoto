/**
 * Shimmer de chargement pour les previews widgets.
 *
 * - Remplit son conteneur parent (w-full h-full) ou utilise des dimensions fixes
 * - Affiche une icône adaptée au type de widget (bar_plot, donut_chart, etc.)
 * - Animation shimmer (balayage de gradient)
 */

import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  PieChart,
  Gauge,
  Map,
  Info,
  Navigation,
  LayoutGrid,
} from 'lucide-react'
import type { PreviewDescriptor } from '@/lib/preview/types'

/** Mapping widget plugin → icône Lucide */
const WIDGET_ICONS: Record<string, LucideIcon> = {
  bar_plot: BarChart3,
  stacked_bar_plot: BarChart3,
  donut_chart: PieChart,
  radial_gauge: Gauge,
  interactive_map: Map,
  general_info: Info,
  navigation: Navigation,
}

/** Déduit le nom du widget plugin depuis un PreviewDescriptor */
function resolveWidgetPlugin(descriptor?: PreviewDescriptor): string | undefined {
  // Mode inline : on a le plugin directement
  if (descriptor?.inline?.widget_plugin) return descriptor.inline.widget_plugin

  // Mode template : le templateId finit souvent par le nom du widget
  const tid = descriptor?.templateId
  if (!tid) return undefined

  // Chercher le suffixe le plus long qui matche un plugin connu
  for (const plugin of Object.keys(WIDGET_ICONS)) {
    if (tid.endsWith(plugin)) return plugin
  }
  return undefined
}

interface PreviewSkeletonProps {
  /** Dimensions fixes (override le mode responsive) */
  width?: number | string
  height?: number | string
  /** Mode compact : icône plus petite (miniatures) */
  compact?: boolean
  /** Descriptor pour déduire l'icône du widget */
  descriptor?: PreviewDescriptor
}

export function PreviewSkeleton({ width, height, compact, descriptor }: PreviewSkeletonProps) {
  const style: React.CSSProperties = width || height
    ? { width, height }
    : {}

  const widgetPlugin = resolveWidgetPlugin(descriptor)
  const Icon = (widgetPlugin && WIDGET_ICONS[widgetPlugin]) || LayoutGrid
  const iconSize = compact ? 'h-5 w-5' : 'h-8 w-8'

  return (
    <div
      className="relative flex items-center justify-center rounded w-full h-full overflow-hidden bg-muted/30"
      style={style}
    >
      {/* Shimmer gradient animé */}
      <div className="absolute inset-0 shimmer-sweep" />

      {/* Icône centrale */}
      <Icon className={`relative z-10 text-muted-foreground/25 ${iconSize}`} />
    </div>
  )
}
