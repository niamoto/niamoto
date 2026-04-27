import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import type { SpatialMapInspection } from '@/features/import/api/spatial-map'

const useQuerySpy = vi.hoisted(() => vi.fn())

vi.mock('@tanstack/react-query', () => ({
  useQuery: useQuerySpy,
}))

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string | Record<string, unknown>, options?: Record<string, unknown>) => {
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

vi.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value?: number }) => <div data-progress={value} />,
}))

vi.mock('lucide-react', () => ({
  AlertCircle: () => <span />,
  AlertTriangle: () => <span />,
  CheckCircle2: () => <span />,
  Clock: () => <span />,
  Database: () => <span />,
  ExternalLink: () => <span />,
  GitBranch: () => <span />,
  Loader2: () => <span />,
  Map: () => <span />,
  MapPin: () => <span />,
  Settings: () => <span />,
  Table2: () => <span />,
  Zap: () => <span />,
}))

import { SourceSummary } from './SourceSummary'

const spatialMap: SpatialMapInspection = {
  reference_name: 'shapes',
  table_name: 'entity_shapes',
  is_mappable: true,
  reason: null,
  geometry_column: 'geom',
  geometry_storage: 'wkt',
  geometry_kind: 'polygon',
  geometry_types: ['POLYGON'],
  id_column: 'id',
  name_column: 'name',
  type_column: 'type',
  layer_column: 'type',
  selected_layer: null,
  layers: [],
  total_features: 20,
  with_geometry: 15,
  without_geometry: 5,
  bounding_box: null,
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

function mockSummaryQueries() {
  useQuerySpy.mockReset()
  useQuerySpy.mockImplementation((options: { queryKey: unknown[] }) => {
    const key = options.queryKey

    if (key[1] === 'data-preview') {
      return {
        data: [
          {
            name: 'entity_shapes',
            count: 20,
            columns: ['id', 'name', 'geom'],
          },
        ],
      }
    }

    if (key[2] === 'enrichment-stats') {
      return {
        data: {
          total: 100,
          enriched: 40,
          pending: 60,
          sources: [
            {
              source_id: 'endemia',
              label: 'Endemia NC',
              total: 100,
              enriched: 40,
              pending: 60,
              status: 'ready',
            },
          ],
        },
        isFetching: false,
      }
    }

    if (key[2] === 'enrichment-job') {
      return {
        data: null,
      }
    }

    return {}
  })
}

describe('SourceSummary', () => {
  it('renders map, hierarchy, and enrichment quick actions for references', () => {
    mockSummaryQueries()

    const html = renderToStaticMarkup(
      <SourceSummary
        entityType="reference"
        name="shapes"
        tableName="entity_shapes"
        kind="spatial"
        connectorType="file_multi_feature"
        path="/data/shapes.gpkg"
        hasEnrichment
        enrichmentSources={[
          {
            id: 'endemia',
            label: 'Endemia NC',
            enabled: true,
          },
          {
            id: 'disabled',
            label: 'Disabled API',
            enabled: false,
          },
        ]}
        hasHierarchy
        hasSpatialMap
        spatialMap={spatialMap}
        onPreview={vi.fn()}
        onConfigure={vi.fn()}
        onOpenExplorer={vi.fn()}
        onOpenHierarchy={vi.fn()}
        onOpenMap={vi.fn()}
        onOpenEnrichment={vi.fn()}
      />
    )

    expect(html).toContain('Map available')
    expect(html).toContain('Hierarchy available')
    expect(html).toContain('Geographic fields detected')
    expect(html).toContain('15 / 20 geometries available')
    expect(html).toContain('Geometry column')
    expect(html).toContain('geom')
    expect(html).toContain('40 / 100 enriched')
    expect(html).toContain('Endemia NC')
    expect(html).not.toContain('Disabled API')
    expect(html).toContain('Open map')
    expect(html).toContain('Open enrichment')
  })
})
