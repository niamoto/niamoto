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
        'collections.standards.compatibilityConfidence': 'Confidence {{confidence}}%',
        'collections.standards.compatibilityExplanation.exactSourceGrain':
          'No compatibility issue detected: the source is already at {{grain}} grain.',
        'collections.standards.compatibilityExplanation.occurrenceRelation':
          'Not 100%: compatibility relies on a detected relation to {{dataset}} ({{foreignKey}} -> {{targetField}}), not on a source directly at {{target}} grain.',
        'collections.standards.compatibilityExplanation.plausible':
          'Not 100%: the source is at {{source}} grain, while the profile targets {{target}} grain.',
        'collections.standards.grainSummary':
          'Source grain: {{source}} · Target grain: {{target}}',
        'collections.standards.evidence.occurrence_relation':
          'Occurrence relation',
        'collections.standards.evidence.site_context': 'Site context',
      }
      return (labels[key] ?? key)
        .replace('{{source}}', String(options?.source ?? ''))
        .replace('{{target}}', String(options?.target ?? ''))
        .replace('{{confidence}}', String(options?.confidence ?? ''))
        .replace('{{grain}}', String(options?.grain ?? ''))
        .replace('{{dataset}}', String(options?.dataset ?? ''))
        .replace('{{foreignKey}}', String(options?.foreignKey ?? ''))
        .replace('{{targetField}}', String(options?.targetField ?? ''))
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
                details:
                  status === 'compatible'
                    ? {
                        occurrence_dataset: 'occurrences',
                        foreign_key: 'taxon_id',
                        target_field: 'id',
                      }
                    : {},
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
    expect(container?.textContent).toContain('Confidence 82%')
    expect(container?.textContent).toContain(
      'Not 100%: compatibility relies on a detected relation to occurrences (taxon_id -> id), not on a source directly at occurrence grain.',
    )
    expect(container?.textContent).toContain('Confidence 80%')
    expect(container?.textContent).toContain('Source grain: taxon · Target grain: occurrence')
    expect(container?.textContent).toContain('Occurrence relation')
  })

  it('shows exact confidence when the source already has the target grain', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <ProfileCompatibilityPanel
          report={{
            standard: 'darwin_core_occurrence',
            target_grain: 'occurrence',
            source: { type: 'collection', name: 'occurrences_publication' },
            source_grain: 'occurrence',
            status: 'compatible',
            confidence: 1,
            warnings: [],
            blockers: [],
            evidence: [
              {
                kind: 'source_grain',
                message: 'Source is occurrence-grain data.',
                confidence: 1,
                details: {},
              },
            ],
          }}
        />,
      )
    })

    expect(container?.textContent).toContain('Confidence 100%')
    expect(container?.textContent).toContain(
      'No compatibility issue detected: the source is already at occurrence grain.',
    )
    expect(container?.textContent).not.toContain('Not 100%')
  })

  it('keeps Humboldt/Event site context plausible with warnings', async () => {
    await renderPanel('plausible')

    expect(container?.textContent).toContain('Plausible')
    expect(container?.textContent).toContain('Site-grain collection still needs Event evidence.')
    expect(container?.textContent).toContain(
      'Not 100%: the source is at site grain, while the profile targets event grain.',
    )
    expect(container?.textContent).toContain('Site context')
  })
})
