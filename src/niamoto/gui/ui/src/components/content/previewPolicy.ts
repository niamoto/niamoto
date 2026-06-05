type CollectionsPreviewMode = 'off' | 'thumbnail'

export function resolveCollectionsPreviewMode({
  isDragging,
}: {
  isDragging?: boolean
} = {}): CollectionsPreviewMode {
  if (isDragging) {
    return 'off'
  }

  return 'thumbnail'
}

export function shouldAutoRefreshCollectionsDetailPreview(): boolean {
  return true
}
