// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AddExportWizard } from './AddExportWizard'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const invalidateQueries = vi.fn(async () => undefined)

const translations: Record<string, string> = {
  'collectionPanel.api.wizard.title': 'Add an export format',
  'collectionPanel.api.wizard.description': 'Configure a new export.',
  'collectionPanel.api.wizard.stepType': 'Type',
  'collectionPanel.api.wizard.stepContent': 'Content',
  'collectionPanel.api.wizard.stepConfirm': 'Confirm',
  'collectionPanel.api.wizard.createNew': 'Create a new format',
  'collectionPanel.api.wizard.simpleTitle': 'Simple JSON export',
  'collectionPanel.api.wizard.simpleDescription': 'Publish all your transformed data as-is',
  'collectionPanel.api.wizard.targetName': 'Export name',
  'collectionPanel.api.wizard.targetNamePlaceholder': 'my_export',
  'collectionPanel.api.wizard.targetNameHelp':
    'Lowercase letters, numbers and underscores only (3-31 chars)',
  'common:actions.previous': 'Previous',
  'common:actions.next': 'Next',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, _opts?: Record<string, unknown>) => translations[key] ?? key,
  }),
}))

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>(
    '@tanstack/react-query'
  )
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries }),
  }
})

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: (props: { open: boolean; children: React.ReactNode }) =>
    props.open ? <div>{props.children}</div> : null,
  DialogContent: (props: { children: React.ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
  DialogHeader: (props: { children: React.ReactNode }) => <div>{props.children}</div>,
  DialogTitle: (props: { children: React.ReactNode }) => <h2>{props.children}</h2>,
  DialogDescription: (props: { children: React.ReactNode }) => <p>{props.children}</p>,
}))

vi.mock('@/features/collections/hooks/useApiExportConfigs', () => ({
  useApiExportTargets: () => ({ data: [] }),
  useCreateApiExportTarget: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
  useUpdateApiExportGroupConfig: () => ({
    isPending: false,
    mutateAsync: vi.fn(),
  }),
  updateApiExportGroupConfig: vi.fn(),
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

function changeInput(element: HTMLInputElement, value: string) {
  element.value = value
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
}

describe('AddExportWizard', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    invalidateQueries.mockClear()
    if (root && container) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    root = null
    container = null
  })

  async function renderWizard() {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <AddExportWizard
          open
          onOpenChange={vi.fn()}
          groupBy="taxons"
        />
      )
    })

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find(
          (button) => button.textContent?.includes('Simple JSON export')
        ) ?? null
      )
    })
  }

  it('disables browser auto-capitalization and correction for export names', async () => {
    await renderWizard()

    const input = container?.querySelector('input')
    expect(input).toBeInstanceOf(HTMLInputElement)
    expect(input?.getAttribute('autocapitalize')).toBe('none')
    expect(input?.getAttribute('autocorrect')).toBe('off')
    expect(input?.getAttribute('spellcheck')).toBe('false')
  })

  it('shows the name guidance only once when validation fails', async () => {
    await renderWizard()

    const input = container?.querySelector('input') as HTMLInputElement
    await act(async () => {
      changeInput(input, 'My_api')
    })

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find(
          (button) => button.textContent?.includes('Next')
        ) ?? null
      )
    })

    const helpText = translations['collectionPanel.api.wizard.targetNameHelp']
    const matches = container?.textContent?.match(
      new RegExp(helpText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')
    )
    expect(matches).toHaveLength(1)
  })
})
