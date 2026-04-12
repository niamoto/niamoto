import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Loader2, Plus, Settings2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useApiExportTargets } from '@/features/collections/hooks/useApiExportConfigs'

import { AddExportWizard } from './AddExportWizard'
import { ExportCard } from './ExportCard'

interface ApiExportsTabProps {
  groupBy: string
}

export function ApiExportsTab({ groupBy }: ApiExportsTabProps) {
  const navigate = useNavigate()
  const { t } = useTranslation(['sources', 'common'])
  const { data: targets, isLoading, error } = useApiExportTargets()
  const [wizardOpen, setWizardOpen] = useState(false)

  // Filter targets that have this group (active OR enabled:false)
  const groupTargets = (targets ?? []).filter((target) =>
    target.groups.some((g) => g.group_by === groupBy)
  )

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-dashed p-4 text-sm text-destructive">
        {error instanceof Error ? error.message : t('collectionPanel.api.loadFailed')}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header — fixed */}
      <div className="shrink-0 flex items-center justify-between gap-4 border-b px-4 py-3">
        <div>
          <h2 className="text-base font-medium">{t('collectionPanel.api.title')}</h2>
          <p className="text-xs text-muted-foreground">
            {t('collectionPanel.api.description', { groupBy })}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/groups/api-settings')}
        >
          <Settings2 className="mr-2 h-4 w-4" />
          {t('collectionPanel.api.globalSettings')}
        </Button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 min-h-0 overflow-auto space-y-4 p-4">
        {/* Export cards */}
        {groupTargets.map((target) => (
          <ExportCard
            key={`${target.name}-${groupBy}`}
            exportTarget={target}
            groupBy={groupBy}
          />
        ))}

        {/* Empty state */}
        {groupTargets.length === 0 && !targets?.length && (
          <div className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
            {t('collectionPanel.api.empty')}
          </div>
        )}

        {/* Add export button */}
        <button
          type="button"
          className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed p-5 text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
          onClick={() => setWizardOpen(true)}
        >
          <Plus className="h-4 w-4" />
          {t('collectionPanel.api.wizard.addFormat')}
        </button>

        {/* Wizard dialog */}
        <AddExportWizard
          open={wizardOpen}
          onOpenChange={setWizardOpen}
          groupBy={groupBy}
        />
      </div>
    </div>
  )
}
