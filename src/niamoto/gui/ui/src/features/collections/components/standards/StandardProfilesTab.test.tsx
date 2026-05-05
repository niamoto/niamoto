// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { StandardProfilesTab } from './StandardProfilesTab'

const profilesState = vi.hoisted(() => ({
  profiles: [] as Array<{
    name: string
    enabled: boolean
    standard: string
    target_grain: string
    source: { type: string; name: string }
    mappings: Record<string, unknown>
    outputs: Array<{ type: string; enabled: boolean; params: Record<string, unknown> }>
    validation_status: string
    metadata: Record<string, unknown>
  }>,
}))

const mutations = vi.hoisted(() => ({
  create: vi.fn(),
  update: vi.fn(),
}))

const defaultProfiles = [
  {
    name: 'dwc_taxon_context',
    enabled: true,
    standard: 'darwin_core_occurrence',
    target_grain: 'occurrence',
    source: { type: 'collection', name: 'taxons' },
    mappings: { occurrenceID: { source: 'id' } },
    outputs: [{ type: 'api_json', enabled: true, params: {} }],
    validation_status: 'partial',
    metadata: {},
  },
  {
    name: 'dwc_occurrences',
    enabled: true,
    standard: 'darwin_core_occurrence',
    target_grain: 'occurrence',
    source: { type: 'dataset', name: 'occurrences' },
    mappings: { occurrenceID: { source: 'id' } },
    outputs: [{ type: 'api_json', enabled: true, params: {} }],
    validation_status: 'conformant',
    metadata: {},
  },
]

profilesState.profiles = defaultProfiles

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const labels: Record<string, string> = {
        'collections.standards.title': 'Standard profiles',
        'collections.standards.description': 'Configure publication profiles.',
        'collections.standards.newProfile': 'New profile',
        'collections.standards.empty': 'No standard profile is configured yet.',
        'collections.standards.editProfileAction': 'Edit profile',
        'collections.standards.profileOverview': 'Profile overview',
        'collections.standards.profileOverviewHelp': 'Profile is saved.',
        'collections.standards.mappedTermsCount': '{{count}} mapped terms',
        'collections.standards.enabledOutputsCount': '{{count}} enabled outputs',
        'collections.standards.standardTypes.darwin_core_occurrence':
          'Darwin Core Occurrence',
        'collections.standards.validationStatus.partial': 'Partial',
        'collections.standards.currentCollection': 'Current collection',
        'collections.standards.selectedProfileStatus': 'Selected profile status',
        'collections.standards.sourceSummary': '{{type}} · {{name}}',
        'collections.standards.compatibility': 'Compatibility',
        'collections.standards.compatibilityStatus.compatible': 'Compatible',
        'collections.standards.grainSummary':
          'Source grain: {{source}} · Target grain: {{target}}',
        'collections.standards.validation': 'Validation',
        'collections.standards.validationStatus.conformant': 'Conformant',
        'collections.standards.outputs': 'Outputs',
        'collections.standards.outputTypes.api_json': 'Profile API JSON',
        'collections.standards.outputEnabled': 'Enabled',
        'collections.standards.generateDraftJson': 'Generate draft JSON',
        'collections.standards.generateDraftOutput': 'Generate test files',
        'collections.standards.testOutput': 'Test output',
        'collections.standards.publicationOutput': 'Publication output',
        'collections.standards.draftRetention': 'Draft retention {{location}}',
        'collections.standards.outputJsonPreview': 'Representative JSON preview',
        'collections.standards.outputJsonPreviewItem': 'Source record {{id}}',
        'collections.standards.outputJsonPreviewLoading': 'Loading preview',
        'collections.standards.outputJsonPreviewFailed': 'Could not load preview.',
        'collections.standards.hiddenSource': 'hidden or technical',
        'collections.standards.legacyHintsTitle': 'Existing standard-like exports',
        'collections.standards.legacyHintDescription':
          'Existing export "{{exportName}}" looks like {{standard}} output.',
        'collections.standards.editProfile': 'Profile settings',
        'collections.standards.profileEditorHelp': 'Profile help',
        'collections.standards.profileName': 'Profile name',
        'collections.standards.standard': 'Standard',
        'collections.standards.source': 'Source data',
        'collections.standards.targetGrain': 'Target grain',
        'collections.standards.mappingTitle': 'Standard term mappings',
        'collections.standards.mappingHelp': 'Map terms.',
        'collections.standards.mappingReferenceHelp': 'Mapping help.',
        'collections.standards.autoConfigure': 'Auto-configure',
        'collections.standards.autoConfigureHelp': 'Build a draft.',
        'collections.standards.saveProfile': 'Save profile',
      }
      return (labels[key] ?? key)
        .replace('{{type}}', String(options?.type ?? ''))
        .replace('{{name}}', String(options?.name ?? ''))
        .replace('{{source}}', String(options?.source ?? ''))
        .replace('{{target}}', String(options?.target ?? ''))
        .replace('{{exportName}}', String(options?.exportName ?? ''))
        .replace('{{standard}}', String(options?.standard ?? ''))
        .replace('{{count}}', String(options?.count ?? ''))
        .replace('{{id}}', String(options?.id ?? ''))
    },
  }),
}))

