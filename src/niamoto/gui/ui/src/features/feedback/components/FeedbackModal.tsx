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
import { Loader2, WifiOff } from 'lucide-react'
import { useFeedback } from '../context/FeedbackProvider'
import { useBrowserOnline } from '../hooks/useBrowserOnline'
import { FeedbackTypeSelector } from './FeedbackTypeSelector'
import { ScreenshotPreview } from './ScreenshotPreview'
import { ContextDetails } from './ContextDetails'
import type { FeedbackType } from '../types'

export function FeedbackModal() {
  const { t } = useTranslation('feedback')
  const feedback = useFeedback()
  const browserOnline = useBrowserOnline()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [includeScreenshot, setIncludeScreenshot] = useState(true)
  const [showConfirmClose, setShowConfirmClose] = useState(false)
  const [titleError, setTitleError] = useState(false)

  const titleRef = useRef<HTMLInputElement>(null)

  // Focus title field when modal opens
  useEffect(() => {
    if (feedback.isOpen) {
      setTimeout(() => titleRef.current?.focus(), 100)
    }
  }, [feedback.isOpen])

  // Reset form only when modal opens (not on type change)
  useEffect(() => {
    if (feedback.isOpen) {
      setTitle('')
      setDescription('')
      setIncludeScreenshot(feedback.type === 'bug')
      setTitleError(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally only on isOpen
  }, [feedback.isOpen])

  // Update screenshot default when type changes
  const handleTypeChange = async (newType: FeedbackType) => {
    feedback.setType(newType)
    setIncludeScreenshot(newType === 'bug')
    // Trigger capture when switching to bug if no screenshot exists yet
    if (newType === 'bug' && !feedback.screenshot && !feedback.isPreparingScreenshot) {
      await feedback.captureScreenshot()
    }
  }

  const handleClose = () => {
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

  const canSend = browserOnline && !feedback.isSending && feedback.cooldownRemaining <= 0 && title.trim().length > 0

  return (
    <>
      <Dialog open={feedback.isOpen} onOpenChange={(open) => { if (!open) handleClose() }}>
        <DialogContent className="max-w-md" showCloseButton>
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
                onChange={(e) => setDescription(e.target.value.slice(0, 5000))}
                placeholder={t('description_placeholder')}
                maxLength={5000}
                rows={4}
                disabled={feedback.isSending}
              />
            </div>

            {/* Screenshot preview */}
            <ScreenshotPreview
              screenshot={feedback.screenshot}
              error={feedback.screenshotError}
              isCapturing={feedback.isPreparingScreenshot}
              included={includeScreenshot}
              onIncludedChange={setIncludeScreenshot}
            />

            {/* Context details (collapsible) */}
            <ContextDetails context={feedback.contextData} />

            {/* Offline warning */}
            {!browserOnline && (
              <div className="flex items-center gap-2 rounded-theme-sm bg-muted px-3 py-2 text-xs text-muted-foreground">
                <WifiOff className="h-3.5 w-3.5 shrink-0" />
                {t('offline_tooltip')}
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
                t('send')
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
