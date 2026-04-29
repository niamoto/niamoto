// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  ApiExportAutoConfigProposal,
  ApiExportGroupConfig,
  ApiExportTargetSummary,
} from '@/features/collections/hooks/useApiExportConfigs'

import { ExportCard } from './ExportCard'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const refetchAutoConfig = vi.fn()
const saveMutation = vi.fn()

const defaultServerConfig: ApiExportGroupConfig = {
  enabled: true,
  group_by: 'taxons',
  detail: { pass_through: true },
  index: { fields: [] },
}
let serverConfig: ApiExportGroupConfig = defaultServerConfig

const proposal: ApiExportAutoConfigProposal = {
  export_name: 'json_api',
  group_by: 'taxons',
  total_entities: 12,
  proposal: {
    enabled: true,
    group_by: 'taxons',
    detail: { pass_through: true },
    index: { fields: [{ name: 'general_info.name.value' }] },
  },
  sections: {
    index: {
      confidence: 'high',
      config: { fields: [{ name: 'general_info.name.value' }] },
      notes: [],
      unresolved: [],
    },
  },
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/components/forms', () => ({
  JsonSchemaForm: () => <div>JsonSchemaForm</div>,
}))

vi.mock('@/components/forms/fields/JsonField', () => ({
  default: () => <textarea aria-label="json" />,
}))

vi.mock('@/components/ui/accordion', () => ({
  Accordion: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AccordionContent: (props: { children: ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
  AccordionItem: (props: { children: ReactNode; className?: string }) => (
    <section className={props.className}>{props.children}</section>
  ),
  AccordionTrigger: (props: { children: ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
}))

vi.mock('@/components/ui/card', () => ({
  Card: (props: { children: ReactNode }) => <div>{props.children}</div>,
  CardContent: (props: { children: ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
  CardHeader: (props: { children: ReactNode; className?: string }) => (
    <div className={props.className}>{props.children}</div>
  ),
}))

vi.mock('@/components/ui/switch', () => ({
  Switch: (props: { checked: boolean; onCheckedChange?: (checked: boolean) => void }) => (
    <button type="button" onClick={() => props.onCheckedChange?.(!props.checked)}>
      {String(props.checked)}
    </button>
  ),
}))

vi.mock('./ApiFieldMappingsEditor', () => ({
  ApiFieldMappingsEditor: () => <div>ApiFieldMappingsEditor</div>,
}))

vi.mock('./DwcMappingEditor', () => ({
  DwcMappingEditor: () => <div>DwcMappingEditor</div>,
}))

vi.mock('./SynchronizedJsonConfigSection', () => ({
  SynchronizedJsonConfigSection: (props: {
    children: ReactNode
    showJsonPreview?: boolean
    jsonPreviewLabel?: string
    jsonPreviewValue?: unknown
  }) => (
    <div>
      {props.children}
      {props.showJsonPreview && (
        <aside>
          <span>{props.jsonPreviewLabel}</span>
          <pre>{JSON.stringify(props.jsonPreviewValue)}</pre>
        </aside>
      )}
    </div>
  ),
}))

vi.mock('./AutoConfigReviewDialog', () => ({
  AutoConfigReviewDialog: (props: {
    open: boolean
    proposal?: ApiExportAutoConfigProposal
    onApply: (sectionKeys: string[]) => void
  }) =>
    props.open && props.proposal ? (
      <button type="button" data-testid="apply-proposal" onClick={() => props.onApply(['index'])}>
        apply proposal
      </button>
    ) : null,
}))

vi.mock('@/features/collections/hooks/useApiExportConfigs', () => ({
  useApiExportGroupConfig: () => ({
    data: serverConfig,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useApiExportSuggestions: () => ({
    data: {
      display_fields: [],
      total_entities: 12,
    },
  }),
  useApiExportPreview: () => ({
    data: { preview: { name: 'Araucaria columnaris' } },
    isFetching: false,
    error: null,
  }),
  useUpdateApiExportGroupConfig: () => ({
    isPending: false,
    mutateAsync: saveMutation,
  }),
  useApiExportAutoConfig: () => ({
    data: proposal,
    isFetching: false,
    error: null,
    refetch: refetchAutoConfig,
  }),
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

describe('ExportCard auto-configuration', () => {
  let container: HTMLDivElement | null = null
  let root: Root | null = null

  const target: ApiExportTargetSummary = {
    name: 'json_api',
    enabled: true,
    exporter: 'json_api_exporter',
    group_names: ['taxons'],
    groups: [{ group_by: 'taxons', enabled: true }],
    params: {},
  }

  afterEach(async () => {
    serverConfig = defaultServerConfig
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

  async function renderCard() {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(<ExportCard exportTarget={target} groupBy="taxons" />)
    })
  }

  it('does not fetch auto-configuration on mount', async () => {
    await renderCard()

    expect(refetchAutoConfig).not.toHaveBeenCalled()
  })

  it('keeps the export card header sticky', async () => {
    await renderCard()

    expect(container!.querySelector('.sticky')).toBeTruthy()
  })

  it('opens auto-configuration on demand and applies it as an unsaved draft', async () => {
    await renderCard()

    await act(async () => {
      click(
        Array.from(container!.querySelectorAll('button')).find((button) =>
          button.textContent?.includes('collectionPanel.api.autoConfig.button')
        ) ?? null
      )
    })

    expect(refetchAutoConfig).toHaveBeenCalled()

    await act(async () => {
      click(container!.querySelector('[data-testid="apply-proposal"]'))
    })

    expect(container!.textContent).toContain('collectionPanel.api.unsaved')
    const saveButton = Array.from(container!.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('common:actions.save')
    )
    expect(saveButton?.className).toContain('animate-pulse')
    expect(saveButton?.className).toContain('bg-amber-500')
    expect(saveMutation).not.toHaveBeenCalled()
  })

  it('shows a Darwin Core JSON preview next to the mapping editor', async () => {
    serverConfig = {
      enabled: true,
      group_by: 'taxons',
      detail: { pass_through: true },
      index: { fields: [] },
      transformer_plugin: 'niamoto_to_dwc_occurrence',
      transformer_params: {
        mapping: {
          occurrenceID: { generator: 'unique_occurrence_id' },
        },
      },
    }

    await renderCard()

    expect(container!.textContent).toContain('DwcMappingEditor')
    expect(container!.textContent).toContain('collectionPanel.api.dwcJsonPreview')
    expect(container!.textContent).toContain('Araucaria columnaris')
  })

  it('shows an empty Darwin Core preview when no mapping is configured', async () => {
    serverConfig = {
      enabled: true,
      group_by: 'taxons',
      detail: { pass_through: true },
      index: { fields: [] },
      transformer_plugin: 'niamoto_to_dwc_occurrence',
      transformer_params: { mapping: {} },
    }

    await renderCard()

    expect(container!.textContent).toContain('collectionPanel.api.dwcJsonPreview')
    expect(container!.textContent).toContain('collectionPanel.api.dwcJsonPreview[]')
  })
})
