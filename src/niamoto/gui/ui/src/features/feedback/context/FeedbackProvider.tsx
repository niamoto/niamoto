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
import { downloadFeedbackReport, sendFeedback } from '../lib/feedback-api'
import {
  subscribeToBugReportRequests,
  type BugReportDraft,
} from '../lib/bug-report-bridge'
import {
  type FeedbackType,
  type FeedbackContext as FeedbackContextData,
  type FeedbackResponse,
} from '../types'
import {
  FeedbackContext,
  type FeedbackReportDownloadState,
  type FeedbackState,
} from './feedbackContext'

const IDLE_DOWNLOAD_STATE: FeedbackReportDownloadState = { status: 'idle' }

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation('feedback')
  const [isOpen, setIsOpen] = useState(false)
  const [type, setType] = useState<FeedbackType>('bug')
  const [isSending, setIsSending] = useState(false)
  const [contextData, setContextData] = useState<FeedbackContextData | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftDescription, setDraftDescription] = useState('')
  const [generatedReport, setGeneratedReport] = useState<FeedbackResponse | null>(null)
  const [reportDownloadState, setReportDownloadState] =
    useState<FeedbackReportDownloadState>(IDLE_DOWNLOAD_STATE)

  const { screenshot, isCapturing, error: screenshotError, capture, clear } = useScreenshot()
  const { collect } = useContextData()

  const openDraft = useCallback(
    async (nextType: FeedbackType = 'bug', draft?: BugReportDraft) => {
      setType(nextType)
      setDraftTitle(draft?.title ?? '')
      setDraftDescription(draft?.description ?? '')
      setGeneratedReport(null)
      setReportDownloadState(IDLE_DOWNLOAD_STATE)

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
    setGeneratedReport(null)
    setReportDownloadState(IDLE_DOWNLOAD_STATE)
  }, [])

  const updateType = useCallback((nextType: FeedbackType) => {
    setGeneratedReport(null)
    setReportDownloadState(IDLE_DOWNLOAD_STATE)
    setType(nextType)
  }, [])

  const clearGeneratedReport = useCallback(() => {
    setGeneratedReport(null)
    setReportDownloadState(IDLE_DOWNLOAD_STATE)
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
      setGeneratedReport(null)
      setReportDownloadState(IDLE_DOWNLOAD_STATE)
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

        setGeneratedReport(result)
        setReportDownloadState(IDLE_DOWNLOAD_STATE)
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

  const downloadGeneratedReport = useCallback(async () => {
    if (!generatedReport || reportDownloadState.status === 'saving') return

    setReportDownloadState({ status: 'saving' })
    try {
      const result = await downloadFeedbackReport(generatedReport)
      setReportDownloadState(result)
    } catch (error) {
      console.error('[feedback] Report download failed:', error)
      const description = error instanceof Error ? error.message : undefined
      setReportDownloadState({
        status: 'error',
        filename: generatedReport.report_filename,
        message: description,
      })
      toast.error(t('download_error'), {
        description,
      })
    }
  }, [generatedReport, reportDownloadState.status, t])

  const openGeneratedReportIssue = useCallback(() => {
    if (!generatedReport?.github_issue_url) return
    void openExternalUrl(generatedReport.github_issue_url)
  }, [generatedReport])

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
    generatedReport,
    reportDownloadState,
    openWithType,
    close,
    setType: updateType,
    captureScreenshot: capture,
    send,
    clearGeneratedReport,
    downloadGeneratedReport,
    openGeneratedReportIssue,
  }), [
    isOpen, type, isSending,
    screenshot, screenshotError, isCapturing,
    contextData, draftTitle, draftDescription, generatedReport,
    reportDownloadState,
    openWithType, close, updateType, capture, send,
    clearGeneratedReport, downloadGeneratedReport, openGeneratedReportIssue,
  ])

  return (
    <FeedbackContext.Provider value={value}>
      {children}
    </FeedbackContext.Provider>
  )
}
