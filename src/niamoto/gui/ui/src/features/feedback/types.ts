export type FeedbackType = 'bug' | 'suggestion' | 'question'

export interface ErrorEntry {
  message: string
  stack?: string
  timestamp: string
}

export interface FeedbackContext {
  app_version: string
  os: string
  current_page: string
  runtime_mode: string
  theme: string
  language: string
  window_size: string
  timestamp: string
  diagnostic?: Record<string, unknown>
  recent_errors?: ErrorEntry[]
}

export interface FeedbackPayload {
  type: FeedbackType
  title: string
  description?: string
  context: FeedbackContext
}

export interface FeedbackResponse {
  success: boolean
  issue_url?: string
  screenshot_uploaded: boolean
}

export class FeedbackError extends Error {
  readonly status: number
  readonly body: Record<string, unknown>

  constructor(status: number, body: Record<string, unknown>) {
    super(`Feedback error ${status}: ${JSON.stringify(body)}`)
    this.name = 'FeedbackError'
    this.status = status
    this.body = body
  }
}
