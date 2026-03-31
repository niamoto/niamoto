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
import { useTranslation } from 'react-i18next'
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
} from '@/features/collections/hooks/useSources'

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
  const { t } = useTranslation(['sources', 'common'])
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
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>{t('dialogs.addPrecomputedSource')}</DialogTitle>
          <DialogDescription>
            {step === 'upload' && t('dialogs.importPrecomputedDescription')}
            {step === 'validation' && t('wizard.verifyingFile', 'Verification of file structure.')}
            {step === 'configure' && t('dialogs.configureParameters')}
            {step === 'confirm' && t('wizard.verifyAndSave', 'Verify and save configuration.')}
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
        <div className="min-h-0 flex-1 overflow-y-auto py-4">
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
                <Label htmlFor="source-name">{t('form.sourceName')}</Label>
                <Input
                  id="source-name"
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  placeholder="plot_stats"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="entity-column">{t('form.entityColumn')}</Label>
                <Select value={entityColumn} onValueChange={setEntityColumn}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('common:placeholders.selectOption')} />
                  </SelectTrigger>
                  <SelectContent>
                    {validationResult.columns.map((col) => (
                      <SelectItem key={col} value={col}>
                        {col}
                        {col === validationResult.entity_column && ` (${t('common:messages.suggested', '(suggested)')}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {t('form.linkToEntities', { reference: referenceName })}
                </p>
              </div>
            </div>
          )}

          {/* Confirm Step */}
          {step === 'confirm' && validationResult && (
            <div className="space-y-3">
              <div className="rounded-md border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{t('common:labels.source')}</span>
                  <span className="font-medium">{sourceName}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{t('reference.file')}</span>
                  <span className="text-sm">{validationResult.file_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{t('form.entityColumn')}</span>
                  <span className="font-mono text-sm">{entityColumn}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{t('reference.entities')}</span>
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

        <DialogFooter className="gap-2 sm:justify-between">
          {step !== 'upload' && (
            <Button variant="outline" onClick={prevStep} disabled={saveMutation.isPending}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('wizard.back')}
            </Button>
          )}

          {step !== 'upload' && (
            <Button onClick={nextStep} disabled={!canProceed() || saveMutation.isPending}>
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common:status.registering')}
                </>
              ) : step === 'confirm' ? (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  {t('common:actions.save')}
                </>
              ) : (
                <>
                  {t('common:actions.next')}
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
  const { t } = useTranslation(['sources', 'common'])
  if (!result.success) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <span className="font-medium text-destructive">{t('validation.validationFailed')}</span>
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
        <span className="font-medium text-success">{t('validation.fileValid')}</span>
      </div>

      {/* File Info */}
      <div className="flex items-center gap-3 rounded-md border p-3">
        <FileSpreadsheet className="h-8 w-8 text-muted-foreground" />
        <div>
          <p className="font-medium">{result.file_name}</p>
          <p className="text-xs text-muted-foreground">
            {result.row_count.toLocaleString()} {t('common:file.rows')} • Delimiter: "{result.delimiter}"
          </p>
        </div>
      </div>

      {/* Class Objects */}
      <div>
        <p className="mb-2 text-sm font-medium">
          {result.class_objects.length} class_objects
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
