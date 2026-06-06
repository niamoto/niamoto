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
  screen_size?: string
  timestamp: string
  uptime?: string
  memory?: string
  backend_status?: string
  diagnostic?: Record<string, unknown>
  recent_errors?: ErrorEntry[]
  navigation_history?: Array<{ path: string; timestamp: string }>
  failed_requests?: Array<{ url: string; status: number; duration: number; timestamp: string }>
  crashes?: Array<{
    component: string
    error: string
    component_stack?: string[]
    timestamp: string
  }>
  state_snapshot?: Record<string, unknown>
}

export interface FeedbackPayload {
  type: FeedbackType
  title: string
  description?: string
  context: FeedbackContext
}

export interface FeedbackReport {
  report_format: 'markdown'
  report_filename: string
  report_content: string
  screenshot_included: boolean
  github_issue_url?: string
}

export interface FeedbackResponse extends FeedbackReport {
  success: boolean
  report_downloaded: boolean
}
