export function shouldUseCandidateApplyPath(
  selectedSuggestionIds: string[],
  candidateSuggestionIds: Set<string>,
  customizedSuggestionIds: Set<string> = new Set(),
): boolean {
  return (
    selectedSuggestionIds.length > 0 &&
    selectedSuggestionIds.every((suggestionId) =>
      candidateSuggestionIds.has(suggestionId),
    ) &&
    selectedSuggestionIds.every(
      (suggestionId) => !customizedSuggestionIds.has(suggestionId),
    )
  )
}
