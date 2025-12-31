/**
 * Widget components
 *
 * Provides widget rendering, gallery interface, and template management.
 */

export { WidgetMiniature } from './WidgetMiniature'
export { WidgetGallery } from './WidgetGallery'
export { WidgetPreviewPanel } from './WidgetPreviewPanel'
export { FieldGroup } from './FieldGroup'
export { WidgetOptionCard } from './WidgetOptionCard'
export { ConfiguredWidgetsList } from './ConfiguredWidgetsList'
export { WidgetConfigForm } from './WidgetConfigForm'

export {
  useSuggestions,
  useTemplates,
  useTemplateSelection,
  useConfiguredWidgets,
  useGenerateConfig,
  useSaveConfig,
} from './useTemplates'

export { useWidgetConfig } from './useWidgetConfig'
export type { ConfiguredWidget, UseWidgetConfigReturn } from './useWidgetConfig'

export type {
  TemplateSuggestion,
  TemplateInfo,
  WidgetCategory,
  FieldGroup as FieldGroupType,
  GenerateConfigResponse,
  SuggestionsResponse,
} from './types'

export { CATEGORY_INFO, SOURCE_INFO, groupSuggestionsByField } from './types'
