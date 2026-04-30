// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AddCollectionDialog } from './AddCollectionDialog'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const createCollection = vi.fn()
const translations: Record<string, string> = {
  'collections.review.addTitle': 'Add a collection',
  'collections.review.addDescription': 'Create a collection.',
  'collections.review.name': 'Collection name',
  'collections.review.label': 'Display name',
  'collections.review.labelPlaceholder': 'Publication occurrences',
  'collections.review.source': 'Source data',
  'collections.review.grain': 'Grain',
  'collections.review.roles': 'Roles',
  'collections.review.visiblePage': 'Visible as a website page',
  'collections.review.create': 'Create collection',
  'collections.review.addFailed': 'Could not create the collection.',
  'collections.review.rolesList.site': 'Site',
  'collections.review.rolesList.api': 'API',
  'collections.review.rolesList.standard': 'Standard',
  'collections.review.rolesList.technical': 'Technical',
  'collections.review.sourceTypes.dataset': 'Dataset',
  'common:actions.cancel': 'Cancel',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => translations[key] ?? key,
  }),
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: (props: { open: boolean; children: ReactNode }) =>
    props.open ? <div>{props.children}</div> : null,
  DialogContent: (props: { children: ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
  DialogDescription: (props: { children: ReactNode }) => <p>{props.children}</p>,
  DialogFooter: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DialogHeader: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DialogTitle: (props: { children: ReactNode }) => <h2>{props.children}</h2>,
}))

vi.mock('@/features/collections/hooks/useCollectionsCatalog', () => ({
  useCreateCollection: () => ({
    isPending: false,
    mutateAsync: createCollection,
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

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

function submit(form: HTMLFormElement | null) {
  if (!form) {
    throw new Error('Expected form to exist')
  }
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
}

describe('AddCollectionDialog', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    createCollection.mockReset()
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    container = null
    root = null
  })

  async function renderDialog(onOpenChange = vi.fn()) {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <AddCollectionDialog
          open
          onOpenChange={onOpenChange}
          sources={[{ type: 'dataset', name: 'occurrences', label: 'occurrences' }]}
        />,
      )
    })
    return onOpenChange
  }

  it('creates a non-page standard/API/technical collection from a source dataset', async () => {
    createCollection.mockResolvedValue({ collection: { name: 'occurrence_profile' } })
    const onOpenChange = await renderDialog()
    const inputs = container!.querySelectorAll('input')

    await act(async () => {
      changeInput(inputs[0], 'occurrence_profile')
    })

    await act(async () => {
      click(
        Array.from(inputs).find((input) =>
          input.parentElement?.textContent?.includes('Technical'),
        ) ?? null,
      )
    })

    await act(async () => {
      submit(container!.querySelector('form'))
    })

    expect(createCollection).toHaveBeenCalledWith({
      name: 'occurrence_profile',
      label: undefined,
      source_type: 'dataset',
      source_name: 'occurrences',
      grain: 'occurrence',
      roles: ['api', 'standard', 'technical'],
      visible: false,
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('keeps backend validation errors visible without closing', async () => {
    createCollection.mockRejectedValue(new Error("Collection 'bad' already exists"))
    const onOpenChange = await renderDialog()

    await act(async () => {
      changeInput(container!.querySelector('#collection-name')!, 'bad')
    })

    await act(async () => {
      submit(container!.querySelector('form'))
    })

    expect(container?.textContent).toContain("Collection 'bad' already exists")
    expect(onOpenChange).not.toHaveBeenCalled()
  })
})
