type Translate = (key: string, options?: Record<string, unknown>) => string

export function formatAutoConfigReviewText(text: string, t: Translate) {
  return text
    .replace(
      /Reference enriched with measurements or geometry; ML also saw dataset-like signals \(([^)]+)\)\./g,
      (_match, confidence: string) =>
        t('autoConfig.reviewReasons.referenceEnrichedDatasetSignals', {
          confidence,
        })
    )
    .replace(
      /ML suggests ([^(]+) \(([^)]+)\) while final decision is ([^.]+)\./g,
      (_match, mlEntityType: string, confidence: string, finalEntityType: string) =>
        t('autoConfig.reviewReasons.mlSuggestsDifferentRole', {
          mlEntityType,
          confidence,
          finalEntityType,
        })
    )
    .replace(
      /Heuristic confidence is low for this file\./g,
      () => t('autoConfig.reviewReasons.lowHeuristicConfidence')
    )
    .replace(
      /Observation-like signals were detected, but the file still behaves like an enriched reference\./g,
      () => t('autoConfig.reviewReasons.observationSignalsInEnrichedReference')
    )
    .replace(
      /Observation-like signals were detected in a file classified as reference\./g,
      () => t('autoConfig.reviewReasons.observationSignalsInReference')
    )
    .replace(
      /The file looks hierarchy-heavy for a dataset; taxonomy extraction should be checked\./g,
      () => t('autoConfig.reviewReasons.hierarchyHeavyDataset')
    )
    .replace(
      /Referenced by another entity and kept as a dataset\./g,
      () => t('autoConfig.reviewReasons.referencedByEntityKeptDataset')
    )
    .replace(
      /ML found observation-oriented signals such as measurements, time, or geometry\./g,
      () => t('autoConfig.reviewReasons.mlObservationSignals')
    )
}
