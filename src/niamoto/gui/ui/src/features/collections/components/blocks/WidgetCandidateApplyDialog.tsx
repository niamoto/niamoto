import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type {
  WidgetCandidateApplyResponse,
  WidgetCandidatePreviewResponse,
  WidgetCandidateSelection,
} from '@/features/collections/api/widget-candidates'

type ReplacementChoice = NonNullable<WidgetCandidateSelection['replacement']>

interface WidgetCandidateApplyDialogProps {
  open: boolean
  preview: WidgetCandidatePreviewResponse | null
  loading: boolean
  applying: boolean
  result: WidgetCandidateApplyResponse | null
  error: Error | null
  onOpenChange: (open: boolean) => void
  onApply: () => void
  onReplacementChange?: (candidateId: string, replacement: ReplacementChoice) => void
}

export function WidgetCandidateApplyDialog({
  open,
  preview,
  loading,
  applying,
  result,
  error,
  onOpenChange,
  onApply,
  onReplacementChange,
}: WidgetCandidateApplyDialogProps) {
  const { t } = useTranslation(['sources'])
  const previewSections = preview
    ? [
        {
          key: 'changes',
          items: preview.changes.filter(
            (change) => change.action !== 'conflict' && change.action !== 'invalid',
          ),
        },
        { key: 'conflicts', items: preview.conflicts },
        { key: 'invalid', items: preview.invalid },
      ].filter((section) => section.items.length > 0)
    : []
  const canApply =
    !loading &&
    !applying &&
    Boolean(preview) &&
    preview!.conflicts.length === 0 &&
    preview!.invalid.length === 0 &&
    preview!.changes.some(
      (change) => change.action === 'add' || change.action === 'replace',
    )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('collectionPanel.widgetCandidates.applyDialog.title')}</DialogTitle>
          <DialogDescription>
            {t('collectionPanel.widgetCandidates.applyDialog.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[52vh] overflow-auto">
          {loading && (
            <div className="flex items-center justify-center p-8 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('collectionPanel.widgetCandidates.applyDialog.checking')}
            </div>
          )}

          {applying && (
            <div className="flex items-center justify-center p-8 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('collectionPanel.widgetCandidates.applyDialog.adding')}
            </div>
          )}

          {!loading && !applying && preview && (
            <div className="space-y-4">
              {previewSections.length === 0 ? (
                <p className="rounded-md border p-3 text-sm text-muted-foreground">
                  {t('collectionPanel.widgetCandidates.applyDialog.empty')}
                </p>
              ) : (
                previewSections.map((section) => (
                  <section key={section.key} className="space-y-2">
                    <h3 className="text-sm font-medium">
                      {t(
                        `collectionPanel.widgetCandidates.applyDialog.sections.${section.key}`,
                      )}
                    </h3>
                    {section.items.map((change) => (
                      <div
                        key={`${section.key}:${change.candidate_id}:${change.action}`}
                        className="rounded-md border p-3 text-sm"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium">{change.title}</p>
                          <span className="rounded-md bg-muted px-2 py-0.5 text-xs">
                            {t(
                              `collectionPanel.widgetCandidates.applyDialog.actions.${change.action}`,
                              { defaultValue: change.action },
                            )}
                          </span>
                        </div>
                        {change.reason && (
                          <p className="mt-1 text-muted-foreground">
                            {change.reason}
                          </p>
                        )}
                        {change.action === 'conflict' && onReplacementChange && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                onReplacementChange(change.candidate_id, 'replace')
                              }
                            >
                              {t(
                                'collectionPanel.widgetCandidates.applyDialog.replaceConflict',
                              )}
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                onReplacementChange(change.candidate_id, 'skip')
                              }
                            >
                              {t(
                                'collectionPanel.widgetCandidates.applyDialog.skipConflict',
                              )}
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </section>
                ))
              )}
            </div>
          )}

          {!applying && error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {error.message}
            </div>
          )}

          {!applying && result && (
            <div className="rounded-md border bg-muted/30 p-3 text-sm">
              {result.message}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            disabled={applying}
            onClick={() => onOpenChange(false)}
          >
            {t('collectionPanel.widgetCandidates.applyDialog.cancel')}
          </Button>
          <Button disabled={!canApply || applying} onClick={onApply}>
            {applying && <Loader2 className="h-4 w-4 animate-spin" />}
            {applying
              ? t('collectionPanel.widgetCandidates.applyDialog.adding')
              : t('collectionPanel.widgetCandidates.applyDialog.addWidgets')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
