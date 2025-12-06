/**
 * Widget Gallery components
 *
 * Provides a gallery interface for browsing and selecting widget templates.
 */

export { WidgetGallery } from './WidgetGallery'
export { WidgetPreviewPanel } from './WidgetPreviewPanel'
export { FieldGroup } from './FieldGroup'
export { WidgetOptionCard } from './WidgetOptionCard'

export {
  useSuggestions,
  useTemplates,
  useTemplateSelection,
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
