// @vitest-environment jsdom

import { act, type ReactElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CollectionCatalog } from '@/features/collections/hooks/useCollectionsCatalog'
import type { StandardProfileConfig } from '@/features/collections/hooks/useStandardProfiles'

import { ProfileEditor } from './ProfileEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const mutations = vi.hoisted(() => ({
  create: vi.fn(),
  update: vi.fn(),
}))

const translations: Record<string, string> = {
  'collections.standards.editProfile': 'Profile settings',
  'collections.standards.newProfile': 'New profile',
  'collections.standards.profileEditorHelp': 'Profile help',
  'collections.standards.profileName': 'Profile name',
  'collections.standards.standard': 'Standard',
  'collections.standards.source': 'Source data',
  'collections.standards.targetGrain': 'Target grain',
  'collections.standards.mappingTitle': 'Standard term mappings',
  'collections.standards.mappingHelp': 'Map terms.',
  'collections.standards.mappingReferenceHelp': 'Mapping help.',
  'collections.standards.outputs': 'Outputs',
  'collections.standards.saveProfile': 'Save profile',
  'collections.standards.saveFailed': 'Could not save the profile.',
  'collections.standards.hiddenSource': 'hidden or technical',
  'collections.standards.standardTypes.darwin_core_occurrence':
    'Darwin Core Occurrence',
  'collections.standards.standardTypes.humboldt_event': 'Humboldt/Event',
  'collections.standards.outputTypes.api_json': 'Profile API JSON',
  'collections.standards.outputTypes.dwc_archive': 'Darwin Core Archive',
  'collections.standards.outputTypes.standard_files': 'Event standard files',
}

const catalog: CollectionCatalog = {
  collections: [
    {
      name: 'taxons',
      label: 'Taxons',
      source_type: 'reference',
      source_name: 'taxons',
      grain: 'taxon',
      roles: ['api', 'standard'],
      visible: true,
      review_status: 'accepted',
      confidence: 1,
      evidence: [],
    },
  ],
  sources: [{ type: 'dataset', name: 'occurrences', label: 'Occurrences' }],
  total: 1,
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => translations[key] ?? key,
  }),
}))

vi.mock('@/features/collections/components/api/DwcMappingEditor', () => ({
  DwcMappingEditor: () => <div>Standard term mappings</div>,
}))

vi.mock('@/features/collections/hooks/useStandardProfiles', () => ({
  useCreateStandardProfile: () => ({
    isPending: false,
    mutateAsync: mutations.create,
  }),
  useUpdateStandardProfile: () => ({
    isPending: false,
    mutateAsync: mutations.update,
  }),
}))

function changeInput(element: HTMLInputElement, value: string) {
  const valueSetter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    'value',
  )?.set
  valueSetter?.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

function submit(form: HTMLFormElement | null) {
  if (!form) {
    throw new Error('Expected form to exist')
  }
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
}

describe('ProfileEditor', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    mutations.create.mockReset()
    mutations.update.mockReset()
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    root = null
    container = null
  })

  async function renderEditor(element: ReactElement) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(element)
    })
  }

  async function rerenderEditor(element: ReactElement) {
    await act(async () => {
      root?.render(element)
    })
  }

  it('preserves existing output params and profile enabled state on update', async () => {
    const profile: StandardProfileConfig = {
      name: 'dwc_taxon_context',
      enabled: false,
      standard: 'darwin_core_occurrence',
      target_grain: 'occurrence',
      source: { type: 'collection', name: 'taxons' },
      mappings: { occurrenceID: { source: 'occurrence_id' } },
      outputs: [
        {
          type: 'api_json',
          enabled: true,
          params: { output_dir: 'custom/api', include_meta: true },
        },
        {
          type: 'dwc_archive',
          enabled: false,
          params: {
            output_dir: 'custom/archive',
            archive_name: 'custom-dwc.zip',
          },
        },
      ],
      validation_status: 'partial',
      metadata: {},
    }
    mutations.update.mockResolvedValue({ profile })

    await renderEditor(<ProfileEditor profile={profile} catalog={catalog} />)

    await act(async () => {
      submit(container!.querySelector('form'))
    })

    const payload = mutations.update.mock.calls[0][0]
    expect(payload).not.toHaveProperty('enabled')
    expect(payload.outputs).toEqual([
      {
        type: 'api_json',
        enabled: true,
        params: { output_dir: 'custom/api', include_meta: true },
      },
      {
        type: 'dwc_archive',
        enabled: false,
        params: {
          output_dir: 'custom/archive',
          archive_name: 'custom-dwc.zip',
        },
      },
    ])
  })

  it('uses the current collection as the effective source when the catalog loads later', async () => {
    const createdProfile: StandardProfileConfig = {
      name: 'dwc_taxon_context',
      enabled: true,
      standard: 'darwin_core_occurrence',
      target_grain: 'occurrence',
      source: { type: 'collection', name: 'taxons' },
      mappings: { occurrenceID: { source: 'id' } },
      outputs: [],
      validation_status: 'draft',
      metadata: {},
    }
    mutations.create.mockResolvedValue({ profile: createdProfile })

    await renderEditor(
      <ProfileEditor catalog={undefined} currentCollectionName="taxons" />,
    )
    await rerenderEditor(
      <ProfileEditor catalog={catalog} currentCollectionName="taxons" />,
    )

    await act(async () => {
      changeInput(
        container!.querySelector('#standard-profile-name')!,
        'dwc_taxon_context',
      )
    })
    await act(async () => {
      submit(container!.querySelector('form'))
    })

    expect(mutations.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'dwc_taxon_context',
        enabled: true,
        source: { type: 'collection', name: 'taxons' },
      }),
    )
  })
})
