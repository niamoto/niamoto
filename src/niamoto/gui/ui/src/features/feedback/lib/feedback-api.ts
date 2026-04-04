import { FeedbackError, type FeedbackPayload, type FeedbackResponse } from '../types'

const WORKER_URL = import.meta.env.VITE_FEEDBACK_WORKER_URL || ''
const API_KEY = import.meta.env.VITE_FEEDBACK_API_KEY || ''

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

  const response = await fetch(`${WORKER_URL}/feedback`, {
    method: 'POST',
    headers: {
      'X-Feedback-Key': API_KEY,
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'unknown' }))
    throw new FeedbackError(response.status, error as Record<string, unknown>)
  }

  return response.json() as Promise<FeedbackResponse>
}
