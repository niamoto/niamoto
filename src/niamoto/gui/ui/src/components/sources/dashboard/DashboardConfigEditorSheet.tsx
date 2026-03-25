import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { EntityConfigEditor } from '@/components/sources/EntityConfigEditor'
import type { DatasetConfig, ReferenceConfig } from '@/components/sources/EntityConfigEditor'

type EditingState =
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

interface DashboardConfigEditorSheetProps {
  editingState: EditingState
  editorError: string | null
  savingConfig: boolean
  title: string
  description: string
  availableReferences: Array<{ name: string; columns: string[] }>
  availableDatasets: string[]
  loadingLabel: string
  savingLabel: string
  onClose: () => void
  onDatasetSave: (name: string, updated: DatasetConfig) => Promise<void> | void
  onReferenceSave: (name: string, updated: ReferenceConfig) => Promise<void> | void
}

export function DashboardConfigEditorSheet({
  editingState,
  editorError,
  savingConfig,
  title,
  description,
  availableReferences,
  availableDatasets,
  loadingLabel,
  savingLabel,
  onClose,
  onDatasetSave,
  onReferenceSave,
}: DashboardConfigEditorSheetProps) {
  return (
    <Sheet open={editingState !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-[min(760px,92vw)] sm:max-w-[760px]">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-110px)] px-6 pb-6">
          <div className="pt-6">
            {editorError && (
              <Alert variant="destructive" className="mb-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{editorError}</AlertDescription>
              </Alert>
            )}

            {savingConfig || !editingState?.config ? (
              <div className="flex min-h-[240px] items-center justify-center">
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {savingConfig ? savingLabel : loadingLabel}
                </div>
              </div>
            ) : editingState.entityType === 'dataset' ? (
              <EntityConfigEditor
                entityName={editingState.name}
                entityType="dataset"
                config={editingState.config}
                detectedColumns={editingState.detectedColumns}
                availableReferences={availableReferences}
                onSave={(updated) => onDatasetSave(editingState.name, updated as DatasetConfig)}
                onCancel={onClose}
              />
            ) : (
              <EntityConfigEditor
                entityName={editingState.name}
                entityType="reference"
                config={editingState.config}
                detectedColumns={editingState.detectedColumns}
                availableDatasets={availableDatasets}
                onSave={(updated) =>
                  onReferenceSave(editingState.name, updated as ReferenceConfig)
                }
                onCancel={onClose}
              />
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
