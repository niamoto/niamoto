import { FeedbackError, type FeedbackPayload, type FeedbackResponse } from '../types'

const WORKER_URL = import.meta.env.VITE_FEEDBACK_WORKER_URL || ''
const API_KEY = import.meta.env.VITE_FEEDBACK_API_KEY || ''
const FEEDBACK_PROXY_URL = '/api/feedback/submit'

interface FeedbackSubmission {
  payload: FeedbackPayload
  screenshot?: Blob | null
}

export async function sendFeedback({ payload, screenshot }: FeedbackSubmission): Promise<FeedbackResponse> {
  const workerUrl = WORKER_URL.trim()
  const apiKey = API_KEY.trim()

  if (!workerUrl) {
    throw new Error("Feedback endpoint not configured in this build.")
  }

  if (!apiKey) {
    throw new Error("Feedback API key not configured in this build.")
  }

  const formData = new FormData()
  formData.append('payload', JSON.stringify(payload))
  formData.append('worker_url', workerUrl)
  formData.append('api_key', apiKey)
  if (screenshot) {
    formData.append('screenshot', screenshot, 'feedback.jpg')
  }

  const response = await fetch(FEEDBACK_PROXY_URL, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'unknown' }))
    throw new FeedbackError(response.status, error as Record<string, unknown>)
  }

  return response.json() as Promise<FeedbackResponse>
}
