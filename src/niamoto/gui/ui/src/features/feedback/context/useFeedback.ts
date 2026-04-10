import { useContext } from 'react'

import { FeedbackContext, type FeedbackState } from './feedbackContext'

export function useFeedback(): FeedbackState {
  const context = useContext(FeedbackContext)
  if (!context) {
    throw new Error('useFeedback must be used within a FeedbackProvider')
  }
  return context
}
