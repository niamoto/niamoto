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
  WidgetProposalApplyResponse,
  WidgetProposalPreviewResponse,
} from '@/features/collections/api/widget-proposals'

interface WidgetProposalApplyDialogProps {
  open: boolean
  preview: WidgetProposalPreviewResponse | null
  loading: boolean
  applying: boolean
  result: WidgetProposalApplyResponse | null
  error: Error | null
  onOpenChange: (open: boolean) => void
  onApply: () => void
}

export function WidgetProposalApplyDialog({
  open,
  preview,
  loading,
  applying,
  result,
  error,
  onOpenChange,
  onApply,
}: WidgetProposalApplyDialogProps) {
  const canApply =
    !loading &&
    Boolean(preview) &&
    preview!.conflicts.length === 0 &&
    preview!.invalid.length === 0 &&
    preview!.changes.some((change) => change.action === 'add' || change.action === 'replace')

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Review changes before adding widgets</DialogTitle>
          <DialogDescription>
            Niamoto will add the selected widgets to the transform and export configuration.
            Nothing is written until you confirm.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[52vh] overflow-auto">
          {loading && (
            <div className="flex items-center justify-center p-8 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Checking generated changes
            </div>
          )}

          {!loading && preview && (
            <div className="space-y-2">
              {preview.changes.map((change) => (
                <div
                  key={`${change.proposal_id}:${change.action}`}
                  className="rounded-md border p-3 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{change.title}</p>
                    <span className="rounded-md bg-muted px-2 py-0.5 text-xs">
                      {change.action}
                    </span>
                  </div>
                  {change.reason && (
                    <p className="mt-1 text-muted-foreground">{change.reason}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {error.message}
            </div>
          )}

          {result && (
            <div className="rounded-md border bg-muted/30 p-3 text-sm">
              {result.message}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!canApply || applying} onClick={onApply}>
            {applying && <Loader2 className="h-4 w-4 animate-spin" />}
            Add widgets
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
