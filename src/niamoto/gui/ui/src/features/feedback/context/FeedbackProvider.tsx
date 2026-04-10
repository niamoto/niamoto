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
import { useScreenshot } from '../hooks/useScreenshot'
import { useContextData } from '../hooks/useContextData'
import { sendFeedback } from '../lib/feedback-api'
import {
  subscribeToBugReportRequests,
  type BugReportDraft,
} from '../lib/bug-report-bridge'
import { FeedbackError, type FeedbackType, type FeedbackContext } from '../types'
import { FeedbackContext, type FeedbackState } from './feedbackContext'

const COOLDOWN_SECONDS = 30

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation('feedback')
  const [isOpen, setIsOpen] = useState(false)
  const [type, setType] = useState<FeedbackType>('bug')
  const [isSending, setIsSending] = useState(false)
  const [cooldownEnd, setCooldownEnd] = useState<number | null>(null)
  const [cooldownRemaining, setCooldownRemaining] = useState(0)
  const [contextData, setContextData] = useState<FeedbackContext | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftDescription, setDraftDescription] = useState('')

  const { screenshot, isCapturing, error: screenshotError, capture, clear } = useScreenshot()
  const { collect } = useContextData()

  // Cooldown timer
  useEffect(() => {
    if (!cooldownEnd) {
      setCooldownRemaining(0)
      return
    }
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((cooldownEnd - Date.now()) / 1000))
      setCooldownRemaining(remaining)
      if (remaining <= 0) setCooldownEnd(null)
    }
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [cooldownEnd])

  // Ref for cooldown check in callbacks
  const cooldownEndRef = useRef(cooldownEnd)
  cooldownEndRef.current = cooldownEnd

  const openDraft = useCallback(
    async (nextType: FeedbackType = 'bug', draft?: BugReportDraft) => {
      // Block if cooldown is active
      if (cooldownEndRef.current && Date.now() < cooldownEndRef.current) return

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
      // Block if cooldown is active
      if (cooldownEndRef.current && Date.now() < cooldownEndRef.current) return

      setIsSending(true)
      try {
        await sendFeedback({
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
        })

        setIsOpen(false)
        setCooldownEnd(Date.now() + COOLDOWN_SECONDS * 1000)
      } catch (error) {
        console.error('[feedback] Send failed:', error)
        const description = error instanceof Error ? error.message : undefined

        if (error instanceof FeedbackError) {
          if (error.status === 429) {
            toast.error(t('rate_limited'))
          } else {
            toast.error(t('send_error'), {
              description,
            })
          }
        } else {
          toast.error(t('send_error'), {
            description,
          })
        }
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
    cooldownRemaining,
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
    isOpen, type, isSending, cooldownRemaining,
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
