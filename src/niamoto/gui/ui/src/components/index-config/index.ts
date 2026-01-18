/**
 * Index configuration components
 *
 * Provides UI for configuring the index generator in export.yml
 */

export { IndexConfigEditor } from './IndexConfigEditor'
export { IndexFiltersConfig } from './IndexFiltersConfig'
export { IndexDisplayFieldsConfig } from './IndexDisplayFieldsConfig'
export { DisplayFieldEditorPanel } from './DisplayFieldEditorPanel'
export {
  useIndexConfig,
  createDefaultDisplayField,
  type IndexDisplayField,
  type IndexFilterConfig,
  type IndexPageConfig,
  type IndexViewConfig,
  type IndexGeneratorConfig,
  type UseIndexConfigReturn,
  type SuggestedDisplayField,
  type SuggestedFilter,
  type IndexFieldSuggestions,
} from './useIndexConfig'
