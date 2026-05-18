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
import { buildDataSourceOptions } from './exportCardSourceOptions'

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

vi.mock('@/components/ui/input', () => ({
  Input: (props: {
    value?: string
    onChange?: (event: { target: { value: string } }) => void
    placeholder?: string
  }) => (
    <input
      data-testid="data-source-input"
      value={props.value ?? ''}
      placeholder={props.placeholder}
      onChange={(event) => props.onChange?.({ target: { value: event.target.value } })}
      onInput={(event) =>
        props.onChange?.({ target: { value: event.currentTarget.value } })
      }
    />
  ),
}))

vi.mock('@/components/ui/select', () => ({
  Select: (props: {
    value?: string
    onValueChange?: (value: string) => void
    children: ReactNode
  }) => (
    <select
      data-testid="data-source-select"
      value={props.value ?? ''}
      onChange={(event) => props.onValueChange?.(event.target.value)}
    >
      {props.children}
    </select>
  ),
  SelectTrigger: () => null,
  SelectValue: () => null,
  SelectContent: (props: { children: ReactNode }) => <>{props.children}</>,
  SelectItem: (props: { value: string; children: ReactNode }) => (
    <option value={props.value}>{props.children}</option>
  ),
}))

vi.mock('@/lib/api/recipes', () => ({
  useAvailableSources: () => ({
    sources: [
      { type: 'dataset', name: 'occurrences', columns: [], transformers: [] },
      { type: 'reference', name: 'plots', columns: [], transformers: [] },
    ],
    loading: false,
    error: null,
  }),
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

  it('builds source override options from the current collection and available sources', () => {
    expect(
      buildDataSourceOptions('plots', ['occurrences', 'plots'], 'custom_source', [
        'taxons',
      ])
    ).toEqual(['plots', 'custom_source', 'occurrences', 'taxons'])
  })

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

  it('uses a dropdown for the data source override', async () => {
    serverConfig = {
      enabled: true,
      group_by: 'taxons',
      data_source: 'occurrences',
      detail: { pass_through: true },
      index: { fields: [] },
    }

    await renderCard()

    const select = container!.querySelector(
      '[data-testid="data-source-select"]'
    ) as HTMLSelectElement

    expect(select).toBeTruthy()
    expect(Array.from(select.options).map((option) => option.value)).toEqual(
      expect.arrayContaining(['__current_collection__', 'occurrences', 'plots'])
    )
    expect(select.value).toBe('occurrences')

    await act(async () => {
      select.value = 'plots'
      select.dispatchEvent(new Event('change', { bubbles: true }))
      await Promise.resolve()
    })

    const saveButton = Array.from(container!.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('common:actions.save')
    )

    await act(async () => {
      click(saveButton ?? null)
      await Promise.resolve()
    })

    expect(saveMutation).toHaveBeenCalledWith(
      expect.objectContaining({ data_source: 'plots' })
    )
  })

  it('still allows entering a custom data source override', async () => {
    await renderCard()

    const input = container!.querySelector(
      '[data-testid="data-source-input"]'
    ) as HTMLInputElement

    expect(input).toBeTruthy()

    await act(async () => {
      input.value = 'custom_stats_table'
      input.dispatchEvent(new Event('input', { bubbles: true }))
      await Promise.resolve()
    })

    const saveButton = Array.from(container!.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('common:actions.save')
    )

    await act(async () => {
      click(saveButton ?? null)
      await Promise.resolve()
    })

    expect(saveMutation).toHaveBeenCalledWith(
      expect.objectContaining({ data_source: 'custom_stats_table' })
    )
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
