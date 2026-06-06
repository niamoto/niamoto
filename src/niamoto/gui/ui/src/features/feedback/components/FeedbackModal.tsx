import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { CheckCircle2, Download, ExternalLink, Loader2 } from 'lucide-react'
import { useFeedback } from '../context/useFeedback'
import { FeedbackTypeSelector } from './FeedbackTypeSelector'
import { ScreenshotPreview } from './ScreenshotPreview'
import { ContextDetails } from './ContextDetails'
import type { FeedbackType } from '../types'

export function FeedbackModal() {
  const { t } = useTranslation('feedback')
  const feedback = useFeedback()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [includeScreenshot, setIncludeScreenshot] = useState(true)
  const [showConfirmClose, setShowConfirmClose] = useState(false)
  const [titleError, setTitleError] = useState(false)

  const titleRef = useRef<HTMLInputElement>(null)

  // Focus title field when modal opens
  useEffect(() => {
    if (feedback.isOpen) {
      const focusTimeout = window.setTimeout(() => titleRef.current?.focus(), 100)
      return () => window.clearTimeout(focusTimeout)
    }
  }, [feedback.isOpen])

  // Reset form only when modal opens (not on type change)
  useEffect(() => {
    if (feedback.isOpen) {
      setTitle(feedback.draftTitle.slice(0, 200))
      setDescription(feedback.draftDescription.slice(0, 5000))
      setIncludeScreenshot(feedback.type === 'bug')
      setTitleError(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally only on isOpen
  }, [feedback.isOpen])

  const handleTypeChange = async (newType: FeedbackType) => {
    feedback.clearGeneratedReport()
    feedback.setType(newType)
    setIncludeScreenshot(newType === 'bug')

    if (newType === 'bug' && !feedback.screenshot && !feedback.isPreparingScreenshot) {
      await feedback.captureScreenshot()
    }
  }

  const handleClose = () => {
    if (feedback.generatedReport) {
      feedback.close()
      return
    }

    if (title.trim() || description.trim()) {
      setShowConfirmClose(true)
    } else {
      feedback.close()
    }
  }

  const handleSubmit = async () => {
    if (!title.trim()) {
      setTitleError(true)
      titleRef.current?.focus()
      return
    }
    setTitleError(false)
    await feedback.send(title.trim(), description.trim(), includeScreenshot)
  }

  const canSend = !feedback.isSending && title.trim().length > 0
  const reportDownloadState = feedback.reportDownloadState
  const isSavingReport = reportDownloadState.status === 'saving'
  const downloadButtonLabel = isSavingReport
    ? t('download_saving')
    : reportDownloadState.status === 'saved' || reportDownloadState.status === 'downloaded'
      ? t('download_again')
      : t('download_report')
  const downloadStatusMessage = (() => {
    switch (reportDownloadState.status) {
      case 'saving':
        return t('download_saving_description')
      case 'saved':
        return reportDownloadState.path
          ? t('download_saved_path', { path: reportDownloadState.path })
          : t('download_saved')
      case 'downloaded':
        return t('download_started', { filename: reportDownloadState.filename })
      case 'cancelled':
        return t('download_cancelled')
      case 'error':
        return reportDownloadState.message
          ? t('download_error_with_detail', { message: reportDownloadState.message })
          : t('download_error_inline')
      default:
        return null
    }
  })()

  return (
    <>
      <Dialog open={feedback.isOpen} onOpenChange={(open) => { if (!open) handleClose() }}>
        <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto" showCloseButton>
          <DialogHeader>
            <DialogTitle>{t('modal_title')}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Type selector */}
            <FeedbackTypeSelector
              value={feedback.type}
              onChange={handleTypeChange}
              disabled={feedback.isSending}
            />

            {/* Title */}
            <div className="space-y-1.5">
              <Label htmlFor="feedback-title">{t('title_label')}</Label>
              <Input
                ref={titleRef}
                id="feedback-title"
                value={title}
                onChange={(e) => {
                  feedback.clearGeneratedReport()
                  setTitle(e.target.value.slice(0, 200))
                  if (titleError) setTitleError(false)
                }}
                placeholder={t('title_placeholder')}
                maxLength={200}
                disabled={feedback.isSending}
                aria-invalid={titleError}
                aria-describedby={titleError ? 'feedback-title-error' : undefined}
                className={titleError ? 'border-destructive' : ''}
              />
              {titleError && (
                <p id="feedback-title-error" className="text-xs text-destructive">
                  {t('title_required')}
                </p>
              )}
              <p className="text-xs text-muted-foreground text-right">{title.length}/200</p>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="feedback-description">{t('description_label')}</Label>
              <Textarea
                id="feedback-description"
                value={description}
                onChange={(e) => {
                  feedback.clearGeneratedReport()
                  setDescription(e.target.value.slice(0, 5000))
                }}
                placeholder={t('description_placeholder')}
                maxLength={5000}
                rows={4}
                disabled={feedback.isSending}
                className="field-sizing-fixed min-h-40 max-h-[40vh] overflow-y-auto whitespace-pre-wrap break-words"
              />
              <p className="text-xs text-muted-foreground text-right">{description.length}/5000</p>
            </div>

            {/* Screenshot preview (visible for bug type) */}
            <ScreenshotPreview
              screenshot={feedback.screenshot}
              error={feedback.screenshotError}
              isCapturing={feedback.isPreparingScreenshot}
              included={includeScreenshot}
              onIncludedChange={(included) => {
                feedback.clearGeneratedReport()
                setIncludeScreenshot(included)
              }}
            />

            {/* Context details (collapsible) */}
            <ContextDetails context={feedback.contextData} />

            {feedback.generatedReport && (
              <div
                aria-live="polite"
                className="rounded-lg border border-primary/25 bg-primary/5 p-4"
              >
                <div className="flex gap-3">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                  <div className="min-w-0 flex-1 space-y-3">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{t('report_ready_title')}</p>
                      <p className="text-sm text-muted-foreground">
                        {t('report_ready_description')}
                      </p>
                      <p className="break-all text-xs text-muted-foreground">
                        {t('report_ready_filename', {
                          filename: feedback.generatedReport.report_filename,
                        })}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void feedback.downloadGeneratedReport()}
                        disabled={isSavingReport}
                        aria-describedby={downloadStatusMessage ? 'feedback-report-download-status' : undefined}
                      >
                        {isSavingReport ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                        ) : (
                          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                        )}
                        {downloadButtonLabel}
                      </Button>
                      {feedback.generatedReport.github_issue_url && (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={feedback.openGeneratedReportIssue}
                        >
                          <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
                          {t('open_github_issue')}
                        </Button>
                      )}
                    </div>
                    {downloadStatusMessage && (
                      <p
                        id="feedback-report-download-status"
                        role={reportDownloadState.status === 'error' ? 'alert' : undefined}
                        className={
                          reportDownloadState.status === 'error'
                            ? 'break-words text-xs text-destructive'
                            : 'break-all text-xs text-muted-foreground'
                        }
                      >
                        {downloadStatusMessage}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Submit */}
            <Button
              onClick={handleSubmit}
              disabled={!canSend}
              className="w-full"
            >
              {feedback.isSending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('sending')}
                </>
              ) : (
                t(feedback.generatedReport ? 'regenerate_report' : 'send')
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirm close dialog */}
      <AlertDialog open={showConfirmClose} onOpenChange={setShowConfirmClose}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirm_close_title')}</AlertDialogTitle>
            <AlertDialogDescription>{t('confirm_close_description')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('confirm_close_cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowConfirmClose(false)
                feedback.close()
              }}
            >
              {t('confirm_close_confirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