vi.mock('@/features/collections/components/api/DwcMappingEditor', () => ({
  DwcMappingEditor: () => <div>Standard term mappings</div>,
}))

vi.mock('@/features/collections/hooks/useCollectionsCatalog', () => ({
  useCollectionsCatalog: () => ({
    data: {
      collections: [
        {
          name: 'taxons',
          label: 'taxons',
          source_type: 'reference',
          source_name: 'taxons',
          roles: ['site', 'api'],
          visible: true,
        },
        {
          name: 'technical_occurrences',
          label: 'technical_occurrences',
          source_type: 'dataset',
          source_name: 'occurrences',
          roles: ['technical', 'standard'],
          visible: false,
        },
        {
          name: 'occurrences_publication',
          label: 'Occurrences publication',
          source_type: 'dataset',
          source_name: 'occurrences',
          roles: ['standard'],
          visible: true,
        },
      ],
      sources: [{ type: 'dataset', name: 'occurrences', label: 'occurrences' }],
      total: 2,
    },
  }),
}))

vi.mock('@/features/collections/hooks/useStandardProfiles', () => ({
  useStandardProfiles: () => ({
    data: {
      profiles: profilesState.profiles,
      legacy_hints: [
        {
          export_name: 'legacy_json_api',
          standard: 'darwin_core_occurrence',
          message: 'Legacy Darwin Core-like output.',
          source: { type: 'collection', name: 'taxons' },
        },
        {
          export_name: 'legacy_occurrences_json_api',
          standard: 'darwin_core_occurrence',
          message: 'Legacy Darwin Core-like output.',
          source: { type: 'dataset', name: 'occurrences' },
        },
      ],
      total: profilesState.profiles.length,
    },
    isLoading: false,
    error: null,
  }),
  useStandardProfileCompatibility: () => ({
    data: {
      standard: 'darwin_core_occurrence',
      target_grain: 'occurrence',
      source: { type: 'collection', name: 'taxons' },
      source_grain: 'taxon',
      status: 'compatible',
      confidence: 0.82,
      evidence: [],
      warnings: [],
      blockers: [],
    },
    isLoading: false,
    error: null,
  }),
  useStandardProfileValidation: () => ({
    data: {
      profile_name: 'dwc_taxon_context',
      standard: 'darwin_core_occurrence',
      status: 'conformant',
      summary: { critical: 0, warning: 0, recommended: 0, info: 0 },
      compatibility: {
        standard: 'darwin_core_occurrence',
        target_grain: 'occurrence',
        source: { type: 'collection', name: 'taxons' },
        source_grain: 'taxon',
        status: 'compatible',
        confidence: 0.82,
        evidence: [],
        warnings: [],
        blockers: [],
      },
      checklist: [],
      issues: [],
    },
    isLoading: false,
    error: null,
  }),
  useCreateStandardProfile: () => ({
    isPending: false,
    mutateAsync: mutations.create,
  }),
  useAutoConfigureStandardProfile: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
  useStandardProfileSourceFields: () => ({
    data: {
      fields: [{ name: 'id' }, { name: 'taxon_id' }],
    },
  }),
  useUpdateStandardProfile: () => ({
    isPending: false,
    mutateAsync: mutations.update,
  }),
  useExecuteStandardProfileOutput: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
  useExecuteStandardProfileOutputDraft: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
  useStandardProfileOutputPreview: () => ({
    data: {
      item_id: 1,
      preview: {
        metadata: { profile_name: 'dwc_taxon_context' },
        records: [{ occurrenceID: 1 }],
      },
    },
    isLoading: false,
    isFetching: false,
    error: null,
  }),
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

describe('StandardProfilesTab', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  beforeEach(() => {
    profilesState.profiles = defaultProfiles
    mutations.create.mockReset()
    mutations.update.mockReset()
  })

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    root = null
    container = null
  })

  async function renderTab(
    collectionName = 'taxons',
    initialEntry = '/groups/taxons?tab=standards',
  ) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter initialEntries={[initialEntry]}>
          <StandardProfilesTab collectionName={collectionName} />
        </MemoryRouter>,
      )
    })
  }

  it('shows Darwin Core Occurrence as an occurrence-grain profile contextualized by taxons', async () => {
    await renderTab()

    expect(container?.textContent).toContain('dwc_taxon_context')
    expect(container?.textContent).not.toContain('dwc_occurrences')
    expect(container?.textContent).toContain('Darwin Core Occurrence')
    expect(container?.textContent).toContain('Source grain: taxon · Target grain: occurrence')
    expect(container?.textContent).toContain('Profile overview')
    expect(container?.textContent).toContain('Edit profile')
    expect(container?.textContent).not.toContain('Static API exports')
    expect(container?.textContent).toContain('Existing standard-like exports')
    expect(container?.textContent).toContain('legacy_json_api')
    expect(container?.textContent).toContain(
      'Existing export "legacy_json_api" looks like Darwin Core Occurrence output.',
    )
    expect(container?.textContent).not.toContain('legacy_occurrences_json_api')
  })

  it('does not fall back to another collection profile when the current collection has none', async () => {
    await renderTab('plots')

    expect(container?.textContent).toContain('No standard profile is configured yet.')
    expect(container?.textContent).toContain('New profile')
    expect(container?.textContent).not.toContain('dwc_taxon_context')
    expect(container?.textContent).not.toContain('dwc_occurrences')
    expect(container?.textContent).not.toContain('legacy_json_api')
  })

  it('shows profiles scoped to a manual collection backing source', async () => {
    await renderTab(
      'occurrences_publication',
      '/groups/occurrences_publication?tab=standards',
    )

    const profileList = container!.querySelector('aside')?.textContent
    expect(profileList).toContain('dwc_occurrences')
    expect(profileList).not.toContain('dwc_taxon_context')
    expect(profileList).toContain('legacy_occurrences_json_api')
  })

  it('opens a requested standard profile draft from data recommendations', async () => {
    profilesState.profiles = []
    await renderTab(
      'occurrences_publication',
      '/groups/occurrences_publication?tab=standards&data_action=create_standard_profile&standard=humboldt_event&target_grain=inventory',
    )

    const standardSelect = container!.querySelector(
      '#standard-profile-standard',
    ) as HTMLSelectElement
    const targetGrainInput = container!.querySelector(
      '#standard-profile-grain',
    ) as HTMLInputElement

    expect(standardSelect.value).toBe('humboldt_event')
    expect(targetGrainInput.value).toBe('inventory')
  })

  it('keeps hidden technical collections available as profile sources', async () => {
    await renderTab()

    await act(async () => {
      click(container!.querySelector('button[title="New profile"]'))
    })

    expect(container?.textContent).toContain('technical_occurrences · collection')
    expect(container?.textContent).toContain('hidden or technical')
  })

  it('disables the new profile button while the new profile form is already open', async () => {
    profilesState.profiles = []
    await renderTab()

    const newProfileButton = container!.querySelector(
      'button[title="New profile"]',
    ) as HTMLButtonElement | null

    expect(newProfileButton?.disabled).toBe(true)
    expect(container?.textContent).toContain('New profile')
  })

  it('returns to the saved profile overview after editing an existing profile', async () => {
    mutations.update.mockResolvedValue({ profile: defaultProfiles[0] })

    await renderTab()

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('Edit profile'),
        ) ?? null,
      )
    })

    expect(container?.textContent).toContain('Profile settings')
    expect(container?.textContent).not.toContain('Profile overview')

    await act(async () => {
      const form = container!.querySelector('form')
      form?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })

    expect(mutations.update).toHaveBeenCalled()
    expect(container?.textContent).toContain('Profile overview')
    expect(container?.textContent).not.toContain('Profile settings')
  })
})
