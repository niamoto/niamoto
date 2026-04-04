import {
  createContext,
  useContext,
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
import { FeedbackError, type FeedbackType, type FeedbackContext } from '../types'

const COOLDOWN_SECONDS = 30

interface FeedbackState {
  isOpen: boolean
  type: FeedbackType
  isSending: boolean
  cooldownRemaining: number
  screenshot: Blob | null
  screenshotError: boolean
  isPreparingScreenshot: boolean
  contextData: FeedbackContext | null
  openWithType: (type?: FeedbackType) => Promise<void>
  close: () => void
  setType: (type: FeedbackType) => void
  captureScreenshot: () => Promise<void>
  send: (title: string, description: string, includeScreenshot: boolean) => Promise<void>
}

const FeedbackContext = createContext<FeedbackState | null>(null)

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation('feedback')
  const [isOpen, setIsOpen] = useState(false)
  const [type, setType] = useState<FeedbackType>('bug')
  const [isSending, setIsSending] = useState(false)
  const [cooldownEnd, setCooldownEnd] = useState<number | null>(null)
  const [cooldownRemaining, setCooldownRemaining] = useState(0)
  const [contextData, setContextData] = useState<FeedbackContext | null>(null)

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

  const openWithType = useCallback(
    async (nextType: FeedbackType = 'bug') => {
      // Block if cooldown is active
      if (cooldownEndRef.current && Date.now() < cooldownEndRef.current) return

      setType(nextType)

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

  const close = useCallback(() => {
    setIsOpen(false)
  }, [])

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
          action: result.issue_url
            ? {
                label: t('view_issue'),
                onClick: () => window.open(result.issue_url, '_blank'),
              }
            : undefined,
        })

        setIsOpen(false)
        setCooldownEnd(Date.now() + COOLDOWN_SECONDS * 1000)
      } catch (error) {
        if (error instanceof FeedbackError) {
          if (error.status === 429) {
            toast.error(t('rate_limited'))
          } else {
            toast.error(t('send_error'))
          }
        } else {
          toast.error(t('send_error'))
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
    openWithType,
    close,
    setType,
    captureScreenshot: capture,
    send,
  }), [
    isOpen, type, isSending, cooldownRemaining,
    screenshot, screenshotError, isCapturing,
    contextData, openWithType, close, setType, capture, send,
  ])

  return (
    <FeedbackContext.Provider value={value}>
      {children}
    </FeedbackContext.Provider>
  )
}

export function useFeedback(): FeedbackState {
  const context = useContext(FeedbackContext)
  if (!context) {
    throw new Error('useFeedback must be used within a FeedbackProvider')
  }
  return context
}
