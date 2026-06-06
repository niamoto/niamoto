import {
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { openExternalUrl } from '@/shared/desktop/openExternalUrl'
import { useScreenshot } from '../hooks/useScreenshot'
import { useContextData } from '../hooks/useContextData'
import { sendFeedback } from '../lib/feedback-api'
import {
  subscribeToBugReportRequests,
  type BugReportDraft,
} from '../lib/bug-report-bridge'
import {
  type FeedbackType,
  type FeedbackContext as FeedbackContextData,
} from '../types'
import { FeedbackContext, type FeedbackState } from './feedbackContext'

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation('feedback')
  const [isOpen, setIsOpen] = useState(false)
  const [type, setType] = useState<FeedbackType>('bug')
  const [isSending, setIsSending] = useState(false)
  const [contextData, setContextData] = useState<FeedbackContextData | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftDescription, setDraftDescription] = useState('')

  const { screenshot, isCapturing, error: screenshotError, capture, clear } = useScreenshot()
  const { collect } = useContextData()

  const openDraft = useCallback(
    async (nextType: FeedbackType = 'bug', draft?: BugReportDraft) => {
      setType(nextType)
      setDraftTitle(draft?.title ?? '')
      setDraftDescription(draft?.description ?? '')

      // Capture screenshot before opening (bug type only)
      if (nextType === 'bug') {
        await capture()
      } else {
        clear()
      }

      // Collect context data
      const ctx = await collect()
      setContextData(ctx)

      setIsOpen(true)
    },
    [capture, clear, collect]
  )

  const openWithType = useCallback(
    async (nextType: FeedbackType = 'bug') => openDraft(nextType),
    [openDraft]
  )

  const close = useCallback(() => {
    setIsOpen(false)
    setDraftTitle('')
    setDraftDescription('')
  }, [])

  useEffect(() => {
    return subscribeToBugReportRequests((draft) => {
      void openDraft('bug', draft)
    })
  }, [openDraft])

  // Keep ref to avoid stale closures in send
  const contextDataRef = useRef(contextData)
  contextDataRef.current = contextData

  const send = useCallback(
    async (title: string, description: string, includeScreenshot: boolean) => {
      const ctx = contextDataRef.current
      if (!ctx) return

      setIsSending(true)
      try {
        const result = await sendFeedback({
          payload: {
            type,
            title: title.slice(0, 200),
            description: description ? description.slice(0, 5000) : undefined,
            context: ctx, // Already redacted at collection time
          },
          screenshot: includeScreenshot ? screenshot : null,
        })

        toast.success(t('success'), {
          description: t('issue_created'),
          ...(result.github_issue_url
            ? {
                action: {
                  label: t('open_github_issue'),
                  onClick: () => {
                    void openExternalUrl(result.github_issue_url!)
                  },
                },
              }
            : {}),
        })

        setIsOpen(false)
      } catch (error) {
        console.error('[feedback] Send failed:', error)
        const description = error instanceof Error ? error.message : undefined

        toast.error(t('send_error'), {
          description,
        })
        // Modal stays open — no data loss
      } finally {
        setIsSending(false)
      }
    },
    [type, screenshot, t]
  )

  const value: FeedbackState = useMemo(() => ({
    isOpen,
    type,
    isSending,
    cooldownRemaining: 0,
    screenshot,
    screenshotError,
    isPreparingScreenshot: isCapturing,
    contextData,
    draftTitle,
    draftDescription,
    openWithType,
    close,
    setType,
    captureScreenshot: capture,
    send,
  }), [
    isOpen, type, isSending,
    screenshot, screenshotError, isCapturing,
    contextData, draftTitle, draftDescription,
    openWithType, close, setType, capture, send,
  ])

  return (
    <FeedbackContext.Provider value={value}>
      {children}
    </FeedbackContext.Provider>
  )
}
