// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfileValidationReport } from './ProfileValidationReport'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const labels: Record<string, string> = {
        'collections.standards.validation': 'Validation',
        'collections.standards.validationStatus.invalid': 'Invalid',
        'collections.standards.criticalCount': '{{count}} critical',
        'collections.standards.checklistStatus.fail': 'Fail',
        'collections.standards.severity.critical': 'Critical',
        'collections.standards.issues': 'Issues',
      }
      return (labels[key] ?? key).replace('{{count}}', String(options?.count ?? ''))
    },
  }),
}))

describe('ProfileValidationReport', () => {
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

  it('shows critical checklist failures and detailed issue rows', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <ProfileValidationReport
          report={{
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
            checklist: [
              {
                code: 'dwc_occurrence_id',
                label: 'Darwin Core occurrenceID',
                status: 'fail',
                severity: 'critical',
                message: "Required mapping 'occurrenceID' is missing.",
              },
            ],
            issues: [
              {
                code: 'dwc_occurrence_id',
                severity: 'critical',
                message: "Required mapping 'occurrenceID' is missing.",
                path: 'mappings.occurrenceID',
              },
            ],
          }}
        />,
      )
    })

    expect(container?.textContent).toContain('Invalid')
    expect(container?.textContent).toContain('1 critical')
    expect(container?.textContent).toContain('Darwin Core occurrenceID')
    expect(container?.textContent).toContain('mappings.occurrenceID')
  })
})
