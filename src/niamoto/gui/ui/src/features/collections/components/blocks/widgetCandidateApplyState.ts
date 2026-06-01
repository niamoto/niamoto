import type {
  WidgetCandidateApplyResponse,
  WidgetCandidatePreviewResponse,
} from '@/features/collections/api/widget-candidates'

export function candidatePreviewFromApplyResponse(
  previousPreview: WidgetCandidatePreviewResponse,
  response: WidgetCandidateApplyResponse,
): WidgetCandidatePreviewResponse {
  const changes = [...response.applied, ...response.skipped]
  const nextChanges = changes.length > 0 ? changes : previousPreview.changes

  return {
    collection: response.collection,
    writes_files: false,
    preview_token: response.preview_token ?? previousPreview.preview_token,
    changes: nextChanges,
    conflicts: nextChanges.filter((change) => change.action === 'conflict'),
    invalid: nextChanges.filter((change) => change.action === 'invalid'),
  }
}
