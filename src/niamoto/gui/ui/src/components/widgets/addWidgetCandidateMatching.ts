import type { WidgetCandidate } from '@/features/collections/api/widget-candidates'
import type { TemplateSuggestion } from './types'

export function candidateMatchesSuggestion(
  candidate: WidgetCandidate,
  suggestion: TemplateSuggestion,
): boolean {
  const sameTitle = normalizeMatchText(candidate.title) === normalizeMatchText(suggestion.name)
  if (sameTitle && titleMatchCanUseCandidate(candidate, suggestion)) return true

  const sameTransformer = candidate.transformer_plugin === suggestion.plugin
  const sameWidget = !candidate.widget_plugin || candidate.widget_plugin === suggestion.widget_plugin
  const sameField =
    !suggestion.matched_column ||
    candidate.source_fields.length === 0 ||
    candidate.source_fields.includes(suggestion.matched_column)

  if (sameTransformer && sameWidget && sameField) return true

  return (
    candidate.origin === 'class_object' &&
    suggestion.source === 'class_object' &&
    sameTransformer &&
    sameField &&
    candidate.source_name === suggestion.source_name
  )
}

function titleMatchCanUseCandidate(
  candidate: WidgetCandidate,
  suggestion: TemplateSuggestion,
): boolean {
  const classObjectInvolved =
    candidate.origin === 'class_object' || suggestion.source === 'class_object'
  if (!classObjectInvolved) return true

  return (
    candidate.origin === 'class_object' &&
    suggestion.source === 'class_object' &&
    candidate.transformer_plugin === suggestion.plugin &&
    candidate.source_name === suggestion.source_name &&
    (
      !suggestion.matched_column ||
      candidate.source_fields.length === 0 ||
      candidate.source_fields.includes(suggestion.matched_column)
    )
  )
}

function normalizeMatchText(value: string | null | undefined): string {
  return (value || '')
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}
