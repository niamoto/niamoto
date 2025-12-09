/**
 * Add Source Dialog - Multi-step dialog for adding pre-calculated sources
 *
 * Steps:
 * 1. Upload: Drag & drop or select CSV file
 * 2. Validation: Display detected class_objects and validation status
 * 3. Configuration: Set source name and entity column
 * 4. Confirmation: Review and save
 */

import { useState, useCallback } from 'react'
import { Check, AlertCircle, FileSpreadsheet, ArrowRight, ArrowLeft, Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { UploadZone } from './UploadZone'
import {
  useUploadSource,
  useSaveSource,
  type UploadValidationResponse,
  type ClassObjectInfo,
} from '@/hooks/useSources'

interface AddSourceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  referenceName: string
  onSuccess?: () => void
}

type Step = 'upload' | 'validation' | 'configure' | 'confirm'

export function AddSourceDialog({
  open,
  onOpenChange,
  referenceName,
  onSuccess,
}: AddSourceDialogProps) {
  const [step, setStep] = useState<Step>('upload')
  const [sourceName, setSourceName] = useState('')
  const [validationResult, setValidationResult] = useState<UploadValidationResponse | null>(null)
  const [entityColumn, setEntityColumn] = useState<string>('')

  const uploadMutation = useUploadSource(referenceName)
  const saveMutation = useSaveSource(referenceName)

  const resetDialog = useCallback(() => {
    setStep('upload')
    setSourceName('')
    setValidationResult(null)
    setEntityColumn('')
    uploadMutation.reset()
    saveMutation.reset()
  }, [uploadMutation, saveMutation])

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetDialog()
    }
    onOpenChange(newOpen)
  }

  const handleFileSelect = async (file: File) => {
    // Auto-generate source name from filename
    const name = file.name.replace(/^raw_/, '').replace(/\.csv$/, '')
    setSourceName(name)

    // Upload and validate
    try {
      const result = await uploadMutation.mutateAsync({ file, sourceName: name })
      setValidationResult(result)

      // Auto-select entity column if detected
      if (result.entity_column) {
        setEntityColumn(result.entity_column)
      }

      setStep('validation')
    } catch {
      // Error is handled by mutation state
    }
  }

  const handleSave = async () => {
    if (!validationResult || !entityColumn) return

    try {
      await saveMutation.mutateAsync({
        source_name: sourceName,
        file_path: validationResult.path,
        entity_id_column: entityColumn,
      })
      onSuccess?.()
      handleOpenChange(false)
    } catch {
      // Error is handled by mutation state
    }
  }

  const canProceed = () => {
    switch (step) {
      case 'upload':
        return false // Handled by file selection
      case 'validation':
        return validationResult?.success === true
      case 'configure':
        return sourceName.trim() !== '' && entityColumn !== ''
      case 'confirm':
        return true
      default:
        return false
    }
  }

  const nextStep = () => {
    switch (step) {
      case 'validation':
        setStep('configure')
        break
      case 'configure':
        setStep('confirm')
        break
      case 'confirm':
        handleSave()
        break
    }
  }

  const prevStep = () => {
    switch (step) {
      case 'validation':
        resetDialog()
        break
      case 'configure':
        setStep('validation')
        break
      case 'confirm':
        setStep('configure')
        break
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Ajouter une source pre-calculee</DialogTitle>
          <DialogDescription>
            {step === 'upload' && 'Importez un fichier CSV avec vos donnees pre-calculees.'}
            {step === 'validation' && 'Verification de la structure du fichier.'}
            {step === 'configure' && 'Configurez les parametres de la source.'}
            {step === 'confirm' && 'Verifiez et enregistrez la configuration.'}
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 py-2">
          {(['upload', 'validation', 'configure', 'confirm'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                  step === s
                    ? 'bg-primary text-primary-foreground'
                    : i < ['upload', 'validation', 'configure', 'confirm'].indexOf(step)
                    ? 'bg-primary/20 text-primary'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {i + 1}
              </div>
              {i < 3 && (
                <div
                  className={`mx-1.5 h-0.5 w-6 ${
                    i < ['upload', 'validation', 'configure', 'confirm'].indexOf(step)
                      ? 'bg-primary/50'
                      : 'bg-muted'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="py-4">
          {/* Upload Step */}
          {step === 'upload' && (
            <UploadZone
              onFileSelect={handleFileSelect}
              isUploading={uploadMutation.isPending}
              error={uploadMutation.error?.message}
            />
          )}

          {/* Validation Step */}
          {step === 'validation' && validationResult && (
            <ValidationStepContent result={validationResult} />
          )}

          {/* Configure Step */}
          {step === 'configure' && validationResult && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="source-name">Nom de la source</Label>
                <Input
                  id="source-name"
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  placeholder="plot_stats"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="entity-column">Colonne d'entite</Label>
                <Select value={entityColumn} onValueChange={setEntityColumn}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selectionnez une colonne" />
                  </SelectTrigger>
                  <SelectContent>
                    {validationResult.columns.map((col) => (
                      <SelectItem key={col} value={col}>
                        {col}
                        {col === validationResult.entity_column && ' (detecte)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Colonne qui relie les donnees aux entites du groupe "{referenceName}"
                </p>
              </div>
            </div>
          )}

          {/* Confirm Step */}
          {step === 'confirm' && validationResult && (
            <div className="space-y-3">
              <div className="rounded-md border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Source</span>
                  <span className="font-medium">{sourceName}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Fichier</span>
                  <span className="text-sm">{validationResult.file_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Colonne d'entite</span>
                  <span className="font-mono text-sm">{entityColumn}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Entites</span>
                  <span>{validationResult.entity_count}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Class objects</span>
                  <span>{validationResult.class_objects.length}</span>
                </div>
              </div>

              {saveMutation.error && (
                <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{saveMutation.error.message}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          {step !== 'upload' && (
            <Button variant="outline" onClick={prevStep} disabled={saveMutation.isPending}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Retour
            </Button>
          )}

          {step !== 'upload' && (
            <Button onClick={nextStep} disabled={!canProceed() || saveMutation.isPending}>
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Enregistrement...
                </>
              ) : step === 'confirm' ? (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  Enregistrer
                </>
              ) : (
                <>
                  Suivant
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

function ValidationStepContent({ result }: { result: UploadValidationResponse }) {
  if (!result.success) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <span className="font-medium text-destructive">Validation echouee</span>
        </div>
        <ul className="space-y-1 text-sm text-muted-foreground">
          {result.validation_errors.map((error, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-destructive">•</span>
              {error}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-md bg-success/10 p-3">
        <Check className="h-5 w-5 text-success" />
        <span className="font-medium text-success">Fichier valide</span>
      </div>

      {/* File Info */}
      <div className="flex items-center gap-3 rounded-md border p-3">
        <FileSpreadsheet className="h-8 w-8 text-muted-foreground" />
        <div>
          <p className="font-medium">{result.file_name}</p>
          <p className="text-xs text-muted-foreground">
            {result.row_count.toLocaleString()} lignes • Delimiteur: "{result.delimiter}"
          </p>
        </div>
      </div>

      {/* Class Objects */}
      <div>
        <p className="mb-2 text-sm font-medium">
          {result.class_objects.length} class_objects detectes
        </p>
        <ScrollArea className="h-[150px]">
          <div className="space-y-1.5 pr-4">
            {result.class_objects.map((co) => (
              <ClassObjectRow key={co.name} classObject={co} />
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}

function ClassObjectRow({ classObject }: { classObject: ClassObjectInfo }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-muted/50 px-2 py-1.5">
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm">{classObject.name}</span>
        <Badge variant="outline" className="text-[10px]">
          {classObject.cardinality === 0 ? 'scalar' : classObject.cardinality}
        </Badge>
      </div>
      <span className="text-xs text-muted-foreground">
        {classObject.suggested_plugin}
      </span>
    </div>
  )
}
