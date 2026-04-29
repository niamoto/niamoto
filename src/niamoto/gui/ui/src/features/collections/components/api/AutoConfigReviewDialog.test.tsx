// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ApiExportAutoConfigProposal } from '@/features/collections/hooks/useApiExportConfigs'

import { AutoConfigReviewDialog } from './AutoConfigReviewDialog'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts?.count !== undefined ? `${key}:${opts.count}` : key,
  }),
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: (props: { open: boolean; children: ReactNode }) =>
    props.open ? <div>{props.children}</div> : null,
  DialogContent: (props: { children: ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
  DialogDescription: (props: { children: ReactNode }) => <p>{props.children}</p>,
  DialogFooter: (props: { children: ReactNode }) => <footer>{props.children}</footer>,
  DialogHeader: (props: { children: ReactNode }) => <header>{props.children}</header>,
  DialogTitle: (props: { children: ReactNode; className?: string }) => (
    <h2 className={props.className}>{props.children}</h2>
  ),
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

function buildProposal(): ApiExportAutoConfigProposal {
  return {
    export_name: 'dwc_api',
    group_by: 'taxons',
    total_entities: 12,
    proposal: {
      enabled: true,
      group_by: 'taxons',
      detail: { pass_through: true },
      index: { fields: [{ name: 'general_info.name.value' }] },
      transformer_plugin: 'niamoto_to_dwc_occurrence',
      transformer_params: {
        mapping: {
          occurrenceID: { generator: 'unique_occurrence_id' },
        },
      },
    },
    sections: {
      index: {
        confidence: 'high',
        config: { fields: [{ name: 'general_info.name.value' }] },
        notes: ['Detected from transformed data.'],
        unresolved: [],
      },
      dwc_mapping: {
        confidence: 'low',
        config: { occurrenceID: { generator: 'unique_occurrence_id' } },
        notes: ['Review unresolved terms.'],
        unresolved: ['decimalLatitude', 'decimalLongitude'],
      },
    },
  }
}

describe('AutoConfigReviewDialog', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    container = null
    root = null
    vi.clearAllMocks()
  })

  async function renderDialog(element: ReactNode) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(element)
    })
  }

  it('shows unresolved Darwin Core terms before applying', async () => {
    await renderDialog(
      <AutoConfigReviewDialog
        open
        onOpenChange={vi.fn()}
        proposal={buildProposal()}
        onApply={vi.fn()}
      />
    )

    expect(container!.textContent).toContain('decimalLatitude')
    expect(container!.textContent).toContain('decimalLongitude')
    expect(container!.textContent).toContain(
      'collectionPanel.api.autoConfig.confidence.low'
    )
  })

  it('applies all visible proposal sections by default', async () => {
    const onApply = vi.fn()
    await renderDialog(
      <AutoConfigReviewDialog
        open
        onOpenChange={vi.fn()}
        proposal={buildProposal()}
        onApply={onApply}
      />
    )

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('collectionPanel.api.autoConfig.apply')
        ) ?? null
      )
    })

    expect(onApply).toHaveBeenCalledWith(['index', 'dwc_mapping'])
  })

  it('allows all proposal sections to be deselected', async () => {
    const onApply = vi.fn()
    await renderDialog(
      <AutoConfigReviewDialog
        open
        onOpenChange={vi.fn()}
        proposal={buildProposal()}
        onApply={onApply}
      />
    )

    const checkboxes = Array.from(
      container!.querySelectorAll('[role="checkbox"]')
    )
    await act(async () => {
      checkboxes.forEach((checkbox) => click(checkbox))
    })

    const applyButton = Array.from(container!.querySelectorAll('button')).find(
      (button) =>
        button.textContent?.includes('collectionPanel.api.autoConfig.apply')
    ) as HTMLButtonElement

    expect(applyButton.disabled).toBe(true)
    await act(async () => {
      click(applyButton)
    })
    expect(onApply).not.toHaveBeenCalled()
  })
})
