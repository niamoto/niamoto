// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CollectionReviewPanel } from './CollectionReviewPanel'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const updateCollection = vi.fn()
const catalogState = vi.hoisted(() => ({
  data: {
    collections: [
      {
        name: 'taxons',
        label: 'taxons',
        source_type: 'reference',
        source_name: 'taxons',
        grain: 'taxon',
        roles: ['site', 'api'],
        visible: true,
        review_status: 'pending',
        confidence: 0.85,
        description: null,
        evidence: [
          {
            kind: 'import_reference',
            message: "Declared reference entity 'taxons' in import.yml",
            confidence: 0.85,
            details: {},
          },
        ],
      },
    ],
    sources: [{ type: 'dataset', name: 'occurrences', label: 'occurrences' }],
    total: 1,
  },
}))

const translations: Record<string, string> = {
  'collections.review.title': 'Review collections',
  'collections.review.description': '{{count}} collection(s) still need a decision.',
  'collections.review.pendingCallout': '{{count}} collection(s) still need review.',
  'collections.review.addCollection': 'Add collection',
  'collections.review.accept': 'Accept',
  'collections.review.defer': 'Defer',
  'collections.review.hide': 'Hide',
  'collections.review.show': 'Show',
  'collections.review.label': 'Display name',
  'collections.review.saveLabel': 'Save name',
  'collections.review.status.pending': 'Pending',
  'collections.review.rolesList.site': 'Site',
  'collections.review.rolesList.api': 'API',
  'collections.review.rolesList.standard': 'Standard',
  'collections.review.rolesList.technical': 'Technical',
  'collections.review.sourceTypes.reference': 'Reference',
  'collections.review.grains.taxon': 'Taxon',
  'collections.review.visible': 'Visible',
  'collections.review.evidence.import_reference': 'Import',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const value = translations[key] ?? key
      return value.replace('{{count}}', String(options?.count ?? ''))
    },
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: (props: { children: ReactNode }) => <span>{props.children}</span>,
  TooltipTrigger: (props: { children: ReactNode }) => <span>{props.children}</span>,
  TooltipContent: (props: { children: ReactNode }) => <span>{props.children}</span>,
}))

vi.mock('./AddCollectionDialog', () => ({
  AddCollectionDialog: () => null,
}))

vi.mock('@/features/collections/hooks/useCollectionsCatalog', () => ({
  useCollectionsCatalog: () => ({
    data: catalogState.data,
    isLoading: false,
    error: null,
  }),
  useUpdateCollection: () => ({
    isPending: false,
    mutateAsync: updateCollection,
  }),
}))

function click(element: Element | null) {
  if (!element) {
    throw new Error('Expected element to exist')
  }
  element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

describe('CollectionReviewPanel', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  afterEach(async () => {
    updateCollection.mockReset()
    if (root) {
      await act(async () => {
        root?.unmount()
      })
    }
    container?.remove()
    container = null
    root = null
  })

  async function renderPanel() {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(<CollectionReviewPanel />)
    })
  }

  it('renders detected collections with a non-blocking review callout', async () => {
    await renderPanel()

    expect(container?.textContent).toContain('Review collections')
    expect(container?.textContent).toContain('taxons')
    expect(container?.textContent).toContain('1 collection(s) still need review.')
    expect(container?.textContent).toContain('Import')
  })

  it('accepts and re-roles a collection through the update hook', async () => {
    updateCollection.mockResolvedValue({ collection: catalogState.data.collections[0] })
    await renderPanel()

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('Accept'),
        ) ?? null,
      )
    })

    expect(updateCollection).toHaveBeenCalledWith({
      collectionName: 'taxons',
      update: { review_status: 'accepted' },
    })

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('Standard'),
        ) ?? null,
      )
    })

    expect(updateCollection).toHaveBeenLastCalledWith({
      collectionName: 'taxons',
      update: { roles: ['site', 'api', 'standard'] },
    })
  })
})
