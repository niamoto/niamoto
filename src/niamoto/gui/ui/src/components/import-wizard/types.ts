export type ImportType = 'taxonomy' | 'plots' | 'occurrences' | 'shapes'

export interface ImportConfig {
  importType: ImportType
  file?: File
  fileAnalysis?: any
  fieldMappings?: Record<string, string>
  advancedOptions?: any
}
