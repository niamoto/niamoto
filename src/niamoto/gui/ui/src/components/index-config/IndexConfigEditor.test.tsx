// @vitest-environment jsdom

import { act, StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { IndexConfigEditor } from './IndexConfigEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

type UseIndexConfigMock = {
  config: {
    enabled: boolean
    page_config: {
      title: string
      description: string
      items_per_page: number
    }
    filters: unknown[]
    display_fields: Array<{
      name: string
      source: string
      type: 'text'
      searchable: boolean
      dynamic_options: boolean
      display: 'normal'
      is_title: boolean
      inline_badge: boolean
    }>
    views: Array<{ type: 'grid'; default: boolean }>
  }
  loading: boolean
  error: string | null
  isDirty: boolean
  setEnabled: ReturnType<typeof vi.fn>
  setPageConfig: ReturnType<typeof vi.fn>
  addFilter: ReturnType<typeof vi.fn>
  updateFilter: ReturnType<typeof vi.fn>
  removeFilter: ReturnType<typeof vi.fn>
  addDisplayField: ReturnType<typeof vi.fn>
  updateDisplayField: ReturnType<typeof vi.fn>
  removeDisplayField: ReturnType<typeof vi.fn>
  reorderDisplayFields: ReturnType<typeof vi.fn>
  setViews: ReturnType<typeof vi.fn>
  save: ReturnType<typeof vi.fn>
  reset: ReturnType<typeof vi.fn>
  fetchSuggestions: ReturnType<typeof vi.fn>
  applySuggestions: ReturnType<typeof vi.fn>
}

const hookRef: { value: UseIndexConfigMock | null } = {
  value: null,
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useGroupIndexPreview: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: (props: { children: ReactNode }) => <div>{props.children}</div>,
  ResizablePanel: (props: { children: ReactNode }) => <div>{props.children}</div>,
  ResizableHandle: () => <div />,
}))

vi.mock('@/components/ui/preview-frame', () => ({
  PreviewFrame: () => <div>Preview</div>,
}))

vi.mock('./useIndexConfig', () => ({
  useIndexConfig: () => hookRef.value,
  createDefaultDisplayField: (partial: Record<string, unknown> = {}) => ({
    name: '',
    source: '',
    type: 'text',
    searchable: false,
    dynamic_options: false,
    display: 'normal',
    is_title: false,
    inline_badge: false,
    ...partial,
  }),
}))

vi.mock('./IndexFiltersConfig', () => ({
  IndexFiltersConfig: () => <div>Filters</div>,
}))

vi.mock('./IndexDisplayFieldsConfig', () => ({
  IndexDisplayFieldsConfig: (props: { onSelect: (index: number) => void }) => (
    <button type="button" data-testid="select-field" onClick={() => props.onSelect(0)}>
      Select field
    </button>
  ),
}))

vi.mock('./DisplayFieldEditorPanel', () => ({
  DisplayFieldEditorPanel: (props: {
    availableFields: unknown[]
    availableFieldsError?: string | null
    loadingAvailableFields?: boolean
    onLoadAvailableFields?: () => void
    onChange?: (field: Record<string, unknown>) => void
  }) => (
    <div>
      <div data-testid="field-options">{props.availableFields.length}</div>
      <div data-testid="field-loading">{String(props.loadingAvailableFields)}</div>
      <div data-testid="field-error">{props.availableFieldsError ?? ''}</div>
      <button type="button" data-testid="load-fields" onClick={props.onLoadAvailableFields}>
        Load fields
      </button>
      <button
        type="button"
        data-testid="change-title-field"
        onClick={() => props.onChange?.({ is_title: true, searchable: true })}
      >
        Change title field
      </button>
    </div>
  ),
}))

