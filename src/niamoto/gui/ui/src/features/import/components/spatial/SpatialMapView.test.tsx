import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import type { SpatialMapInspection } from '@/features/import/api/spatial-map'

const useQuerySpy = vi.hoisted(() => vi.fn())

vi.mock('@tanstack/react-query', () => ({
  useQuery: useQuerySpy,
}))

vi.mock('@/features/import/api/spatial-map', () => ({
  getSpatialMapRenderUrl: (referenceName: string) =>
    `/api/stats/spatial-map/${encodeURIComponent(referenceName)}/render`,
}))

vi.mock('react-i18next', () => ({
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
  useTranslation: () => ({
    t: (
      _key: string,
      fallback?: string | Record<string, unknown>,
      options?: Record<string, unknown>
    ) => {
      const template = typeof fallback === 'string' ? fallback : _key
      const values = typeof fallback === 'object' ? fallback : options

      return template.replace(/\{\{(\w+)\}\}/g, (_match, token: string) =>
        String(values?.[token] ?? '')
      )
    },
  }),
}))

vi.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AlertTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    variant: _variant,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string }) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/select', () => ({
  Select: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectTrigger: ({ children }: { children: ReactNode }) => <button type="button">{children}</button>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
}))

vi.mock('lucide-react', () => ({
  AlertTriangle: () => <span />,
  Layers: () => <span />,
  Loader2: () => <span />,
  Map: () => <span />,
  MapPin: () => <span />,
}))

import { SpatialMapView } from './SpatialMapView'

const spatialSummary: SpatialMapInspection = {
  reference_name: 'shapes',
  table_name: 'entity_shapes',
  is_mappable: true,
  reason: null,
  geometry_column: 'geometry',
  geometry_storage: 'wkt',
  geometry_kind: 'polygon',
  geometry_types: ['POLYGON'],
  id_column: 'id',
  name_column: 'name',
  type_column: 'type',
  layer_column: 'type',
  selected_layer: null,
  layers: [
    {
      value: 'province',
      label: 'Province',
      feature_count: 2,
      with_geometry: 2,
    },
    {
      value: 'protected_area',
      label: 'Protected area',
      feature_count: 3,
      with_geometry: 1,
    },
  ],
  total_features: 5,
  with_geometry: 3,
  without_geometry: 2,
  bounding_box: {
    min_x: 164,
    min_y: -22,
    max_x: 167,
    max_y: -20,
  },
  feature_collection: {
    type: 'FeatureCollection',
    features: [],
  },
  limit: 0,
  offset: 0,
  result_count: 0,
  has_more: false,
  next_offset: null,
}

function mockSpatialQueries() {
  useQuerySpy.mockReset()
  useQuerySpy.mockImplementation((options: { queryKey: unknown[] }) => {
    if (options.queryKey.length === 4) {
      return {
        data: spatialSummary,
        isLoading: false,
        isError: false,
        isFetching: false,
      }
    }

    return {
      data: undefined,
      isLoading: false,
      isError: false,
      isFetching: false,
    }
  })
}

describe('SpatialMapView', () => {
  it('starts multi-layer references on the layer overview instead of the first layer', () => {
    mockSpatialQueries()

    const html = renderToStaticMarkup(<SpatialMapView referenceName="shapes" />)

    expect(html).toContain('Layer overview')
    expect(html).toContain('Select a layer to load the interactive map.')
    expect(html).not.toContain('<iframe')
    expect(useQuerySpy).toHaveBeenCalledTimes(2)
    expect(useQuerySpy.mock.calls[1]?.[0]).toMatchObject({ enabled: false })
  })
})
