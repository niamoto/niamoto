// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CollectionDataOptionsResponse } from '@/features/collections/hooks/useCollectionDataOptions'

import { DataWorkspace } from './DataWorkspace'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const queryState = vi.hoisted(() => ({
  value: {
    data: undefined as CollectionDataOptionsResponse | undefined,
    isLoading: false,
    error: null as Error | null,
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const labels: Record<string, string> = {
        'common:status.loading': 'Loading',
        'collectionPanel.data.title': 'Data outputs',
        'collectionPanel.data.description':
          'Outputs for {{collection}}',
        'collectionPanel.data.collection': 'Collection',
        'collectionPanel.data.grain': 'Grain',
        'collectionPanel.data.source': 'Source',
        'collectionPanel.data.reviewStatus': 'Review',
        'collectionPanel.data.outputListTitle': 'Data outputs',
        'collectionPanel.data.outputListDescription': 'Outputs and formats',
        'collectionPanel.data.configuredTitle': 'Configured outputs',
        'collectionPanel.data.configuredDescription': 'Configured outputs description',
        'collectionPanel.data.availableTitle': 'Available output types',
        'collectionPanel.data.legacyTitle': 'Existing standard-like exports',
        'collectionPanel.data.recommendationTitle': 'Recommended output available',
        'collectionPanel.data.recommendationDescription': 'Review recommendation',
        'collectionPanel.data.enabled': 'Enabled',
        'collectionPanel.data.disabled': 'Disabled',
        'collectionPanel.data.confidence': '{{confidence}}% confidence',
        'collectionPanel.data.standardProfileSummary':
          '{{standard}} with {{mappedTerms}} terms and {{enabledOutputs}} outputs',
        'collectionPanel.data.simpleJsonSummary': 'Simple JSON summary',
        'collectionPanel.data.suitability.recommended': 'Recommended',
        'collectionPanel.data.actions.create_standard_profile':
          'Create standard profile',
        'collectionPanel.data.actions.edit_standard_profile':
          'Edit standard profile',
        'collectionPanel.data.reasonTitle': 'Why this option',
        'collectionPanel.data.evidenceTitle': 'Evidence',
        'collectionPanel.data.noEvidence': 'No evidence',
        'collections.standards.standardTypes.darwin_core_occurrence':
          'Darwin Core Occurrence',
        'collections.standards.validationStatus.conformant': 'Conformant',
        'collections.review.status.accepted': 'Accepted',
      }
      return (labels[key] ?? key)
        .replace('{{collection}}', String(options?.collection ?? ''))
        .replace('{{confidence}}', String(options?.confidence ?? ''))
        .replace('{{standard}}', String(options?.standard ?? ''))
        .replace('{{mappedTerms}}', String(options?.mappedTerms ?? ''))
        .replace('{{enabledOutputs}}', String(options?.enabledOutputs ?? ''))
    },
  }),
}))

vi.mock('@/features/collections/hooks/useCollectionDataOptions', () => ({
  useCollectionDataOptions: () => queryState.value,
}))

vi.mock('./DataOutputDetail', () => ({
  DataOutputDetail: (props: { output: { label: string } }) => (
    <section>Detail {props.output.label}</section>
  ),
}))

