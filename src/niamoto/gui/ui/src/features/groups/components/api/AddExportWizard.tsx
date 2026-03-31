import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileJson, Leaf, Loader2, Settings, Zap } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useApiExportTargets,
  useCreateApiExportTarget,
  useUpdateApiExportGroupConfig,
  type ApiExportTargetSummary,
} from '@/features/groups/hooks/useApiExportConfigs'

type Template = 'simple' | 'dwc' | 'manual'
type WizardStep = 'type' | 'content' | 'confirm'

interface AddExportWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  groupBy: string
}

const NAME_PATTERN = /^[a-z][a-z0-9_]{2,30}$/

/** Stepper indicator */
function Stepper({ step }: { step: WizardStep }) {
  const { t } = useTranslation('sources')
  const steps: { key: WizardStep; label: string }[] = [
    { key: 'type', label: t('groupPanel.api.wizard.stepType') },
    { key: 'content', label: t('groupPanel.api.wizard.stepContent') },
    { key: 'confirm', label: t('groupPanel.api.wizard.stepConfirm') },
  ]
  const currentIdx = steps.findIndex((s) => s.key === step)

  return (
    <div className="flex items-center gap-2 mb-6">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center gap-2">
          <div
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
              i <= currentIdx
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {i + 1}
          </div>
          <span
            className={`text-xs font-medium ${
              i <= currentIdx ? 'text-foreground' : 'text-muted-foreground'
            }`}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <div className={`h-px w-8 ${i < currentIdx ? 'bg-primary' : 'bg-muted'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

export function AddExportWizard({ open, onOpenChange, groupBy }: AddExportWizardProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data: targets } = useApiExportTargets()
  const createTarget = useCreateApiExportTarget()

  const [step, setStep] = useState<WizardStep>('type')
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [selectedExisting, setSelectedExisting] = useState<ApiExportTargetSummary | null>(null)
  const [targetName, setTargetName] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)

  // For activating existing targets
  const activateMutation = useUpdateApiExportGroupConfig(
    selectedExisting?.name ?? '',
    groupBy
  )

  // Existing targets not yet active for this group
  const availableExistingTargets = (targets ?? []).filter(
    (target) => !target.groups.some((g) => g.group_by === groupBy)
  )

  const resetWizard = () => {
    setStep('type')
    setSelectedTemplate(null)
    setSelectedExisting(null)
    setTargetName('')
    setNameError(null)
  }

  const handleClose = () => {
    onOpenChange(false)
    setTimeout(resetWizard, 200) // after animation
  }

  const validateName = (name: string): boolean => {
    if (!NAME_PATTERN.test(name)) {
      setNameError(t('groupPanel.api.wizard.targetNameHelp'))
      return false
    }
    if (targets?.some((t) => t.name === name)) {
      setNameError(t('groupPanel.api.wizard.nameExists', { name }))
      return false
    }
    setNameError(null)
    return true
  }

  const handleSelectExisting = (target: ApiExportTargetSummary) => {
    setSelectedExisting(target)
    setSelectedTemplate(null)
    setStep('confirm')
  }

  const handleSelectTemplate = (template: Template) => {
    setSelectedTemplate(template)
    setSelectedExisting(null)
    setStep('content')
  }

  const handleContentNext = () => {
    if (!validateName(targetName)) return
    setStep('confirm')
  }

  const handleConfirm = async () => {
    try {
      if (selectedExisting) {
        // Activate existing target for this group
        await activateMutation.mutateAsync({
          enabled: true,
          group_by: groupBy,
          detail: { pass_through: true },
          index: { fields: [] },
        })
        toast.success(
          t('groupPanel.api.wizard.activated', { name: selectedExisting.name, groupBy })
        )
      } else if (selectedTemplate) {
        // Create new target then activate for group
        const created = await createTarget.mutateAsync({
          name: targetName,
          template: selectedTemplate,
        })
        // Now activate for this group
        const response = await fetch(
          `/api/config/export/api-targets/${encodeURIComponent(created.name)}/groups/${encodeURIComponent(groupBy)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              enabled: true,
              group_by: groupBy,
              detail: { pass_through: true },
              index: { fields: [] },
              ...(selectedTemplate === 'dwc'
                ? {
                    transformer_plugin: 'niamoto_to_dwc_occurrence',
                    transformer_params: {
                      occurrence_list_source: 'occurrences',
                      occurrence_table: 'occurrences',
                      taxonomy_entity: groupBy,
                      taxon_id_column: 'id_taxonref',
                      taxon_id_field: 'id',
                      mapping: {},
                    },
                  }
                : {}),
            }),
          }
        )
        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: 'Unknown error' }))
          throw new Error(err.detail)
        }
        toast.success(
          t('groupPanel.api.wizard.created', { name: targetName, groupBy })
        )
      }
      handleClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('groupPanel.api.saveFailed'))
    }
  }

  const isPending = createTarget.isPending || activateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('groupPanel.api.wizard.title')}</DialogTitle>
          <DialogDescription>
            {t('groupPanel.api.wizard.description', { groupBy })}
          </DialogDescription>
        </DialogHeader>

        <Stepper step={step} />

        {/* ── Step 1: Type ── */}
        {step === 'type' && (
          <div className="space-y-4">
            {/* Existing targets section */}
            {availableExistingTargets.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t('groupPanel.api.wizard.existingTargets')}
                </p>
                <div className="space-y-2">
                  {availableExistingTargets.map((target) => (
                    <button
                      key={target.name}
                      type="button"
                      className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent"
                      onClick={() => handleSelectExisting(target)}
                    >
                      <Zap className="h-5 w-5 shrink-0 text-amber-500" />
                      <div>
                        <div className="text-sm font-medium">{target.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {t('groupPanel.api.wizard.activateDescription')}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Create new section */}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t('groupPanel.api.wizard.createNew')}
              </p>
              <div className="space-y-2">
                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent"
                  onClick={() => handleSelectTemplate('simple')}
                >
                  <FileJson className="h-5 w-5 shrink-0 text-blue-500" />
                  <div>
                    <div className="text-sm font-medium">
                      {t('groupPanel.api.wizard.simpleTitle')}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t('groupPanel.api.wizard.simpleDescription')}
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent"
                  onClick={() => handleSelectTemplate('dwc')}
                >
                  <Leaf className="h-5 w-5 shrink-0 text-green-600" />
                  <div>
                    <div className="text-sm font-medium">
                      {t('groupPanel.api.wizard.dwcTitle')}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t('groupPanel.api.wizard.dwcDescription')}
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent"
                  onClick={() => handleSelectTemplate('manual')}
                >
                  <Settings className="h-5 w-5 shrink-0 text-gray-500" />
                  <div>
                    <div className="text-sm font-medium">
                      {t('groupPanel.api.wizard.manualTitle')}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t('groupPanel.api.wizard.manualDescription')}
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Step 2: Content ── */}
        {step === 'content' && selectedTemplate && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('groupPanel.api.wizard.targetName')}</Label>
              <Input
                value={targetName}
                onChange={(e) => {
                  setTargetName(e.target.value)
                  setNameError(null)
                }}
                placeholder={t('groupPanel.api.wizard.targetNamePlaceholder')}
                autoFocus
              />
              {nameError && <p className="text-xs text-destructive">{nameError}</p>}
              <p className="text-xs text-muted-foreground">
                {t('groupPanel.api.wizard.targetNameHelp')}
              </p>
            </div>

            {selectedTemplate === 'dwc' && (
              <div className="rounded-lg border bg-green-50 p-3 dark:bg-green-950/20">
                <p className="text-sm text-green-800 dark:text-green-200">
                  {t('groupPanel.api.wizard.dwcAutoMapping')}
                </p>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep('type')}>
                {t('common:actions.previous')}
              </Button>
              <Button onClick={handleContentNext} disabled={!targetName.trim()}>
                {t('common:actions.next')}
              </Button>
            </div>
          </div>
        )}

        {/* ── Step 3: Confirm ── */}
        {step === 'confirm' && (
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/30 p-4">
              <p className="text-sm">
                {selectedExisting
                  ? t('groupPanel.api.wizard.confirmActivate', {
                      name: selectedExisting.name,
                      groupBy,
                    })
                  : t('groupPanel.api.wizard.confirmCreate', {
                      name: targetName,
                      template: selectedTemplate,
                      groupBy,
                    })}
              </p>
              {selectedExisting && (
                <Badge variant="secondary" className="mt-2">
                  {selectedExisting.name}
                </Badge>
              )}
            </div>

            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setStep(selectedExisting ? 'type' : 'content')}
                disabled={isPending}
              >
                {t('common:actions.previous')}
              </Button>
              <Button onClick={handleConfirm} disabled={isPending}>
                {isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                {selectedExisting
                  ? t('groupPanel.api.wizard.activate')
                  : t('groupPanel.api.wizard.create')}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
