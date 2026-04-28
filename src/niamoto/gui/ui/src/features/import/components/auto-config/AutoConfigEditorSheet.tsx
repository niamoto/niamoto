import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EntityConfigEditor } from '@/features/import/components/editors/EntityConfigEditor'
import type {
  AuxiliarySourceConfig,
  DatasetConfig,
  LayerConfig,
  ReferenceConfig,
} from '@/features/import/components/editors/EntityConfigEditor'

type EditingEntity =
  | { type: 'dataset'; name: string; config: DatasetConfig; columns: string[] }
  | { type: 'reference'; name: string; config: ReferenceConfig; columns: string[] }
  | { type: 'auxiliary'; index: number; name: string; config: AuxiliarySourceConfig; columns: string[] }
  | { type: 'layer'; index: number; config: LayerConfig }
  | null

interface AutoConfigEditorSheetProps {
  editingEntity: EditingEntity
  open: boolean
  title: string
  description: string
  availableReferences: Array<{ name: string; columns: string[] }>
  availableDatasets: string[]
  availableAuxiliaryTargets: string[]
  onClose: () => void
  onDatasetSave: (name: string, updated: DatasetConfig) => void
  onReferenceSave: (name: string, updated: ReferenceConfig) => void
  onAuxiliarySave: (index: number, updated: AuxiliarySourceConfig) => void
  onLayerSave: (index: number, updated: LayerConfig) => void
}

export function AutoConfigEditorSheet({
  editingEntity,
  open,
  title,
  description,
  availableReferences,
  availableDatasets,
  availableAuxiliaryTargets,
  onClose,
  onDatasetSave,
  onReferenceSave,
  onAuxiliarySave,
  onLayerSave,
}: AutoConfigEditorSheetProps) {
  return (
    <Sheet open={open} onOpenChange={() => onClose()}>
      <SheetContent className="w-[500px] sm:max-w-[500px]">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-120px)] pr-4">
          {editingEntity?.type === 'dataset' && (
            <EntityConfigEditor
              entityName={editingEntity.name}
              entityType="dataset"
              config={editingEntity.config}
              detectedColumns={editingEntity.columns}
              availableReferences={availableReferences}
              onSave={(updated) => onDatasetSave(editingEntity.name, updated as DatasetConfig)}
              onCancel={onClose}
            />
          )}
          {editingEntity?.type === 'reference' && (
            <EntityConfigEditor
              entityName={editingEntity.name}
              entityType="reference"
              config={editingEntity.config}
              detectedColumns={editingEntity.columns}
              availableDatasets={availableDatasets}
              onSave={(updated) => onReferenceSave(editingEntity.name, updated as ReferenceConfig)}
              onCancel={onClose}
            />
          )}
          {editingEntity?.type === 'auxiliary' && (
            <EntityConfigEditor
              entityName={editingEntity.name}
              entityType="auxiliary"
              config={editingEntity.config}
              detectedColumns={editingEntity.columns}
              availableAuxiliaryTargets={availableAuxiliaryTargets}
              onSave={(updated) =>
                onAuxiliarySave(editingEntity.index, updated as AuxiliarySourceConfig)
              }
              onCancel={onClose}
            />
          )}
          {editingEntity?.type === 'layer' && (
            <EntityConfigEditor
              entityName={editingEntity.config.name}
              entityType="layer"
              config={editingEntity.config}
              onSave={(updated) => onLayerSave(editingEntity.index, updated as LayerConfig)}
              onCancel={onClose}
            />
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
