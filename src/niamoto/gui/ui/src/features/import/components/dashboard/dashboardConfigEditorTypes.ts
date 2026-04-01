import type {
  DatasetConfig,
  ReferenceConfig,
} from '@/features/import/components/editors/EntityConfigEditor'

export type EditingState =
  | {
      entityType: 'dataset'
      name: string
      config: DatasetConfig | null
      detectedColumns: string[]
    }
  | {
      entityType: 'reference'
      name: string
      config: ReferenceConfig | null
      detectedColumns: string[]
    }
  | null
