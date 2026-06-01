import { FeedbackError, type FeedbackPayload, type FeedbackResponse } from '../types'
import { apiFetch } from '@/shared/lib/api/fetch'

const FEEDBACK_PROXY_URL = '/api/feedback/submit'

interface FeedbackSubmission {
  payload: FeedbackPayload
  screenshot?: Blob | null
}

export async function sendFeedback({ payload, screenshot }: FeedbackSubmission): Promise<FeedbackResponse> {
  const formData = new FormData()
  formData.append('payload', JSON.stringify(payload))
  if (screenshot) {
    formData.append('screenshot', screenshot, 'feedback.jpg')
  }

  const response = await apiFetch(FEEDBACK_PROXY_URL, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'unknown' }))
    throw new FeedbackError(response.status, error as Record<string, unknown>)
  }

  return response.json() as Promise<FeedbackResponse>
}
