// Types for transformer suggestions API

export interface ColumnProfile {
  name: string
  data_category: DataCategory
  field_purpose: FieldPurpose
  cardinality: number
  suggested_bins?: number[]
  suggested_labels?: string[]
  value_range?: [number, number]
}

export type DataCategory =
  | 'numeric_continuous'
  | 'numeric_discrete'
  | 'categorical'
  | 'categorical_high_card'
  | 'boolean'
  | 'temporal'
  | 'geographic'
  | 'text'
  | 'identifier'

export type FieldPurpose =
  | 'primary_key'
  | 'foreign_key'
  | 'measurement'
  | 'classification'
  | 'location'
  | 'description'
  | 'metadata'

export interface TransformerConfig {
  plugin: string
  params: Record<string, any>
}

export interface TransformerSuggestion {
  transformer: string
  confidence: number
  reason: string
  config: TransformerConfig
}

export interface TransformerSuggestionsResponse {
  entity_name: string
  analyzed_at: string
  columns: ColumnProfile[]
  suggestions: Record<string, TransformerSuggestion[]>
}

// UI state types
export interface SuggestionSelection {
  columnName: string
  transformerName: string
  config: TransformerConfig
  selected: boolean
}

// Display helpers
export const DATA_CATEGORY_LABELS: Record<DataCategory, string> = {
  numeric_continuous: 'Numérique continu',
  numeric_discrete: 'Numérique discret',
  categorical: 'Catégoriel',
  categorical_high_card: 'Catégoriel (haute cardinalité)',
  boolean: 'Booléen',
  temporal: 'Temporel',
  geographic: 'Géographique',
  text: 'Texte',
  identifier: 'Identifiant',
}

export const FIELD_PURPOSE_LABELS: Record<FieldPurpose, string> = {
  primary_key: 'Clé primaire',
  foreign_key: 'Clé étrangère',
  measurement: 'Mesure',
  classification: 'Classification',
  location: 'Localisation',
  description: 'Description',
  metadata: 'Métadonnée',
}

export const TRANSFORMER_LABELS: Record<string, string> = {
  binned_distribution: 'Distribution par classes',
  statistical_summary: 'Résumé statistique',
  categorical_distribution: 'Distribution catégorielle',
  top_ranking: 'Top N valeurs',
  binary_counter: 'Compteur binaire',
  geospatial_extractor: 'Extraction géospatiale',
  time_series_analysis: 'Analyse temporelle',
}
