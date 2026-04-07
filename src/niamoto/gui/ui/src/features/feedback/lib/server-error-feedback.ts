import { toast } from 'sonner'

import i18n from '@/i18n'
import { requestBugReport } from './bug-report-bridge'

const DEDUPE_WINDOW_MS = 15_000
const recentPrompts = new Map<string, number>()

function buildPromptKey(path: string, detail: string): string {
  return `${path}::${detail}`
}

function shouldPrompt(key: string): boolean {
  const now = Date.now()

  for (const [entryKey, timestamp] of recentPrompts.entries()) {
    if (now - timestamp > DEDUPE_WINDOW_MS) {
      recentPrompts.delete(entryKey)
    }
  }

  const previous = recentPrompts.get(key)
  if (previous && now - previous < DEDUPE_WINDOW_MS) {
    return false
  }

  recentPrompts.set(key, now)
  return true
}

export function normalizeApiErrorPath(url?: string): string {
  if (!url) return '/api'

  if (url.startsWith('/')) return url

  try {
    return new URL(url).pathname || '/api'
  } catch {
    return url
  }
}

export function promptServerErrorBugReport(
  url?: string,
  detail?: string
): void {
  const path = normalizeApiErrorPath(url)
  const normalizedDetail = detail?.trim() || ''
  const key = buildPromptKey(path, normalizedDetail)

  if (!shouldPrompt(key)) {
    return
  }

  toast.error(i18n.t('feedback:server_error_toast_title'), {
    description:
      normalizedDetail || i18n.t('feedback:server_error_toast_description'),
    action: {
      label: i18n.t('feedback:report_bug_cta'),
      onClick: () => {
        requestBugReport({
          title: i18n.t('feedback:prefill_server_error_title', { path }),
          description: normalizedDetail
            ? i18n.t('feedback:prefill_server_error_description_with_detail', {
                path,
                detail: normalizedDetail,
              })
            : i18n.t('feedback:prefill_server_error_description', { path }),
        })
      },
    },
  })
}

export function resetServerErrorFeedbackForTests(): void {
  recentPrompts.clear()
}
