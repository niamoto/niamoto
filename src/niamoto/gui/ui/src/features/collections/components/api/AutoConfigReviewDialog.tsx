import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Sparkles } from 'lucide-react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ApiExportAutoConfigProposal } from '@/features/collections/hooks/useApiExportConfigs'

interface AutoConfigReviewDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  proposal?: ApiExportAutoConfigProposal
  isLoading?: boolean
  error?: Error | null
  onApply: (sectionKeys: string[]) => void
}

const SECTION_ORDER = ['index', 'detail', 'dwc_mapping', 'json_options']

function getSectionLabelKey(sectionKey: string) {
  switch (sectionKey) {
    case 'index':
      return 'collectionPanel.api.indexFields'
    case 'detail':
      return 'collectionPanel.api.detailFields'
    case 'dwc_mapping':
      return 'collectionPanel.api.dwcMapping'
    case 'json_options':
      return 'collectionPanel.api.jsonOverrides'
    default:
      return 'collectionPanel.api.autoConfig.section'
  }
}

export function AutoConfigReviewDialog({
  open,
  onOpenChange,
  proposal,
  isLoading = false,
  error = null,
  onApply,
}: AutoConfigReviewDialogProps) {
  const { t } = useTranslation(['sources', 'common'])
  const orderedSections = useMemo(() => {
    if (!proposal) return []
    const sectionKeys = Object.keys(proposal.sections)
    return sectionKeys.sort((left, right) => {
      const leftIndex = SECTION_ORDER.indexOf(left)
      const rightIndex = SECTION_ORDER.indexOf(right)
      return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex)
    })
  }, [proposal])
  const [selectedSections, setSelectedSections] = useState<string[]>([])

  useEffect(() => {
    if (open) {
      // Reset the review checklist every time a fresh proposal is opened.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedSections(orderedSections)
    }
  }, [open, orderedSections])

  const visibleSelectedSections = selectedSections

  const toggleSection = (sectionKey: string, checked: boolean | 'indeterminate') => {
    setSelectedSections((current) => {
      if (checked === true) {
        return Array.from(new Set([...current, sectionKey]))
      }
      return current.filter((key) => key !== sectionKey)
    })
  }

  const handleApply = () => {
    onApply(visibleSelectedSections)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            {t('collectionPanel.api.autoConfig.title')}
          </DialogTitle>
          <DialogDescription>
            {t('collectionPanel.api.autoConfig.description')}
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            {t('collectionPanel.api.autoConfig.loading')}
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        )}

        {proposal && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              {t('collectionPanel.api.autoConfig.entries', {
                count: proposal.total_entities,
              })}
            </p>

            {orderedSections.map((sectionKey) => {
              const section = proposal.sections[sectionKey]
              const checked = visibleSelectedSections.includes(sectionKey)

              return (
                <div key={sectionKey} className="rounded-md border p-3">
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-2">
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(nextChecked) =>
                          toggleSection(sectionKey, nextChecked)
                        }
                        aria-label={t('collectionPanel.api.autoConfig.toggleSection')}
                      />
                      <div>
                        <h3 className="text-sm font-medium">
                          {t(getSectionLabelKey(sectionKey))}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          {section.notes[0] ?? t('collectionPanel.api.autoConfig.section')}
                        </p>
                      </div>
                    </div>
                    <Badge variant="secondary" className="shrink-0 text-[10px]">
                      {t(`collectionPanel.api.autoConfig.confidence.${section.confidence}`)}
                    </Badge>
                  </div>

                  {section.notes.length > 1 && (
                    <ul className="ml-6 list-disc space-y-1 text-xs text-muted-foreground">
                      {section.notes.slice(1).map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  )}

                  {section.unresolved.length > 0 && (
                    <div className="mt-3 rounded-md bg-amber-50 p-2 text-xs text-amber-900">
                      <span className="font-medium">
                        {t('collectionPanel.api.autoConfig.unresolved')}
                      </span>{' '}
                      {section.unresolved.join(', ')}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common:actions.cancel')}
          </Button>
          <Button
            onClick={handleApply}
            disabled={!proposal || visibleSelectedSections.length === 0}
          >
            {t('collectionPanel.api.autoConfig.apply')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
