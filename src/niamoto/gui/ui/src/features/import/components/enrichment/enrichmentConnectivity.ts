export type EnrichmentAvailability =
  | 'unknown'
  | 'checking'
  | 'available'
  | 'unavailable'

export function shouldShowEnrichmentConnectivityWarning({
  enrichmentAvailability,
  jobStatus,
  jobLoadingScope,
}: {
  enrichmentAvailability: EnrichmentAvailability
  jobStatus?: string | null
  jobLoadingScope?: string | null
}) {
  if (enrichmentAvailability !== 'unavailable') {
    return false
  }

  return (
    jobStatus !== 'paused_offline' &&
    jobStatus !== 'running' &&
    jobLoadingScope === null
  )
}
