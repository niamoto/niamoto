// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfileOutputsPanel } from './ProfileOutputsPanel'

const executeOutput = vi.fn()
const outputPreview = vi.fn()

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const labels: Record<string, string> = {
        'collections.standards.outputs': 'Outputs',
        'collections.standards.validationStatus.invalid': 'Invalid',
        'collections.standards.publicationBlocked': 'Publication blocked',
        'collections.standards.outputTypes.api_json': 'Profile API JSON',
        'collections.standards.outputTypes.dwc_archive': 'Darwin Core Archive',
        'collections.standards.outputEnabled': 'Enabled',
        'collections.standards.generateDraftJson': 'Generate draft JSON',
        'collections.standards.generateDraftOutput': 'Generate test files',
        'collections.standards.generatePublicationFile': 'Generate files',
        'collections.standards.lastOutput': 'Last output',
        'collections.standards.testOutput': 'Test output',
        'collections.standards.publicationOutput': 'Publication output',
        'collections.standards.draftRetention': 'Draft retention {{location}}',
        'collections.standards.outputFailed': 'Could not generate the output.',
        'collections.standards.outputJsonPreview': 'Representative JSON preview',
        'collections.standards.outputJsonPreviewItem': 'Source record {{id}}',
        'collections.standards.outputJsonPreviewLoading': 'Loading preview',
        'collections.standards.outputJsonPreviewFailed': 'Could not load preview.',
      }
      let value = labels[key] ?? key
      if (typeof value === 'string') {
        Object.entries(options ?? {}).forEach(([optionKey, optionValue]) => {
          value = value.replace(`{{${optionKey}}}`, String(optionValue))
        })
      }
      return value
    },
  }),
}))

vi.mock('@/features/collections/hooks/useStandardProfiles', () => ({
  useExecuteStandardProfileOutput: () => ({
    isPending: false,
    mutateAsync: executeOutput,
  }),
  useExecuteStandardProfileOutputDraft: () => ({
    isPending: false,
    mutateAsync: executeOutput,
  }),
  useStandardProfileOutputPreview: () => outputPreview(),
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

describe('ProfileOutputsPanel', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    executeOutput.mockReset()
    outputPreview.mockReset()
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    root = null
    container = null
  })

  async function renderPanel(draftMode = false) {
    outputPreview.mockReturnValue({
      data: {
        item_id: 1,
        preview: {
          metadata: { profile_name: 'dwc_occurrences' },
          records: [{ occurrenceID: 1, locality: 'Aoupinié' }],
        },
      },
      isLoading: false,
      isFetching: false,
      error: null,
    })
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <ProfileOutputsPanel
          profile={{
            name: 'dwc_occurrences',
            enabled: true,
            standard: 'darwin_core_occurrence',
            target_grain: 'occurrence',
            source: { type: 'dataset', name: 'occurrences' },
            mappings: {},
            outputs: [
              { type: 'api_json', enabled: true, params: {} },
              { type: 'dwc_archive', enabled: true, params: {} },
            ],
            validation_status: 'invalid',
            metadata: {},
          }}
          validation={{
            profile_name: 'dwc_occurrences',
            standard: 'darwin_core_occurrence',
            status: 'invalid',
            summary: { critical: 1, warning: 0, recommended: 0, info: 0 },
            compatibility: {
              standard: 'darwin_core_occurrence',
              target_grain: 'occurrence',
              source: { type: 'dataset', name: 'occurrences' },
              source_grain: 'occurrence',
              status: 'compatible',
              confidence: 0.9,
              evidence: [],
              warnings: [],
              blockers: [],
            },
            checklist: [],
            issues: [],
          }}
          draftMode={draftMode}
        />,
      )
    })
  }

  it('allows draft API JSON but disables publication files on critical validation', async () => {
    executeOutput.mockResolvedValue({
      output_path: '/tmp/dwc_occurrences.json',
    })
    await renderPanel()

    const buttons = Array.from(container!.querySelectorAll('button'))
    const draftButton = buttons.find((button) =>
      button.textContent?.includes('Generate draft JSON'),
    )
    const publicationButton = buttons.find((button) =>
      button.textContent?.includes('Generate files'),
    )

    expect(draftButton).toBeTruthy()
    expect(draftButton?.hasAttribute('disabled')).toBe(false)
    expect(publicationButton?.hasAttribute('disabled')).toBe(true)
    expect(container?.textContent).toContain('Publication blocked')

    await act(async () => {
      click(draftButton ?? null)
    })

    expect(executeOutput).toHaveBeenCalledWith('api_json')
    expect(container?.textContent).toContain('/tmp/dwc_occurrences.json')
  })

  it('shows a representative API JSON preview for the profile output', async () => {
    await renderPanel()

    expect(container?.textContent).toContain('Representative JSON preview')
    expect(container?.textContent).toContain('Source record 1')
    expect(container?.textContent).toContain('Aoupinié')
  })

  it('labels draft mode outputs as test artifacts with retention metadata', async () => {
    executeOutput.mockResolvedValue({
      output_path: '/tmp/.draft/profile-dwc.zip',
      metadata: {
        retention_policy: {
          location: 'exports/.draft/profiles',
        },
      },
    })
    await renderPanel(true)

    const buttons = Array.from(container!.querySelectorAll('button'))
    const testFileButton = buttons.find((button) =>
      button.textContent?.includes('Generate test files'),
    )

    expect(testFileButton).toBeTruthy()
    expect(testFileButton?.hasAttribute('disabled')).toBe(false)

    await act(async () => {
      click(testFileButton ?? null)
    })

    expect(executeOutput).toHaveBeenCalledWith('dwc_archive')
    expect(container?.textContent).toContain('Test output')
    expect(container?.textContent).toContain('Draft retention exports/.draft/profiles')
  })
})
