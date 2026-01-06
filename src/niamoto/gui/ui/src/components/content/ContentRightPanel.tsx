/**
 * ContentRightPanel - Contextual right panel
 *
 * Shows different content based on selection state:
 * - No widget selected → LayoutOverview (grid preview of all widgets)
 * - Widget selected → WidgetDetailPanel (preview + params + YAML)
 */
import { LayoutOverview } from './LayoutOverview'
import { WidgetDetailPanel } from './WidgetDetailPanel'
import type { ConfiguredWidget } from '@/components/widgets'

interface ContentRightPanelProps {
  selectedWidget: ConfiguredWidget | null
  allWidgets: ConfiguredWidget[]
  groupBy: string
  onSelectWidget: (widget: ConfiguredWidget | null) => void
  onBack: () => void
  onUpdateWidget: (widgetId: string, config: Partial<ConfiguredWidget>) => Promise<boolean>
  onDeleteWidget: (widgetId: string) => Promise<boolean>
  onLayoutSaved?: () => void
}

export function ContentRightPanel({
  selectedWidget,
  allWidgets,
  groupBy,
  onSelectWidget,
  onBack,
  onUpdateWidget,
  onDeleteWidget,
  onLayoutSaved,
}: ContentRightPanelProps) {
  // If no widget selected, show layout overview
  if (!selectedWidget) {
    return (
      <LayoutOverview
        widgets={allWidgets}
        groupBy={groupBy}
        onSelectWidget={onSelectWidget}
        onLayoutSaved={onLayoutSaved}
      />
    )
  }

  // Widget selected, show detail panel
  return (
    <WidgetDetailPanel
      widget={selectedWidget}
      groupBy={groupBy}
      onBack={onBack}
      onUpdate={(config) => onUpdateWidget(selectedWidget.id, config)}
      onDelete={() => onDeleteWidget(selectedWidget.id)}
    />
  )
}
