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
  Clock,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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

function groupResultsBySource(results: EnrichmentResult[]) {
  const grouped = new Map<string, { label: string; results: EnrichmentResult[] }>()

  for (const result of results) {
    const existing = grouped.get(result.source_id)
    if (existing) {
      existing.results.push(result)
    } else {
      grouped.set(result.source_id, {
        label: result.source_label,
        results: [result],
      })
    }
  }

  return grouped
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

export function EnrichmentTab({
  referenceName,
  hasEnrichment,
  onConfigSaved,
}: EnrichmentTabProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { isOffline } = useNetworkStatus()
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [referenceConfig, setReferenceConfig] = useState<ReferenceConfigPayload | null>(null)
  const [configLoading, setConfigLoading] = useState(true)
  const [configSaving, setConfigSaving] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [configSaved, setConfigSaved] = useState(false)
  const [persistedEnrichmentEnabled, setPersistedEnrichmentEnabled] = useState(hasEnrichment)
  const [isSetupExpanded, setIsSetupExpanded] = useState(!hasEnrichment)

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
  const [activeRuntimeTab, setActiveRuntimeTab] = useState<'preview' | 'results'>('preview')

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
  const resultsBySource = useMemo(() => groupResultsBySource(results), [results])

  useEffect(() => {
    setPersistedEnrichmentEnabled(hasEnrichment)
    setIsSetupExpanded(!hasEnrichment)
    setConfigSaved(false)
  }, [referenceName, hasEnrichment])

  useEffect(() => {
    if (previewScope !== 'all' && !enabledSources.some((source) => source.id === previewScope)) {
      setPreviewScope('all')
    }
  }, [enabledSources, previewScope])

  const loadReferenceConfig = useCallback(async () => {
    setConfigLoading(true)
    setConfigError(null)
    try {
      const response = await apiClient.get(`/config/references/${referenceName}/config`)
      const normalized = normalizeReferenceConfigPayload(response.data)
      const nextPersistedEnabled = Boolean(normalized?.enrichment?.some((source) => source.enabled))
      setReferenceConfig(normalized)
      setPersistedEnrichmentEnabled(nextPersistedEnabled)
      setIsSetupExpanded(!nextPersistedEnabled)
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
    if (activeRuntimeTab === 'results') {
      void loadResults()
    } else if (entities.length === 0 && !entitiesLoading) {
      void loadEntities()
    }
  }, [activeRuntimeTab, effectiveHasEnrichment, entities.length, entitiesLoading, loadEntities, loadResults])

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
    updateEnrichmentList((previous) => [
      ...previous,
      createDefaultEnrichmentSource(apiCategory, previous.length),
    ])
    setIsSetupExpanded(true)
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
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      const index = normalized.findIndex((source) => source.id === sourceId)
      if (index === -1) return previous

      const source = normalized[index]
      const duplicate = createDefaultEnrichmentSource(apiCategory, normalized.length)
      const entry = apiConfigToEnrichment(
        {
          id: duplicate.id!,
          label: `${source.label} Copy`,
        },
        source.config
      )
      return [
        ...normalized.slice(0, index + 1).map((item) => apiConfigToEnrichment(item, item.config)),
        entry,
        ...normalized.slice(index + 1).map((item) => apiConfigToEnrichment(item, item.config)),
      ]
    })
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
        activeRuntimeTab === 'results' ? loadResults() : Promise.resolve(),
      ])
    } finally {
      setIsRefreshing(false)
    }
  }

  const previewEnrichment = async (queryOverride?: string) => {
    const query = (queryOverride ?? previewQuery).trim()
    if (!query) return

    setPreviewLoading(true)
    setPreviewError(null)
    setPreviewData(null)

    try {
      const response = await apiClient.post<PreviewResponse>(
        `/enrichment/preview/${referenceName}`,
        {
          query,
          source_id: previewScope === 'all' ? undefined : previewScope,
        }
      )
      setPreviewQuery(query)
      setPreviewData(response.data)
    } catch (err: any) {
      setPreviewError(err.response?.data?.detail || t('enrichmentTab.errors.preview'))
    } finally {
      setPreviewLoading(false)
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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-base">{t('sources:reference.apiEnrichment')}</CardTitle>
              <CardDescription>{t('sources:configEditor.enrichWithApi')}</CardDescription>
            </div>
            {sources.length > 0 && !isSetupExpanded ? (
              <Button variant="outline" size="sm" onClick={() => setIsSetupExpanded(true)}>
                {t('common:actions.edit')}
              </Button>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
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

          {configLoading || !referenceConfig ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : !isSetupExpanded && sources.length > 0 ? (
            <div className="space-y-3 rounded-lg border bg-muted/30 px-4 py-3">
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
              </div>
              <div className="space-y-2">
                {sources.map((source) => (
                  <div key={source.id} className="flex items-center justify-between rounded border bg-background px-3 py-2 text-sm">
                    <div className="min-w-0">
                      <div className="truncate font-medium">{source.label}</div>
                      <div className="truncate text-muted-foreground">{source.config.api_url || source.plugin}</div>
                    </div>
                    <Badge variant={source.enabled ? 'secondary' : 'outline'}>
                      {source.enabled
                        ? t('sources:configEditor.enabled')
                        : t('sources:configEditor.disabled')}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between rounded-lg border px-4 py-3">
                <div>
                  <Label className="text-sm font-medium">
                    {t('enrichmentTab.config.sourcesTitle', {
                      defaultValue: 'API sources',
                    })}
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    {t('enrichmentTab.config.sourcesDescription', {
                      defaultValue: 'Add one or several APIs to enrich this reference.',
                    })}
                  </p>
                </div>
                <Button type="button" onClick={addSource}>
                  <Plus className="mr-2 h-4 w-4" />
                  {t('enrichmentTab.config.addSource', {
                    defaultValue: 'Ajouter une API',
                  })}
                </Button>
              </div>

              {sources.length === 0 ? (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {t('enrichmentTab.config.empty', {
                      defaultValue: 'Aucune source API configurée pour cette référence.',
                    })}
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="space-y-4">
                  {sources.map((source, index) => (
                    <Card key={source.id} className="border-border/70">
                      <CardHeader className="pb-3">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                          <div className="min-w-0 flex-1 space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant="outline">{source.id}</Badge>
                              <Badge variant={source.enabled ? 'secondary' : 'outline'}>
                                {source.enabled
                                  ? t('sources:configEditor.enabled')
                                  : t('sources:configEditor.disabled')}
                              </Badge>
                            </div>
                            <div className="grid gap-2 md:grid-cols-[1fr_auto] md:items-center">
                              <Input
                                value={source.label}
                                onChange={(event) => updateSourceLabel(source.id, event.target.value)}
                                placeholder={t('enrichmentTab.config.sourceLabel', {
                                  defaultValue: 'Nom de la source',
                                })}
                              />
                              <div className="flex items-center gap-2">
                                <Label htmlFor={`source-enabled-${source.id}`} className="text-sm">
                                  {source.enabled
                                    ? t('sources:configEditor.enabled')
                                    : t('sources:configEditor.disabled')}
                                </Label>
                                <Switch
                                  id={`source-enabled-${source.id}`}
                                  checked={source.enabled}
                                  onCheckedChange={(checked) => toggleSourceEnabled(source.id, checked)}
                                />
                              </div>
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center justify-end gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={index === 0}
                              onClick={() => moveSource(source.id, 'up')}
                            >
                              <ChevronUp className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={index === sources.length - 1}
                              onClick={() => moveSource(source.id, 'down')}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => duplicateSource(source.id)}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => removeSource(source.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <ApiEnrichmentConfig
                          config={source.config}
                          onChange={(apiConfig) => updateSourceConfig(source.id, apiConfig)}
                          category={apiCategory}
                        />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              <div className="flex justify-end border-t pt-4">
                <Button onClick={saveEnrichmentConfig} disabled={configSaving}>
                  {configSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t('sources:configEditor.saving')}
                    </>
                  ) : (
                    t('sources:configEditor.save')
                  )}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {effectiveHasEnrichment ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.status')}</CardTitle>
              </CardHeader>
              <CardContent className="min-h-[120px] space-y-2">
                {job ? (
                  <>
                    <Badge variant={job.status === 'running' ? 'default' : 'outline'}>
                      {t(`enrichmentTab.status.${job.status}`, {
                        defaultValue: job.status,
                      })}
                    </Badge>
                    {job.current_source_label ? (
                      <p className="text-xs text-muted-foreground">
                        {t('enrichmentTab.runtime.currentSource', {
                          defaultValue: 'Source en cours : {{name}}',
                          name: job.current_source_label,
                        })}
                      </p>
                    ) : null}
                    {job.current_entity ? (
                      <p className="truncate text-xs text-muted-foreground">
                        {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                      </p>
                    ) : null}
                  </>
                ) : (
                  <Badge variant="outline">{t('enrichmentTab.status.ready')}</Badge>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.progress')}</CardTitle>
              </CardHeader>
              <CardContent className="min-h-[120px]">
                {job ? (
                  <div className="space-y-2">
                    <Progress value={job.total > 0 ? (job.processed / job.total) * 100 : 0} className="h-2" />
                    <p className="text-sm">
                      {job.processed.toLocaleString()} / {job.total.toLocaleString()} ({Math.round(job.total > 0 ? (job.processed / job.total) * 100 : 0)}%)
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">-</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.database')}</CardTitle>
              </CardHeader>
              <CardContent className="min-h-[120px]">
                {statsLoading ? (
                  <div className="flex h-full items-center justify-center">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                ) : stats ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        {t('enrichmentTab.runtime.entities', {
                          defaultValue: 'Entités',
                        })}
                      </span>
                      <span className="font-medium">{stats.entity_total.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{t('enrichmentTab.stats.enriched')}</span>
                      <span className="font-medium text-green-600">{stats.enriched.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{t('enrichmentTab.stats.pending')}</span>
                      <span className="font-medium text-orange-500">{stats.pending.toLocaleString()}</span>
                    </div>
                    {stats.total > 0 ? (
                      <Progress value={(stats.enriched / stats.total) * 100} className="h-1.5" />
                    ) : null}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">-</p>
                )}
              </CardContent>
            </Card>
          </div>

          {isOffline ? (
            <Alert>
              <WifiOff className="h-4 w-4" />
              <AlertTitle>{t('enrichmentTab.offline.title')}</AlertTitle>
              <AlertDescription>{t('enrichmentTab.offline.description')}</AlertDescription>
            </Alert>
          ) : null}

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">
                {t('enrichmentTab.runtime.globalTitle', {
                  defaultValue: 'Lancement global',
                })}
              </CardTitle>
              <CardDescription>{t('enrichmentTab.actions.description')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {!job || ['completed', 'failed', 'cancelled'].includes(job.status) ? (
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
              ) : job.status === 'running' ? (
                <>
                  <Button variant="secondary" onClick={() => pauseJob()} disabled={jobLoadingScope !== null}>
                    {jobLoadingScope === 'all' ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Pause className="mr-2 h-4 w-4" />
                    )}
                    {t('enrichmentTab.actions.pause')}
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive">
                        <StopCircle className="mr-2 h-4 w-4" />
                        {t('common:actions.cancel')}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>{t('enrichmentTab.cancelDialog.title')}</AlertDialogTitle>
                        <AlertDialogDescription>
                          {t('enrichmentTab.cancelDialog.description', {
                            processed: job.processed,
                            total: job.total,
                          })}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>{t('enrichmentTab.cancelDialog.continue')}</AlertDialogCancel>
                        <AlertDialogAction onClick={() => cancelJob()} className="bg-destructive text-destructive-foreground">
                          {t('enrichmentTab.cancelDialog.confirm')}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </>
              ) : job.status === 'paused' || job.status === 'paused_offline' ? (
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
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive">
                        <StopCircle className="mr-2 h-4 w-4" />
                        {t('common:actions.cancel')}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>{t('enrichmentTab.cancelDialog.title')}</AlertDialogTitle>
                        <AlertDialogDescription>
                          {t('enrichmentTab.cancelDialog.description', {
                            processed: job.processed,
                            total: job.total,
                          })}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>{t('enrichmentTab.cancelDialog.resume')}</AlertDialogCancel>
                        <AlertDialogAction onClick={() => cancelJob()} className="bg-destructive text-destructive-foreground">
                          {t('enrichmentTab.cancelDialog.confirm')}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </>
              ) : null}

              <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                {t('common:actions.refresh')}
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-4">
            {enabledSources.map((source) => {
              const sourceStats = stats?.sources.find((item) => item.source_id === source.id)
              const sourceProgress = getSourceProgress(source.id, sourceStats)
              const isRunningSingleSource = runningSingleSourceId === source.id

              return (
                <Card key={source.id} className="border-border/70">
                  <CardHeader className="pb-3">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <CardTitle className="text-base">{source.label}</CardTitle>
                          <Badge variant="outline">{source.id}</Badge>
                          {sourceStats ? (
                            <Badge variant={sourceStats.status === 'running' ? 'default' : 'outline'}>
                              {t(`enrichmentTab.status.${sourceStats.status}`, {
                                defaultValue: sourceStats.status,
                              })}
                            </Badge>
                          ) : null}
                        </div>
                        <CardDescription>{source.config.api_url || source.plugin}</CardDescription>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {(!job || ['completed', 'failed', 'cancelled'].includes(job.status)) && (sourceStats?.pending ?? 0) > 0 ? (
                          <Button
                            type="button"
                            onClick={() => startSourceJob(source.id)}
                            disabled={jobLoadingScope !== null || isOffline}
                            title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
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

                        {isRunningSingleSource && job?.status === 'running' ? (
                          <>
                            <Button variant="secondary" onClick={() => pauseJob(source.id)} disabled={jobLoadingScope !== null}>
                              {jobLoadingScope === source.id ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Pause className="mr-2 h-4 w-4" />
                              )}
                              {t('enrichmentTab.actions.pause')}
                            </Button>
                            <Button variant="destructive" onClick={() => cancelJob(source.id)} disabled={jobLoadingScope !== null}>
                              <StopCircle className="mr-2 h-4 w-4" />
                              {t('common:actions.cancel')}
                            </Button>
                          </>
                        ) : null}

                        {isRunningSingleSource && (job?.status === 'paused' || job?.status === 'paused_offline') ? (
                          <>
                            <Button onClick={() => resumeJob(source.id)} disabled={jobLoadingScope !== null || isOffline}>
                              {jobLoadingScope === source.id ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="mr-2 h-4 w-4" />
                              )}
                              {t('enrichmentTab.actions.resume')}
                            </Button>
                            <Button variant="destructive" onClick={() => cancelJob(source.id)} disabled={jobLoadingScope !== null}>
                              <StopCircle className="mr-2 h-4 w-4" />
                              {t('common:actions.cancel')}
                            </Button>
                          </>
                        ) : null}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{t('enrichmentTab.cards.progress')}</span>
                        <span>
                          {sourceProgress.processed.toLocaleString()} / {sourceProgress.total.toLocaleString()} ({Math.round(sourceProgress.percentage)}%)
                        </span>
                      </div>
                      <Progress value={sourceProgress.percentage} className="h-1.5" />
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                        {t('enrichmentTab.stats.enriched')}: {sourceStats?.enriched.toLocaleString() ?? 0}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-orange-500" />
                        {t('enrichmentTab.stats.pending')}: {sourceStats?.pending.toLocaleString() ?? 0}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {job?.error ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{t('common:status.error')}</AlertTitle>
              <AlertDescription>{job.error}</AlertDescription>
            </Alert>
          ) : null}

          <Tabs
            value={activeRuntimeTab}
            onValueChange={(value) => setActiveRuntimeTab(value as 'preview' | 'results')}
            className="space-y-4"
          >
            <TabsList>
              <TabsTrigger value="preview">{t('enrichmentTab.tabs.preview')}</TabsTrigger>
              <TabsTrigger value="results">{t('enrichmentTab.tabs.results')}</TabsTrigger>
            </TabsList>

            <TabsContent value="preview" className="space-y-4">
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">{t('enrichmentTab.preview.selectEntity')}</CardTitle>
                    <CardDescription>{t('enrichmentTab.preview.selectEntityDescription')}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-2">
                      <Label>{t('enrichmentTab.runtime.previewScope', { defaultValue: 'Scope' })}</Label>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant={previewScope === 'all' ? 'default' : 'outline'}
                          onClick={() => setPreviewScope('all')}
                        >
                          {t('enrichmentTab.runtime.previewAllSources', {
                            defaultValue: 'Toutes les APIs',
                          })}
                        </Button>
                        {enabledSources.map((source) => (
                          <Button
                            key={source.id}
                            type="button"
                            size="sm"
                            variant={previewScope === source.id ? 'default' : 'outline'}
                            onClick={() => setPreviewScope(source.id)}
                          >
                            {source.label}
                          </Button>
                        ))}
                      </div>
                    </div>

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

                    <ScrollArea className="h-[320px] rounded-md border">
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
                              onClick={() => {
                                setPreviewQuery(entity.name)
                                void previewEnrichment(entity.name)
                              }}
                              className={`group flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-accent ${
                                previewQuery === entity.name ? 'bg-accent' : ''
                              }`}
                            >
                              <span className="truncate flex-1">{entity.name}</span>
                              <div className="flex items-center gap-2">
                                {entity.total_sources && entity.total_sources > 1 ? (
                                  <Badge variant="outline" className="text-xs">
                                    {entity.enriched_count ?? 0}/{entity.total_sources}
                                  </Badge>
                                ) : null}
                                {entity.enriched ? (
                                  <Badge variant="secondary" className="bg-green-100 text-xs text-green-700">
                                    <CheckCircle2 className="mr-1 h-3 w-3" />
                                    {t('enrichmentTab.stats.enrichedOne')}
                                  </Badge>
                                ) : null}
                                <Eye className="h-4 w-4 opacity-0 group-hover:opacity-50" />
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </ScrollArea>

                    <div className="border-t pt-2">
                      <Label className="mb-1.5 block text-xs text-muted-foreground">
                        {t('enrichmentTab.preview.manualInput')}
                      </Label>
                      <div className="flex gap-2">
                        <Input
                          placeholder={t('common:labels.name')}
                          value={previewQuery}
                          onChange={(event) => setPreviewQuery(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') {
                              void previewEnrichment()
                            }
                          }}
                        />
                        <Button
                          type="button"
                          onClick={() => previewEnrichment()}
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
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">{t('enrichmentTab.preview.resultTitle')}</CardTitle>
                    <CardDescription>{t('enrichmentTab.preview.resultDescription')}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {previewLoading ? (
                      <div className="flex min-h-[320px] items-center justify-center">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    ) : previewError ? (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{previewError}</AlertDescription>
                      </Alert>
                    ) : previewData?.results?.length ? (
                      <div className="space-y-4">
                        {previewData.results.map((result) => (
                          <Card key={`${result.source_id}-${previewData.entity_name}`} className="border-border/70">
                            <CardHeader className="pb-3">
                              <div className="flex flex-wrap items-center gap-2">
                                <CardTitle className="text-sm">{result.source_label}</CardTitle>
                                <Badge variant={result.success ? 'secondary' : 'destructive'}>
                                  {result.success
                                    ? t('enrichmentTab.result.success')
                                    : t('enrichmentTab.result.failed')}
                                </Badge>
                              </div>
                            </CardHeader>
                            <CardContent>
                              {result.success && result.data ? (
                                <div className="rounded-md border">
                                  <Table>
                                    <TableHeader>
                                      <TableRow>
                                        <TableHead>{t('enrichmentTab.table.field')}</TableHead>
                                        <TableHead>{t('enrichmentTab.table.value')}</TableHead>
                                      </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                      {Object.entries(result.data).map(([field, value]) => (
                                        <TableRow key={field}>
                                          <TableCell className="font-medium">{field}</TableCell>
                                          <TableCell>{renderValue(value)}</TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </div>
                              ) : (
                                <Alert variant="destructive">
                                  <AlertCircle className="h-4 w-4" />
                                  <AlertDescription>{result.error || t('enrichmentTab.errors.preview')}</AlertDescription>
                                </Alert>
                              )}
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    ) : (
                      <div className="flex min-h-[320px] flex-col items-center justify-center text-center text-muted-foreground">
                        <Eye className="mb-3 h-10 w-10 opacity-30" />
                        <div className="text-sm font-medium">{t('enrichmentTab.preview.emptyTitle')}</div>
                        <div className="text-sm">{t('enrichmentTab.preview.emptyDescription')}</div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="results" className="space-y-4">
              {resultsLoading ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : results.length === 0 ? (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>{t('enrichmentTab.results.emptyTitle')}</AlertTitle>
                  <AlertDescription>{t('enrichmentTab.results.emptyDescription')}</AlertDescription>
                </Alert>
              ) : (
                <div className="space-y-4">
                  {Array.from(resultsBySource.entries()).map(([sourceId, group]) => (
                    <Card key={sourceId} className="border-border/70">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">{group.label}</CardTitle>
                        <CardDescription>{group.results.length} result(s)</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="rounded-md border">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>{t('enrichmentTab.table.entity')}</TableHead>
                                <TableHead>{t('enrichmentTab.result.success')}</TableHead>
                                <TableHead>{t('enrichmentTab.table.date')}</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {group.results.map((result) => (
                                <TableRow
                                  key={`${sourceId}-${getResultEntityName(result)}-${result.processed_at}`}
                                  className="cursor-pointer"
                                  onClick={() => setSelectedResult(result)}
                                >
                                  <TableCell className="font-medium">{getResultEntityName(result)}</TableCell>
                                  <TableCell>
                                    <Badge variant={result.success ? 'secondary' : 'destructive'}>
                                      {result.success
                                        ? t('enrichmentTab.result.success')
                                        : t('enrichmentTab.result.failed')}
                                    </Badge>
                                  </TableCell>
                                  <TableCell className="text-muted-foreground">
                                    {new Date(result.processed_at).toLocaleString()}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </>
      ) : null}

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
                        <TableRow key={field}>
                          <TableCell className="font-medium">{field}</TableCell>
                          <TableCell>{renderValue(value)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
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
