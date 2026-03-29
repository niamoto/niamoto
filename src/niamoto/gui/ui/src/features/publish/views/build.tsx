import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePublishStore, selectIsBuilding } from '@/features/publish/store/publishStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Send,
  Package,
  CheckCircle,
  XCircle,
  Globe,
  FileJson,
  Database,
  Layers,
  FolderOpen,
  ExternalLink,
  RefreshCw
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { executeExportAndWait } from '@/lib/api/export'
import { apiClient } from '@/shared/lib/api/client'
import { useProgressiveCounter } from '@/shared/hooks/useProgressiveCounter'

function getExportedSitePreviewUrl(path: string) {
  return `/api/site/preview-exported/${path.replace(/^\/+/, '')}`
}

function getExportedHomePath(lang?: string, languages?: string[]) {
  const uniqueLanguages = Array.from(new Set((languages || []).filter(Boolean)))
  if (uniqueLanguages.length > 1 && lang) {
    return `${lang}/index.html`
  }
  return 'index.html'
}

export default function PublishBuild() {
  const { t, i18n } = useTranslation('publish')
  const navigate = useNavigate()
  const { setBreadcrumbs } = useNavigationStore()
  const previewLang = i18n.language?.split('-')[0] || 'fr'
  const [siteLanguages, setSiteLanguages] = useState<string[] | undefined>(undefined)

  const {
    currentBuild,
    buildHistory,
    startBuild,
    updateBuild,
    completeBuild,
    clearBuildHistory,
  } = usePublishStore()

  const isBuilding = usePublishStore(selectIsBuilding)
  const lastBuild = buildHistory[0]
  const [exportPath, setExportPath] = useState('')
  const [includeTransform, setIncludeTransform] = useState(true)
  const [currentPhase, setCurrentPhase] = useState<string | null>(null)

  const totalFilesCounter = useProgressiveCounter(
    lastBuild?.status === 'completed' && lastBuild.metrics?.totalFiles
      ? lastBuild.metrics.totalFiles
      : 0,
    2000,
    lastBuild?.status === 'completed'
  )

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Publish', path: '/publish' },
      { label: t('build.title', 'Build') }
    ])
  }, [setBreadcrumbs, t])

  useEffect(() => {
    const loadWorkingDir = async () => {
      try {
        const response = await apiClient.get('/config/project')
        const workingDir = response.data.working_directory || '.'
        setExportPath(`${workingDir}/exports`)
      } catch (error) {
        console.error('Failed to load working directory:', error)
        setExportPath('exports')
      }
    }
    loadWorkingDir()
  }, [])

  useEffect(() => {
    const loadSiteLanguages = async () => {
      try {
        const response = await apiClient.get('/site/config')
        setSiteLanguages(response.data.site?.languages)
      } catch (error) {
        console.error('Failed to load site languages:', error)
        setSiteLanguages(undefined)
      }
    }
    loadSiteLanguages()
  }, [])

  const runBuild = async () => {
    startBuild()
    setCurrentPhase(null)
    const startTime = Date.now()

    try {
      const result = await executeExportAndWait(
        { config_path: 'config/export.yml', include_transform: includeTransform },
        (progress, message, phase) => {
          setCurrentPhase(phase ?? null)
          const phaseLabel = phase === 'transform'
            ? t('build.phaseTransformLabel', 'Transformations')
            : t('build.phaseExportLabel', 'Site generation')
          updateBuild({ progress, message: `${phaseLabel} · ${localizeBackendMessage(message, t)}` })
        }
      )

      if (result.result) {
        const exports = result.result.exports || {}
        const metrics = result.result.metrics || {}

        const targets: { name: string; files: number }[] = []
        let totalFiles = 0

        Object.entries(exports).forEach(([name, exportData]: [string, any]) => {
          if (exportData && exportData.data) {
            const filesGenerated = exportData.data.files_generated || 0
            if (filesGenerated > 0) {
              targets.push({ name, files: filesGenerated })
              totalFiles += filesGenerated
            }
          }
        })

        if (totalFiles === 0 && metrics.generated_pages) {
          totalFiles = metrics.generated_pages
        }

        const duration = metrics.execution_time
          ? metrics.execution_time
          : (Date.now() - startTime) / 1000

        completeBuild({
          totalFiles,
          duration: parseFloat(duration.toFixed(1)),
          targets
        })

        toast.success(t('build.success', 'Build completed successfully!'))
      }
    } catch (error) {
      console.error('Build error:', error)
      completeBuild(undefined, String(error))
      toast.error(t('build.error', 'Build error'))
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('build.title', 'Build')}</h1>
          <p className="text-muted-foreground">{t('build.description', 'Generate the static site from your data')}</p>
        </div>
      </div>

      {/* Export Targets Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 space-y-2">
            <div className="flex items-center justify-between">
              <Globe className="w-8 h-8 text-purple-500" />
              <Badge variant="secondary">{t('build.targets.web', 'Website')}</Badge>
            </div>
            <h3 className="font-semibold">{t('build.targets.webTitle', 'Static Website')}</h3>
            <p className="text-xs text-muted-foreground">
              {t('build.targets.webDescription', 'HTML pages with navigation, maps and visualizations')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 space-y-2">
            <div className="flex items-center justify-between">
              <FileJson className="w-8 h-8 text-blue-500" />
              <Badge variant="secondary">{t('build.targets.api', 'API JSON')}</Badge>
            </div>
            <h3 className="font-semibold">{t('build.targets.apiTitle', 'API JSON Statique')}</h3>
            <p className="text-xs text-muted-foreground">
              {t('build.targets.apiDescription', 'JSON endpoints for each entity')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 space-y-2">
            <div className="flex items-center justify-between">
              <Database className="w-8 h-8 text-green-500" />
              <Badge variant="secondary">{t('build.targets.dwc', 'Darwin Core')}</Badge>
            </div>
            <h3 className="font-semibold">{t('build.targets.dwcTitle', 'Darwin Core Archive')}</h3>
            <p className="text-xs text-muted-foreground">
              {t('build.targets.dwcDescription', 'Export au format standard GBIF')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Build Section */}
      <Card>
        <CardHeader>
          <CardTitle>{t('build.generation', 'Site Generation')}</CardTitle>
          <CardDescription>{t('build.generationDescription', 'Create the complete static website')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Transform checkbox */}
          {!isBuilding && (
            <div className="flex items-center space-x-2">
              <Checkbox
                id="include-transform"
                checked={includeTransform}
                onCheckedChange={(checked) => setIncludeTransform(checked === true)}
              />
              <Label htmlFor="include-transform" className="text-sm cursor-pointer">
                {t('build.includeTransform', 'Recompute statistics before generation')}
              </Label>
            </div>
          )}

          {/* Building State */}
          {isBuilding && currentBuild && (
            <div className="space-y-4">
              {/* Phase indicator */}
              {includeTransform && (
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span className={currentPhase === 'transform' ? 'font-semibold text-foreground' : ''}>
                    {t('build.phaseTransform', 'Phase 1/2 : Transformations')} {currentPhase === 'transform' ? '...' : currentPhase === 'export' ? '—' : ''}
                  </span>
                  <span className={currentPhase === 'export' ? 'font-semibold text-foreground' : ''}>
                    {t('build.phaseExport', 'Phase 2/2 : Export')} {currentPhase === 'export' ? '...' : ''}
                  </span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span>{currentBuild.message}</span>
                <span>{currentBuild.progress}%</span>
              </div>
              <Progress value={currentBuild.progress} />
            </div>
          )}

          {/* Success State */}
          {!isBuilding && lastBuild?.status === 'completed' && (
            <div className="space-y-4">
              <Alert className="border-green-500/20 bg-green-500/10">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <AlertDescription>
                  {t('build.success', 'Build completed successfully!')}
                </AlertDescription>
              </Alert>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-primary">
                      {totalFilesCounter.value.toLocaleString()}
                    </div>
                    <p className="text-xs text-muted-foreground">{t('build.metrics.files', 'Files Generated')}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold text-primary">
                      {lastBuild.metrics?.duration}s
                    </div>
                    <p className="text-xs text-muted-foreground">{t('build.metrics.duration', 'Generation Time')}</p>
                  </CardContent>
                </Card>
              </div>

              {/* Target Breakdown */}
              {lastBuild.metrics?.targets && lastBuild.metrics.targets.length > 0 && (
                <div className="pt-4 border-t">
                  <h4 className="text-sm font-medium mb-3">{t('build.metrics.breakdown', 'Breakdown by Target')}</h4>
                  <div className="space-y-2">
                    {lastBuild.metrics.targets.map((target) => (
                      <div key={target.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2">
                          {target.name === 'web_pages' && <Globe className="w-4 h-4 text-purple-500" />}
                          {target.name === 'json_api' && <FileJson className="w-4 h-4 text-blue-500" />}
                          {target.name.includes('dwc') && <Database className="w-4 h-4 text-green-500" />}
                          {!['web_pages', 'json_api'].includes(target.name) && !target.name.includes('dwc') && (
                            <Layers className="w-4 h-4 text-muted-foreground" />
                          )}
                          <span className="text-sm font-medium capitalize">
                            {target.name.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <Badge variant="secondary">
                          {target.files.toLocaleString()} {t('files', 'fichiers')}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Output Path */}
              {exportPath && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                  <FolderOpen className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">{t('build.outputPath', 'Directory')} :</span>
                  <code className="text-sm">{exportPath}</code>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={() => window.open(getExportedSitePreviewUrl(getExportedHomePath(previewLang, siteLanguages)), '_blank')}
                  className="flex-1"
                >
                  <Globe className="w-4 h-4 mr-2" />
                  {t('build.preview', 'View site')}
                </Button>
                <Button variant="secondary" onClick={() => navigate('/publish/deploy')} className="flex-1">
                  <Send className="w-4 h-4 mr-2" />
                  {t('build.deploy', 'Deploy')}
                </Button>
              </div>
            </div>
          )}

          {/* Error State */}
          {!isBuilding && lastBuild?.status === 'failed' && (
            <Alert variant="destructive">
              <XCircle className="w-4 h-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>
                  {lastBuild.error?.includes('Network Error')
                    ? t('build.errorNetwork', 'Server connection lost during build. Please retry generation.')
                    : lastBuild.error || t('build.error', 'Build error')}
                </span>
                <Button variant="ghost" size="sm" className="ml-2 h-6 px-2 text-destructive" onClick={clearBuildHistory}>
                  <XCircle className="w-3 h-3" />
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Ready State */}
          {!isBuilding && lastBuild?.status !== 'completed' && lastBuild?.status !== 'failed' && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">{t('build.ready', 'Ready to generate')}</span>
              </div>
            </div>
          )}

          {/* Build Button */}
          <Button
            size="lg"
            className="w-full"
            onClick={runBuild}
            disabled={isBuilding}
          >
            {isBuilding ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                {t('build.building', 'Generating...')}
              </>
            ) : lastBuild?.status === 'completed' ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                {t('build.rebuild', 'Regenerate Site')}
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                {t('build.trigger', 'Generate Site')}
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Preview Section */}
      {lastBuild?.status === 'completed' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{t('build.previewTitle', 'Site Preview')}</CardTitle>
                <CardDescription>{t('build.previewDescription', 'Preview of the generated site')}</CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(getExportedSitePreviewUrl(getExportedHomePath(previewLang, siteLanguages)), '_blank')}
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                {t('build.openNewTab', 'Nouvel onglet')}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border overflow-hidden">
              <iframe
                key={lastBuild?.completedAt ?? ''}
                src={getExportedSitePreviewUrl(getExportedHomePath(previewLang, siteLanguages))}
                className="w-full h-[80vh] border-0"
                title={t('build.previewTitle', 'Site Preview')}
                sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

/**
 * Localise les messages structurés envoyés par le backend.
 * Format: "key" ou "key:param1:param2"
 */
function localizeBackendMessage(message: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  if (message.startsWith('transform:')) {
    const parts = message.split(':')
    const group = (parts[1] || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    const widget = (parts[2] || '').replace(/_/g, ' ')
    const item = parts[3] || ''
    if (item) {
      return t('build.progress.transformItem', { group, widget, item, defaultValue: `${group} · ${item} · ${widget}` })
    }
    return t('build.progress.transform', { group, widget, defaultValue: `${group} · ${widget}` })
  }
  if (message.startsWith('export.generating:')) {
    const pct = message.split(':')[1] || ''
    return t('build.progress.generating', { pct, defaultValue: `Génération en cours... (${pct}%)` })
  }
  if (message.startsWith('export.done:')) {
    const parts = message.split(':')
    return t('build.progress.exportDone', { name: parts[1] || '', count: parts[2] || '', defaultValue: `Export ${parts[1]} terminé (${parts[2]})` })
  }
  if (message === 'transform.running') {
    return t('build.progress.transformRunning', { defaultValue: 'Transformations en cours...' })
  }
  if (message === 'export.starting') {
    return t('build.progress.exportStarting', { defaultValue: 'Generating site...' })
  }
  // Fallback : message brut (anciens jobs ou messages non structurés)
  return message
}