function buildHook(overrides: Partial<UseIndexConfigMock> = {}): UseIndexConfigMock {
  return {
    config: {
      enabled: true,
      page_config: {
        title: 'Plots',
        description: '',
        items_per_page: 24,
      },
      filters: [],
      display_fields: [
        {
          name: 'name',
          source: 'general_info.name.value',
          type: 'text',
          searchable: true,
          dynamic_options: false,
          display: 'normal',
          is_title: true,
          inline_badge: false,
        },
      ],
      views: [{ type: 'grid', default: true }],
    },
    loading: false,
    error: null,
    isDirty: false,
    setEnabled: vi.fn(),
    setPageConfig: vi.fn(),
    addFilter: vi.fn(),
    updateFilter: vi.fn(),
    removeFilter: vi.fn(),
    addDisplayField: vi.fn(),
    updateDisplayField: vi.fn(),
    removeDisplayField: vi.fn(),
    reorderDisplayFields: vi.fn(),
    setViews: vi.fn(),
    save: vi.fn(),
    reset: vi.fn(),
    fetchSuggestions: vi.fn(),
    applySuggestions: vi.fn(),
    ...overrides,
  }
}

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  return {
    container,
    async render(element: ReactNode) {
      await act(async () => {
        root.render(element)
        await Promise.resolve()
      })
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('IndexConfigEditor', () => {
  beforeEach(() => {
    hookRef.value = buildHook()
  })

  afterEach(() => {
    hookRef.value = null
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('clears the available-field loading state when suggestions fail to load', async () => {
    hookRef.value = buildHook({
      fetchSuggestions: vi.fn().mockRejectedValue(new Error('network failed')),
    })
    const harness = createHarness()

    await harness.render(<IndexConfigEditor groupBy="plots" />)

    await act(async () => {
      ;(harness.container.querySelector('[data-testid="select-field"]') as HTMLButtonElement).click()
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(hookRef.value.fetchSuggestions).toHaveBeenCalledOnce()
    expect(harness.container.querySelector('[data-testid="field-loading"]')?.textContent).toBe(
      'false'
    )
    expect(harness.container.querySelector('[data-testid="field-error"]')?.textContent).toBe(
      'fieldEditor.fieldPickerLoadError'
    )

    await harness.unmount()
  })

  it('finishes loading available fields under React StrictMode', async () => {
    hookRef.value = buildHook({
      fetchSuggestions: vi.fn().mockResolvedValue({
        display_fields: [],
        filters: [],
        total_entities: 22,
        available_fields: [
          {
            name: 'name',
            source: 'general_info.name.value',
            type: 'text',
            label: 'Name',
            searchable: true,
            suggested_as_filter: false,
            dynamic_options: false,
            priority: 'high',
          },
        ],
      }),
    })
    const harness = createHarness()

    await harness.render(
      <StrictMode>
        <IndexConfigEditor groupBy="plots" />
      </StrictMode>
    )

    await act(async () => {
      ;(harness.container.querySelector('[data-testid="select-field"]') as HTMLButtonElement).click()
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(hookRef.value.fetchSuggestions).toHaveBeenCalledOnce()
    expect(harness.container.querySelector('[data-testid="field-loading"]')?.textContent).toBe(
      'false'
    )
    expect(harness.container.querySelector('[data-testid="field-options"]')?.textContent).toBe(
      '1'
    )

    await harness.unmount()
  })

  it('applies field editor changes immediately to the parent config', async () => {
    const updateDisplayField = vi.fn()
    hookRef.value = buildHook({ updateDisplayField })
    const harness = createHarness()

    await harness.render(<IndexConfigEditor groupBy="plots" />)

    await act(async () => {
      ;(harness.container.querySelector('[data-testid="select-field"]') as HTMLButtonElement).click()
      await Promise.resolve()
    })

    await act(async () => {
      ;(harness.container.querySelector('[data-testid="change-title-field"]') as HTMLButtonElement).click()
      await Promise.resolve()
    })

    expect(updateDisplayField).toHaveBeenCalledWith(0, {
      is_title: true,
      searchable: true,
    })

    await harness.unmount()
  })
})
