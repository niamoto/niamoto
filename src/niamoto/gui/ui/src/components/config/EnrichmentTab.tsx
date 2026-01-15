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
import { apiClient } from '@/lib/api/client'
import { toast } from 'sonner'

interface EnrichmentTabProps {
  referenceName: string
}

interface EnrichmentJob {
  id: string
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
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
            Voir l'image
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

export function EnrichmentTab({ referenceName }: EnrichmentTabProps) {
  const { t } = useTranslation()

  // State
  const [stats, setStats] = useState<EnrichmentStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)  // Only true on initial load

  const [job, setJob] = useState<EnrichmentJob | null>(null)
  const [jobLoading, setJobLoading] = useState(false)

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
      toast.success('Enrichissement demarre', {
        description: `${stats?.pending || 0} entites a traiter`,
      })
    } catch (err: any) {
      console.error('Failed to start job:', err)
      toast.error('Erreur au demarrage', {
        description: err.response?.data?.detail || 'Impossible de demarrer le job',
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
      toast.info('Enrichissement en pause', {
        description: 'Vous pouvez reprendre a tout moment',
      })
    } catch (err: any) {
      console.error('Failed to pause job:', err)
      toast.error('Erreur', {
        description: 'Impossible de mettre en pause',
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
      toast.success('Enrichissement repris', {
        description: 'Le traitement continue',
      })
    } catch (err: any) {
      console.error('Failed to resume job:', err)
      toast.error('Erreur', {
        description: 'Impossible de reprendre',
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
      toast.warning('Enrichissement annule', {
        description: `${job.processed} entites traitees`,
      })
    } catch (err: any) {
      console.error('Failed to cancel job:', err)
      toast.error('Erreur', {
        description: 'Impossible d\'annuler',
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
      setPreviewError(err.response?.data?.detail || 'Preview failed')
    } finally {
      setPreviewLoading(false)
    }
  }

  // Initial load - only run on mount or when referenceName changes
  useEffect(() => {
    loadStats(true)  // Show loader on initial load
    loadJobStatus().then((jobData) => {
      if (jobData && jobData.status === 'running') {
        startPolling()
      }
    })

    return () => stopPolling()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [referenceName])

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
        return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />En cours</Badge>
      case 'paused':
        return <Badge variant="secondary"><Pause className="h-3 w-3 mr-1" />En pause</Badge>
      case 'completed':
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />Termine</Badge>
      case 'failed':
        return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" />Echoue</Badge>
      case 'cancelled':
        return <Badge variant="outline"><StopCircle className="h-3 w-3 mr-1" />Annule</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Status Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Statut</CardTitle>
          </CardHeader>
          <CardContent className="min-h-[120px]">
            {job ? (
              <div className="space-y-2">
                {getStatusBadge(job.status)}
                {job.current_entity && (
                  <p className="text-xs text-muted-foreground truncate">
                    En cours: {job.current_entity}
                  </p>
                )}
              </div>
            ) : (
              <Badge variant="outline">Pret</Badge>
            )}
          </CardContent>
        </Card>

        {/* Progress Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Progression</CardTitle>
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
            <CardTitle className="text-sm font-medium">Base de donnees</CardTitle>
          </CardHeader>
          <CardContent className="min-h-[120px]">
            {statsLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : stats ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Total</span>
                  <span className="font-medium">{stats.total.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle2 className="h-3 w-3" />
                    Enrichis
                  </span>
                  <span className="font-medium text-green-600">{stats.enriched.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1 text-orange-500">
                    <Clock className="h-3 w-3" />
                    En attente
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

      {/* Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Actions</CardTitle>
          <CardDescription>
            Gerer le processus d'enrichissement
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {!job || job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled' ? (
            <Button onClick={startJob} disabled={jobLoading || stats?.pending === 0}>
              {jobLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Demarrer l'enrichissement
            </Button>
          ) : job.status === 'running' ? (
            <>
              <Button variant="secondary" onClick={pauseJob} disabled={isPausing}>
                {isPausing ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Pause className="h-4 w-4 mr-2" />
                )}
                Pause
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <StopCircle className="h-4 w-4 mr-2" />
                    Annuler
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Annuler l'enrichissement ?</AlertDialogTitle>
                    <AlertDialogDescription>
                      {job.processed} entites sur {job.total} ont ete traitees.
                      Cette action ne peut pas etre annulee.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Continuer</AlertDialogCancel>
                    <AlertDialogAction onClick={cancelJob} className="bg-destructive text-destructive-foreground">
                      Annuler le job
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          ) : job.status === 'paused' ? (
            <>
              <Button onClick={resumeJob} disabled={isResuming}>
                {isResuming ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Reprendre
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <StopCircle className="h-4 w-4 mr-2" />
                    Annuler
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Annuler l'enrichissement ?</AlertDialogTitle>
                    <AlertDialogDescription>
                      {job.processed} entites sur {job.total} ont ete traitees.
                      Cette action ne peut pas etre annulee.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Reprendre</AlertDialogCancel>
                    <AlertDialogAction onClick={cancelJob} className="bg-destructive text-destructive-foreground">
                      Annuler le job
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          ) : null}

          <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Actualiser
          </Button>
        </CardContent>
      </Card>

      {/* Job Error */}
      {job?.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur</AlertTitle>
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
            Apercu
          </TabsTrigger>
          <TabsTrigger value="results" className="gap-1">
            <Database className="h-4 w-4" />
            Resultats
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
                    <CardTitle className="text-sm font-medium">Selectionner une entite</CardTitle>
                    <CardDescription>
                      Choisissez une entite a tester
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
                      placeholder="Rechercher..."
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
                      <p className="text-sm">Cliquez sur rechercher pour charger les entites</p>
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
                                Enrichi
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
                  <Label className="text-xs text-muted-foreground mb-1.5 block">Ou saisir manuellement :</Label>
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
                <CardTitle className="text-sm font-medium">Resultat de l'apercu</CardTitle>
                <CardDescription>
                  Donnees retournees par l'API
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
                    <span className="ml-2 text-sm text-muted-foreground">Interrogation de l'API...</span>
                  </div>
                )}

                {!previewData && !previewError && !previewLoading && (
                  <div className="text-center py-6 text-muted-foreground border border-dashed rounded-lg">
                    <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Selectionnez une entite</p>
                    <p className="text-xs">pour tester la configuration d'enrichissement</p>
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
                        Images ({previewData.api_enrichment.images.length})
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
                          <TableHead className="w-1/4">Champ</TableHead>
                          <TableHead>Valeur</TableHead>
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
                <CardTitle className="text-sm font-medium">Resultats d'enrichissement</CardTitle>
                <CardDescription>
                  Entites enrichies lors du dernier job
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={loadResults} disabled={resultsLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${resultsLoading ? 'animate-spin' : ''}`} />
                Actualiser
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
                  <p>Aucun resultat disponible</p>
                  <p className="text-xs">Lancez un enrichissement pour voir les resultats</p>
                </div>
              ) : (
                <ScrollArea className="h-64">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Entite</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Actions</TableHead>
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
                                Succes
                              </Badge>
                            ) : (
                              <Badge variant="destructive">
                                <AlertCircle className="h-3 w-3 mr-1" />
                                Echec
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

      {/* Result Detail Dialog */}
      <Dialog open={!!selectedResult} onOpenChange={(open) => !open && setSelectedResult(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>{selectedResult?.entity_name || selectedResult?.taxon_name}</DialogTitle>
            <DialogDescription>
              Donnees enrichies le {selectedResult && new Date(selectedResult.processed_at).toLocaleString()}
            </DialogDescription>
          </DialogHeader>
          {selectedResult?.data && (
            <ScrollArea className="flex-1">
              {/* Images */}
              {selectedResult.data.images && Array.isArray(selectedResult.data.images) && selectedResult.data.images.length > 0 && (
                <div className="mb-4">
                  <Label className="text-xs text-muted-foreground mb-2 block">
                    Images ({selectedResult.data.images.length})
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
                    <TableHead className="w-1/4">Champ</TableHead>
                    <TableHead>Valeur</TableHead>
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
