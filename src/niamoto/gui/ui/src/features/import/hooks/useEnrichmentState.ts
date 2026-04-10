/**
 * useEnrichmentState — Extracted state, effects, and actions from EnrichmentTab.
 *
 * Phase 1 of the enrichment tab UX redesign: pure state extraction,
 * no visual changes. The component renders identically but delegates
 * all data management to this hook.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'
import { useNetworkStatus } from '@/shared/hooks/useNetworkStatus'
import { useNotificationStore } from '@/stores/notificationStore'

import type { ApiCategory, ApiConfig } from '../components/enrichment/ApiEnrichmentConfig'
import {
  apiConfigToEnrichment,
  createDefaultEnrichmentSource,
  normalizeEnrichmentSources,
  type NormalizedEnrichmentSource,
  type ReferenceEnrichmentConfig,
} from '../components/enrichment/enrichmentSources'

// ---------------------------------------------------------------------------
// Interfaces (re-exported for consumers)
// ---------------------------------------------------------------------------

export interface ReferenceConfigPayload {
  kind?: string
  description?: string
  connector?: Record<string, unknown>
  hierarchy?: Record<string, unknown>
  schema?: Record<string, unknown>
  enrichment?: ReferenceEnrichmentConfig[]
}

interface ReferenceConfigResponse {
  name?: string
  config?: ReferenceConfigPayload
}

export interface EnrichmentSourceStats {
  source_id: string
  label: string
  enabled: boolean
  total: number
  enriched: number
  pending: number
  status: string
}

export interface EnrichmentStatsResponse {
  reference_name?: string
  entity_total: number
  source_total: number
  total: number
  enriched: number
  pending: number
  sources: EnrichmentSourceStats[]
}

export interface EnrichmentJob {
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

export interface EnrichmentResult {
  reference_name?: string
  source_id: string
  source_label: string
  entity_name?: string
  taxon_name?: string
  success: boolean
  data?: Record<string, unknown>
  error?: string
  processed_at: string
}

export interface PreviewSourceResult {
  source_id: string
  source_label: string
  success: boolean
  data?: Record<string, unknown>
  raw_data?: unknown
  error?: string
  config_used?: Record<string, unknown>
}

export interface PreviewResponse {
  success: boolean
  entity_name: string
  results: PreviewSourceResult[]
  error?: string
}

export interface EntityOption {
  id: number | string
  name: string
  enriched: boolean
  enriched_count?: number
  total_sources?: number
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

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

export function referenceHasGeometry(config: ReferenceConfigPayload | null | undefined): boolean {
  if (!config || typeof config !== 'object') {
    return false
  }

  if (config.kind === 'spatial') {
    return true
  }

  const fields = Array.isArray(config.schema?.fields) ? config.schema.fields : []
  return fields.some((field) => field && typeof field === 'object' && field.type === 'geometry')
}

export function getResultEntityName(result: EnrichmentResult): string {
  return result.entity_name || result.taxon_name || '-'
}

// ---------------------------------------------------------------------------
// Hook options & return type
// ---------------------------------------------------------------------------

export interface UseEnrichmentStateOptions {
  referenceName: string
  hasEnrichment: boolean
  mode?: 'workspace' | 'quick'
  initialSourceId?: string | null
  onConfigSaved?: () => void
}

export interface SourceProgress {
  total: number
  processed: number
  percentage: number
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useEnrichmentState({
  referenceName,
  hasEnrichment,
  mode = 'workspace',
  initialSourceId = null,
  onConfigSaved,
}: UseEnrichmentStateOptions) {
  const { t } = useTranslation(['sources', 'common'])
  const { isOffline } = useNetworkStatus()
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const previewRequestRef = useRef(0)
  const previewSourceSignatureRef = useRef<string | null>(null)
  const entitiesPreloadedRef = useRef(false)
  const resultsPreloadedRef = useRef(false)
  const workspaceSectionRef = useRef<HTMLDivElement | null>(null)

  // -- Config state ---------------------------------------------------------
  const [referenceConfig, setReferenceConfig] = useState<ReferenceConfigPayload | null>(null)
  const [configLoading, setConfigLoading] = useState(true)
  const [configSaving, setConfigSaving] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [configSaved, setConfigSaved] = useState(false)
  const [persistedEnrichmentEnabled, setPersistedEnrichmentEnabled] = useState(hasEnrichment)

  // -- Stats / Job / Results ------------------------------------------------
  const [stats, setStats] = useState<EnrichmentStatsResponse | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [job, setJob] = useState<EnrichmentJob | null>(null)
  const [results, setResults] = useState<EnrichmentResult[]>([])
  const [resultsLoading, setResultsLoading] = useState(false)

  // -- Entities / Preview ---------------------------------------------------
  const [entities, setEntities] = useState<EntityOption[]>([])
  const [entitiesLoading, setEntitiesLoading] = useState(false)
  const [entitySearch, setEntitySearch] = useState('')
  const [previewQuery, setPreviewQuery] = useState('')
  const [previewScope, setPreviewScope] = useState<string>('all')
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [selectedResult, setSelectedResult] = useState<EnrichmentResult | null>(null)

  // -- UI state -------------------------------------------------------------
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null)
  const [pendingInitialSourceId, setPendingInitialSourceId] = useState<string | null>(initialSourceId)
  const [workspacePane, setWorkspacePane] = useState<'config' | 'preview' | 'results'>('config')
  const [previewResultMode, setPreviewResultMode] = useState<'mapped' | 'raw'>('mapped')
  const [jobLoadingScope, setJobLoadingScope] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // -- Derived state --------------------------------------------------------
  const isSpatialReference = useMemo(() => referenceHasGeometry(referenceConfig), [referenceConfig])
  const apiCategory: ApiCategory = isSpatialReference ? 'spatial' : 'taxonomy'

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
  const canLoadEntities = sources.length > 0
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

  // -- Data loaders ---------------------------------------------------------

  const loadReferenceConfig = useCallback(async () => {
    setConfigLoading(true)
    setConfigError(null)
    try {
      const response = await apiClient.get(`/config/references/${referenceName}/config`)
      const normalized = normalizeReferenceConfigPayload(response.data)
      const nextPersistedEnabled = Boolean(normalized?.enrichment?.some((source) => source.enabled))
      setReferenceConfig(normalized)
      setPersistedEnrichmentEnabled(nextPersistedEnabled)
    } catch (err: unknown) {
      console.error('Failed to load reference config:', err)
      setConfigError(getApiErrorMessage(err, t('enrichmentTab.errors.loadConfig')))
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
    } catch (err: unknown) {
      const isNotFound =
        typeof err === 'object' &&
        err !== null &&
        'response' in err &&
        typeof err.response === 'object' &&
        err.response !== null &&
        'status' in err.response &&
        err.response.status === 404

      if (!isNotFound) {
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

  // -- Polling --------------------------------------------------------------

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

  // -- Effects --------------------------------------------------------------

  useEffect(() => {
    setPersistedEnrichmentEnabled(hasEnrichment)
    setConfigSaved(false)
    setWorkspacePane('config')
    entitiesPreloadedRef.current = false
    resultsPreloadedRef.current = false
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
    if (mode === 'quick') {
      if (effectiveHasEnrichment && !resultsPreloadedRef.current) {
        resultsPreloadedRef.current = true
        void loadResults()
      }
      if (canLoadEntities && !entitiesPreloadedRef.current && !entitiesLoading) {
        entitiesPreloadedRef.current = true
        void loadEntities()
      }
      return
    }

    if (effectiveHasEnrichment && !resultsPreloadedRef.current) {
      resultsPreloadedRef.current = true
      void loadResults()
    }

    if (canLoadEntities && !entitiesPreloadedRef.current && !entitiesLoading) {
      entitiesPreloadedRef.current = true
      void loadEntities()
    }
  }, [
    canLoadEntities,
    effectiveHasEnrichment,
    entitiesLoading,
    loadEntities,
    loadResults,
    mode,
  ])

  // -- Source manipulation --------------------------------------------------

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

  const addSource = useCallback(() => {
    const newSource = createDefaultEnrichmentSource(apiCategory, sources.length)
    updateEnrichmentList((previous) => [
      ...previous,
      newSource,
    ])
    setActiveSourceId(newSource.id ?? null)
    setWorkspacePane('config')
  }, [apiCategory, sources.length, updateEnrichmentList])

  const updateSource = useCallback((sourceId: string, updater: (source: NormalizedEnrichmentSource) => ReferenceEnrichmentConfig) => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return normalized.map((source) => (
        source.id === sourceId ? updater(source) : apiConfigToEnrichment(source, source.config)
      ))
    })
  }, [apiCategory, updateEnrichmentList])

  const updateSourceLabel = useCallback((sourceId: string, label: string) => {
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
  }, [apiCategory, updateEnrichmentList])

  const updateSourceConfig = useCallback((sourceId: string, apiConfig: ApiConfig) => {
    updateSource(sourceId, (source) => apiConfigToEnrichment(source, apiConfig))
  }, [updateSource])

  const resetPreviewState = useCallback((nextScope?: string) => {
    previewRequestRef.current += 1
    setPreviewLoading(false)
    setPreviewError(null)
    setPreviewData(null)
    if (nextScope !== undefined) {
      setPreviewScope(nextScope)
    }
  }, [])

  const applyPresetLabel = useCallback((sourceId: string, label: string) => {
    updateSourceLabel(sourceId, label)
    resetPreviewState(sourceId)
  }, [resetPreviewState, updateSourceLabel])

  const toggleSourceEnabled = useCallback((sourceId: string, enabled: boolean) => {
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
  }, [apiCategory, updateEnrichmentList])

  const duplicateSource = useCallback((sourceId: string) => {
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
  }, [apiCategory, sources, updateEnrichmentList])

  const moveSource = useCallback((sourceId: string, direction: 'up' | 'down') => {
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
  }, [apiCategory, updateEnrichmentList])

  const removeSource = useCallback((sourceId: string) => {
    updateEnrichmentList((previous) => {
      const normalized = normalizeEnrichmentSources(previous, apiCategory)
      return normalized
        .filter((source) => source.id !== sourceId)
        .map((source) => apiConfigToEnrichment(source, source.config))
    })
  }, [apiCategory, updateEnrichmentList])

  // -- Config save ----------------------------------------------------------

  const saveEnrichmentConfig = useCallback(async () => {
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
    } catch (err: unknown) {
      console.error('Failed to save enrichment config:', err)
      const message = getApiErrorMessage(err, t('enrichmentTab.errors.saveConfig'))
      setConfigError(message)
      toast.error(t('enrichmentTab.toasts.saveErrorTitle'), {
        description: message,
      })
    } finally {
      setConfigSaving(false)
    }
  }, [loadReferenceConfig, loadStats, onConfigSaved, referenceConfig, referenceName, t])

  // -- Job controls ---------------------------------------------------------

  const trackStartedJob = useCallback((startedJob: EnrichmentJob, pendingCount: number) => {
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
  }, [referenceName, t])

  const startGlobalJob = useCallback(async () => {
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
    } catch (err: unknown) {
      console.error('Failed to start job:', err)
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: getApiErrorMessage(err, t('enrichmentTab.errors.startJob')),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }, [isOffline, referenceName, startPolling, stats?.pending, t, trackStartedJob])

  const startSourceJob = useCallback(async (sourceId: string) => {
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
    } catch (err: unknown) {
      console.error('Failed to start source job:', err)
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: getApiErrorMessage(err, t('enrichmentTab.errors.startJob')),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }, [isOffline, referenceName, startPolling, stats?.sources, t, trackStartedJob])

  const pauseJob = useCallback(async (sourceId?: string) => {
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
    } catch (err: unknown) {
      console.error('Failed to pause job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: getApiErrorMessage(err, t('enrichmentTab.errors.pauseJob')),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }, [loadJobStatus, referenceName, t])

  const resumeJob = useCallback(async (sourceId?: string) => {
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
    } catch (err: unknown) {
      console.error('Failed to resume job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: getApiErrorMessage(err, t('enrichmentTab.errors.resumeJob')),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }, [isOffline, loadJobStatus, referenceName, startPolling, t])

  const cancelJob = useCallback(async (sourceId?: string) => {
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
    } catch (err: unknown) {
      console.error('Failed to cancel job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: getApiErrorMessage(err, t('enrichmentTab.errors.cancelJob')),
      })
    } finally {
      setJobLoadingScope(null)
    }
  }, [job?.processed, loadJobStatus, loadStats, referenceName, stopPolling, t])

  // -- Refresh / Preview ----------------------------------------------------

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([
        loadStats(),
        loadJobStatus(),
        effectiveHasEnrichment ? loadResults() : Promise.resolve(),
        canLoadEntities ? loadEntities(entitySearch) : Promise.resolve(),
      ])
    } finally {
      setIsRefreshing(false)
    }
  }, [canLoadEntities, effectiveHasEnrichment, entitySearch, loadEntities, loadJobStatus, loadResults, loadStats])

  // Preview-related effects
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

  const previewEnrichment = useCallback(async (
    queryOverride?: string,
    scopeOverride?: string,
    entityIdOverride?: string | number
  ) => {
    const query = String(queryOverride ?? previewQuery ?? '').trim()
    if (!query) return
    const nextScope = scopeOverride ?? previewScope
    const requestId = ++previewRequestRef.current
    const previewSourceOverride = nextScope === 'all'
      ? undefined
      : sources.find((source) => source.id === nextScope)

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
          entity_id: entityIdOverride,
          source_config: previewSourceOverride
            ? apiConfigToEnrichment(previewSourceOverride, previewSourceOverride.config)
            : undefined,
        }
      )
      if (requestId !== previewRequestRef.current) {
        return
      }
      setPreviewQuery(query)
      setPreviewData(response.data)
    } catch (err: unknown) {
      if (requestId !== previewRequestRef.current) {
        return
      }
      setPreviewError(getApiErrorMessage(err, t('enrichmentTab.errors.preview')))
    } finally {
      if (requestId === previewRequestRef.current) {
        setPreviewLoading(false)
      }
    }
  }, [previewQuery, previewScope, referenceName, sources, t])

  // -- Derived variables (job-related) --------------------------------------

  const runningSingleSourceId = job?.mode === 'single' ? job.source_id ?? undefined : undefined

  const getSourceProgress = useCallback((sourceId: string, srcStats: EnrichmentSourceStats | undefined): SourceProgress => {
    if (job && job.current_source_id === sourceId) {
      const total = job.current_source_total ?? srcStats?.total ?? 0
      const processed = job.current_source_processed ?? 0
      const percentage = total > 0 ? (processed / total) * 100 : 0
      return { total, processed, percentage }
    }

    const total = srcStats?.total ?? 0
    const processed = srcStats?.enriched ?? 0
    const percentage = total > 0 ? (processed / total) * 100 : 0
    return { total, processed, percentage }
  }, [job])

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

  // -- Return ---------------------------------------------------------------

  return {
    // Config
    referenceConfig,
    configLoading,
    configSaving,
    configError,
    configSaved,
    persistedEnrichmentEnabled,
    effectiveHasEnrichment,

    // Stats
    stats,
    statsLoading,

    // Job
    job,
    jobLoadingScope,
    isTerminalJob,
    runningSingleSourceId,

    // Results
    results,
    resultsLoading,
    recentResults,

    // Entities
    entities,
    entitiesLoading,
    entitySearch,
    setEntitySearch,

    // Preview
    previewQuery,
    setPreviewQuery,
    previewScope,
    setPreviewScope,
    previewData,
    previewLoading,
    previewError,
    previewResultMode,
    setPreviewResultMode,

    // Sources
    sources,
    enabledSources,
    activeSource,
    activeSourceId,
    setActiveSourceId,
    activeSourceStats,
    activeSourceResults,
    activeSourceProgress,
    activeSourceIndex,
    activePreviewResult,
    isRunningSingleSource,
    canStartActiveSource,
    previewableSources,
    quickSelectedSource,

    // UI
    workspacePane,
    setWorkspacePane,
    selectedResult,
    setSelectedResult,
    isRefreshing,
    isSpatialReference,
    apiCategory,

    // Network
    isOffline,

    // Actions
    addSource,
    updateSource,
    updateSourceLabel,
    updateSourceConfig,
    applyPresetLabel,
    toggleSourceEnabled,
    duplicateSource,
    moveSource,
    removeSource,
    saveEnrichmentConfig,
    startGlobalJob,
    startSourceJob,
    pauseJob,
    resumeJob,
    cancelJob,
    handleRefresh,
    previewEnrichment,
    resetPreviewState,
    loadEntities,
    getSourceProgress,

    // Refs
    workspaceSectionRef,
  }
}
