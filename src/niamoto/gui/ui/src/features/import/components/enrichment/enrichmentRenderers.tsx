/**
 * Render helpers for enrichment preview results.
 *
 * Pure display functions extracted from EnrichmentTab — each renders
 * a structured summary for a specific API source (GBIF, Tropicos, COL,
 * BHL, iNaturalist, OpenMeteo, GeoNames).
 */

import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ExternalLink, ImageIcon, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SourceSummary = Record<string, any>
type Translate = (key: string, options?: Record<string, unknown>) => string

const asSummary = (value: unknown): SourceSummary =>
  typeof value === 'object' && value !== null ? (value as SourceSummary) : {}

const URL_PATTERN = /^(https?:\/\/[^\s]+)$/i
const IMAGE_PATTERN = /\.(jpg|jpeg|png|gif|webp|svg|bmp)(\?.*)?$/i

const isImageUrl = (value: string): boolean =>
  IMAGE_PATTERN.test(value) ||
  value.includes('/image') ||
  value.includes('/photo') ||
  value.includes('/thumb') ||
  value.includes('/media/cache')

const asUrl = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null
  }

  const url = value.trim()
  return URL_PATTERN.test(url) ? url : null
}

const ImageWithLoader = ({
  src,
  href = src,
  alt,
  className = 'h-16 w-16',
}: {
  src: string
  href?: string
  alt: string
  className?: string
}) => {
  const { t } = useTranslation(['sources'])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  return (
    <div className={`relative inline-block ${className}`}>
      {loading && !error ? (
        <div className="absolute inset-0 flex items-center justify-center rounded bg-muted">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : null}
      {error ? (
        <div className="flex h-full w-full items-center justify-center gap-2 rounded border bg-muted p-1 text-xs text-muted-foreground">
          <ImageIcon className="h-4 w-4" />
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="truncate text-blue-600 hover:underline"
          >
            {t('enrichmentTab.viewImage')}
          </a>
        </div>
      ) : (
        <a href={href} target="_blank" rel="noopener noreferrer" className="block h-full w-full">
          <img
            src={src}
            alt={alt}
            loading="lazy"
            className={`h-full w-full rounded border object-cover transition-opacity hover:opacity-80 ${
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

const extractImageGalleryItem = (value: unknown) => {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null
  }

  const item = value as SourceSummary
  const thumbnail =
    asUrl(item.small_thumb) ||
    asUrl(item.thumbnail_url) ||
    asUrl(item.thumbnail) ||
    asUrl(item.thumb) ||
    asUrl(item.mid_thumb) ||
    asUrl(item.big_thumb) ||
    asUrl(item.url) ||
    asUrl(item.source_url) ||
    asUrl(item.identifier)
  const href =
    asUrl(item.url) ||
    asUrl(item.big_thumb) ||
    asUrl(item.source_url) ||
    asUrl(item.identifier) ||
    thumbnail

  if (!thumbnail || !href || (!isImageUrl(thumbnail) && !isImageUrl(href))) {
    return null
  }

  return {
    thumbnail,
    href,
    author: item.auteur || item.author || item.creator || item.credit,
    date: item.datmaj || item.date || item.created_at || item.updated_at,
  }
}

const renderImageGallery = (value: unknown): React.ReactNode | null => {
  if (!Array.isArray(value)) {
    return null
  }

  const images = value
    .map(extractImageGalleryItem)
    .filter((item): item is NonNullable<ReturnType<typeof extractImageGalleryItem>> => item !== null)

  if (images.length === 0) {
    return null
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(88px,1fr))] gap-2">
      {images.map((image, index) => (
        <div key={`${image.href}-${index}`} className="min-w-0 rounded-md border bg-background p-1">
          <ImageWithLoader
            src={image.thumbnail}
            href={image.href}
            alt={typeof image.author === 'string' ? image.author : `Image ${index + 1}`}
            className="aspect-square w-full"
          />
          {image.author || image.date ? (
            <div className="mt-1 space-y-0.5 text-[10px] leading-tight text-muted-foreground">
              {image.author ? <div className="truncate">{String(image.author)}</div> : null}
              {image.date ? <div className="truncate tabular-nums">{String(image.date)}</div> : null}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  )
}

const renderValue = (value: unknown): React.ReactNode => {
  if (value === null || value === undefined) return '-'

  if (typeof value === 'string') {
    const url = asUrl(value)
    if (url) {
      if (isImageUrl(url)) {
        return <ImageWithLoader src={value} alt="Preview" />
      }

      return (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline"
        >
          <span className="max-w-[200px] truncate">{url}</span>
          <ExternalLink className="h-3 w-3 shrink-0" />
        </a>
      )
    }

    return value
  }

  const gallery = renderImageGallery(value)
  if (gallery) {
    return gallery
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

const renderMappedPreview = (data: SourceSummary) => (
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

const renderRawPreview = (rawData: unknown) => (
  <div className="max-h-[360px] overflow-auto rounded-md bg-background p-3">
    <pre className="whitespace-pre-wrap break-words text-xs leading-5">
      {JSON.stringify(rawData, null, 2)}
    </pre>
  </div>
)

const isStructuredSourceSummary = (data: SourceSummary | undefined): boolean =>
  Boolean(
    data &&
      typeof data === 'object' &&
      (
        'location' in data ||
        'elevation' in data ||
        'admin' in data ||
        'nearby_place' in data ||
        'geometry_summary' in data ||
        'elevation_summary' in data ||
        'admin_summary' in data ||
        'sampling' in data ||
        'match' in data ||
        'taxonomy' in data ||
        'occurrence_summary' in data ||
        'observation_summary' in data ||
        'media_summary' in data ||
        'taxon' in data ||
        'places' in data ||
        'nomenclature' in data ||
        'vernaculars' in data ||
        'references' in data ||
        'distribution_summary' in data ||
        'title_summary' in data ||
        'name_mentions' in data ||
        'page_links' in data ||
        'references_count' in data
      )
  )

const renderSummaryRows = (rows: Array<[string, unknown]>) => (
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

const renderStatusPill = (t: Translate, status: unknown) => {
  if (typeof status !== 'string' || status.length === 0) {
    return null
  }

  const label = t(`dashboard.enrichment.structured.status.${status}`, {
    defaultValue: status.replace(/_/g, ' '),
  })

  return (
    <Badge variant={status === 'complete' ? 'secondary' : 'outline'} className="text-[11px] font-medium">
      {label}
    </Badge>
  )
}

const renderNameResolutionSummary = (nameResolution: SourceSummary, t: Translate) => {
  if (!nameResolution || Object.keys(nameResolution).length === 0) {
    return null
  }

  return (
    <div className="rounded-lg border border-border/70 bg-background p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="text-sm font-semibold">
          {t('dashboard.enrichment.structured.nameResolution', { defaultValue: 'Name resolution' })}
        </div>
        {renderStatusPill(t, nameResolution.status)}
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
            <div className="text-xs font-medium text-muted-foreground">
              {t('dashboard.enrichment.structured.alternatives', { defaultValue: 'Alternatives' })}
            </div>
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

const renderOpenMeteoStructuredSummary = (
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const location = asSummary(data.location)
  const elevation = asSummary(data.elevation)
  const geometrySummary = asSummary(data.geometry_summary)
  const elevationSummary = asSummary(data.elevation_summary)
  const sampling = asSummary(data.sampling)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {(Object.keys(location).length > 0 || Object.keys(elevation).length > 0) ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Location</div>
              {renderStatusPill(t, blockStatus.location)}
            </div>
            {blockErrors.location ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.location)}</div>
            ) : (
              renderSummaryRows([
                ['latitude', location.latitude],
                ['longitude', location.longitude],
              ])
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Elevation</div>
              {renderStatusPill(t, blockStatus.elevation)}
            </div>
            {blockErrors.elevation ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.elevation)}</div>
            ) : (
              renderSummaryRows([
                ['value_m', elevation.value_m],
                ['source_dataset', elevation.source_dataset],
              ])
            )}
          </div>
        </>
      ) : null}

      {(Object.keys(geometrySummary).length > 0 || Object.keys(elevationSummary).length > 0) ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Geometry summary</div>
              {renderStatusPill(t, blockStatus.geometry_summary)}
            </div>
            {blockErrors.geometry_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.geometry_summary)}</div>
            ) : (
              renderSummaryRows([
                ['geometry_type', geometrySummary.geometry_type],
                ['sample_mode', geometrySummary.sample_mode],
                ['sample_count', geometrySummary.sample_count],
                ['centroid', geometrySummary.centroid],
                ['bbox', geometrySummary.bbox],
              ])
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Elevation summary</div>
              {renderStatusPill(t, blockStatus.elevation_summary)}
            </div>
            {blockErrors.elevation_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.elevation_summary)}</div>
            ) : (
              renderSummaryRows([
                ['centroid_elevation_m', elevationSummary.centroid_elevation_m],
                ['min_elevation_m', elevationSummary.min_elevation_m],
                ['max_elevation_m', elevationSummary.max_elevation_m],
                ['mean_elevation_m', elevationSummary.mean_elevation_m],
                ['source_dataset', elevationSummary.source_dataset],
              ])
            )}
          </div>
        </>
      ) : null}

      {Object.keys(sampling).length > 0 ? (
        <div className="rounded-lg border border-border/70 bg-background p-3">
          <div className="mb-3 text-sm font-semibold">Sampling</div>
          {renderSummaryRows([
            ['strategy', sampling.strategy],
            ['sample_mode', sampling.sample_mode],
            ['sample_count', sampling.sample_count],
          ])}
        </div>
      ) : null}

      {Object.keys(asSummary(data.provenance)).length > 0 ? (
        <div className="rounded-lg border border-border/70 bg-background p-3">
          <div className="mb-3 text-sm font-semibold">
            {t('dashboard.enrichment.structured.provenance', { defaultValue: 'Provenance' })}
          </div>
          {renderSummaryRows(Object.entries(asSummary(data.provenance)))}
        </div>
      ) : null}
    </div>
  )
}

const renderGeoNamesStructuredSummary = (
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const location = asSummary(data.location)
  const admin = asSummary(data.admin)
  const nearbyPlace = asSummary(data.nearby_place)
  const geometrySummary = asSummary(data.geometry_summary)
  const adminSummary = asSummary(data.admin_summary)
  const sampling = asSummary(data.sampling)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {(Object.keys(location).length > 0 || Object.keys(admin).length > 0 || Object.keys(nearbyPlace).length > 0) ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Location</div>
              {renderStatusPill(t, blockStatus.location)}
            </div>
            {blockErrors.location ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.location)}</div>
            ) : (
              renderSummaryRows([
                ['latitude', location.latitude],
                ['longitude', location.longitude],
              ])
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Administrative context</div>
              {renderStatusPill(t, blockStatus.admin)}
            </div>
            {blockErrors.admin ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.admin)}</div>
            ) : (
              renderSummaryRows([
                ['country_code', admin.country_code],
                ['country_name', admin.country_name],
                ['admin1', admin.admin1],
                ['admin2', admin.admin2],
              ])
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Nearby place</div>
              {renderStatusPill(t, blockStatus.nearby_place)}
            </div>
            {blockErrors.nearby_place ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.nearby_place)}</div>
            ) : (
              renderSummaryRows([
                ['name', nearbyPlace.name],
                ['distance_km', nearbyPlace.distance_km],
                ['country_name', nearbyPlace.country_name],
                ['admin1', nearbyPlace.admin1],
                ['population', nearbyPlace.population],
              ])
            )}
          </div>
        </>
      ) : null}

      {(Object.keys(geometrySummary).length > 0 || Object.keys(adminSummary).length > 0) ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Geometry summary</div>
              {renderStatusPill(t, blockStatus.geometry_summary)}
            </div>
            {blockErrors.geometry_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.geometry_summary)}</div>
            ) : (
              renderSummaryRows([
                ['geometry_type', geometrySummary.geometry_type],
                ['sample_mode', geometrySummary.sample_mode],
                ['sample_count', geometrySummary.sample_count],
                ['centroid', geometrySummary.centroid],
                ['bbox', geometrySummary.bbox],
              ])
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Administrative summary</div>
              {renderStatusPill(t, blockStatus.admin_summary)}
            </div>
            {blockErrors.admin_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.admin_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['sample_count', adminSummary.sample_count]])}
                {Array.isArray(adminSummary.countries) && adminSummary.countries.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Countries</div>
                    <div className="flex flex-wrap gap-2">
                      {adminSummary.countries.map((country: string) => (
                        <Badge key={country} variant="outline">{country}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                {Array.isArray(adminSummary.admin1_values) && adminSummary.admin1_values.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Admin 1</div>
                    <div className="flex flex-wrap gap-2">
                      {adminSummary.admin1_values.map((item: string) => (
                        <Badge key={item} variant="outline">{item}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                {Array.isArray(adminSummary.admin2_values) && adminSummary.admin2_values.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Admin 2</div>
                    <div className="flex flex-wrap gap-2">
                      {adminSummary.admin2_values.map((item: string) => (
                        <Badge key={item} variant="outline">{item}</Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                {Array.isArray(adminSummary.nearest_places) && adminSummary.nearest_places.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Nearby places</div>
                    <div className="space-y-2">
                      {adminSummary.nearest_places.map((item: SourceSummary) => (
                        <div key={String(item.name)} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                          <span className="truncate">{String(item.name)}</span>
                          {item.distance_km ? <Badge variant="outline">{String(item.distance_km)} km</Badge> : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </>
      ) : null}

      {Object.keys(sampling).length > 0 ? (
        <div className="rounded-lg border border-border/70 bg-background p-3">
          <div className="mb-3 text-sm font-semibold">Sampling</div>
          {renderSummaryRows([
            ['strategy', sampling.strategy],
            ['sample_mode', sampling.sample_mode],
            ['sample_count', sampling.sample_count],
          ])}
        </div>
      ) : null}

      {Object.keys(asSummary(data.provenance)).length > 0 ? (
        <div className="rounded-lg border border-border/70 bg-background p-3">
          <div className="mb-3 text-sm font-semibold">
            {t('dashboard.enrichment.structured.provenance', { defaultValue: 'Provenance' })}
          </div>
          {renderSummaryRows(Object.entries(asSummary(data.provenance)))}
        </div>
      ) : null}
    </div>
  )
}

const renderGbifStructuredSummary = (
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const nameResolution = asSummary(data.name_resolution)
  const match = asSummary(data.match)
  const taxonomy = asSummary(data.taxonomy)
  const occurrenceSummary = asSummary(data.occurrence_summary)
  const mediaSummary = asSummary(data.media_summary)
  const links = asSummary(data.links)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)
  const noMatch = blockStatus.match === 'no_match' || !match.usage_key

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {renderNameResolutionSummary(nameResolution, t)}
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">
            {t('dashboard.enrichment.structured.match', { defaultValue: 'Match' })}
          </div>
          {renderStatusPill(t, blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue:
                'No exploitable identifier was found for this source, so dependent blocks were not run.',
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
              {renderStatusPill(t, blockStatus.taxonomy)}
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
              {renderStatusPill(t, blockStatus.occurrence_summary)}
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
              {renderStatusPill(t, blockStatus.media_summary)}
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
                  {mediaSummary.items.map((item: SourceSummary, index: number) => (
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
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const nameResolution = asSummary(data.name_resolution)
  const match = asSummary(data.match)
  const nomenclature = asSummary(data.nomenclature)
  const taxonomy = asSummary(data.taxonomy)
  const references = asSummary(data.references)
  const distributionSummary = asSummary(data.distribution_summary)
  const mediaSummary = asSummary(data.media_summary)
  const links = asSummary(data.links)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)
  const noMatch = blockStatus.match === 'no_match' || !match.name_id

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {renderNameResolutionSummary(nameResolution, t)}
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">Match</div>
          {renderStatusPill(t, blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue:
                'No exploitable identifier was found for this source, so dependent blocks were not run.',
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
              {renderStatusPill(t, blockStatus.nomenclature)}
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
              {renderStatusPill(t, blockStatus.taxonomy)}
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
              {renderStatusPill(t, blockStatus.references)}
            </div>
            {blockErrors.references ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.references)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['references_count', references.references_count]])}
                {Array.isArray(references.items) && references.items.length > 0 ? (
                  <div className="space-y-2">
                    {references.items.map((item: SourceSummary, index: number) => (
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
              {renderStatusPill(t, blockStatus.distribution_summary)}
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
              {renderStatusPill(t, blockStatus.media_summary)}
            </div>
            {blockErrors.media_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.media_summary)}</div>
            ) : Array.isArray(mediaSummary.items) && mediaSummary.items.length > 0 ? (
              <div className="space-y-3">
                {renderSummaryRows([['media_count', mediaSummary.media_count]])}
                <div className="grid gap-3 md:grid-cols-2">
                  {mediaSummary.items.map((item: SourceSummary, index: number) => (
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

const renderInaturalistStructuredSummary = (
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const match = asSummary(data.match)
  const taxon = asSummary(data.taxon)
  const observationSummary = asSummary(data.observation_summary)
  const mediaSummary = asSummary(data.media_summary)
  const places = asSummary(data.places)
  const links = asSummary(data.links)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)
  const noMatch = blockStatus.match === 'no_match' || !match.taxon_id

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">Match</div>
          {renderStatusPill(t, blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue:
                'No exploitable identifier was found for this source, so dependent blocks were not run.',
            })}
          </div>
        ) : (
          renderSummaryRows([
            ['taxon_id', match.taxon_id],
            ['scientific_name', match.scientific_name],
            ['preferred_common_name', match.preferred_common_name],
            ['rank', match.rank],
            ['iconic_taxon_name', match.iconic_taxon_name],
            ['matched_name', match.matched_name],
          ])
        )}
      </div>

      {!noMatch ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Taxon</div>
              {renderStatusPill(t, blockStatus.taxon)}
            </div>
            {blockErrors.taxon ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.taxon)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['preferred_common_name', taxon.preferred_common_name],
                  ['observations_count', taxon.observations_count],
                  ['conservation_status', taxon.conservation_status],
                  ['iconic_taxon_name', taxon.iconic_taxon_name],
                  ['wikipedia_url', taxon.wikipedia_url],
                ])}
                {taxon.default_photo ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Default photo</div>
                    <div className="rounded-md border p-3">
                      <div className="mb-2">
                        {renderValue(taxon.default_photo.medium_url || taxon.default_photo.square_url)}
                      </div>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        {taxon.default_photo.attribution ? <div>{taxon.default_photo.attribution}</div> : null}
                        {taxon.default_photo.license_code ? <div>{taxon.default_photo.license_code}</div> : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Observations</div>
              {renderStatusPill(t, blockStatus.observation_summary)}
            </div>
            {blockErrors.observation_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.observation_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['observations_count', observationSummary.observations_count],
                  ['research_grade_count', observationSummary.research_grade_count],
                  ['casual_count', observationSummary.casual_count],
                  ['needs_id_count', observationSummary.needs_id_count],
                ])}
                {Array.isArray(observationSummary.recent_observations) && observationSummary.recent_observations.length > 0 ? (
                  <div className="space-y-2">
                    {observationSummary.recent_observations.map((item: SourceSummary, index: number) => (
                      <div key={`${item.observation_id || index}`} className="rounded-md border p-3">
                        <div className="text-sm font-medium">
                          Observation {String(item.observation_id || index + 1)}
                        </div>
                        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                          {item.observed_on ? <div>{item.observed_on}</div> : null}
                          {item.quality_grade ? <div>{item.quality_grade}</div> : null}
                          {item.place_guess ? <div>{item.place_guess}</div> : null}
                          {item.observation_url ? <div className="break-words">{renderValue(item.observation_url)}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : blockStatus.observation_summary === 'disabled' ? (
                  <div className="text-sm text-muted-foreground">Observation summary disabled.</div>
                ) : null}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Media</div>
              {renderStatusPill(t, blockStatus.media_summary)}
            </div>
            {blockErrors.media_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.media_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['media_count', mediaSummary.media_count]])}
                {Array.isArray(mediaSummary.sample) && mediaSummary.sample.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {mediaSummary.sample.map((item: SourceSummary, index: number) => (
                      <div key={`${item.medium_url || item.square_url || index}`} className="rounded-md border p-3">
                        <div className="mb-2">
                          {renderValue(item.medium_url || item.square_url)}
                        </div>
                        <div className="space-y-1 text-xs text-muted-foreground">
                          {item.attribution ? <div>{item.attribution}</div> : null}
                          {item.license_code ? <div>{item.license_code}</div> : null}
                          {item.observation_url ? <div className="break-words">{renderValue(item.observation_url)}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : blockStatus.media_summary === 'disabled' ? (
                  <div className="text-sm text-muted-foreground">Media summary disabled.</div>
                ) : (
                  <div className="text-sm text-muted-foreground">Aucun média résumé.</div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Places</div>
              {renderStatusPill(t, blockStatus.places)}
            </div>
            {blockErrors.places ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.places)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['places_count', places.places_count]])}
                {Array.isArray(places.top_places) && places.top_places.length > 0 ? (
                  <div className="space-y-2">
                    {places.top_places.map((item: SourceSummary) => (
                      <div key={String(item.name)} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                        <span>{String(item.name)}</span>
                        <Badge variant="outline">{String(item.count)}</Badge>
                      </div>
                    ))}
                  </div>
                ) : blockStatus.places === 'disabled' ? (
                  <div className="text-sm text-muted-foreground">Places summary disabled.</div>
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

const renderBhlStructuredSummary = (
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const match = asSummary(data.match)
  const titleSummary = asSummary(data.title_summary)
  const publications = asSummary(data.publications)
  const nameMentions = asSummary(data.name_mentions)
  const pageLinks = asSummary(data.page_links)
  const referencesCount = asSummary(data.references_count)
  const links = asSummary(data.links)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)
  const noMatch =
    blockStatus.match === 'no_match' ||
    (!match.name_confirmed && !referencesCount.titles && !referencesCount.pages)

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">Match</div>
          {renderStatusPill(t, blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue:
                'No exploitable identifier was found for this source, so dependent blocks were not run.',
            })}
          </div>
        ) : (
          renderSummaryRows([
            ['submitted_name', match.submitted_name],
            ['name_confirmed', match.name_confirmed],
            ['name_canonical', match.name_canonical],
            ['namebank_id', match.namebank_id],
            ['match_status', match.match_status],
          ])
        )}
      </div>

      {!noMatch ? (
        <>
          <div className="rounded-lg border border-border/70 bg-background p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">Titles</div>
              {renderStatusPill(t, blockStatus.title_summary)}
            </div>
            {blockErrors.title_summary ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.title_summary)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([
                  ['title_count', titleSummary.title_count ?? referencesCount.titles],
                  ['item_count', titleSummary.item_count ?? referencesCount.items],
                  ['page_count', titleSummary.page_count ?? referencesCount.pages],
                ])}
                {blockErrors.publications ? (
                  <div className="text-sm text-muted-foreground">{String(blockErrors.publications)}</div>
                ) : Array.isArray(publications.sample) && publications.sample.length > 0 ? (
                  <div className="space-y-2">
                    {publications.sample.map((item: SourceSummary, index: number) => (
                      <div key={`${item.title_id || item.title_url || index}`} className="rounded-md border p-3">
                        <div className="text-sm font-medium">{item.short_title || item.full_title || 'Title'}</div>
                        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                          {item.publication_date ? <div>{item.publication_date}</div> : null}
                          {item.publisher_name ? <div>{item.publisher_name}</div> : null}
                          {item.item_count !== undefined ? <div>{String(item.item_count)} item(s)</div> : null}
                          {item.title_url ? <div className="break-words">{item.title_url}</div> : null}
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
              <div className="text-sm font-semibold">Mentions</div>
              {renderStatusPill(t, blockStatus.name_mentions)}
            </div>
            {blockErrors.name_mentions ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.name_mentions)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['mentions_count', nameMentions.mentions_count]])}
                {Array.isArray(nameMentions.sample) && nameMentions.sample.length > 0 ? (
                  <div className="space-y-2">
                    {nameMentions.sample.map((item: SourceSummary, index: number) => (
                      <div key={`${item.name_confirmed || item.name_found || index}`} className="rounded-md border p-3">
                        <div className="text-sm font-medium">{item.name_confirmed || item.name_found || 'Mention'}</div>
                        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                          {item.name_found ? <div>Found: {item.name_found}</div> : null}
                          {item.name_canonical ? <div>Canonical: {item.name_canonical}</div> : null}
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
              <div className="text-sm font-semibold">Pages</div>
              {renderStatusPill(t, blockStatus.page_links)}
            </div>
            {blockErrors.page_links ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.page_links)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['pages', referencesCount.pages]])}
                {Array.isArray(pageLinks.sample) && pageLinks.sample.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {pageLinks.sample.map((item: SourceSummary, index: number) => (
                      <div key={`${item.page_id || item.page_url || index}`} className="rounded-md border p-3">
                        <div className="mb-2">{renderValue(item.thumbnail_url || item.page_url || item.page_id)}</div>
                        <div className="space-y-1 text-xs text-muted-foreground">
                          {item.page_id ? <div>Page {String(item.page_id)}</div> : null}
                          {item.page_type ? <div>{item.page_type}</div> : null}
                          {item.page_url ? <div className="break-words">{item.page_url}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : blockStatus.page_links === 'disabled' ? (
                  <div className="text-sm text-muted-foreground">Page preview disabled.</div>
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

const renderColStructuredSummary = (
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  const nameResolution = asSummary(data.name_resolution)
  const match = asSummary(data.match)
  const taxonomy = asSummary(data.taxonomy)
  const nomenclature = asSummary(data.nomenclature)
  const vernaculars = asSummary(data.vernaculars)
  const distributionSummary = asSummary(data.distribution_summary)
  const references = asSummary(data.references)
  const links = asSummary(data.links)
  const blockStatus = asSummary(data.block_status)
  const blockErrors = asSummary(data.block_errors)
  const noMatch = blockStatus.match === 'no_match' || !match.taxon_id

  return (
    <div className="max-h-[420px] space-y-3 overflow-auto pr-2">
      {renderNameResolutionSummary(nameResolution, t)}
      <div className="rounded-lg border border-border/70 bg-background p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm font-semibold">Match</div>
          {renderStatusPill(t, blockStatus.match)}
        </div>
        {noMatch ? (
          <div className="text-sm text-muted-foreground">
            {t('dashboard.enrichment.structured.noMatch', {
              defaultValue:
                'No exploitable identifier was found for this source, so dependent blocks were not run.',
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
              {renderStatusPill(t, blockStatus.taxonomy)}
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
                      {taxonomy.classification.map((item: SourceSummary, index: number) => {
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
              {renderStatusPill(t, blockStatus.nomenclature)}
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
              {renderStatusPill(t, blockStatus.vernaculars)}
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
                      {vernaculars.sample.map((item: SourceSummary, index: number) => {
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
              {renderStatusPill(t, blockStatus.distribution_summary)}
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
              {renderStatusPill(t, blockStatus.references)}
            </div>
            {blockErrors.references ? (
              <div className="text-sm text-muted-foreground">{String(blockErrors.references)}</div>
            ) : (
              <div className="space-y-3">
                {renderSummaryRows([['references_count', references.references_count]])}
                {Array.isArray(references.items) && references.items.length > 0 ? (
                  <div className="space-y-2">
                    {references.items.map((item: SourceSummary, index: number) => (
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
  data: SourceSummary,
  t: (key: string, options?: Record<string, unknown>) => string
) => {
  if (
    data?.provenance?.profile === 'openmeteo_elevation_v1' ||
    'elevation_summary' in data ||
    'elevation' in data
  ) {
    return renderOpenMeteoStructuredSummary(data, t)
  }

  if (
    data?.provenance?.profile === 'geonames_spatial_v1' ||
    'admin_summary' in data ||
    'admin' in data ||
    'nearby_place' in data
  ) {
    return renderGeoNamesStructuredSummary(data, t)
  }

  if (
    data?.provenance?.profile === 'bhl_references' ||
    'title_summary' in data ||
    'name_mentions' in data ||
    'page_links' in data
  ) {
    return renderBhlStructuredSummary(data, t)
  }

  if (
    data?.provenance?.profile === 'inaturalist_rich' ||
    'taxon' in data ||
    'observation_summary' in data ||
    'places' in data
  ) {
    return renderInaturalistStructuredSummary(data, t)
  }

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

export {
  ImageWithLoader,
  isStructuredSourceSummary,
  renderValue,
  renderMappedPreview,
  renderRawPreview,
  renderStructuredSummary,
}