describe('DataWorkspace', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null
  let latestLocation = ''

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    container = null
    root = null
    queryState.value = {
      data: undefined,
      isLoading: false,
      error: null,
    }
    latestLocation = ''
  })

  async function renderWorkspace() {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={['/groups/occurrences?tab=data']}>
          <DataWorkspace collectionName="occurrences" />
          <LocationProbe onChange={(location) => {
            latestLocation = location
          }} />
        </MemoryRouter>,
      )
    })
  }

  it('surfaces configured collection outputs before available options', async () => {
    queryState.value = {
      data: {
        collection: {
          name: 'occurrences',
          label: 'Occurrences',
          grain: 'occurrence',
          roles: ['api', 'standard'],
          source: { type: 'dataset', name: 'occurrences' },
          review_status: 'accepted',
        },
        state: 'configured',
        configured_outputs: [
          {
            id: 'standard_profile:dwc_occurrences',
            kind: 'standard_profile',
            name: 'dwc_occurrences',
            label: 'dwc_occurrences',
            enabled: true,
            status: 'conformant',
            family: 'standard',
            source: { type: 'collection', name: 'occurrences' },
            standard: 'darwin_core_occurrence',
            target_grain: 'occurrence',
            validation_status: 'conformant',
            actions: [
              {
                type: 'edit_standard_profile',
                label: 'Edit standard profile',
                target: { profile_name: 'dwc_occurrences' },
              },
            ],
            evidence: [
              {
                kind: 'configured_standard_profile',
                message: 'A standard profile is configured.',
                confidence: 1,
                details: {},
              },
            ],
            summary: { mapped_terms: 15, enabled_outputs: 2 },
          },
        ],
        available_options: [
          {
            id: 'darwin_core_occurrence',
            family: 'standard',
            label: 'Darwin Core Occurrence',
            suitability: 'recommended',
            confidence: 1,
            standard: 'darwin_core_occurrence',
            target_grain: 'occurrence',
            reasons: ['Source is occurrence-grain data.'],
            missing_evidence: [],
            evidence: [],
            action: null,
          },
        ],
        primary_action: null,
        missing_evidence: [],
        sensitivity: { message: 'Review fields before publishing.' },
      },
      isLoading: false,
      error: null,
    }

    await renderWorkspace()

    expect(container?.textContent).toContain('Data outputs')
    expect(container?.textContent).toContain('dwc_occurrences')
    expect(container?.textContent).toContain('Darwin Core Occurrence with 15 terms and 2 outputs')
    expect(container?.textContent).toContain('Detail dwc_occurrences')
  })

  it('shows the primary recommendation when no output is configured', async () => {
    queryState.value = {
      data: {
        collection: {
          name: 'occurrences',
          label: 'Occurrences',
          grain: 'occurrence',
          roles: ['api', 'standard'],
          source: { type: 'dataset', name: 'occurrences' },
          review_status: 'accepted',
        },
        state: 'recommended',
        configured_outputs: [],
        available_options: [
          {
            id: 'simple_json',
            family: 'simple_json',
            label: 'Simple JSON',
            suitability: 'possible',
            confidence: 1,
            standard: null,
            target_grain: null,
            reasons: ['Simple collection API is available.'],
            missing_evidence: [],
            evidence: [],
            action: {
              type: 'create_api_output',
              label: 'Create simple JSON',
              target: {
                collection: 'occurrences',
                template: 'simple',
              },
            },
          },
          {
            id: 'darwin_core_occurrence',
            family: 'standard',
            label: 'Darwin Core Occurrence',
            suitability: 'recommended',
            confidence: 0.95,
            standard: 'darwin_core_occurrence',
            target_grain: 'occurrence',
            reasons: ['Source is occurrence-grain data.'],
            missing_evidence: [],
            evidence: [],
            action: {
              type: 'create_standard_profile',
              label: 'Create Darwin Core Occurrence',
              target: {
                collection: 'occurrences',
                standard: 'darwin_core_occurrence',
                target_grain: 'occurrence',
              },
            },
          },
        ],
        primary_action: {
          type: 'create_standard_profile',
          label: 'Create Darwin Core Occurrence',
          target: {
            collection: 'occurrences',
            standard: 'darwin_core_occurrence',
            target_grain: 'occurrence',
          },
        },
        missing_evidence: [],
        sensitivity: {},
      },
      isLoading: false,
      error: null,
    }

    await renderWorkspace()

    expect(container?.textContent).toContain('Recommended output available')
    expect(container?.textContent).toContain('Create standard profile')
    expect(container?.querySelector('article')?.textContent).toContain(
      'Darwin Core Occurrence',
    )
    expect(container?.querySelector('article')?.textContent).toContain('95% confidence')

    await act(async () => {
      const button = Array.from(container!.querySelectorAll('button')).find((item) =>
        item.textContent?.includes('Create standard profile'),
      )
      button?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(latestLocation).toBe(
      '/groups/occurrences?data_action=create_standard_profile&collection=occurrences&standard=darwin_core_occurrence&target_grain=occurrence&tab=standards',
    )
  })
})

function LocationProbe({ onChange }: { onChange: (location: string) => void }) {
  const location = useLocation()
  onChange(`${location.pathname}${location.search}`)
  return null
}
