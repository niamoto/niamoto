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

export {
  useSuggestions,
  useTemplates,
  useTemplateSelection,
  useConfiguredWidgets,
  useGenerateConfig,
  useSaveConfig,
} from './useTemplates'

export type {
  TemplateSuggestion,
  TemplateInfo,
  WidgetCategory,
  FieldGroup as FieldGroupType,
  GenerateConfigResponse,
  SuggestionsResponse,
} from './types'

export { CATEGORY_INFO, SOURCE_INFO, groupSuggestionsByField } from './types'
