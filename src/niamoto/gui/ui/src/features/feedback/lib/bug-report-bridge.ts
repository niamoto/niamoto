export interface BugReportDraft {
  title: string
  description?: string
}

type BugReportListener = (draft: BugReportDraft) => void

const listeners = new Set<BugReportListener>()

export function subscribeToBugReportRequests(
  listener: BugReportListener
): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function requestBugReport(draft: BugReportDraft): void {
  for (const listener of listeners) {
    listener(draft)
  }
}
