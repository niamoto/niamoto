// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfileCompatibilityPanel } from './ProfileCompatibilityPanel'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const labels: Record<string, string> = {
        'collections.standards.compatibility': 'Compatibility',
        'collections.standards.compatibilityStatus.compatible': 'Compatible',
        'collections.standards.compatibilityStatus.plausible': 'Plausible',
        'collections.standards.grainSummary':
          'Source grain: {{source}} · Target grain: {{target}}',
        'collections.standards.evidence.occurrence_relation':
          'Occurrence relation',
        'collections.standards.evidence.site_context': 'Site context',
      }
      return (labels[key] ?? key)
        .replace('{{source}}', String(options?.source ?? ''))
        .replace('{{target}}', String(options?.target ?? ''))
    },
  }),
}))

describe('ProfileCompatibilityPanel', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

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

  async function renderPanel(status: 'compatible' | 'plausible') {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <ProfileCompatibilityPanel
          report={{
            standard: status === 'compatible' ? 'darwin_core_occurrence' : 'humboldt_event',
            target_grain: status === 'compatible' ? 'occurrence' : 'event',
            source: { type: 'collection', name: status === 'compatible' ? 'taxons' : 'plots' },
            source_grain: status === 'compatible' ? 'taxon' : 'site',
            status,
            confidence: status === 'compatible' ? 0.82 : 0.62,
            warnings:
              status === 'plausible'
                ? ['Site-grain collection still needs Event evidence.']
                : [],
            blockers: [],
            evidence: [
              {
                kind: status === 'compatible' ? 'occurrence_relation' : 'site_context',
                message:
                  status === 'compatible'
                    ? 'Source collection is related to occurrence-grain data.'
                    : 'Site collection may provide inventory context.',
                confidence: 0.8,
                details: {},
              },
            ],
          }}
        />,
      )
    })
  }

  it('shows occurrence-grain compatibility for a Darwin Core taxon context', async () => {
    await renderPanel('compatible')

    expect(container?.textContent).toContain('Compatible')
    expect(container?.textContent).toContain('Source grain: taxon · Target grain: occurrence')
    expect(container?.textContent).toContain('Occurrence relation')
  })

  it('keeps Humboldt/Event site context plausible with warnings', async () => {
    await renderPanel('plausible')

    expect(container?.textContent).toContain('Plausible')
    expect(container?.textContent).toContain('Site-grain collection still needs Event evidence.')
    expect(container?.textContent).toContain('Site context')
  })
})
