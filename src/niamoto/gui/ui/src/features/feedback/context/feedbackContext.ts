import { createContext } from 'react'

import type { FeedbackContext, FeedbackType } from '../types'

export interface FeedbackState {
  isOpen: boolean
  type: FeedbackType
  isSending: boolean
  cooldownRemaining: number
  screenshot: Blob | null
  screenshotError: boolean
  isPreparingScreenshot: boolean
  contextData: FeedbackContext | null
  draftTitle: string
  draftDescription: string
  openWithType: (type?: FeedbackType) => Promise<void>
  close: () => void
  setType: (type: FeedbackType) => void
  captureScreenshot: () => Promise<void>
  send: (title: string, description: string, includeScreenshot: boolean) => Promise<void>
}

export const FeedbackContext = createContext<FeedbackState | null>(null)
