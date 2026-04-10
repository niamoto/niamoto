/**
 * EnrichmentTab - Multi-source enrichment management for reference entities.
 *
 * Features:
 * - Configure several external APIs per reference
 * - Start one source or all enabled sources
 * - Track global and per-source progress
 * - Preview enrichment results grouped by source
 * - View persisted enrichment results grouped by source
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  Database,
  Eye,
  ExternalLink,
  ImageIcon,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  StopCircle,
  Trash2,
  WifiOff,
} from 'lucide-react'

import { apiClient } from '@/shared/lib/api/client'
import { useNetworkStatus } from '@/shared/hooks/useNetworkStatus'
import { useNotificationStore } from '@/stores/notificationStore'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import { ApiEnrichmentConfig, type ApiCategory, type ApiConfig } from './ApiEnrichmentConfig'
import {
  apiConfigToEnrichment,
  createDefaultEnrichmentSource,
  normalizeEnrichmentSources,
  type NormalizedEnrichmentSource,
  type ReferenceEnrichmentConfig,
} from './enrichmentSources'

interface EnrichmentTabProps {
  referenceName: string
  hasEnrichment: boolean
  onConfigSaved?: () => void
  mode?: 'workspace' | 'quick'
  initialSourceId?: string | null
  onOpenWorkspace?: (sourceId?: string) => void
}

interface ReferenceConfigPayload {
  kind?: string
  description?: string
  connector?: Record<string, any>
  hierarchy?: Record<string, any>
  schema?: Record<string, any>
  enrichment?: ReferenceEnrichmentConfig[]
}

interface ReferenceConfigResponse {
  name?: string
  config?: ReferenceConfigPayload
}

interface EnrichmentSourceStats {
  source_id: string
  label: string
  enabled: boolean
  total: number
  enriched: number
  pending: number
  status: string
}

interface EnrichmentStatsResponse {
  reference_name?: string
  entity_total: number
  source_total: number
  total: number
  enriched: number
  pending: number
  sources: EnrichmentSourceStats[]
}

interface EnrichmentJob {
  id: string
  reference_name: string
  mode: 'all' | 'single'
  status: 'pending' | 'running' | 'paused' | 'paused_offline' | 'completed' | 'failed' | 'cancelled'
  total: number
  processed: number
  successful: number
  failed: number
  started_at: string
  updated_at: string
  source_ids: string[]
  source_id?: string | null
  source_label?: string | null
  current_source_id?: string | null
  current_source_label?: string | null
  current_source_processed?: number
  current_source_total?: number
  error?: string | null
  current_entity?: string | null
}

interface EnrichmentResult {
  reference_name?: string
  source_id: string
  source_label: string
  entity_name?: string
  taxon_name?: string
  success: boolean
  data?: Record<string, any>
  error?: string
  processed_at: string
}

interface PreviewSourceResult {
  source_id: string
  source_label: string
  success: boolean
  data?: Record<string, any>
  raw_data?: any
  error?: string
  config_used?: Record<string, any>
}

interface PreviewResponse {
  success: boolean
  entity_name: string
  results: PreviewSourceResult[]
  error?: string
}

interface EntityOption {
  id: number
  name: string
  enriched: boolean
  enriched_count?: number
  total_sources?: number
}

function normalizeReferenceConfigPayload(
  payload: ReferenceConfigPayload | ReferenceConfigResponse | null | undefined
): ReferenceConfigPayload | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }
  if ('config' in payload && payload.config && typeof payload.config === 'object') {
    return normalizeReferenceConfigPayload(payload.config)
  }
  return payload as ReferenceConfigPayload
}

function getResultEntityName(result: EnrichmentResult): string {
  return result.entity_name || result.taxon_name || '-'
}

const ImageWithLoader = ({ src, alt }: { src: string; alt: string }) => {
  const { t } = useTranslation(['sources'])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  return (
    <div className="relative inline-block">
      {loading && !error ? (
        <div className="absolute inset-0 flex items-center justify-center rounded bg-muted">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : null}
      {error ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ImageIcon className="h-4 w-4" />
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="max-w-[150px] truncate text-blue-600 hover:underline"
          >
            {t('enrichmentTab.viewImage')}
          </a>
        </div>
      ) : (
        <a href={src} target="_blank" rel="noopener noreferrer">
          <img
            src={src}
            alt={alt}
            className={`h-16 w-16 rounded border object-cover transition-opacity hover:opacity-80 ${
              loading ? 'opacity-0' : 'opacity-100'
            }`}
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false)
              setError(true)
            }}
          />
        </a>
      )}
    </div>
  )
}

const renderValue = (value: any): React.ReactNode => {
  if (value === null || value === undefined) return '-'

  if (typeof value === 'string') {
    const urlPattern = /^(https?:\/\/[^\s]+)$/i
    if (urlPattern.test(value)) {
      const imagePattern = /\.(jpg|jpeg|png|gif|webp|svg|bmp)(\?.*)?$/i
      const isImageUrl =
        imagePattern.test(value) ||
        value.includes('/image') ||
        value.includes('/photo') ||
        value.includes('/thumb') ||
        value.includes('/media/cache')

      if (isImageUrl) {
        return <ImageWithLoader src={value} alt="Preview" />
      }

      return (
        <a
          href={value}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline"
        >
          <span className="max-w-[200px] truncate">{value}</span>
          <ExternalLink className="h-3 w-3 shrink-0" />
        </a>
      )
    }

    return value
  }

  if (typeof value === 'object') {
    return (
      <pre className="max-w-md whitespace-pre-wrap text-xs">
        {JSON.stringify(value, null, 2)}
      </pre>
    )
  }

  return String(value)
}

const renderMappedPreview = (data: Record<string, any>) => (
  <div className="max-h-[360px] overflow-auto pr-2">
    <div className="space-y-2">
      {Object.entries(data).map(([field, value]) => (
        <div
          key={field}
          className="grid items-start grid-cols-[120px_minmax(0,1fr)] gap-3 border-b border-border/60 py-2 last:border-b-0"
        >
          <div className="text-xs font-medium text-muted-foreground">{field}</div>
          <div className="min-w-0 break-words text-sm">{renderValue(value)}</div>
        </div>
      ))}
    </div>
  </div>
)

const renderRawPreview = (rawData: any) => (
  <div className="max-h-[360px] overflow-auto rounded-md bg-background p-3">
    <pre className="whitespace-pre-wrap break-words text-xs leading-5">
      {JSON.stringify(rawData, null, 2)}
    </pre>
  </div>
)

const isStructuredSourceSummary = (data: Record<string, any> | undefined): boolean =>
  Boolean(
    data &&
      typeof data === 'object' &&
      (
        'match' in data ||
        'taxonomy' in data ||
        'occurrence_summary' in data ||
        'media_summary' in data ||
        'nomenclature' in data ||
        'vernaculars' in data ||
        'references' in data ||
        'distribution_summary' in data
      )
  )

const renderSummaryRows = (rows: Array<[string, any]>) => (
  <div className="space-y-2">
    {rows
      .filter(([, value]) => value !== undefined && value !== null && value !== '')
      .map(([label, value]) => (
        <div
          key={label}
          className="grid items-start grid-cols-[140px_minmax(0,1fr)] gap-3 border-b border-border/50 py-2 last:border-b-0"
        >
          <div className="text-xs font-medium text-muted-foreground">{label}</div>
          <div className="min-w-0 break-words text-sm">{renderValue(value)}</div>
        </div>
      ))}
  </div>
)

const renderStatusPill = (status: string | undefined) =>
  status ? (
    <Badge variant={status === 'complete' ? 'secondary' : 'outline'} className="text-[11px] uppercase">
      {status}
    </Badge>
  ) : null

const renderNameResolutionSummary = (nameResolution: Record<string, any>) => {
  if (!nameResolution || Object.keys(nameResolution).length === 0) {
    return null
  }

  return (
    <div className="rounded-lg border border-border/70 bg-background p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="text-sm font-semibold">Name resolution</div>
        {renderStatusPill(typeof nameResolution.status === 'string' ? nameResolution.status : undefined)}
      </div>
      <div className="space-y-3">
        {renderSummaryRows([
          ['submitted_name', nameResolution.submitted_name],
          ['query_name', nameResolution.query_name],
          ['matched_name', nameResolution.matched_name],
          ['best_result', nameResolution.best_result],
          ['data_source_title', nameResolution.data_source_title],
          ['data_source_id', nameResolution.data_source_id],
          ['score', nameResolution.score],
          ['match_type', nameResolution.match_type],
          ['was_corrected', nameResolution.was_corrected],
          ['error', nameResolution.error],
        ])}
        {Array.isArray(nameResolution.alternatives) && nameResolution.alternatives.length > 0 ? (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">Alternatives</div>
            <div className="flex flex-wrap gap-2">
              {nameResolution.alternatives.map((alternative: string) => (
                <Badge key={alternative} variant="outline">{alternative}</Badge>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

const renderGbifStructuredSummary = (
  data: Record<string, any>,
  t: (key: string, options?: Record<string, any>) => string
) => {
  const nameResolution = data.name_resolution ?? {}
  const match = data.match ?? {}
  const taxonomy = data.taxonomy ?? {}
  const occurrenceSummary = data.occurrence_summary ?? {}
  const mediaSummary = data.media_summary ?? {}
  const links = data.links ?? {}
  const blockStatus = data.block_status ?? {}
  const blockErrors = data.block_errors ?? {}
  const noMatch = blockStatus.match === 'no_match' || !match.usage_key

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {renderNameResolutionSummary(nameResolution)}
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">
            {t('dashboard.enrichment.structured.match', { defaultValue: 'Match' })}
          </div>
          {renderStatusPill(blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue: 'GBIF n’a pas retourné de match exploitable pour ce test.',
            })}
          </div>
        ) : (
          renderSummaryRows([
            ['usage_key', match.usage_key],
            ['scientific_name', match.scientific_name],
            ['canonical_name', match.canonical_name],
            ['status', match.status],
            ['rank', match.rank],
            ['confidence', match.confidence],
            ['match_type', match.match_type],
            ['taxonomy_source', match.taxonomy_source],
          ])
        )}
      </div>

      {!noMatch ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">
                {t('dashboard.enrichment.structured.taxonomy', { defaultValue: 'Taxonomy' })}
              </div>
              {renderStatusPill(blockStatus.taxonomy)}
            </div>
            {blockErrors.taxonomy ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.taxonomy)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['kingdom', taxonomy.kingdom],
                  ['phylum', taxonomy.phylum],
                  ['class', taxonomy.class],
                  ['order', taxonomy.order],
                  ['family', taxonomy.family],
                  ['genus', taxonomy.genus],
                  ['species', taxonomy.species],
                  ['synonyms_count', taxonomy.synonyms_count],
                  ['iucn_category', taxonomy.iucn_category],
                ])}
                {Array.isArray(taxonomy.vernacular_names) && taxonomy.vernacular_names.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">
                      {t('dashboard.enrichment.structured.vernacularNames', {
                        defaultValue: 'Noms vernaculaires',
                      })}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {taxonomy.vernacular_names.map((name: string) => (
                        <Badge key={name} variant="outline">{name}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">
                {t('dashboard.enrichment.structured.occurrences', { defaultValue: 'Occurrences' })}
              </div>
              {renderStatusPill(blockStatus.occurrence_summary)}
            </div>
            {blockErrors.occurrence_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.occurrence_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['occurrence_count', occurrenceSummary.occurrence_count],
                  ['datasets_count', occurrenceSummary.datasets_count],
                ])}
                {Array.isArray(occurrenceSummary.countries) && occurrenceSummary.countries.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Countries</div>
                    <div className="flex flex-wrap gap-2">
                      {occurrenceSummary.countries.map((country: string) => (
                        <Badge key={country} variant="outline">{country}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                {Array.isArray(occurrenceSummary.basis_of_record) && occurrenceSummary.basis_of_record.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Basis of record</div>
                    <div className="flex flex-wrap gap-2">
                      {occurrenceSummary.basis_of_record.map((basis: string) => (
                        <Badge key={basis} variant="outline">{basis}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">
                {t('dashboard.enrichment.structured.media', { defaultValue: 'Media' })}
              </div>
              {renderStatusPill(blockStatus.media_summary)}
            </div>
            {blockErrors.media_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.media_summary)}</div>
            ) : Array.isArray(mediaSummary.items) && mediaSummary.items.length > 0 ? (
              <div className="space-y-3">
                <div className="text-sm text-muted-foreground">
                  {t('dashboard.enrichment.structured.mediaCount', {
                    defaultValue: '{{count}} media item(s)',
                    count: mediaSummary.media_count ?? mediaSummary.items.length,
                  })}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {mediaSummary.items.map((item: Record<string, any>, index: number) => (
                    <div key={`${item.identifier || item.source_url || index}`} className="rounded-md border p-3">
                      <div className="mb-2">{renderValue(item.thumbnail_url || item.identifier || item.source_url)}</div>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        {item.creator ? <div>{item.creator}</div> : null}
                        {item.license ? <div>{item.license}</div> : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">
                {t('dashboard.enrichment.structured.noMedia', { defaultValue: 'Aucun média résumé.' })}
              </div>
            )}
          </div>

          {Object.keys(links).length > 0 ? (
            <div className="rounded-lg border border-border/70 bg-background p-3">
              <div className="mb-3 text-sm font-semibold">
                {t('dashboard.enrichment.structured.links', { defaultValue: 'Links' })}
              </div>
              {renderSummaryRows(Object.entries(links))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

const renderTropicosStructuredSummary = (
  data: Record<string, any>,
  t: (key: string, options?: Record<string, any>) => string
) => {
  const nameResolution = data.name_resolution ?? {}
  const match = data.match ?? {}
  const nomenclature = data.nomenclature ?? {}
  const taxonomy = data.taxonomy ?? {}
  const references = data.references ?? {}
  const distributionSummary = data.distribution_summary ?? {}
  const mediaSummary = data.media_summary ?? {}
  const links = data.links ?? {}
  const blockStatus = data.block_status ?? {}
  const blockErrors = data.block_errors ?? {}
  const noMatch = blockStatus.match === 'no_match' || !match.name_id

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {renderNameResolutionSummary(nameResolution)}
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">Match</div>
          {renderStatusPill(blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue: "Tropicos n’a pas retourné de match exploitable pour ce test.",
            })}
          </div>
        ) : (
          renderSummaryRows([
            ['name_id', match.name_id],
            ['scientific_name', match.scientific_name],
            ['scientific_name_with_authors', match.scientific_name_with_authors],
            ['family', match.family],
            ['rank', match.rank],
            ['nomenclature_status', match.nomenclature_status],
            ['candidate_count', match.candidate_count],
          ])
        )}
      </div>

      {!noMatch ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Nomenclature</div>
              {renderStatusPill(blockStatus.nomenclature)}
            </div>
            {blockErrors.nomenclature ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.nomenclature)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['accepted_name_id', nomenclature.accepted_name_id],
                  ['accepted_name', nomenclature.accepted_name],
                  ['accepted_name_with_authors', nomenclature.accepted_name_with_authors],
                  ['synonyms_count', nomenclature.synonyms_count],
                  ['accepted_name_count', nomenclature.accepted_name_count],
                ])}
                {Array.isArray(nomenclature.selected_synonyms) && nomenclature.selected_synonyms.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Synonyms</div>
                    <div className="flex flex-wrap gap-2">
                      {nomenclature.selected_synonyms.map((name: string) => (
                        <Badge key={name} variant="outline">{name}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Taxonomy</div>
              {renderStatusPill(blockStatus.taxonomy)}
            </div>
            {blockErrors.taxonomy ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.taxonomy)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['family', taxonomy.family]])}
                {Array.isArray(taxonomy.higher_taxa) && taxonomy.higher_taxa.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Higher taxa</div>
                    <div className="flex flex-wrap gap-2">
                      {taxonomy.higher_taxa.map((taxon: string) => (
                        <Badge key={taxon} variant="outline">{taxon}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">References</div>
              {renderStatusPill(blockStatus.references)}
            </div>
            {blockErrors.references ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.references)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['references_count', references.references_count]])}
                {Array.isArray(references.items) && references.items.length > 0 ? (
                  <div className="space-y-2">
                    {references.items.map((item: Record<string, any>, index: number) => (
                      <div key={`${item.title || item.full_citation || index}`} className="rounded-md border p-3">
                        <div className="text-sm font-medium">{item.title || item.full_citation || 'Reference'}</div>
                        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                          {item.abbreviated_title ? <div>{item.abbreviated_title}</div> : null}
                          {item.year_published ? <div>{item.year_published}</div> : null}
                          {item.full_citation ? <div className="break-words">{item.full_citation}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Distribution</div>
              {renderStatusPill(blockStatus.distribution_summary)}
            </div>
            {blockErrors.distribution_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.distribution_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['distribution_count', distributionSummary.distribution_count]])}
                {Array.isArray(distributionSummary.countries) && distributionSummary.countries.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Countries</div>
                    <div className="flex flex-wrap gap-2">
                      {distributionSummary.countries.map((country: string) => (
                        <Badge key={country} variant="outline">{country}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                {Array.isArray(distributionSummary.regions) && distributionSummary.regions.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Regions</div>
                    <div className="flex flex-wrap gap-2">
                      {distributionSummary.regions.map((region: string) => (
                        <Badge key={region} variant="outline">{region}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Media</div>
              {renderStatusPill(blockStatus.media_summary)}
            </div>
            {blockErrors.media_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.media_summary)}</div>
            ) : Array.isArray(mediaSummary.items) && mediaSummary.items.length > 0 ? (
              <div className="space-y-3">
                {renderSummaryRows([['media_count', mediaSummary.media_count]])}
                <div className="grid gap-3 md:grid-cols-2">
                  {mediaSummary.items.map((item: Record<string, any>, index: number) => (
                    <div key={`${item.identifier || item.source_url || index}`} className="rounded-md border p-3">
                      <div className="mb-2">{renderValue(item.thumbnail_url || item.source_url || item.identifier)}</div>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        {item.caption ? <div>{item.caption}</div> : null}
                        {item.creator ? <div>{item.creator}</div> : null}
                        {item.license ? <div>{item.license}</div> : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Aucun média résumé.</div>
            )}
          </div>

          {Object.keys(links).length > 0 ? (
            <div className="rounded-lg border border-border/70 bg-background p-3">
              <div className="mb-3 text-sm font-semibold">Links</div>
              {renderSummaryRows(Object.entries(links))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

const renderColStructuredSummary = (
  data: Record<string, any>,
  t: (key: string, options?: Record<string, any>) => string
) => {
  const nameResolution = data.name_resolution ?? {}
  const match = data.match ?? {}
  const taxonomy = data.taxonomy ?? {}
  const nomenclature = data.nomenclature ?? {}
  const vernaculars = data.vernaculars ?? {}
  const distributionSummary = data.distribution_summary ?? {}
  const references = data.references ?? {}
  const links = data.links ?? {}
  const blockStatus = data.block_status ?? {}
  const blockErrors = data.block_errors ?? {}
  const noMatch = blockStatus.match === 'no_match' || !match.taxon_id

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {renderNameResolutionSummary(nameResolution)}
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">Match</div>
          {renderStatusPill(blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue: "Catalogue of Life n’a pas retourné de match exploitable pour ce test.",
            })}
          </div>
        ) : (
          renderSummaryRows([
            ['taxon_id', match.taxon_id],
            ['name_id', match.name_id],
            ['scientific_name', match.scientific_name],
            ['authorship', match.authorship],
            ['rank', match.rank],
            ['status', match.status],
            ['dataset_key', match.dataset_key],
          ])
        )}
      </div>

      {!noMatch ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Taxonomy</div>
              {renderStatusPill(blockStatus.taxonomy)}
            </div>
            {blockErrors.taxonomy ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.taxonomy)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['kingdom', taxonomy.kingdom],
                  ['phylum', taxonomy.phylum],
                  ['class', taxonomy.class],
                  ['order', taxonomy.order],
                  ['family', taxonomy.family],
                  ['genus', taxonomy.genus],
                  ['species', taxonomy.species],
                ])}
                {Array.isArray(taxonomy.classification) && taxonomy.classification.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Classification</div>
                    <div className="flex flex-wrap gap-2">
                      {taxonomy.classification.map((item: Record<string, any>, index: number) => {
                        const label = [item.rank, item.name].filter(Boolean).join(': ')
                        return (
                          <Badge key={`${item.rank || 'rank'}-${item.name || index}`} variant="outline">
                            {label}
                          </Badge>
                        )
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Nomenclature</div>
              {renderStatusPill(blockStatus.nomenclature)}
            </div>
            {blockErrors.nomenclature ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.nomenclature)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['accepted_name', nomenclature.accepted_name],
                  ['accepted_name_with_authors', nomenclature.accepted_name_with_authors],
                  ['synonyms_count', nomenclature.synonyms_count],
                ])}
                {Array.isArray(nomenclature.synonyms_sample) && nomenclature.synonyms_sample.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Synonyms</div>
                    <div className="flex flex-wrap gap-2">
                      {nomenclature.synonyms_sample.map((name: string) => (
                        <Badge key={name} variant="outline">{name}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Vernaculars</div>
              {renderStatusPill(blockStatus.vernaculars)}
            </div>
            {blockErrors.vernaculars ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.vernaculars)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['vernacular_count', vernaculars.vernacular_count]])}
                {Array.isArray(vernaculars.sample) && vernaculars.sample.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Sample</div>
                    <div className="flex flex-wrap gap-2">
                      {vernaculars.sample.map((item: Record<string, any>, index: number) => {
                        const label = [item.name, item.language ? `(${item.language})` : '']
                          .filter(Boolean)
                          .join(' ')
                        return (
                          <Badge key={`${item.name || 'vernacular'}-${item.language || index}`} variant="outline">
                            {label}
                          </Badge>
                        )
                      })}
                    </div>
                  </div>
                ) : null}
                {vernaculars.by_language && typeof vernaculars.by_language === 'object' ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">By language</div>
                    <div className="space-y-2">
                      {Object.entries(vernaculars.by_language).map(([language, names]) => (
                        <div key={language} className="rounded-md border p-3">
                          <div className="mb-2 text-xs font-medium text-muted-foreground">{language}</div>
                          <div className="flex flex-wrap gap-2">
                            {Array.isArray(names)
                              ? names.map((name) => (
                                  <Badge key={`${language}-${String(name)}`} variant="outline">
                                    {String(name)}
                                  </Badge>
                                ))
                              : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Distribution</div>
              {renderStatusPill(blockStatus.distribution_summary)}
            </div>
            {blockErrors.distribution_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.distribution_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['distribution_count', distributionSummary.distribution_count]])}
                {Array.isArray(distributionSummary.areas) && distributionSummary.areas.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Areas</div>
                    <div className="flex flex-wrap gap-2">
                      {distributionSummary.areas.map((area: string) => (
                        <Badge key={area} variant="outline">{area}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                {Array.isArray(distributionSummary.gazetteers) && distributionSummary.gazetteers.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Gazetteers</div>
                    <div className="flex flex-wrap gap-2">
                      {distributionSummary.gazetteers.map((gazetteer: string) => (
                        <Badge key={gazetteer} variant="outline">{gazetteer}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">References</div>
              {renderStatusPill(blockStatus.references)}
            </div>
            {blockErrors.references ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.references)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['references_count', references.references_count]])}
                {Array.isArray(references.items) && references.items.length > 0 ? (
                  <div className="space-y-2">
                    {references.items.map((item: Record<string, any>, index: number) => (
                      <div key={`${item.id || item.citation || index}`} className="rounded-md border p-3">
                        <div className="text-sm font-medium">{item.title || item.citation || 'Reference'}</div>
                        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                          {item.year ? <div>{String(item.year)}</div> : null}
                          {item.citation ? <div className="break-words">{item.citation}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {Object.keys(links).length > 0 ? (
            <div className="rounded-lg border border-border/70 bg-background p-3">
              <div className="mb-3 text-sm font-semibold">Links</div>
              {renderSummaryRows(Object.entries(links))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

const renderStructuredSummary = (
  data: Record<string, any>,
  t: (key: string, options?: Record<string, any>) => string
) => {
  if (
    data?.provenance?.profile === 'col_rich' ||
    'vernaculars' in data
  ) {
    return renderColStructuredSummary(data, t)
  }

  if (
    data?.provenance?.profile === 'tropicos_rich' ||
    'nomenclature' in data ||
    'references' in data ||
    'distribution_summary' in data
  ) {
    return renderTropicosStructuredSummary(data, t)
  }

  return renderGbifStructuredSummary(data, t)
}

export function EnrichmentTab({
  referenceName,
  hasEnrichment,
  onConfigSaved,
  mode = 'workspace',
  initialSourceId = null,
  onOpenWorkspace,
}: EnrichmentTabProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { isOffline } = useNetworkStatus()
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const previewRequestRef = useRef(0)
  const previewSourceSignatureRef = useRef<string | null>(null)
  const workspaceSectionRef = useRef<HTMLDivElement | null>(null)

  const [referenceConfig, setReferenceConfig] = useState<ReferenceConfigPayload | null>(null)
  const [configLoading, setConfigLoading] = useState(true)
  const [configSaving, setConfigSaving] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [configSaved, setConfigSaved] = useState(false)
  const [persistedEnrichmentEnabled, setPersistedEnrichmentEnabled] = useState(hasEnrichment)

  const [stats, setStats] = useState<EnrichmentStatsResponse | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [job, setJob] = useState<EnrichmentJob | null>(null)
  const [results, setResults] = useState<EnrichmentResult[]>([])
  const [resultsLoading, setResultsLoading] = useState(false)

  const [entities, setEntities] = useState<EntityOption[]>([])
  const [entitiesLoading, setEntitiesLoading] = useState(false)
  const [entitySearch, setEntitySearch] = useState('')
  const [previewQuery, setPreviewQuery] = useState('')
  const [previewScope, setPreviewScope] = useState<string>('all')
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [selectedResult, setSelectedResult] = useState<EnrichmentResult | null>(null)
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null)
  const [pendingInitialSourceId, setPendingInitialSourceId] = useState<string | null>(initialSourceId)
  const [workspacePane, setWorkspacePane] = useState<'config' | 'preview' | 'results'>('config')
  const [previewResultMode, setPreviewResultMode] = useState<'mapped' | 'raw'>('mapped')

  const [jobLoadingScope, setJobLoadingScope] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const apiCategory: ApiCategory =
    referenceConfig?.kind === 'spatial' ? 'spatial' : 'taxonomy'

  const sources = useMemo(
    () => normalizeEnrichmentSources(referenceConfig?.enrichment, apiCategory),
    [apiCategory, referenceConfig?.enrichment]
  )
  const enabledSources = useMemo(
    () => sources.filter((source) => source.enabled),
    [sources]
  )
  const effectiveHasEnrichment = persistedEnrichmentEnabled
  const activeSource = useMemo(
    () => sources.find((source) => source.id === activeSourceId) ?? sources[0] ?? null,
    [activeSourceId, sources]
  )
  const activeSourceStats = useMemo(
    () => stats?.sources.find((item) => item.source_id === activeSource?.id),
    [activeSource?.id, stats?.sources]
  )
  const activeSourceResults = useMemo(
    () => (activeSource ? results.filter((result) => result.source_id === activeSource.id) : []),
    [activeSource, results]
  )
  const previewableSources = useMemo(
    () => (mode === 'quick' ? (enabledSources.length > 0 ? enabledSources : sources) : enabledSources),
    [enabledSources, mode, sources]
  )
  const quickSelectedSource = useMemo(
    () => previewableSources.find((source) => source.id === previewScope) ?? previewableSources[0] ?? null,
    [previewScope, previewableSources]
  )
  const previewSourceSignature = useMemo(() => {
    const previewSource = mode === 'quick' ? quickSelectedSource : activeSource
    if (!previewSource) {
      return null
    }

    return JSON.stringify({
      id: previewSource.id,
      config: previewSource.config,
    })
  }, [activeSource, mode, quickSelectedSource])
  const recentResults = useMemo(() => results.slice(0, 6), [results])

  useEffect(() => {
    setPersistedEnrichmentEnabled(hasEnrichment)
    setConfigSaved(false)
    setWorkspacePane('config')
  }, [referenceName, hasEnrichment])

  useEffect(() => {
    setPendingInitialSourceId(initialSourceId)
  }, [initialSourceId, referenceName])

  useEffect(() => {
    if (!sources.length) {
      setActiveSourceId(null)
      return
    }

    if (!activeSourceId || !sources.some((source) => source.id === activeSourceId)) {
      setActiveSourceId(sources[0].id)
    }
  }, [activeSourceId, sources])

  useEffect(() => {
    if (mode !== 'workspace' || !activeSource?.id) return
    if (previewScope !== activeSource.id) {
      setPreviewScope(activeSource.id)
    }
  }, [activeSource?.id, mode, previewScope])

  useEffect(() => {
    if (mode === 'quick') {
      const fallback = previewableSources[0]?.id ?? 'all'
      if (previewScope === 'all' && fallback !== 'all') {
        setPreviewScope(fallback)
        return
      }
      if (previewScope !== 'all' && !previewableSources.some((source) => source.id === previewScope)) {
        setPreviewScope(fallback)
      }
      return
    }

    if (previewScope !== 'all' && !enabledSources.some((source) => source.id === previewScope)) {
      setPreviewScope('all')
    }
  }, [enabledSources, mode, previewScope, previewableSources])

  const loadReferenceConfig = useCallback(async () => {
    setConfigLoading(true)
    setConfigError(null)
    try {
      const response = await apiClient.get(`/config/references/${referenceName}/config`)
      const normalized = normalizeReferenceConfigPayload(response.data)
      const nextPersistedEnabled = Boolean(normalized?.enrichment?.some((source) => source.enabled))
      setReferenceConfig(normalized)
      setPersistedEnrichmentEnabled(nextPersistedEnabled)
    } catch (err: any) {
      console.error('Failed to load reference config:', err)
      setConfigError(err.response?.data?.detail || t('enrichmentTab.errors.loadConfig'))
      setPersistedEnrichmentEnabled(false)
      setReferenceConfig(null)
    } finally {
      setConfigLoading(false)
    }
  }, [referenceName, t])

  const loadStats = useCallback(async (showLoader = false) => {
    if (showLoader) {
      setStatsLoading(true)
    }
    try {
      const response = await apiClient.get<EnrichmentStatsResponse>(`/enrichment/stats/${referenceName}`)
      setStats(response.data)
    } catch (err) {
      console.error('Failed to load stats:', err)
      setStats((previous) => previous ?? {
        entity_total: 0,
        source_total: 0,
        total: 0,
        enriched: 0,
        pending: 0,
        sources: [],
      })
    } finally {
      if (showLoader) {
        setStatsLoading(false)
      }
    }
  }, [referenceName])

  const loadJobStatus = useCallback(async () => {
    try {
      const response = await apiClient.get<EnrichmentJob>(`/enrichment/job/${referenceName}`)
      setJob(response.data)
      return response.data
    } catch (err: any) {
      if (err.response?.status !== 404) {
        console.error('Failed to load job status:', err)
      }
      setJob(null)
      return null
    }
  }, [referenceName])

  const loadResults = useCallback(async () => {
    setResultsLoading(true)
    try {
      const response = await apiClient.get(`/enrichment/results/${referenceName}`, {
        params: { limit: 100 },
      })
      setResults(response.data.results || [])
    } catch (err) {
      console.error('Failed to load results:', err)
      setResults([])
    } finally {
      setResultsLoading(false)
    }
  }, [referenceName])

  const loadEntities = useCallback(async (search = '') => {
    setEntitiesLoading(true)
    try {
      const response = await apiClient.get(`/enrichment/entities/${referenceName}`, {
        params: { limit: 50, search },
      })
      setEntities(response.data.entities || [])
    } catch (err) {
      console.error('Failed to load entities:', err)
      setEntities([])
    } finally {
      setEntitiesLoading(false)
    }
  }, [referenceName])

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return

    pollIntervalRef.current = setInterval(async () => {
      const jobData = await loadJobStatus()
      await loadStats()

      if (!jobData || ['completed', 'failed', 'cancelled'].includes(jobData.status)) {
        stopPolling()
        void loadResults()
      }
    }, 1000)
  }, [loadJobStatus, loadResults, loadStats, stopPolling])

  useEffect(() => {
    void loadReferenceConfig()

    return () => stopPolling()
  }, [loadReferenceConfig, referenceName, stopPolling])

  useEffect(() => {
    if (!effectiveHasEnrichment) {
      stopPolling()
      setStatsLoading(false)
      setStats(null)
      setJob(null)
      setResults([])
      return
    }

    void loadStats(true)
    void loadJobStatus().then((jobData) => {
      if (jobData && ['running', 'paused', 'paused_offline'].includes(jobData.status)) {
        startPolling()
      }
    })

    return () => stopPolling()
  }, [effectiveHasEnrichment, loadJobStatus, loadStats, referenceName, startPolling, stopPolling])

  useEffect(() => {
    if (!effectiveHasEnrichment) return

    if (mode === 'quick') {
      if (results.length === 0) {
        void loadResults()
      }
      if (entities.length === 0 && !entitiesLoading) {
        void loadEntities()
      }
      return
    }

    if (workspacePane === 'results') {
      void loadResults()
    } else if (workspacePane === 'preview' && entities.length === 0 && !entitiesLoading) {
      void loadEntities()
    }
  }, [
    workspacePane,
    effectiveHasEnrichment,
    entities.length,
    entitiesLoading,
    loadEntities,
    loadResults,
    mode,
    results.length,
  ])

  const updateEnrichmentList = useCallback(
    (
      updater:
        | ReferenceEnrichmentConfig[]
        | ((previous: ReferenceEnrichmentConfig[]) => ReferenceEnrichmentConfig[])
    ) => {
      setConfigSaved(false)
      setReferenceConfig((previous) => {
        if (!previous) return previous
        const current = previous.enrichment ?? []
        const next = typeof updater === 'function' ? updater(current) : updater
        return {
          ...previous,
          enrichment: next,
        }
      })
    },
    []
  )

  const addSource = () => {
    const newSource = createDefaultEnrichmentSource(apiCategory, sources.length)
    updateEnrichmentList((previous) => [
      ...previous,
      newSource,
    ])
    setActiveSourceId(newSource.id ?? null)
    setWorkspacePane('config')
  }

  const updateSource = (sourceId: string, updater: (source: NormalizedEnrichmentSource) => ReferenceEnrichmentConfig) => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return normalized.map((source) => (
        source.id === sourceId ? updater(source) : apiConfigToEnrichment(source, source.config)
      ))
    })
  }

  const updateSourceLabel = (sourceId: string, label: string) => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return normalized.map((source) => (
        source.id === sourceId
          ? {
              ...apiConfigToEnrichment(source, source.config),
              label,
            }
          : apiConfigToEnrichment(source, source.config)
      ))
    })
  }

  const updateSourceConfig = (sourceId: string, apiConfig: ApiConfig) => {
    updateSource(sourceId, (source) => apiConfigToEnrichment(source, apiConfig))
  }

  const applyPresetLabel = (sourceId: string, label: string) => {
    updateSourceLabel(sourceId, label)
    resetPreviewState(sourceId)
  }

  const toggleSourceEnabled = (sourceId: string, enabled: boolean) => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return normalized.map((source) => (
        source.id === sourceId
          ? apiConfigToEnrichment(source, {
              ...source.config,
              enabled,
            })
          : apiConfigToEnrichment(source, source.config)
      ))
    })
  }

  const duplicateSource = (sourceId: string) => {
    const index = sources.findIndex((source) => source.id === sourceId)
    if (index === -1) return

    const source = sources[index]
    const duplicate = createDefaultEnrichmentSource(apiCategory, sources.length)
    const entry = apiConfigToEnrichment(
      {
        id: duplicate.id!,
        label: `${source.label} Copy`,
      },
      source.config
    )

    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return [
        ...normalized.slice(0, index + 1).map((item) => apiConfigToEnrichment(item, item.config)),
        entry,
        ...normalized.slice(index + 1).map((item) => apiConfigToEnrichment(item, item.config)),
      ]
    })
    setActiveSourceId(duplicate.id ?? null)
    setWorkspacePane('config')
  }

  const moveSource = (sourceId: string, direction: 'up' | 'down') => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      const index = normalized.findIndex((source) => source.id === sourceId)
      if (index === -1) return previous

      const targetIndex = direction === 'up' ? index - 1 : index + 1
      if (targetIndex < 0 || targetIndex >= normalized.length) {
        return previous
      }

      const reordered = [...normalized]
      const [moved] = reordered.splice(index, 1)
      reordered.splice(targetIndex, 0, moved)

      return reordered.map((source) => apiConfigToEnrichment(source, source.config))
    })
  }

  const removeSource = (sourceId: string) => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return normalized
        .filter((source) => source.id !== sourceId)
        .map((source) => apiConfigToEnrichment(source, source.config))
    })
  }

  const saveEnrichmentConfig = async () => {
    if (!referenceConfig) return

    setConfigSaving(true)
    setConfigError(null)
    setConfigSaved(false)
    try {
      await apiClient.put(`/config/references/${referenceName}/config`, referenceConfig)
      setConfigSaved(true)
      await loadReferenceConfig()
      await loadStats(true)
      onConfigSaved?.()
      toast.success(t('enrichmentTab.toasts.configSaved'))
    } catch (err: any) {
      console.error('Failed to save enrichment config:', err)
      setConfigError(err.response?.data?.detail || t('enrichmentTab.errors.saveConfig'))
      toast.error(t('enrichmentTab.toasts.saveErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.saveConfig'),
      })
    } finally {
      setConfigSaving(false)
    }
  }

  const trackStartedJob = (startedJob: EnrichmentJob, pendingCount: number) => {
    useNotificationStore.getState().trackJob({
      jobId: startedJob.id,
      jobType: 'enrichment',
      status: 'running',
      progress: 0,
      message: t('enrichmentTab.toasts.startedDescription', {
        count: pendingCount,
      }),
      startedAt: new Date().toISOString(),
      meta: { referenceName },
    })
  }

  const startGlobalJob = async () => {
    if (isOffline) return

    setJobLoadingScope('all')
    try {
      const response = await apiClient.post<EnrichmentJob>(`/enrichment/start/${referenceName}`)
      setJob(response.data)
      startPolling()
      trackStartedJob(response.data, stats?.pending ?? 0)
      toast.success(t('enrichmentTab.toasts.startedTitle'), {
        description: t('enrichmentTab.toasts.startedDescription', {
          count: stats?.pending ?? 0,
        }),
      })
    } catch (err: any) {
      console.error('Failed to start job:', err)
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.startJob'),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }

  const startSourceJob = async (sourceId: string) => {
    if (isOffline) return

    const sourceStats = stats?.sources.find((source) => source.source_id === sourceId)
    setJobLoadingScope(sourceId)
    try {
      const response = await apiClient.post<EnrichmentJob>(`/enrichment/start/${referenceName}/${sourceId}`)
      setJob(response.data)
      startPolling()
      trackStartedJob(response.data, sourceStats?.pending ?? 0)
      toast.success(t('enrichmentTab.toasts.startedTitle'), {
        description: t('enrichmentTab.toasts.startedDescription', {
          count: sourceStats?.pending ?? 0,
        }),
      })
    } catch (err: any) {
      console.error('Failed to start source job:', err)
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.startJob'),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }

  const pauseJob = async (sourceId?: string) => {
    setJobLoadingScope(sourceId ?? 'all')
    try {
      const path = sourceId
        ? `/enrichment/pause/${referenceName}/${sourceId}`
        : `/enrichment/pause/${referenceName}`
      await apiClient.post(path)
      await loadJobStatus()
      toast.info(t('enrichmentTab.toasts.pausedTitle'), {
        description: t('enrichmentTab.toasts.pausedDescription'),
      })
    } catch (err: any) {
      console.error('Failed to pause job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.pauseJob'),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }

  const resumeJob = async (sourceId?: string) => {
    if (isOffline) return

    setJobLoadingScope(sourceId ?? 'all')
    try {
      const path = sourceId
        ? `/enrichment/resume/${referenceName}/${sourceId}`
        : `/enrichment/resume/${referenceName}`
      await apiClient.post(path)
      await loadJobStatus()
      startPolling()
      toast.success(t('enrichmentTab.toasts.resumedTitle'), {
        description: t('enrichmentTab.toasts.resumedDescription'),
      })
    } catch (err: any) {
      console.error('Failed to resume job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.resumeJob'),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }

  const cancelJob = async (sourceId?: string) => {
    setJobLoadingScope(sourceId ?? 'all')
    try {
      const path = sourceId
        ? `/enrichment/cancel/${referenceName}/${sourceId}`
        : `/enrichment/cancel/${referenceName}`
      await apiClient.post(path)
      await loadJobStatus()
      stopPolling()
      await loadStats()
      toast.warning(t('enrichmentTab.toasts.cancelledTitle'), {
        description: t('enrichmentTab.toasts.cancelledDescription', {
          count: job?.processed ?? 0,
        }),
      })
    } catch (err: any) {
      console.error('Failed to cancel job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.cancelJob'),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([
        loadStats(),
        loadJobStatus(),
        mode === 'quick' || workspacePane === 'results' ? loadResults() : Promise.resolve(),
        mode === 'quick' ? loadEntities(entitySearch) : Promise.resolve(),
      ])
    } finally {
      setIsRefreshing(false)
    }
  }

  const resetPreviewState = useCallback((nextScope?: string) => {
    previewRequestRef.current += 1
    setPreviewLoading(false)
    setPreviewError(null)
    setPreviewData(null)
    if (nextScope !== undefined) {
      setPreviewScope(nextScope)
    }
  }, [])

  useEffect(() => {
    if (!pendingInitialSourceId || !sources.some((source) => source.id === pendingInitialSourceId)) {
      return
    }

    setActiveSourceId(pendingInitialSourceId)
    setWorkspacePane('config')
    resetPreviewState(pendingInitialSourceId)
    setPendingInitialSourceId(null)
  }, [pendingInitialSourceId, resetPreviewState, sources])

  useEffect(() => {
    if (mode !== 'workspace') {
      return
    }
    workspaceSectionRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [activeSource?.id, mode, workspacePane])

  useEffect(() => {
    if (!previewSourceSignature) {
      previewSourceSignatureRef.current = null
      return
    }

    if (previewSourceSignatureRef.current === null) {
      previewSourceSignatureRef.current = previewSourceSignature
      return
    }

    if (previewSourceSignatureRef.current === previewSourceSignature) {
      return
    }

    previewSourceSignatureRef.current = previewSourceSignature
    resetPreviewState(mode === 'quick' ? quickSelectedSource?.id : activeSource?.id)
  }, [activeSource?.id, mode, previewSourceSignature, quickSelectedSource?.id, resetPreviewState])

  const previewEnrichment = async (queryOverride?: string, scopeOverride?: string) => {
    const query = (queryOverride ?? previewQuery).trim()
    if (!query) return
    const nextScope = scopeOverride ?? previewScope
    const requestId = ++previewRequestRef.current

    setPreviewLoading(true)
    setPreviewError(null)
    setPreviewData(null)
    if (nextScope !== previewScope) {
      setPreviewScope(nextScope)
    }

    try {
      const response = await apiClient.post<PreviewResponse>(
        `/enrichment/preview/${referenceName}`,
        {
          query,
          source_id: nextScope === 'all' ? undefined : nextScope,
        }
      )
      if (requestId !== previewRequestRef.current) {
        return
      }
      setPreviewQuery(query)
      setPreviewData(response.data)
    } catch (err: any) {
      if (requestId !== previewRequestRef.current) {
        return
      }
      setPreviewError(err.response?.data?.detail || t('enrichmentTab.errors.preview'))
    } finally {
      if (requestId === previewRequestRef.current) {
        setPreviewLoading(false)
      }
    }
  }

  const runningSingleSourceId = job?.mode === 'single' ? job.source_id ?? undefined : undefined

  const getSourceProgress = (sourceId: string, sourceStats: EnrichmentSourceStats | undefined) => {
    if (job && job.current_source_id === sourceId) {
      const total = job.current_source_total ?? sourceStats?.total ?? 0
      const processed = job.current_source_processed ?? 0
      const percentage = total > 0 ? (processed / total) * 100 : 0
      return {
        total,
        processed,
        percentage,
      }
    }

    const total = sourceStats?.total ?? 0
    const processed = sourceStats?.enriched ?? 0
    const percentage = total > 0 ? (processed / total) * 100 : 0
    return {
      total,
      processed,
      percentage,
    }
  }

  const activeSourceProgress = activeSource
    ? getSourceProgress(activeSource.id, activeSourceStats)
    : null
  const activeSourceIndex = activeSource
    ? sources.findIndex((source) => source.id === activeSource.id)
    : -1
  const activePreviewResult = activeSource
    ? previewData?.results?.find((result) => result.source_id === activeSource.id) ?? null
    : null
  const isTerminalJob = !job || ['completed', 'failed', 'cancelled'].includes(job.status)
  const isRunningSingleSource = activeSource ? runningSingleSourceId === activeSource.id : false
  const canStartActiveSource = Boolean(
    activeSource &&
      activeSource.enabled &&
      isTerminalJob &&
      (activeSourceStats?.pending ?? 0) > 0
  )

  if (mode === 'quick') {
    const quickPreviewResult =
      quickSelectedSource && previewData?.results?.length
        ? previewData.results.find((result) => result.source_id === quickSelectedSource.id) ?? null
        : null

    return (
      <div className="space-y-4">
        {configError ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{configError}</AlertDescription>
          </Alert>
        ) : null}

        <Card className="sticky top-0 z-20 overflow-hidden border-border/70 bg-background shadow-sm">
          <CardContent className="space-y-4 p-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {t('enrichmentTab.summary.enabledSources', {
                    defaultValue: '{{count}} source(s) enabled',
                    count: enabledSources.length,
                  })}
                </Badge>
                <Badge variant="outline">
                  {t('enrichmentTab.summary.totalSources', {
                    defaultValue: '{{count}} source(s) configured',
                    count: sources.length,
                  })}
                </Badge>
                {stats ? (
                  <>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.enriched')}: {stats.enriched.toLocaleString()}
                    </Badge>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.pending')}: {stats.pending.toLocaleString()}
                    </Badge>
                  </>
                ) : null}
              </div>

              {job ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge variant={job.status === 'running' ? 'default' : 'outline'}>
                      {t(`enrichmentTab.status.${job.status}`, {
                        defaultValue: job.status,
                      })}
                    </Badge>
                    {job.current_source_label ? (
                      <span className="text-muted-foreground">{job.current_source_label}</span>
                    ) : null}
                    {job.current_entity ? (
                      <span className="truncate text-muted-foreground">
                        {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                      </span>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{t('enrichmentTab.cards.progress')}</span>
                      <span>
                        {job.processed.toLocaleString()} / {job.total.toLocaleString()}
                      </span>
                    </div>
                    <Progress value={job.total > 0 ? (job.processed / job.total) * 100 : 0} className="h-1.5" />
                  </div>
                </div>
              ) : stats?.total ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t('enrichmentTab.cards.progress')}</span>
                    <span>
                      {stats.enriched.toLocaleString()} / {stats.total.toLocaleString()}
                    </span>
                  </div>
                  <Progress value={stats.total > 0 ? (stats.enriched / stats.total) * 100 : 0} className="h-1.5" />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('enrichmentTab.actions.description')}
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-4">
              {isTerminalJob ? (
                <Button
                  onClick={startGlobalJob}
                  disabled={jobLoadingScope !== null || !stats || stats.pending === 0 || isOffline}
                  title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
                >
                  {jobLoadingScope === 'all' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  {t('enrichmentTab.runtime.startAll', {
                    defaultValue: 'Lancer toutes les APIs',
                  })}
                </Button>
              ) : job?.status === 'running' ? (
                <>
                  <Button variant="secondary" onClick={() => pauseJob()} disabled={jobLoadingScope !== null}>
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Pause className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.pause')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : job?.status === 'paused' || job?.status === 'paused_offline' ? (
                <>
                  <Button
                    onClick={() => resumeJob()}
                    disabled={jobLoadingScope !== null || isOffline}
                    title={isOffline ? t('enrichmentTab.offline.internetRequiredResume') : undefined}
                  >
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.resume')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : null}

              <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                {t('common:actions.refresh')}
              </Button>

              {onOpenWorkspace ? (
                <Button variant="outline" onClick={() => onOpenWorkspace(quickSelectedSource?.id)}>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {t('dashboard.actions.openWorkspace', {
                    defaultValue: 'Ouvrir le workspace',
                  })}
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {isOffline ? (
          <Alert>
            <WifiOff className="h-4 w-4" />
            <AlertTitle>{t('enrichmentTab.offline.title')}</AlertTitle>
            <AlertDescription>{t('enrichmentTab.offline.description')}</AlertDescription>
          </Alert>
        ) : null}

        {configLoading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : sources.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-start gap-3 p-6">
              <div>
                <h3 className="font-medium">
                  {t('enrichmentTab.config.empty', {
                    defaultValue: 'Aucune source API configurée pour cette référence.',
                  })}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {t('dashboard.enrichment.quickEmpty', {
                    defaultValue: 'Le panel rapide sert à lancer et tester. Ouvre le workspace pour configurer les sources.',
                  })}
                </p>
              </div>
              {onOpenWorkspace ? (
                <Button onClick={() => onOpenWorkspace(quickSelectedSource?.id)}>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {t('dashboard.actions.openWorkspace', {
                    defaultValue: 'Ouvrir le workspace',
                  })}
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(400px,1.1fr)]">
            <Card className="border-border/70">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  {t('enrichmentTab.config.sourcesTitle', {
                    defaultValue: 'API sources',
                  })}
                </CardTitle>
                <CardDescription>
                  {t('dashboard.enrichment.quickPanelDescription', {
                    defaultValue: 'Sélectionne une source pour la tester ou lancer un enrichissement rapide.',
                  })}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {sources.map((source) => {
                  const sourceStats = stats?.sources.find((item) => item.source_id === source.id)
                  const sourceProgress = getSourceProgress(source.id, sourceStats)
                  const isSelected = quickSelectedSource?.id === source.id
                  const canStartSource =
                    source.enabled &&
                    (!job || ['completed', 'failed', 'cancelled'].includes(job.status)) &&
                    (sourceStats?.pending ?? 0) > 0

                  return (
                    <div
                      key={source.id}
                      className={`rounded-xl border px-4 py-3 transition-colors ${
                        isSelected ? 'border-primary/40 bg-primary/5' : 'border-border/70 bg-background'
                      }`}
                    >
                      <div className="space-y-3">
                        <div className="min-w-0 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              className="truncate text-left font-medium hover:text-primary"
                              onClick={() => resetPreviewState(source.id)}
                            >
                              {source.label}
                            </button>
                            <Badge variant={source.enabled ? 'secondary' : 'outline'}>
                              {source.enabled
                                ? t('sources:configEditor.enabled')
                                : t('sources:configEditor.disabled')}
                            </Badge>
                            {sourceStats ? (
                              <Badge variant="outline">
                                {t(`enrichmentTab.status.${sourceStats.status}`, {
                                  defaultValue: sourceStats.status,
                                })}
                              </Badge>
                            ) : null}
                          </div>
                          <div className="truncate text-xs text-muted-foreground">
                            {source.config.api_url || source.plugin}
                          </div>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                              <span>{t('enrichmentTab.cards.progress')}</span>
                              <span>
                                {sourceProgress.processed.toLocaleString()} / {sourceProgress.total.toLocaleString()}
                              </span>
                            </div>
                            <Progress value={sourceProgress.percentage} className="h-1.5" />
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-3">
                          <Button
                            type="button"
                            size="sm"
                            variant={isSelected ? 'default' : 'outline'}
                            onClick={() => resetPreviewState(source.id)}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.testApi', {
                              defaultValue: "Tester l'API",
                            })}
                          </Button>

                          {canStartSource ? (
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => startSourceJob(source.id)}
                              disabled={jobLoadingScope !== null || isOffline}
                            >
                              {jobLoadingScope === source.id ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="mr-2 h-4 w-4" />
                              )}
                              {t('enrichmentTab.runtime.startSource', {
                                defaultValue: 'Lancer cette API',
                              })}
                            </Button>
                          ) : null}

                          {onOpenWorkspace ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => onOpenWorkspace(source.id)}
                            >
                              {t('common:actions.edit')}
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card className="border-border/70">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    {t('dashboard.actions.testApi', {
                      defaultValue: "Tester l'API",
                    })}
                  </CardTitle>
                  <div className="space-y-1">
                    <CardDescription>
                      {quickSelectedSource
                        ? quickSelectedSource.label
                        : t('dashboard.enrichment.quickSelectSource', {
                            defaultValue: 'Sélectionne une source pour tester sa réponse.',
                          })}
                    </CardDescription>
                    {quickSelectedSource?.config.api_url ? (
                      <div className="truncate text-xs text-muted-foreground">
                        {quickSelectedSource.config.api_url}
                      </div>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {quickSelectedSource?.enabled ? (
                    <>
                      <div className="space-y-2">
                        <Label>{t('common:labels.name')}</Label>
                        <div className="flex gap-2">
                          <Input
                            placeholder={t('enrichmentTab.preview.manualInput')}
                            value={previewQuery}
                            onChange={(event) => setPreviewQuery(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === 'Enter') {
                                void previewEnrichment(undefined, quickSelectedSource.id)
                              }
                            }}
                          />
                          <Button
                            type="button"
                            onClick={() => previewEnrichment(undefined, quickSelectedSource.id)}
                            disabled={previewLoading || !previewQuery.trim()}
                          >
                            {previewLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>

                      {entities.length > 0 ? (
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">
                            {t('dashboard.enrichment.quickExamples', {
                              defaultValue: 'Essayer avec une entité existante',
                            })}
                          </Label>
                          <div className="flex flex-wrap gap-2">
                            {entities.slice(0, 6).map((entity) => (
                              <Button
                                key={entity.id}
                                type="button"
                                size="sm"
                                variant="outline"
                                className="max-w-full"
                                onClick={() => {
                                  setPreviewQuery(entity.name)
                                  void previewEnrichment(entity.name, quickSelectedSource.id)
                                }}
                              >
                                <span className="truncate">{entity.name}</span>
                              </Button>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div className="rounded-lg border bg-muted/20 p-3">
                        {previewLoading ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                          </div>
                        ) : previewError ? (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{previewError}</AlertDescription>
                          </Alert>
                        ) : quickPreviewResult?.success ? (
                          <div className="space-y-3">
                            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/70 bg-background p-1">
                              <Button
                                type="button"
                                size="sm"
                                variant={previewResultMode === 'mapped' ? 'default' : 'ghost'}
                                onClick={() => setPreviewResultMode('mapped')}
                              >
                                {t('dashboard.enrichment.mappedFields', {
                                  defaultValue: 'Champs mappés',
                                })}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant={previewResultMode === 'raw' ? 'default' : 'ghost'}
                                onClick={() => setPreviewResultMode('raw')}
                              >
                                {t('dashboard.enrichment.rawApiResponse', {
                                  defaultValue: 'Réponse brute API',
                                })}
                              </Button>
                            </div>

                            {previewResultMode === 'mapped' ? (
                              quickPreviewResult.data && Object.keys(quickPreviewResult.data).length > 0 ? (
                                isStructuredSourceSummary(quickPreviewResult.data)
                                  ? renderStructuredSummary(quickPreviewResult.data, t)
                                  : renderMappedPreview(quickPreviewResult.data)
                              ) : (
                                <div className="py-8 text-center text-sm text-muted-foreground">
                                  {t('dashboard.enrichment.noMappedFields', {
                                    defaultValue: 'Aucun champ mappé pour cette source.',
                                  })}
                                </div>
                              )
                            ) : quickPreviewResult.raw_data !== undefined ? (
                              renderRawPreview(quickPreviewResult.raw_data)
                            ) : (
                              <div className="py-8 text-center text-sm text-muted-foreground">
                                {t('dashboard.enrichment.noRawApiResponse', {
                                  defaultValue: 'Aucune réponse brute disponible pour ce test.',
                                })}
                              </div>
                            )}
                          </div>
                        ) : quickPreviewResult?.error ? (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{quickPreviewResult.error}</AlertDescription>
                          </Alert>
                        ) : (
                          <div className="py-8 text-center text-sm text-muted-foreground">
                            {t('dashboard.enrichment.quickTesterEmpty', {
                              defaultValue: "Lance un test pour voir immédiatement la réponse de l'API.",
                            })}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                      {t('dashboard.enrichment.quickTesterDisabled', {
                        defaultValue: 'Active cette source dans le workspace complet pour pouvoir la tester.',
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="border-border/70">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    {t('enrichmentTab.tabs.results')}
                  </CardTitle>
                  <CardDescription>
                    {t('dashboard.enrichment.quickResultsDescription', {
                      defaultValue: 'Aperçu rapide des derniers traitements. Le détail complet est dans le workspace.',
                    })}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {resultsLoading ? (
                    <div className="flex items-center justify-center py-6">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : recentResults.length > 0 ? (
                    <div className="space-y-2">
                      {recentResults.map((result) => (
                        <div
                          key={`${result.source_id}-${getResultEntityName(result)}-${result.processed_at}`}
                          className="rounded-lg border px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">{getResultEntityName(result)}</div>
                              <div className="truncate text-xs text-muted-foreground">{result.source_label}</div>
                            </div>
                            <Badge variant={result.success ? 'secondary' : 'destructive'}>
                              {result.success
                                ? t('enrichmentTab.result.success')
                                : t('enrichmentTab.result.failed')}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {t('enrichmentTab.results.emptyDescription')}
                    </p>
                  )}

                  {onOpenWorkspace ? (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => onOpenWorkspace(quickSelectedSource?.id)}
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      {t('dashboard.actions.openWorkspace', {
                        defaultValue: 'Ouvrir le workspace',
                      })}
                    </Button>
                  ) : null}
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {configError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{configError}</AlertDescription>
        </Alert>
      ) : null}

      {configSaved ? (
        <Alert className="border-success/30 bg-success/10">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <AlertDescription className="text-success">
            {t('sources:configEditor.savedSuccess')}
          </AlertDescription>
        </Alert>
      ) : null}

      <Card className="sticky top-0 z-20 overflow-hidden border-border/70 bg-background shadow-sm">
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {t('enrichmentTab.summary.enabledSources', {
                    defaultValue: '{{count}} source(s) enabled',
                    count: enabledSources.length,
                  })}
                </Badge>
                <Badge variant="outline">
                  {t('enrichmentTab.summary.totalSources', {
                    defaultValue: '{{count}} source(s) configured',
                    count: sources.length,
                  })}
                </Badge>
                {stats ? (
                  <>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.enriched')}: {stats.enriched.toLocaleString()}
                    </Badge>
                    <Badge variant="outline">
                      {t('enrichmentTab.stats.pending')}: {stats.pending.toLocaleString()}
                    </Badge>
                  </>
                ) : null}
              </div>

              {job ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge variant={job.status === 'running' ? 'default' : 'outline'}>
                      {t(`enrichmentTab.status.${job.status}`, {
                        defaultValue: job.status,
                      })}
                    </Badge>
                    {job.current_source_label ? (
                      <span className="text-muted-foreground">{job.current_source_label}</span>
                    ) : null}
                    {job.current_entity ? (
                      <span className="truncate text-muted-foreground">
                        {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                      </span>
                    ) : null}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{t('enrichmentTab.cards.progress')}</span>
                      <span>
                        {job.processed.toLocaleString()} / {job.total.toLocaleString()}
                      </span>
                    </div>
                    <Progress value={job.total > 0 ? (job.processed / job.total) * 100 : 0} className="h-1.5" />
                  </div>
                </div>
              ) : statsLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('tree.loading', 'Loading...')}
                </div>
              ) : stats?.total ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t('enrichmentTab.cards.progress')}</span>
                    <span>
                      {stats.enriched.toLocaleString()} / {stats.total.toLocaleString()}
                    </span>
                  </div>
                  <Progress value={stats.total > 0 ? (stats.enriched / stats.total) * 100 : 0} className="h-1.5" />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('enrichmentTab.actions.description')}
                </p>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={saveEnrichmentConfig} disabled={configSaving || configLoading || !referenceConfig}>
                {configSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('sources:configEditor.saving')}
                  </>
                ) : (
                  t('sources:configEditor.save')
                )}
              </Button>

              {isTerminalJob ? (
                <Button
                  onClick={startGlobalJob}
                  disabled={jobLoadingScope !== null || !stats || stats.pending === 0 || isOffline}
                  title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
                >
                  {jobLoadingScope === 'all' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  {t('enrichmentTab.runtime.startAll', {
                    defaultValue: 'Lancer toutes les APIs',
                  })}
                </Button>
              ) : job?.status === 'running' ? (
                <>
                  <Button variant="secondary" onClick={() => pauseJob()} disabled={jobLoadingScope !== null}>
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Pause className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.pause')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : job?.status === 'paused' || job?.status === 'paused_offline' ? (
                <>
                  <Button
                    onClick={() => resumeJob()}
                    disabled={jobLoadingScope !== null || isOffline}
                    title={isOffline ? t('enrichmentTab.offline.internetRequiredResume') : undefined}
                  >
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.resume')}
                  </Button>
                  <Button variant="destructive" onClick={() => cancelJob()} disabled={jobLoadingScope !== null}>
                    <StopCircle className="mr-2 h-4 w-4" />
                    {t('common:actions.cancel')}
                  </Button>
                </>
              ) : null}

              <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                {t('common:actions.refresh')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {isOffline ? (
        <Alert>
          <WifiOff className="h-4 w-4" />
          <AlertTitle>{t('enrichmentTab.offline.title')}</AlertTitle>
          <AlertDescription>{t('enrichmentTab.offline.description')}</AlertDescription>
        </Alert>
      ) : null}

      {job?.error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{t('common:status.error')}</AlertTitle>
          <AlertDescription>{job.error}</AlertDescription>
        </Alert>
      ) : null}

      {configLoading || !referenceConfig ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : sources.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-start gap-3 p-6">
            <div>
              <h3 className="font-medium">
                {t('enrichmentTab.config.empty', {
                  defaultValue: 'Aucune source API configurée pour cette référence.',
                })}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {t('dashboard.enrichment.workspaceEmpty', {
                  defaultValue: 'Ajoute une première source pour configurer, tester et lancer ton enrichissement.',
                })}
              </p>
            </div>
            <Button onClick={addSource}>
              <Plus className="mr-2 h-4 w-4" />
              {t('enrichmentTab.config.addSource', {
                defaultValue: 'Ajouter une API',
              })}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <Card className="border-border/70">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-sm font-medium">
                    {t('enrichmentTab.config.sourcesTitle', {
                      defaultValue: 'API sources',
                    })}
                  </CardTitle>
                  <CardDescription>
                    {t('dashboard.enrichment.workspaceListDescription', {
                      defaultValue: 'Sélectionne une source pour la configurer ou la tester.',
                    })}
                  </CardDescription>
                </div>
                <Button type="button" size="sm" onClick={addSource}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {sources.map((source) => {
                  const sourceStats = stats?.sources.find((item) => item.source_id === source.id)
                  const sourceProgress = getSourceProgress(source.id, sourceStats)
                  const isSelected = activeSource?.id === source.id

                  return (
                    <button
                      key={source.id}
                      type="button"
                      onClick={() => {
                        setActiveSourceId(source.id)
                        setWorkspacePane('config')
                        resetPreviewState(source.id)
                      }}
                      className={`w-full rounded-xl border px-3 py-3 text-left transition-colors ${
                        isSelected ? 'border-primary/40 bg-primary/5' : 'border-border/70 bg-background hover:bg-muted/30'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium">{source.label}</div>
                          <div className="mt-1 truncate text-xs text-muted-foreground">
                            {source.config.api_url || source.plugin}
                          </div>
                        </div>
                        <Badge variant={source.enabled ? 'secondary' : 'outline'}>
                          {source.enabled
                            ? t('sources:configEditor.enabled')
                            : t('sources:configEditor.disabled')}
                        </Badge>
                      </div>

                      <div className="mt-3 space-y-1.5">
                        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                          <span>{sourceStats?.status || t('enrichmentTab.status.ready')}</span>
                          <span>
                            {sourceProgress.processed.toLocaleString()} / {sourceProgress.total.toLocaleString()}
                          </span>
                        </div>
                        <Progress value={sourceProgress.percentage} className="h-1.5" />
                      </div>
                      {sourceStats ? (
                        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                          <span>
                            {t('enrichmentTab.stats.enriched')}: {sourceStats.enriched.toLocaleString()}
                          </span>
                          <span>
                            {t('enrichmentTab.stats.pending')}: {sourceStats.pending.toLocaleString()}
                          </span>
                        </div>
                      ) : null}
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {activeSource ? (
            <>
              <div ref={workspaceSectionRef} className="space-y-4">
                <Card className="border-border/70">
                  <CardHeader className="space-y-5 pb-4">
                    <div className="space-y-3">
                      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline">{activeSource.id}</Badge>
                          <Badge
                            variant={
                              activeSourceStats?.status === 'running' || isRunningSingleSource
                                ? 'default'
                                : 'outline'
                            }
                          >
                            {t(`enrichmentTab.status.${activeSourceStats?.status || 'ready'}`, {
                              defaultValue: activeSourceStats?.status || 'ready',
                            })}
                          </Badge>
                        </div>

                        <div className="flex items-center justify-between gap-3 rounded-full border border-border/70 bg-muted/20 px-3 py-2 xl:min-w-[230px] xl:justify-start">
                          <div className="min-w-0">
                            <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                              {t('dashboard.enrichment.sourceAvailability', {
                                defaultValue: 'Disponibilité',
                              })}
                            </div>
                            <div className="text-sm font-medium">
                              {activeSource.enabled
                                ? t('sources:configEditor.enabled')
                                : t('sources:configEditor.disabled')}
                            </div>
                          </div>
                          <Switch
                            id={`source-enabled-${activeSource.id}`}
                            checked={activeSource.enabled}
                            onCheckedChange={(checked) => toggleSourceEnabled(activeSource.id, checked)}
                          />
                        </div>
                      </div>

                      <div className="min-w-0 space-y-2">
                        <Label htmlFor={`source-label-${activeSource.id}`} className="text-xs font-medium text-muted-foreground">
                          {t('enrichmentTab.config.sourceLabel', {
                            defaultValue: 'Nom de la source',
                          })}
                        </Label>
                        <Input
                          id={`source-label-${activeSource.id}`}
                          value={activeSource.label}
                          onChange={(event) => updateSourceLabel(activeSource.id, event.target.value)}
                          placeholder={t('enrichmentTab.config.sourceLabel', {
                            defaultValue: 'Nom de la source',
                          })}
                          className="max-w-md xl:max-w-lg"
                        />
                        <div className="truncate text-xs text-muted-foreground">
                          {activeSource.config.api_url || activeSource.plugin}
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{t('enrichmentTab.cards.progress')}</span>
                          <span>
                            {activeSourceProgress?.processed.toLocaleString() ?? 0} / {activeSourceProgress?.total.toLocaleString() ?? 0}
                          </span>
                        </div>
                        <Progress value={activeSourceProgress?.percentage ?? 0} className="h-1.5" />
                      </div>

                      {activeSourceStats ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={activeSource.enabled ? 'secondary' : 'outline'}>
                            {activeSource.enabled
                              ? t('sources:configEditor.enabled')
                              : t('sources:configEditor.disabled')}
                          </Badge>
                          <Badge variant="outline">
                            {t('enrichmentTab.stats.enriched')}: {activeSourceStats.enriched.toLocaleString()}
                          </Badge>
                          <Badge variant="outline">
                            {t('enrichmentTab.stats.pending')}: {activeSourceStats.pending.toLocaleString()}
                          </Badge>
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={activeSource.enabled ? 'secondary' : 'outline'}>
                            {activeSource.enabled
                              ? t('sources:configEditor.enabled')
                              : t('sources:configEditor.disabled')}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-3 border-t border-border/70 pt-4">
                      <div className="flex flex-col gap-3 2xl:flex-row 2xl:items-center 2xl:justify-between">
                        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/70 bg-muted/20 p-1">
                          <Button
                            type="button"
                            size="sm"
                            variant={workspacePane === 'config' ? 'default' : 'ghost'}
                            onClick={() => setWorkspacePane('config')}
                          >
                            <Settings className="mr-2 h-4 w-4" />
                            {t('reference.configuration', {
                              defaultValue: 'Configuration',
                            })}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant={workspacePane === 'preview' ? 'default' : 'ghost'}
                            onClick={() => setWorkspacePane('preview')}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            {t('dashboard.actions.testApi', {
                              defaultValue: "Tester l'API",
                            })}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant={workspacePane === 'results' ? 'default' : 'ghost'}
                            onClick={() => setWorkspacePane('results')}
                          >
                            <Database className="mr-2 h-4 w-4" />
                            {t('enrichmentTab.tabs.results')}
                          </Button>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          {canStartActiveSource ? (
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => startSourceJob(activeSource.id)}
                              disabled={jobLoadingScope !== null || isOffline}
                            >
                              {jobLoadingScope === activeSource.id ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="mr-2 h-4 w-4" />
                              )}
                              {t('enrichmentTab.runtime.startSource', {
                                defaultValue: 'Lancer cette API',
                              })}
                            </Button>
                          ) : null}

                          {isRunningSingleSource && job?.status === 'running' ? (
                            <>
                              <Button size="sm" variant="secondary" onClick={() => pauseJob(activeSource.id)} disabled={jobLoadingScope !== null}>
                                {jobLoadingScope === activeSource.id ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <Pause className="mr-2 h-4 w-4" />
                                )}
                                {t('enrichmentTab.actions.pause')}
                              </Button>
                              <Button size="sm" variant="destructive" onClick={() => cancelJob(activeSource.id)} disabled={jobLoadingScope !== null}>
                                <StopCircle className="mr-2 h-4 w-4" />
                                {t('common:actions.cancel')}
                              </Button>
                            </>
                          ) : null}

                          {isRunningSingleSource && (job?.status === 'paused' || job?.status === 'paused_offline') ? (
                            <>
                              <Button size="sm" onClick={() => resumeJob(activeSource.id)} disabled={jobLoadingScope !== null || isOffline}>
                                {jobLoadingScope === activeSource.id ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <Play className="mr-2 h-4 w-4" />
                                )}
                                {t('enrichmentTab.actions.resume')}
                              </Button>
                              <Button size="sm" variant="destructive" onClick={() => cancelJob(activeSource.id)} disabled={jobLoadingScope !== null}>
                                <StopCircle className="mr-2 h-4 w-4" />
                                {t('common:actions.cancel')}
                              </Button>
                            </>
                          ) : null}

                          <div className="flex items-center gap-1 rounded-xl border border-border/70 bg-background p-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              disabled={activeSourceIndex === 0}
                              onClick={() => moveSource(activeSource.id, 'up')}
                            >
                              <ChevronUp className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              disabled={activeSourceIndex === sources.length - 1}
                              onClick={() => moveSource(activeSource.id, 'down')}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => duplicateSource(activeSource.id)}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive">
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>
                                    {t('dashboard.enrichment.deleteSourceTitle', {
                                      defaultValue: 'Supprimer cette source ?',
                                    })}
                                  </AlertDialogTitle>
                                  <AlertDialogDescription>
                                    {t('dashboard.enrichment.deleteSourceDescription', {
                                      defaultValue: 'La source sera retirée de la configuration locale jusqu’à la prochaine sauvegarde.',
                                    })}
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>{t('common:actions.cancel')}</AlertDialogCancel>
                                  <AlertDialogAction onClick={() => removeSource(activeSource.id)}>
                                    {t('common:actions.delete')}
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {workspacePane === 'config' ? (
                  <Card className="border-border/70">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        {t('dashboard.enrichment.configTitle', {
                          defaultValue: 'Configuration détaillée',
                        })}
                      </CardTitle>
                      <CardDescription>
                        {t('dashboard.enrichment.configDescription', {
                          defaultValue: 'Règle la connexion, l’authentification et le mapping pour la source active.',
                        })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ApiEnrichmentConfig
                        key={activeSource.id}
                        config={activeSource.config}
                        onChange={(apiConfig) => updateSourceConfig(activeSource.id, apiConfig)}
                        onPresetSelect={(presetName) => applyPresetLabel(activeSource.id, presetName)}
                        category={apiCategory}
                      />
                    </CardContent>
                  </Card>
                ) : null}

                {workspacePane === 'preview' ? (
                  <Card className="border-border/70">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        {t('dashboard.actions.testApi', {
                          defaultValue: "Tester l'API",
                        })}
                      </CardTitle>
                      <CardDescription>
                        {t('dashboard.enrichment.inspectorDescription', {
                          defaultValue: 'Teste la source active et consulte ses derniers résultats sans quitter la configuration.',
                        })}
                      </CardDescription>
                      {activeSource.config.api_url ? (
                        <div className="truncate text-xs text-muted-foreground">
                          {activeSource.config.api_url}
                        </div>
                      ) : null}
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {activeSource.enabled ? (
                        <>
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">
                              {t('enrichmentTab.preview.manualInput')}
                            </Label>
                            <div className="flex gap-2">
                              <Input
                                placeholder={t('common:labels.name')}
                                value={previewQuery}
                                onChange={(event) => setPreviewQuery(event.target.value)}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') {
                                    void previewEnrichment(undefined, activeSource.id)
                                  }
                                }}
                              />
                              <Button
                                type="button"
                                onClick={() => previewEnrichment(undefined, activeSource.id)}
                                disabled={previewLoading || !previewQuery.trim()}
                              >
                                {previewLoading ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Eye className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">
                              {t('dashboard.enrichment.quickExamples', {
                                defaultValue: 'Essayer avec une entité existante',
                              })}
                            </Label>
                            <div className="flex gap-2">
                              <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                  placeholder={t('common:actions.search')}
                                  value={entitySearch}
                                  onChange={(event) => setEntitySearch(event.target.value)}
                                  className="pl-9"
                                  onKeyDown={(event) => {
                                    if (event.key === 'Enter') {
                                      void loadEntities(entitySearch)
                                    }
                                  }}
                                />
                              </div>
                              <Button type="button" variant="outline" onClick={() => loadEntities(entitySearch)}>
                                <Search className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>

                          <ScrollArea className="h-[220px] rounded-md border">
                            {entitiesLoading ? (
                              <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                              </div>
                            ) : entities.length === 0 ? (
                              <div className="py-8 text-center text-muted-foreground">
                                <Database className="mx-auto mb-2 h-8 w-8 opacity-50" />
                                <p className="text-sm">{t('enrichmentTab.preview.loadEntities')}</p>
                              </div>
                            ) : (
                              <div className="p-1">
                                {entities.map((entity) => (
                                  <button
                                    key={entity.id}
                                    type="button"
                                    onClick={() => {
                                      setPreviewQuery(entity.name)
                                      void previewEnrichment(entity.name, activeSource.id)
                                    }}
                                    className={`group flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-accent ${
                                      previewQuery === entity.name ? 'bg-accent' : ''
                                    }`}
                                  >
                                    <span className="truncate flex-1">{entity.name}</span>
                                    <Eye className="h-4 w-4 opacity-0 group-hover:opacity-50" />
                                  </button>
                                ))}
                              </div>
                            )}
                          </ScrollArea>

                          <div className="rounded-lg border bg-muted/20 p-3">
                            {previewLoading ? (
                              <div className="flex min-h-[220px] items-center justify-center">
                                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                              </div>
                            ) : previewError ? (
                              <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{previewError}</AlertDescription>
                              </Alert>
                            ) : activePreviewResult?.success ? (
                              <div className="space-y-3">
                                <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/70 bg-background p-1">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={previewResultMode === 'mapped' ? 'default' : 'ghost'}
                                    onClick={() => setPreviewResultMode('mapped')}
                                  >
                                    {t('dashboard.enrichment.mappedFields', {
                                      defaultValue: 'Champs mappés',
                                    })}
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={previewResultMode === 'raw' ? 'default' : 'ghost'}
                                    onClick={() => setPreviewResultMode('raw')}
                                  >
                                    {t('dashboard.enrichment.rawApiResponse', {
                                      defaultValue: 'Réponse brute API',
                                    })}
                                  </Button>
                                </div>

                                {previewResultMode === 'mapped' ? (
                                  activePreviewResult.data && Object.keys(activePreviewResult.data).length > 0 ? (
                                    isStructuredSourceSummary(activePreviewResult.data)
                                      ? renderStructuredSummary(activePreviewResult.data, t)
                                      : renderMappedPreview(activePreviewResult.data)
                                  ) : (
                                    <div className="py-8 text-center text-sm text-muted-foreground">
                                      {t('dashboard.enrichment.noMappedFields', {
                                        defaultValue: 'Aucun champ mappé pour cette source.',
                                      })}
                                    </div>
                                  )
                                ) : activePreviewResult.raw_data !== undefined ? (
                                  renderRawPreview(activePreviewResult.raw_data)
                                ) : (
                                  <div className="py-8 text-center text-sm text-muted-foreground">
                                    {t('dashboard.enrichment.noRawApiResponse', {
                                      defaultValue: 'Aucune réponse brute disponible pour ce test.',
                                    })}
                                  </div>
                                )}
                              </div>
                            ) : activePreviewResult?.error ? (
                              <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{activePreviewResult.error}</AlertDescription>
                              </Alert>
                            ) : (
                              <div className="flex min-h-[220px] flex-col items-center justify-center text-center text-muted-foreground">
                                <Eye className="mb-3 h-10 w-10 opacity-30" />
                                <div className="text-sm font-medium">{t('enrichmentTab.preview.emptyTitle')}</div>
                                <div className="text-sm">{t('enrichmentTab.preview.emptyDescription')}</div>
                              </div>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                          {t('dashboard.enrichment.quickTesterDisabled', {
                            defaultValue: 'Active cette source pour pouvoir la tester.',
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : null}

                {workspacePane === 'results' ? (
                  <Card className="border-border/70">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">
                        {t('enrichmentTab.tabs.results')}
                      </CardTitle>
                      <CardDescription>
                        {t('dashboard.enrichment.resultsDescription', {
                          defaultValue: 'Consulte les enrichissements déjà produits pour la source active.',
                        })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {resultsLoading ? (
                        <div className="flex items-center justify-center py-10">
                          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                      ) : activeSourceResults.length === 0 ? (
                        <Alert>
                          <AlertCircle className="h-4 w-4" />
                          <AlertTitle>{t('enrichmentTab.results.emptyTitle')}</AlertTitle>
                          <AlertDescription>{t('enrichmentTab.results.emptyDescription')}</AlertDescription>
                        </Alert>
                      ) : (
                        <>
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">
                              {activeSourceResults.length.toLocaleString()} result(s)
                            </Badge>
                            <Badge variant="outline">
                              {t('enrichmentTab.stats.enriched')}: {(activeSourceStats?.enriched ?? 0).toLocaleString()}
                            </Badge>
                            <Badge variant="outline">
                              {t('enrichmentTab.stats.pending')}: {(activeSourceStats?.pending ?? 0).toLocaleString()}
                            </Badge>
                          </div>

                          <ScrollArea className="max-h-[620px]">
                            <div className="space-y-2">
                              {activeSourceResults.map((result) => (
                                <button
                                  key={`${activeSource.id}-${getResultEntityName(result)}-${result.processed_at}`}
                                  type="button"
                                  className="w-full rounded-lg border px-3 py-3 text-left transition-colors hover:bg-muted/30"
                                  onClick={() => setSelectedResult(result)}
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <div className="truncate text-sm font-medium">
                                        {getResultEntityName(result)}
                                      </div>
                                      <div className="mt-1 text-xs text-muted-foreground">
                                        {new Date(result.processed_at).toLocaleString()}
                                      </div>
                                    </div>
                                    <Badge variant={result.success ? 'secondary' : 'destructive'}>
                                      {result.success
                                        ? t('enrichmentTab.result.success')
                                        : t('enrichmentTab.result.failed')}
                                    </Badge>
                                  </div>
                                </button>
                              ))}
                            </div>
                          </ScrollArea>
                        </>
                      )}
                    </CardContent>
                  </Card>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      )}

      <Dialog open={selectedResult !== null} onOpenChange={(open) => !open && setSelectedResult(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{selectedResult ? getResultEntityName(selectedResult) : ''}</DialogTitle>
            <DialogDescription>
              {selectedResult?.source_label
                ? `${selectedResult.source_label} · ${new Date(selectedResult.processed_at).toLocaleString()}`
                : ''}
            </DialogDescription>
          </DialogHeader>
          {selectedResult ? (
            selectedResult.success && selectedResult.data ? (
              <ScrollArea className="max-h-[60vh]">
                {isStructuredSourceSummary(selectedResult.data) ? (
                  renderStructuredSummary(selectedResult.data, t)
                ) : (
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t('enrichmentTab.table.field')}</TableHead>
                          <TableHead>{t('enrichmentTab.table.value')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(selectedResult.data).map(([field, value]) => (
                          <TableRow key={field} className="align-top">
                            <TableCell className="align-top font-medium">{field}</TableCell>
                            <TableCell className="align-top break-words">{renderValue(value)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </ScrollArea>
            ) : (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{selectedResult.error || t('enrichmentTab.result.failed')}</AlertDescription>
              </Alert>
            )
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
