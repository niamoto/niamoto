/**
 * EnrichmentTab - Reusable enrichment management component for references
 *
 * Features:
 * - View enrichment stats from database
 * - Start/pause/resume/cancel enrichment jobs
 * - Track progress in real-time
 * - Preview individual entity enrichment
 * - View enrichment results
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Search,
  StopCircle,
  Eye,
  Database,
  Clock,
  ImageIcon,
  ExternalLink,
} from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { apiClient } from '@/shared/lib/api/client'
import { ApiEnrichmentConfig, type ApiConfig, type ApiCategory } from './ApiEnrichmentConfig'
import { toast } from 'sonner'
import { useNotificationStore } from '@/stores/notificationStore'
import { useNetworkStatus } from '@/hooks/useNetworkStatus'
import { WifiOff } from 'lucide-react'

interface EnrichmentTabProps {
  referenceName: string
  hasEnrichment: boolean
  onConfigSaved?: () => void
}

interface ReferenceEnrichmentConfig {
  plugin?: string
  enabled?: boolean
  config?: {
    api_url?: string
    auth_method?: 'none' | 'api_key' | 'bearer' | 'basic'
    auth_params?: {
      key?: string
      location?: 'header' | 'query'
      name?: string
      username?: string
      password?: string
    }
    query_params?: Record<string, string>
    query_field?: string
    query_param_name?: string
    rate_limit?: number
    cache_results?: boolean
    response_mapping?: Record<string, string>
  }
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

function enrichmentToApiConfig(enrichment?: ReferenceEnrichmentConfig): ApiConfig {
  return {
    enabled: enrichment?.enabled ?? false,
    plugin: enrichment?.plugin ?? 'api_taxonomy_enricher',
    api_url: enrichment?.config?.api_url ?? '',
    auth_method: (enrichment?.config?.auth_method as ApiConfig['auth_method']) ?? 'none',
    auth_params: enrichment?.config?.auth_params,
    query_params: enrichment?.config?.query_params,
    query_field: enrichment?.config?.query_field ?? 'full_name',
    query_param_name: enrichment?.config?.query_param_name ?? 'q',
    rate_limit: enrichment?.config?.rate_limit ?? 2,
    cache_results: enrichment?.config?.cache_results ?? true,
    response_mapping: enrichment?.config?.response_mapping,
  }
}

function apiConfigToEnrichment(apiConfig: ApiConfig): ReferenceEnrichmentConfig {
  return {
    plugin: apiConfig.plugin,
    enabled: apiConfig.enabled,
    config: {
      api_url: apiConfig.api_url,
      auth_method: apiConfig.auth_method,
      auth_params: apiConfig.auth_params,
      query_params: apiConfig.query_params,
      query_field: apiConfig.query_field,
      query_param_name: apiConfig.query_param_name,
      rate_limit: apiConfig.rate_limit,
      cache_results: apiConfig.cache_results,
      response_mapping: apiConfig.response_mapping,
    },
  }
}

interface EnrichmentJob {
  id: string
  status: 'pending' | 'running' | 'paused' | 'paused_offline' | 'completed' | 'failed' | 'cancelled'
  total: number
  processed: number
  successful: number
  failed: number
  started_at: string
  updated_at: string
  error?: string
  current_entity?: string
}

interface EnrichmentResult {
  entity_name?: string
  taxon_name?: string  // Legacy field name from backend
  success: boolean
  data?: Record<string, any>
  error?: string
  processed_at: string
}

interface EnrichmentStats {
  total: number
  enriched: number
  pending: number
}

// Component for image with loading state
const ImageWithLoader = ({ src, alt }: { src: string; alt: string }) => {
  const { t } = useTranslation(['sources'])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  return (
    <div className="relative inline-block">
      {loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted rounded">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
      {error ? (
        <div className="flex items-center gap-2 text-muted-foreground text-xs">
          <ImageIcon className="h-4 w-4" />
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline truncate max-w-[150px]"
          >
            {t('enrichmentTab.viewImage')}
          </a>
        </div>
      ) : (
        <a href={src} target="_blank" rel="noopener noreferrer">
          <img
            src={src}
            alt={alt}
            className={`h-16 w-16 object-cover rounded border hover:opacity-80 transition-opacity ${loading ? 'opacity-0' : 'opacity-100'}`}
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

// Helper to detect and render URLs as clickable links or images
const renderValue = (value: any): React.ReactNode => {
  if (value === null || value === undefined) return '-'

  if (typeof value === 'string') {
    // Check if it's a URL
    const urlPattern = /^(https?:\/\/[^\s]+)$/i
    if (urlPattern.test(value)) {
      // Check if it's an image URL
      const imagePattern = /\.(jpg|jpeg|png|gif|webp|svg|bmp)(\?.*)?$/i
      const isImageUrl = imagePattern.test(value) ||
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
          className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
        >
          <span className="truncate max-w-[200px]">{value}</span>
          <ExternalLink className="h-3 w-3 shrink-0" />
        </a>
      )
    }

    // Check if value contains URLs mixed with text
    const urlInTextPattern = /(https?:\/\/[^\s]+)/gi
    const parts = value.split(urlInTextPattern)
    if (parts.length > 1) {
      return (
        <span>
          {parts.map((part, idx) => {
            if (urlInTextPattern.test(part)) {
              urlInTextPattern.lastIndex = 0 // Reset regex state
              return (
                <a
                  key={idx}
                  href={part}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
                >
                  {part}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )
            }
            return <span key={idx}>{part}</span>
          })}
        </span>
      )
    }

    return value
  }

  if (typeof value === 'object') {
    // For objects, check if any nested value is a URL
    return (
      <pre className="text-xs whitespace-pre-wrap max-w-md">
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

  // State
  const [stats, setStats] = useState<EnrichmentStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)  // Only true on initial load

  const [job, setJob] = useState<EnrichmentJob | null>(null)
  const [jobLoading, setJobLoading] = useState(false)
  const [configLoading, setConfigLoading] = useState(true)
  const [configSaving, setConfigSaving] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [configSaved, setConfigSaved] = useState(false)
  const [referenceConfig, setReferenceConfig] = useState<ReferenceConfigPayload | null>(null)
  const [isSetupExpanded, setIsSetupExpanded] = useState(!hasEnrichment)

  const [results, setResults] = useState<EnrichmentResult[]>([])
  const [resultsLoading, setResultsLoading] = useState(false)

  const [previewQuery, setPreviewQuery] = useState('')
  const [previewData, setPreviewData] = useState<any | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Entity list for selector
  const [entities, setEntities] = useState<Array<{ id: number; name: string; enriched: boolean }>>([])
  const [entitiesLoading, setEntitiesLoading] = useState(false)
  const [entitySearch, setEntitySearch] = useState('')

  const [selectedResult, setSelectedResult] = useState<EnrichmentResult | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isPausing, setIsPausing] = useState(false)
  const [isResuming, setIsResuming] = useState(false)

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const apiCategory: ApiCategory =
    referenceConfig?.kind === 'spatial' ? 'spatial' : 'taxonomy'
  const enrichmentConfig = enrichmentToApiConfig(referenceConfig?.enrichment?.[0])
  const enrichmentEnabled = enrichmentConfig.enabled

  const loadReferenceConfig = useCallback(async () => {
    setConfigLoading(true)
    setConfigError(null)
    try {
      const response = await apiClient.get(`/config/references/${referenceName}/config`)
      const normalized = normalizeReferenceConfigPayload(response.data)
      setReferenceConfig(normalized)
      setIsSetupExpanded(!(normalized?.enrichment?.[0]?.enabled ?? false))
    } catch (err: any) {
      console.error('Failed to load reference config:', err)
      setConfigError(err.response?.data?.detail || t('enrichmentTab.errors.loadConfig'))
      setReferenceConfig(null)
    } finally {
      setConfigLoading(false)
    }
  }, [referenceName])

  const updateEnrichmentConfig = (apiConfig: ApiConfig) => {
    setConfigSaved(false)
    setReferenceConfig((previous) => {
      if (!previous) return previous
      return {
        ...previous,
        enrichment: [apiConfigToEnrichment(apiConfig)],
      }
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

  // Load enrichment stats (silent refresh - no loading state after initial load)
  const loadStats = useCallback(async (showLoader = false) => {
    if (showLoader) setStatsLoading(true)
    try {
      const response = await apiClient.get(`/enrichment/stats/${referenceName}`)
      setStats(response.data)
    } catch (err: any) {
      console.error('Failed to load stats:', err)
      // Set default stats if endpoint doesn't exist yet
      setStats(prev => prev ?? { total: 0, enriched: 0, pending: 0 })
    } finally {
      if (showLoader) setStatsLoading(false)
    }
  }, [referenceName])

  // Load current job status
  const loadJobStatus = useCallback(async () => {
    try {
      const response = await apiClient.get(`/enrichment/job/${referenceName}`)
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

  // Start enrichment job
  const startJob = async () => {
    setJobLoading(true)
    try {
      const response = await apiClient.post(`/enrichment/start/${referenceName}`)
      setJob(response.data)
      startPolling()
      useNotificationStore.getState().trackJob({
        jobId: response.data.id,
        jobType: 'enrichment',
        status: 'running',
        progress: 0,
        message: `${stats?.pending || 0} entités à traiter`,
        startedAt: new Date().toISOString(),
        meta: { referenceName },
      })
      toast.success(t('enrichmentTab.toasts.startedTitle'), {
        description: t('enrichmentTab.toasts.startedDescription', {
          count: stats?.pending || 0,
        }),
      })
    } catch (err: any) {
      console.error('Failed to start job:', err)
      toast.error(t('enrichmentTab.toasts.startErrorTitle'), {
        description: err.response?.data?.detail || t('enrichmentTab.errors.startJob'),
      })
    } finally {
      setJobLoading(false)
    }
  }

  // Pause job
  const pauseJob = async () => {
    if (!job) return
    setIsPausing(true)
    try {
      await apiClient.post(`/enrichment/pause/${referenceName}`)
      await loadJobStatus()
      toast.info(t('enrichmentTab.toasts.pausedTitle'), {
        description: t('enrichmentTab.toasts.pausedDescription'),
      })
    } catch (err: any) {
      console.error('Failed to pause job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: t('enrichmentTab.errors.pauseJob'),
      })
    } finally {
      setIsPausing(false)
    }
  }

  // Resume job
  const resumeJob = async () => {
    if (!job) return
    setIsResuming(true)
    try {
      await apiClient.post(`/enrichment/resume/${referenceName}`)
      startPolling()
      toast.success(t('enrichmentTab.toasts.resumedTitle'), {
        description: t('enrichmentTab.toasts.resumedDescription'),
      })
    } catch (err: any) {
      console.error('Failed to resume job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: t('enrichmentTab.errors.resumeJob'),
      })
    } finally {
      setIsResuming(false)
    }
  }

  // Cancel job
  const cancelJob = async () => {
    if (!job) return
    try {
      await apiClient.post(`/enrichment/cancel/${referenceName}`)
      await loadJobStatus()
      stopPolling()
      toast.warning(t('enrichmentTab.toasts.cancelledTitle'), {
        description: t('enrichmentTab.toasts.cancelledDescription', {
          count: job.processed,
        }),
      })
    } catch (err: any) {
      console.error('Failed to cancel job:', err)
      toast.error(t('enrichmentTab.toasts.genericErrorTitle'), {
        description: t('enrichmentTab.errors.cancelJob'),
      })
    }
  }

  // Poll for job updates
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return

    pollIntervalRef.current = setInterval(async () => {
      const jobData = await loadJobStatus()
      loadStats()
      // Stop polling if job is no longer running
      if (!jobData || jobData.status === 'completed' || jobData.status === 'failed' || jobData.status === 'cancelled' || jobData.status === 'paused') {
        stopPolling()
        if (jobData?.status === 'completed' || jobData?.status === 'failed' || jobData?.status === 'cancelled') {
          loadResults()
        }
      }
    }, 1000)
  }, [loadJobStatus, loadStats])

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  // Load results
  const loadResults = async () => {
    setResultsLoading(true)
    try {
      const response = await apiClient.get(`/enrichment/results/${referenceName}`, {
        params: { limit: 50 }
      })
      setResults(response.data.results || [])
    } catch (err: any) {
      console.error('Failed to load results:', err)
    } finally {
      setResultsLoading(false)
    }
  }

  // Load entities for selector
  const loadEntities = useCallback(async (search: string = '') => {
    setEntitiesLoading(true)
    try {
      const response = await apiClient.get(`/enrichment/entities/${referenceName}`, {
        params: { limit: 50, search }
      })
      setEntities(response.data.entities || [])
    } catch (err: any) {
      console.error('Failed to load entities:', err)
      setEntities([])
    } finally {
      setEntitiesLoading(false)
    }
  }, [referenceName])

  // Preview entity enrichment
  const previewEnrichment = async (queryOverride?: string) => {
    const query = queryOverride || previewQuery
    if (!query.trim()) return

    setPreviewLoading(true)
    setPreviewError(null)
    setPreviewData(null)

    try {
      const response = await apiClient.post(`/enrichment/preview/${referenceName}`, {
        query: query.trim()
      })
      setPreviewData(response.data)
    } catch (err: any) {
      setPreviewError(err.response?.data?.detail || t('enrichmentTab.errors.preview'))
    } finally {
      setPreviewLoading(false)
    }
  }

  // Initial load - only run on mount or when referenceName changes
  useEffect(() => {
    loadReferenceConfig()

    if (!hasEnrichment) {
      stopPolling()
      setStatsLoading(false)
      setStats(null)
      setJob(null)
      setResults([])
      return
    }

    loadStats(true)  // Show loader on initial load
    loadJobStatus().then((jobData) => {
      if (jobData && jobData.status === 'running') {
        startPolling()
      }
    })

    return () => stopPolling()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasEnrichment, loadJobStatus, loadReferenceConfig, loadStats, referenceName, startPolling, stopPolling])

  // Manual refresh handler
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await Promise.all([loadStats(), loadJobStatus()])
    setIsRefreshing(false)
  }

  // Calculate progress
  const progress = job ? (job.total > 0 ? (job.processed / job.total) * 100 : 0) : 0

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />{t('enrichmentTab.status.running')}</Badge>
      case 'paused':
        return <Badge variant="secondary"><Pause className="h-3 w-3 mr-1" />{t('enrichmentTab.status.paused')}</Badge>
      case 'paused_offline':
        return <Badge variant="secondary"><WifiOff className="h-3 w-3 mr-1" />{t('enrichmentTab.status.pausedOffline')}</Badge>
      case 'completed':
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />{t('enrichmentTab.status.completed')}</Badge>
      case 'failed':
        return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" />{t('enrichmentTab.status.failed')}</Badge>
      case 'cancelled':
        return <Badge variant="outline"><StopCircle className="h-3 w-3 mr-1" />{t('enrichmentTab.status.cancelled')}</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
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
            {enrichmentEnabled && !isSetupExpanded ? (
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
            <Alert className="bg-success/10 border-success/30">
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
          ) : enrichmentEnabled && !isSetupExpanded ? (
            <div className="rounded-lg border bg-muted/30 px-4 py-3">
              <div className="min-w-0">
                <div className="text-sm font-medium">
                  {enrichmentConfig.plugin || t('sources:configEditor.apiEnrichment')}
                </div>
                <div className="text-sm text-muted-foreground truncate">
                  {enrichmentConfig.api_url || t('sources:configEditor.enabled')}
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between rounded-lg border px-4 py-3">
                <div>
                  <Label htmlFor="reference-enrichment-enabled" className="text-sm font-medium">
                    {t('sources:configEditor.apiEnrichment')}
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    {t('sources:configEditor.enrichWithApi')}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Label htmlFor="reference-enrichment-enabled" className="text-sm">
                    {enrichmentEnabled
                      ? t('sources:configEditor.enabled')
                      : t('sources:configEditor.disabled')}
                  </Label>
                  <Switch
                    id="reference-enrichment-enabled"
                    checked={enrichmentEnabled}
                    onCheckedChange={(checked) =>
                      updateEnrichmentConfig({
                        ...enrichmentConfig,
                        enabled: checked,
                      })
                    }
                  />
                </div>
              </div>

              {enrichmentEnabled ? (
                <ApiEnrichmentConfig
                  config={enrichmentConfig}
                  onChange={updateEnrichmentConfig}
                  category={apiCategory}
                />
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {t('reference.enrichmentNotConfigured', {
                      defaultValue: 'Enable and save API enrichment to unlock this workspace.',
                    })}
                  </AlertDescription>
                </Alert>
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

      {hasEnrichment || enrichmentEnabled ? (
        <>
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Status Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.status')}</CardTitle>
          </CardHeader>
          <CardContent className="min-h-[120px]">
            {job ? (
              <div className="space-y-2">
                {getStatusBadge(job.status)}
                {job.current_entity && (
                  <p className="text-xs text-muted-foreground truncate">
                    {t('enrichmentTab.currentEntity', { name: job.current_entity })}
                  </p>
                )}
              </div>
            ) : (
              <Badge variant="outline">{t('enrichmentTab.status.ready')}</Badge>
            )}
          </CardContent>
        </Card>

        {/* Progress Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.progress')}</CardTitle>
          </CardHeader>
          <CardContent className="min-h-[120px]">
            {job ? (
              <div className="space-y-2">
                <Progress value={progress} className="h-2" />
                <p className="text-sm">
                  {job.processed.toLocaleString()} / {job.total.toLocaleString()} ({Math.round(progress)}%)
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">-</p>
            )}
          </CardContent>
        </Card>

        {/* Database Stats Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.database')}</CardTitle>
          </CardHeader>
          <CardContent className="min-h-[120px]">
            {statsLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : stats ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{t('enrichmentTab.stats.total')}</span>
                  <span className="font-medium">{stats.total.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle2 className="h-3 w-3" />
                    {t('enrichmentTab.stats.enriched')}
                  </span>
                  <span className="font-medium text-green-600">{stats.enriched.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-orange-500">
                    <Clock className="h-3 w-3" />
                    {t('enrichmentTab.stats.pending')}
                  </span>
                  <span className="font-medium text-orange-500">{stats.pending.toLocaleString()}</span>
                </div>
                {stats.total > 0 && (
                  <Progress value={(stats.enriched / stats.total) * 100} className="h-1 mt-2" />
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">-</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Offline warning */}
      {isOffline && (
        <Alert>
          <WifiOff className="h-4 w-4" />
          <AlertTitle>{t('enrichmentTab.offline.title')}</AlertTitle>
          <AlertDescription>
            {t('enrichmentTab.offline.description')}
          </AlertDescription>
        </Alert>
      )}

      {/* Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">{t('enrichmentTab.cards.actions')}</CardTitle>
          <CardDescription>
            {t('enrichmentTab.actions.description')}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {!job || job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled' ? (
            <Button
              onClick={startJob}
              disabled={jobLoading || stats?.pending === 0 || isOffline}
              title={isOffline ? t('enrichmentTab.offline.internetRequired') : undefined}
            >
              {jobLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {t('enrichmentTab.actions.start')}
            </Button>
          ) : job.status === 'running' ? (
            <>
              <Button variant="secondary" onClick={pauseJob} disabled={isPausing}>
                {isPausing ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Pause className="h-4 w-4 mr-2" />
                )}
                {t('enrichmentTab.actions.pause')}
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <StopCircle className="h-4 w-4 mr-2" />
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
                    <AlertDialogAction onClick={cancelJob} className="bg-destructive text-destructive-foreground">
                      {t('enrichmentTab.cancelDialog.confirm')}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          ) : job.status === 'paused' || job.status === 'paused_offline' ? (
            <>
              <Button onClick={resumeJob} disabled={isResuming || isOffline}
                title={isOffline ? t('enrichmentTab.offline.internetRequiredResume') : undefined}
              >
                {isResuming ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                {t('enrichmentTab.actions.resume')}
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <StopCircle className="h-4 w-4 mr-2" />
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
                    <AlertDialogAction onClick={cancelJob} className="bg-destructive text-destructive-foreground">
                      {t('enrichmentTab.cancelDialog.confirm')}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          ) : null}

          <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {t('common:actions.refresh')}
          </Button>
        </CardContent>
      </Card>

      {/* Job Error */}
      {job?.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{t('common:status.error')}</AlertTitle>
          <AlertDescription>{job.error}</AlertDescription>
        </Alert>
      )}

      {/* Sub-tabs for Preview and Results */}
      <Tabs defaultValue="preview" className="space-y-4" onValueChange={(value) => {
        if (value === 'results') {
          loadResults()
        } else if (value === 'preview' && entities.length === 0) {
          loadEntities()
        }
      }}>
        <TabsList>
          <TabsTrigger value="preview" className="gap-1">
            <Eye className="h-4 w-4" />
            {t('enrichmentTab.tabs.preview')}
          </TabsTrigger>
          <TabsTrigger value="results" className="gap-1">
            <Database className="h-4 w-4" />
            {t('enrichmentTab.tabs.results')}
            {results.length > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                {results.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Preview Tab */}
        <TabsContent value="preview">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Entity selector */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-medium">{t('enrichmentTab.preview.selectEntity')}</CardTitle>
                    <CardDescription>
                      {t('enrichmentTab.preview.selectEntityDescription')}
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => loadEntities(entitySearch)}
                    disabled={entitiesLoading}
                  >
                    <RefreshCw className={`h-4 w-4 ${entitiesLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Search input */}
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder={t('common:actions.search')}
                      value={entitySearch}
                      onChange={(e) => setEntitySearch(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && loadEntities(entitySearch)}
                      className="pl-8"
                    />
                  </div>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => loadEntities(entitySearch)}
                    disabled={entitiesLoading}
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                </div>

                {/* Entity list */}
                <ScrollArea className="h-64 border rounded-md">
                  {entitiesLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : entities.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Database className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">{t('enrichmentTab.preview.loadEntities')}</p>
                    </div>
                  ) : (
                    <div className="p-1">
                      {entities.map((entity) => (
                        <button
                          key={entity.id}
                          onClick={() => {
                            setPreviewQuery(entity.name)
                            previewEnrichment(entity.name)
                          }}
                          className={`w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent flex items-center justify-between group ${
                            previewQuery === entity.name ? 'bg-accent' : ''
                          }`}
                        >
                          <span className="truncate flex-1">{entity.name}</span>
                          <div className="flex items-center gap-2">
                            {entity.enriched && (
                              <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                {t('enrichmentTab.stats.enrichedOne')}
                              </Badge>
                            )}
                            <Eye className="h-4 w-4 opacity-0 group-hover:opacity-50" />
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </ScrollArea>

                {/* Manual input fallback */}
                <div className="pt-2 border-t">
                  <Label className="text-xs text-muted-foreground mb-1.5 block">{t('enrichmentTab.preview.manualInput')}</Label>
                  <div className="flex gap-2">
                    <Input
                      placeholder={t('common:labels.name')}
                      value={previewQuery}
                      onChange={(e) => setPreviewQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && previewEnrichment()}
                      className="text-sm"
                    />
                    <Button
                      size="sm"
                      onClick={() => previewEnrichment()}
                      disabled={previewLoading || !previewQuery.trim()}
                    >
                      {previewLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Preview result */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">{t('enrichmentTab.preview.resultTitle')}</CardTitle>
                <CardDescription>
                  {t('enrichmentTab.preview.resultDescription')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {previewError && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{previewError}</AlertDescription>
                  </Alert>
                )}

                {previewLoading && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">{t('enrichmentTab.preview.loading')}</span>
                  </div>
                )}

                {!previewData && !previewError && !previewLoading && (
                  <div className="text-center py-6 text-muted-foreground border border-dashed rounded-lg">
                    <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">{t('enrichmentTab.preview.emptyTitle')}</p>
                    <p className="text-xs">{t('enrichmentTab.preview.emptyDescription')}</p>
                  </div>
                )}

              {previewData && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <span className="font-medium">{previewData.entity_name || previewData.taxon_name}</span>
                  </div>

                  {/* Images if present */}
                  {previewData.api_enrichment?.images && Array.isArray(previewData.api_enrichment.images) && previewData.api_enrichment.images.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground flex items-center gap-1">
                        <ImageIcon className="h-3 w-3" />
                        {t('enrichmentTab.result.images', { count: previewData.api_enrichment.images.length })}
                      </Label>
                      <div className="grid grid-cols-4 gap-2">
                        {previewData.api_enrichment.images.slice(0, 4).map((img: any, idx: number) => (
                          <div key={idx} className="aspect-square">
                            <img
                              src={img.small_thumb || img.big_thumb}
                              alt={img.auteur || `Image ${idx + 1}`}
                              className="w-full h-full object-cover rounded border"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Data table */}
                  <ScrollArea className="h-80">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-1/4">{t('enrichmentTab.table.field')}</TableHead>
                          <TableHead>{t('enrichmentTab.table.value')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(previewData.api_enrichment || {})
                          .filter(([key]) => key !== 'images')
                          .map(([key, value]) => (
                            <TableRow key={key}>
                              <TableCell className="font-mono text-xs align-top">{key}</TableCell>
                              <TableCell className="text-sm">
                                {renderValue(value)}
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </div>
              )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Results Tab */}
        <TabsContent value="results">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-sm font-medium">{t('enrichmentTab.results.title')}</CardTitle>
                <CardDescription>
                  {t('enrichmentTab.results.description')}
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={loadResults} disabled={resultsLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${resultsLoading ? 'animate-spin' : ''}`} />
                {t('common:actions.refresh')}
              </Button>
            </CardHeader>
            <CardContent>
              {resultsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : results.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>{t('enrichmentTab.results.emptyTitle')}</p>
                  <p className="text-xs">{t('enrichmentTab.results.emptyDescription')}</p>
                </div>
              ) : (
                <ScrollArea className="h-64">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('enrichmentTab.table.entity')}</TableHead>
                        <TableHead>{t('enrichmentTab.cards.status')}</TableHead>
                        <TableHead>{t('enrichmentTab.table.date')}</TableHead>
                        <TableHead>{t('enrichmentTab.cards.actions')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.map((result, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{result.entity_name || result.taxon_name || '-'}</TableCell>
                          <TableCell>
                            {result.success ? (
                              <Badge className="bg-green-500">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                {t('enrichmentTab.result.success')}
                              </Badge>
                            ) : (
                              <Badge variant="destructive">
                                <AlertCircle className="h-3 w-3 mr-1" />
                                {t('enrichmentTab.result.failed')}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {new Date(result.processed_at).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedResult(result)}
                              disabled={!result.data}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
        </>
      ) : null}

      {/* Result Detail Dialog */}
      <Dialog open={!!selectedResult} onOpenChange={(open) => !open && setSelectedResult(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>{selectedResult?.entity_name || selectedResult?.taxon_name}</DialogTitle>
            <DialogDescription>
              {t('enrichmentTab.result.enrichedOn', {
                date: selectedResult && new Date(selectedResult.processed_at).toLocaleString(),
              })}
            </DialogDescription>
          </DialogHeader>
          {selectedResult?.data && (
            <ScrollArea className="flex-1">
              {/* Images */}
              {selectedResult.data.images && Array.isArray(selectedResult.data.images) && selectedResult.data.images.length > 0 && (
                <div className="mb-4">
                  <Label className="text-xs text-muted-foreground mb-2 block">
                    {t('enrichmentTab.result.images', { count: selectedResult.data.images.length })}
                  </Label>
                  <div className="grid grid-cols-4 gap-2">
                    {selectedResult.data.images.slice(0, 8).map((img: any, idx: number) => (
                      <div key={idx} className="aspect-square">
                        <img
                          src={img.small_thumb || img.big_thumb}
                          alt={img.auteur || `Image ${idx + 1}`}
                          className="w-full h-full object-cover rounded border"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Data table */}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-1/4">{t('enrichmentTab.table.field')}</TableHead>
                    <TableHead>{t('enrichmentTab.table.value')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(selectedResult.data)
                    .filter(([key]) => key !== 'images')
                    .map(([key, value]) => (
                      <TableRow key={key}>
                        <TableCell className="font-mono text-xs align-top">{key}</TableCell>
                        <TableCell className="text-sm">
                          {renderValue(value)}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default EnrichmentTab
