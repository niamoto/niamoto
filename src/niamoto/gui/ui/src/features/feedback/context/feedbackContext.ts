import { createContext } from 'react'

import type {
  FeedbackContext as FeedbackContextData,
  FeedbackResponse,
  FeedbackType,
} from '../types'

export type FeedbackReportDownloadState =
  | { status: 'idle' }
  | { status: 'saving' }
  | { status: 'saved'; filename: string; path?: string }
  | { status: 'downloaded'; filename: string }
  | { status: 'cancelled'; filename: string }
  | { status: 'error'; filename?: string; message?: string }

export interface FeedbackState {
  isOpen: boolean
  type: FeedbackType
  isSending: boolean
  cooldownRemaining: number
  screenshot: Blob | null
  screenshotError: boolean
  isPreparingScreenshot: boolean
  contextData: FeedbackContextData | null
  draftTitle: string
  draftDescription: string
  generatedReport: FeedbackResponse | null
  reportDownloadState: FeedbackReportDownloadState
  openWithType: (type?: FeedbackType) => Promise<void>
  close: () => void
  setType: (type: FeedbackType) => void
  captureScreenshot: () => Promise<void>
  send: (title: string, description: string, includeScreenshot: boolean) => Promise<void>
  clearGeneratedReport: () => void
  downloadGeneratedReport: () => Promise<void>
  openGeneratedReportIssue: () => void
}

export const FeedbackContext = createContext<FeedbackState | null>(null)
