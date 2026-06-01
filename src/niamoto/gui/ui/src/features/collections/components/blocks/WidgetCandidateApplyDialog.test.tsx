// @vitest-environment jsdom

import { act } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { WidgetCandidateApplyDialog } from './WidgetCandidateApplyDialog'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) =>
      options?.defaultValue ?? key,
  }),
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ open, children }: { open: boolean; children: ReactNode }) =>
    open ? <div>{children}</div> : null,
  DialogContent: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  DialogDescription: ({ children }: { children: ReactNode }) => (
    <p>{children}</p>
  ),
  DialogFooter: ({ children }: { children: ReactNode }) => (
    <footer>{children}</footer>
  ),
  DialogHeader: ({ children }: { children: ReactNode }) => (
    <header>{children}</header>
  ),
  DialogTitle: ({ children }: { children: ReactNode }) => (
    <h2>{children}</h2>
  ),
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}))

describe('WidgetCandidateApplyDialog', () => {
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
  })

  it('shows conflict and invalid details even when there are no applicable changes', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <WidgetCandidateApplyDialog
          open
          preview={{
            collection: 'taxons',
            writes_files: false,
            preview_token: 'preview-1',
            changes: [],
            conflicts: [
              {
                candidate_id: 'candidate-conflict',
                widget_id: 'candidate-conflict',
                title: 'Already configured chart',
                action: 'conflict',
                reason: 'A matching widget already exists.',
              },
            ],
            invalid: [
              {
                candidate_id: 'candidate-invalid',
                widget_id: 'candidate-invalid',
                title: 'Stale candidate',
                action: 'invalid',
                reason: 'The source field is no longer available.',
              },
            ],
          }}
          loading={false}
          applying={false}
          result={null}
          error={null}
          onOpenChange={vi.fn()}
          onApply={vi.fn()}
        />,
      )
    })

    expect(container.textContent).toContain('Already configured chart')
    expect(container.textContent).toContain('A matching widget already exists.')
    expect(container.textContent).toContain('Stale candidate')
    expect(container.textContent).toContain('The source field is no longer available.')
  })

  it('lets users resolve a conflict before applying', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    const onReplacementChange = vi.fn()

    await act(async () => {
      root?.render(
        <WidgetCandidateApplyDialog
          open
          preview={{
            collection: 'taxons',
            writes_files: false,
            preview_token: 'preview-1',
            changes: [],
            conflicts: [
              {
                candidate_id: 'candidate-conflict',
                widget_id: 'candidate-conflict',
                title: 'Already configured chart',
                action: 'conflict',
                reason: 'A matching widget already exists.',
              },
            ],
            invalid: [],
          }}
          loading={false}
          applying={false}
          result={null}
          error={null}
          onOpenChange={vi.fn()}
          onApply={vi.fn()}
          onReplacementChange={onReplacementChange}
        />,
      )
    })

    const replaceButton = [...container.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('replaceConflict'),
    )
    expect(replaceButton).toBeDefined()

    await act(async () => {
      replaceButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(onReplacementChange).toHaveBeenCalledWith(
      'candidate-conflict',
      'replace',
    )
  })
})
