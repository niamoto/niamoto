import type {
  CollectionDataAction,
  CollectionDataConfiguredOutput,
  CollectionDataOption,
} from '@/features/collections/hooks/useCollectionDataOptions'
import type { CollectionTab } from '@/features/collections/routing'

type Translate = (key: string, options?: Record<string, unknown>) => string

export function tabForDataAction(
  action: CollectionDataAction | null | undefined,
): CollectionTab | null {
  if (!action) {
    return null
  }
  if (action.type.includes('standard')) {
    return 'standards'
  }
  if (action.type.includes('api')) {
    return 'api'
  }
  return null
}

export function dataActionLabel(
  action: CollectionDataAction | null | undefined,
  t: Translate,
) {
  if (!action) {
    return ''
  }
  const key = `collectionPanel.data.actions.${action.type}`
  const translated = t(key)
  return translated === key ? action.label : translated
}

export function configuredOutputSummary(
  output: CollectionDataConfiguredOutput,
  t: Translate,
) {
  if (output.kind === 'standard_profile') {
    return t('collectionPanel.data.standardProfileSummary', {
      standard: standardOutputLabel(output, t),
      mappedTerms: String(output.summary.mapped_terms ?? 0),
      enabledOutputs: String(output.summary.enabled_outputs ?? 0),
    })
  }

  if (output.kind === 'legacy_standard_hint') {
    return t('collectionPanel.data.legacySummary', {
      standard: standardOutputLabel(output, t),
    })
  }

  return t('collectionPanel.data.simpleJsonSummary')
}

export function outputStatusLabel(
  output: CollectionDataConfiguredOutput,
  t: Translate,
) {
  if (output.validation_status) {
    const key = `collections.standards.validationStatus.${output.validation_status}`
    const translated = t(key)
    return translated === key ? output.validation_status : translated
  }
  const key = `collectionPanel.data.status.${output.status}`
  const translated = t(key)
  return translated === key ? output.status : translated
}

export function standardOutputLabel(
  output: Pick<CollectionDataConfiguredOutput, 'standard'>,
  t: Translate,
) {
  if (!output.standard) {
    return t('collectionPanel.data.standardFallback')
  }
  const key = `collections.standards.standardTypes.${output.standard}`
  const translated = t(key)
  return translated === key ? output.standard : translated
}

export function suitabilityBadgeVariant(
  suitability: CollectionDataOption['suitability'],
) {
  if (suitability === 'recommended') {
    return 'success'
  }
  if (suitability === 'not_recommended') {
    return 'secondary'
  }
  return 'outline'
}
