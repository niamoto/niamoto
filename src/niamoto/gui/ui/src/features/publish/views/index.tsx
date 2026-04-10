import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { type Locale, formatDistanceToNow } from 'date-fns'
import { enUS, fr } from 'date-fns/locale'
import {
  AlertCircle,
  CheckCircle,
  Clock,
  ExternalLink,
  Globe,
  History,
  Loader2,
  Monitor,
  Package,
  RefreshCw,
  Send,
  Settings2,
  Smartphone,
  Tablet,
} from 'lucide-react'
import { toast } from 'sonner'
import { useNavigationStore } from '@/stores/navigationStore'
import {
  usePublishStore,
  selectIsBuilding,
  selectIsDeploying,
  type BuildJob,
  type DeployPlatform,
} from '@/features/publish/store/publishStore'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { PreviewFrame, type DeviceSize, DEVICE_DIMENSIONS } from '@/components/ui/preview-frame'
import {
  useGroups,
  useGroupIndexPreview,
  useSiteConfig,
  useTemplatePreview,
} from '@/shared/hooks/useSiteConfig'
import { usePipelineStatus } from '@/hooks/usePipelineStatus'
import { executeExportAndWait } from '@/features/publish/api/export'
import { apiClient } from '@/shared/lib/api/client'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import PublishDeployContent from '@/features/publish/views/deploy'
import {
  getProjectName,
  PLATFORM_ORDER,
  PLATFORMS,
} from '@/features/publish/views/deployPlatformConfig'
import PublishHistoryContent from '@/features/publish/views/history'
import { cn } from '@/lib/utils'

function getExportedSitePreviewUrl(path: string) {
  return `/api/site/preview-exported/${path.replace(/^\/+/, '')}`
}

function getAbsolutePreviewUrl(path: string) {
  const relativeUrl = getExportedSitePreviewUrl(path)
  if (typeof window === 'undefined') {
    return relativeUrl
  }

  return new URL(relativeUrl, window.location.origin).toString()
}

function getExportedHomePath(lang?: string, languages?: string[]) {
  const uniqueLanguages = Array.from(new Set((languages || []).filter(Boolean)))
  if (uniqueLanguages.length > 1 && lang) {
    return `${lang}/index.html`
  }
  return 'index.html'
}

function formatDateDistance(dateStr: string | undefined, locale: Locale) {
  if (!dateStr) return '—'
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale })
  } catch {
    return dateStr
  }
}

function getPublishStatus({
  currentBuild,
  currentDeploy,
  hasSuccessfulBuild,
  isStale,
  t,
}: {
  currentBuild: BuildJob | null
  currentDeploy: { status: string } | null
  hasSuccessfulBuild: boolean
  isStale: boolean
  t: (key: string, defaultValue?: string) => string
}) {
  if (currentDeploy?.status === 'running') {
    return { label: t('deploy.deploying', 'Deploying...'), variant: 'secondary' as const }
  }
  if (currentBuild?.status === 'running') {
    return { label: t('build.building', 'Generating...'), variant: 'secondary' as const }
  }
  if (!hasSuccessfulBuild) {
    return { label: t('publishStatus.neverGenerated', 'Never generated'), variant: 'outline' as const }
  }
  if (isStale) {
    return { label: t('publishStatus.outOfDate', 'Out of date'), variant: 'secondary' as const }
  }
  return { label: t('publishStatus.upToDate', 'Up to date'), variant: 'default' as const }
}

function StaticSitePreview({
  device,
  onDeviceChange,
  lang,
  languages,
  className,
}: {
  device: DeviceSize
  onDeviceChange: (d: DeviceSize) => void
  lang?: string
  languages?: string[]
  className?: string
}) {
  const { t } = useTranslation('publish')
  const { isDesktop } = useRuntimeMode()
  const [iframeKey, setIframeKey] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const dims = DEVICE_DIMENSIONS[device]
  const previewUrl = getExportedSitePreviewUrl(getExportedHomePath(lang, languages))
  const externalPreviewUrl = getAbsolutePreviewUrl(
    getExportedHomePath(lang, languages)
  )

  const handleOpenPreview = async () => {
    if (isDesktop && window.__TAURI__?.core) {
      await window.__TAURI__.core.invoke('open_external_url', {
        url: externalPreviewUrl,
      })
      return
    }

    window.open(externalPreviewUrl, '_blank', 'noopener,noreferrer')
  }

  useEffect(() => {
    const update = () => {
      if (!containerRef.current) return
      const cw = containerRef.current.clientWidth - 32
      const ch = containerRef.current.clientHeight - 32
      setScale(Math.min(cw / dims.width, ch / dims.height, 1))
    }

    update()
    const ro = new ResizeObserver(update)
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [dims.height, dims.width])

  return (
    <div className={cn('flex h-full min-h-0 flex-col bg-muted/20', className)}>
      <div className="flex items-center justify-between border-b bg-background px-4 py-2">
        <div className="text-sm text-muted-foreground">
          {dims.width}x{dims.height} ({Math.round(scale * 100)}%)
        </div>
        <div className="flex items-center gap-2">
          <ToggleGroup type="single" value={device} onValueChange={(v) => v && onDeviceChange(v as DeviceSize)} size="sm">
            <ToggleGroupItem value="mobile" aria-label="Mobile">
              <Smartphone className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem value="tablet" aria-label="Tablet">
              <Tablet className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem value="desktop" aria-label="Desktop">
              <Monitor className="h-4 w-4" />
            </ToggleGroupItem>
          </ToggleGroup>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIframeKey((current) => current + 1)}
            title={t('common:actions.refresh', 'Refresh')}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => void handleOpenPreview()}>
            <ExternalLink className="mr-2 h-4 w-4" />
            {isDesktop
              ? t('build.openBrowser', 'Open in Browser')
              : t('build.openNewTab', 'Open in New Tab')}
          </Button>
        </div>
      </div>

      <div ref={containerRef} className="flex flex-1 items-center justify-center overflow-hidden p-4">
        <div className="relative flex items-center justify-center" style={{ width: dims.width * scale, height: dims.height * scale }}>
          <div
            className="absolute overflow-hidden rounded-lg border bg-white shadow-sm"
            style={{
              width: dims.width,
              height: dims.height,
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
              top: 0,
              left: 0,
            }}
          >
            <iframe
              key={iframeKey}
              src={previewUrl}
              className="h-full w-full border-0"
              title="Generated site preview"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function PublishOverview() {
  const { t, i18n } = useTranslation('publish')
  const [searchParams, setSearchParams] = useSearchParams()
  const { setBreadcrumbs } = useNavigationStore()
  const dateLocale = i18n.language === 'fr' ? fr : enUS
  const previewLang = i18n.language?.split('-')[0] || 'fr'

  const {
    currentBuild,
    currentDeploy,
    buildHistory,
    deployHistory,
    platformConfigs,
    preferredPlatform,
    startBuild,
    updateBuild,
    completeBuild,
    startDeploy,
    appendDeployLog,
    setDeploymentUrl,
    setPreferredPlatform,
    completeDeploy,
  } = usePublishStore()

  const isBuilding = usePublishStore(selectIsBuilding)
  const isDeploying = usePublishStore(selectIsDeploying)
  const lastBuild = buildHistory[0]
  const lastSuccessfulBuild = buildHistory.find((job) => job.status === 'completed') ?? null
  const hasSuccessfulBuild = lastSuccessfulBuild !== null
  const [previewDevice, setPreviewDevice] = useState<DeviceSize>('desktop')
  const [dynamicHtml, setDynamicHtml] = useState<string | null>(null)
  const [includeTransform, setIncludeTransform] = useState(true)
  const [currentPhase, setCurrentPhase] = useState<string | null>(null)
  const [exportPath, setExportPath] = useState('exports')
  const [compactPanel, setCompactPanel] = useState<'actions' | 'preview'>('actions')

  const activePanel = searchParams.get('panel')
  const { data: siteConfig } = useSiteConfig()
  const { data: groupsData } = useGroups()
  const { data: pipelineData } = usePipelineStatus()
  const previewMutation = useTemplatePreview()
  const groupIndexMutation = useGroupIndexPreview()
  const groups = groupsData?.groups || []
  const isStale = pipelineData?.publication?.status === 'stale'
  const groupsStatus = pipelineData?.groups?.status
  const canRecomputeStatistics = groupsStatus !== 'unconfigured'
  const shouldIncludeTransformByDefault = groupsStatus === 'stale' || groupsStatus === 'never_run'
  const includeTransformLabel = groupsStatus === 'never_run'
    ? t('build.includeTransformInitial', 'Compute statistics before generation')
    : t('build.includeTransform', 'Recompute statistics before generation')

  const configuredPlatforms = PLATFORM_ORDER.filter((platform) => Boolean(platformConfigs[platform]))
  const primaryPlatform = configuredPlatforms.includes(preferredPlatform as DeployPlatform)
    ? (preferredPlatform as DeployPlatform)
    : configuredPlatforms[0]
  const primaryPlatformConfig = primaryPlatform
    ? (platformConfigs[primaryPlatform] as Record<string, string> | undefined)
    : undefined
  const primaryDeploy = primaryPlatform
    ? deployHistory.find((job) => job.platform === primaryPlatform)
    : undefined
  const isPrimaryDeploying = primaryPlatform !== undefined
    && currentDeploy?.platform === primaryPlatform
    && isDeploying

  const publishStatus = getPublishStatus({
    currentBuild,
    currentDeploy,
    hasSuccessfulBuild,
    isStale,
    t: (key, defaultValue) => (defaultValue ? t(key, defaultValue) : t(key)),
  })

  useEffect(() => {
    setBreadcrumbs([{ label: t('title', 'Publish') }])
  }, [setBreadcrumbs, t])

  useEffect(() => {
    const loadWorkingDir = async () => {
      try {
        const response = await apiClient.get('/config/project')
        const workingDir = response.data.working_directory || '.'
        setExportPath(`${workingDir}/exports`)
      } catch (error) {
        console.error('Failed to load working directory:', error)
      }
    }

    void loadWorkingDir()
  }, [])

  useEffect(() => {
    setIncludeTransform(shouldIncludeTransformByDefault)
  }, [shouldIncludeTransformByDefault])

  const openPanel = (panel: 'destinations' | 'history') => {
    const next = new URLSearchParams(searchParams)
    next.set('panel', panel)
    setSearchParams(next)
  }

  const closePanel = () => {
    const next = new URLSearchParams(searchParams)
    next.delete('panel')
    setSearchParams(next, { replace: true })
  }

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

        Object.entries(exports).forEach(([name, exportData]: [string, Record<string, unknown>]) => {
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
          targets,
        })

        toast.success(t('build.success', 'Build completed successfully!'))
      }
    } catch (error) {
      console.error('Build error:', error)
      completeBuild(undefined, String(error))
      toast.error(t('build.error', 'Build error'))
    }
  }

  const handleDeployPrimary = async () => {
    if (!primaryPlatform || !primaryPlatformConfig) {
      openPanel('destinations')
      return
    }

    if (!hasSuccessfulBuild || isPrimaryDeploying) return

    const projectName = getProjectName(primaryPlatform, primaryPlatformConfig)
    setPreferredPlatform(primaryPlatform)
    startDeploy(primaryPlatform, projectName, primaryPlatformConfig.branch)

    try {
      const secretFields = PLATFORMS[primaryPlatform].fields.filter((field) => field.isSecret)

      for (const field of secretFields) {
        const value = primaryPlatformConfig[field.key]
        if (value?.trim()) {
          try {
            await apiClient.post(`/deploy/credentials/${primaryPlatform}`, { key: field.key, value })
          } catch {
            appendDeployLog(`❌ Failed to save ${field.key} to keyring`)
          }
        }
      }

      const extra: Record<string, string> = {}
      for (const [key, value] of Object.entries(primaryPlatformConfig)) {
        if (
          key !== 'projectName'
          && key !== 'branch'
          && !secretFields.some((field) => field.key === key)
          && value
        ) {
          extra[key] = value
        }
      }

      const response = await fetch('/api/deploy/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: primaryPlatform,
          project_name: projectName,
          branch: primaryPlatformConfig.branch || null,
          extra,
        }),
      })

      if (!response.ok || !response.body) {
        completeDeploy(`HTTP ${response.status}: ${response.statusText}`)
        toast.error(t('deploy.error', 'Deployment error'))
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let hasErrors = false
      let hasSuccess = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)

          if (data === 'DONE') {
            if (hasErrors && !hasSuccess) {
              completeDeploy('Deployment failed')
              toast.error(t('deploy.error', 'Deployment error'))
            } else {
              completeDeploy()
              toast.success(t('deploy.success', 'Deployment successful!'))
            }
            return
          }

          if (data.startsWith('URL: ')) {
            setDeploymentUrl(data.substring(5))
          } else if (data.startsWith('ERROR: ')) {
            hasErrors = true
            appendDeployLog(`❌ ${data.substring(7)}`)
          } else if (data.startsWith('SUCCESS: ')) {
            hasSuccess = true
            appendDeployLog(`✅ ${data.substring(9)}`)
          } else {
            appendDeployLog(data)
          }
        }
      }

      completeDeploy('Stream ended unexpectedly')
    } catch (error) {
      console.error('Deploy error:', error)
      completeDeploy(String(error))
      toast.error(t('deploy.error', 'Deployment error'))
    }
  }

  const loadPagePreview = useCallback((page: typeof siteConfig extends { static_pages: (infer P)[] } | undefined ? P : never) => {
    if (!siteConfig || !page) return
    previewMutation.mutate({
      template: page.template || 'page.html',
      context: { ...(page.context || {}) },
      site: siteConfig.site as Record<string, unknown>,
      navigation: siteConfig.navigation.map((item) => ({
        text: item.text,
        url: item.url,
        children: item.children,
      })),
      footer_navigation: siteConfig.footer_navigation.map((section) => ({
        title: section.title,
        links: section.links,
      })),
      output_file: page.output_file,
      gui_lang: i18n.language?.split('-')[0] || 'fr',
    }, {
      onSuccess: (data) => setDynamicHtml(data.html),
    })
  }, [i18n.language, previewMutation, siteConfig])

  const loadDynamicPreview = useCallback(() => {
    if (!siteConfig) return
    const indexPage = siteConfig.static_pages.find((page) =>
      page.template === 'index.html' || page.output_file === 'index.html' || page.name === 'index'
    ) || siteConfig.static_pages[0]

    if (indexPage) {
      loadPagePreview(indexPage)
    }
  }, [loadPagePreview, siteConfig])

  const handlePreviewLinkClick = (href: string) => {
    if (!siteConfig) return
    const normalized = href.replace(/^\//, '')
    const filename = normalized.split('/').pop() || href

    const groupByIndex = groups.find((group) => {
      const indexPattern = group.index_output_pattern || `${group.name}/index.html`
      return normalized === indexPattern
    })

    if (groupByIndex) {
      groupIndexMutation.mutate({
        groupName: groupByIndex.name,
        request: {
          site: siteConfig.site as Record<string, unknown>,
          navigation: siteConfig.navigation.map((item) => ({
            text: item.text as string,
            url: item.url,
            children: item.children,
          })),
          gui_lang: i18n.language?.split('-')[0] || 'fr',
        },
      }, {
        onSuccess: (data) => setDynamicHtml(data.html),
      })
      return
    }

    const groupByPath = groups.find((group) =>
      normalized.startsWith(`${group.name}/`) && normalized !== `${group.name}/index.html`
    )
    if (groupByPath) return

    const targetPage = siteConfig.static_pages.find((page) =>
      page.output_file === normalized || page.output_file === href
    ) || siteConfig.static_pages.find((page) =>
      page.output_file === filename
    )

    if (targetPage) {
      loadPagePreview(targetPage)
    }
  }

  useEffect(() => {
    if (!hasSuccessfulBuild && siteConfig && dynamicHtml === null) {
      loadDynamicPreview()
    }
  }, [dynamicHtml, hasSuccessfulBuild, loadDynamicPreview, siteConfig])

  const activityItems = [
    ...buildHistory.slice(0, 3).map((job) => ({ type: 'build' as const, ...job })),
    ...deployHistory.slice(0, 3).map((job) => ({ type: 'deploy' as const, ...job })),
  ]
    .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
    .slice(0, 5)

  const headerTitle = (siteConfig?.site?.title as string | undefined) || 'Niamoto'
  const summaryMetrics = [
    {
      key: 'files',
      label: t('build.metrics.files', 'Files generated'),
      value: lastSuccessfulBuild?.metrics?.totalFiles?.toLocaleString() || '—',
    },
    {
      key: 'duration',
      label: t('build.metrics.duration', 'Generation time'),
      value: lastSuccessfulBuild?.metrics?.duration ? `${lastSuccessfulBuild.metrics.duration}s` : '—',
    },
    {
      key: 'generated',
      label: t('build.lastGenerated', 'Last generated'),
      value: lastSuccessfulBuild
        ? formatDateDistance(lastSuccessfulBuild.completedAt || lastSuccessfulBuild.startedAt, dateLocale)
        : '—',
    },
    {
      key: 'path',
      label: t('build.outputPath', 'Directory'),
      value: exportPath,
      truncate: true,
    },
  ]

  const previewContent = hasSuccessfulBuild ? (
    <StaticSitePreview
      device={previewDevice}
      onDeviceChange={setPreviewDevice}
      lang={siteConfig?.site?.lang as string || previewLang}
      languages={siteConfig?.site?.languages as string[] | undefined}
      className="h-full"
    />
  ) : (
    <PreviewFrame
      html={dynamicHtml}
      isLoading={previewMutation.isPending || groupIndexMutation.isPending}
      device={previewDevice}
      onDeviceChange={setPreviewDevice}
      onRefresh={loadDynamicPreview}
      onLinkClick={handlePreviewLinkClick}
      title={t('overview.previewDynamic', 'Dynamic preview')}
      emptyMessage={t('overview.noPreview', 'Generate the site to preview the final output')}
      className="h-full"
    />
  )

  const actionsContent = (
    <div className="space-y-4 p-4 md:p-6">
      <Card>
        <CardHeader>
          <CardTitle>{t('build.configuration', 'Generation settings')}</CardTitle>
          <CardDescription>
            {t('build.generationDescription', 'Create the latest version of your static site from the current data and configuration.')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {lastBuild?.status === 'failed' && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {lastBuild.error?.includes('Network Error')
                  ? t('build.errorNetwork', 'Server connection lost during build. Please retry generation.')
                  : lastBuild.error || t('build.error', 'Build error')}
              </AlertDescription>
            </Alert>
          )}

          {isBuilding && currentBuild ? (
            <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
              {includeTransform && (
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span className={currentPhase === 'transform' ? 'font-semibold text-foreground' : ''}>
                    {t('build.phaseTransform', 'Phase 1/2: Transformations')}
                  </span>
                  <span className={currentPhase === 'export' ? 'font-semibold text-foreground' : ''}>
                    {t('build.phaseExport', 'Phase 2/2: Export')}
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between text-sm">
                <span>{currentBuild.message}</span>
                <span>{currentBuild.progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div className="h-full bg-primary transition-all duration-300" style={{ width: `${currentBuild.progress}%` }} />
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {canRecomputeStatistics && (
                <div className="flex w-full items-center justify-between rounded-lg border px-4 py-3">
                  <Label htmlFor="include-transform" className="cursor-pointer text-sm font-medium">
                    {includeTransformLabel}
                  </Label>
                  <Switch
                    id="include-transform"
                    checked={includeTransform}
                    onCheckedChange={setIncludeTransform}
                  />
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('deploy.trigger', 'Put Online')}</CardTitle>
          <CardDescription>
            {t('deploy.description', 'Publish your site online using a configured destination')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!hasSuccessfulBuild && (
            <Alert>
              <Clock className="h-4 w-4" />
              <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <span>{t('deploy.noBuild', 'You need to generate the site first before deploying.')}</span>
                <Button size="sm" variant="outline" onClick={runBuild} disabled={isBuilding}>
                  <Package className="mr-2 h-4 w-4" />
                  {t('build.trigger', 'Generate Site')}
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {isStale && hasSuccessfulBuild && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <span>{t('deploy.staleWarning', 'The exported site is outdated. Regenerate the site before deploying.')}</span>
                <Button size="sm" variant="outline" onClick={runBuild} disabled={isBuilding}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {t('build.rebuild', 'Regenerate Site')}
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {configuredPlatforms.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-start gap-4 py-8">
                <div>
                  <h3 className="font-semibold">{t('deploy.dashboard.emptyTitle', 'No publishing destination configured')}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('deploy.dashboard.emptyDescription', 'Configure a destination to publish your site online.')}
                  </p>
                </div>
                <Button onClick={() => openPanel('destinations')}>
                  <Settings2 className="mr-2 h-4 w-4" />
                  {t('deploy.dashboard.addDeployment', 'Set Up a Destination')}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="space-y-4 pt-6">
                <div className="flex flex-col gap-3">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold">
                        {primaryPlatform ? PLATFORMS[primaryPlatform].name : t('deploy.trigger', 'Deploy')}
                      </h3>
                      {primaryDeploy?.status === 'completed' && (
                        <Badge variant="default" className="bg-green-500">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          {t('status.completed', 'Completed')}
                        </Badge>
                      )}
                      {primaryDeploy?.status === 'failed' && (
                        <Badge variant="destructive">
                          <AlertCircle className="mr-1 h-3 w-3" />
                          {t('status.failed', 'Failed')}
                        </Badge>
                      )}
                      {!primaryDeploy && (
                        <Badge variant="outline">{t('deploy.dashboard.noDeployYet', 'Never deployed')}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {primaryPlatformConfig && primaryPlatform
                        ? getProjectName(primaryPlatform, primaryPlatformConfig)
                        : t('deploy.dashboard.emptyDescription', 'Configure a destination to publish your site online.')}
                    </p>
                    {primaryDeploy && (
                      <p className="text-sm text-muted-foreground">
                        {t('deploy.dashboard.lastDeployAt', 'Last deployment')} {formatDateDistance(primaryDeploy.completedAt || primaryDeploy.startedAt, dateLocale)}
                      </p>
                    )}
                    {primaryDeploy?.deploymentUrl && (
                      <a
                        href={primaryDeploy.deploymentUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
                      >
                        <Globe className="h-4 w-4" />
                        {primaryDeploy.deploymentUrl}
                      </a>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={handleDeployPrimary}
                      disabled={!hasSuccessfulBuild || isStale || isPrimaryDeploying}
                    >
                      {isPrimaryDeploying ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          {t('deploy.deploying', 'Deploying...')}
                        </>
                      ) : (
                        <>
                          <Send className="mr-2 h-4 w-4" />
                          {t('deploy.trigger', 'Deploy')}
                        </>
                      )}
                    </Button>
                    {primaryDeploy?.deploymentUrl && (
                      <Button variant="outline" asChild>
                        <a href={primaryDeploy.deploymentUrl} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="mr-2 h-4 w-4" />
                          {t('deploy.viewSite', 'View Live Site')}
                        </a>
                      </Button>
                    )}
                    <Button variant="secondary" onClick={() => openPanel('destinations')}>
                      <Settings2 className="mr-2 h-4 w-4" />
                      {t('deploy.dashboard.manageDestinations', 'Manage Destinations')}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>{t('overview.recentActivity', 'Recent Activity')}</CardTitle>
            <CardDescription>{t('history.description', 'Recent generations and deployments')}</CardDescription>
          </div>
          <Button variant="outline" onClick={() => openPanel('history')} className="w-full sm:w-auto">
            <History className="mr-2 h-4 w-4" />
            {t('history.title', 'View Full History')}
          </Button>
        </CardHeader>
        <CardContent>
          {activityItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t('overview.noActivity', 'No recent activity yet')}
            </p>
          ) : (
            <div className="space-y-3">
              {activityItems.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-lg bg-muted/40 p-3">
                  <div className="flex items-center gap-3">
                    {item.type === 'build' ? (
                      <Package className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Send className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <div className="text-sm font-medium">
                        {item.type === 'build'
                          ? t('build.title', 'Build')
                          : `${t('deploy.title', 'Deploy')} · ${item.platform}`}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatDateDistance(item.completedAt || item.startedAt, dateLocale)}
                      </div>
                    </div>
                  </div>
                  <Badge variant={item.status === 'completed' ? 'default' : item.status === 'failed' ? 'destructive' : 'secondary'}>
                    {t(`status.${item.status}`, item.status)}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-3 xl:px-6">
        <div className="min-w-0">
          <h1 className="text-lg font-semibold">{headerTitle}</h1>
          <p className="text-xs text-muted-foreground">{t('title', 'Publish')}</p>
        </div>
        <div className="ml-4 flex shrink-0 items-center gap-2">
          <Badge variant={publishStatus.variant} className="hidden sm:inline-flex px-3 py-1 text-sm">
            {publishStatus.label}
          </Badge>
          <Button size="sm" onClick={runBuild} disabled={isBuilding}>
            {isBuilding ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('build.building', 'Generating...')}
              </>
            ) : lastSuccessfulBuild ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                {t('build.rebuild', 'Regenerate Site')}
              </>
            ) : (
              <>
                <Package className="mr-2 h-4 w-4" />
                {t('build.trigger', 'Generate Site')}
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="border-b bg-background px-4 py-3 xl:px-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {summaryMetrics.map((metric) => (
            <div key={metric.key} className="min-w-0">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {metric.label}
              </p>
              <p className={cn('mt-1 text-sm font-medium', metric.truncate && 'truncate')}>
                {metric.value}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="hidden min-h-0 flex-1 xl:grid xl:grid-cols-[minmax(360px,420px)_minmax(0,1fr)] xl:gap-6 xl:px-6 xl:py-6">
        <Card className="flex min-h-0 flex-col overflow-hidden">
          <ScrollArea className="h-full">
            {actionsContent}
          </ScrollArea>
        </Card>

        <Card className="flex min-h-0 flex-col overflow-hidden">
          <CardHeader className="border-b pb-4">
            <CardTitle>{t('overview.openPreview', 'Preview Site')}</CardTitle>
            <CardDescription>
              {hasSuccessfulBuild
                ? t('build.previewDescription', 'Preview the generated site')
                : t('overview.previewDynamic', 'Preview the current site structure before generation')}
            </CardDescription>
          </CardHeader>
          <CardContent className="min-h-0 flex-1 p-0">
            {previewContent}
          </CardContent>
        </Card>
      </div>

      <div className="flex min-h-0 flex-1 flex-col xl:hidden">
        <div className="border-b bg-background px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <Badge variant={publishStatus.variant} className="px-3 py-1 text-sm">
              {publishStatus.label}
            </Badge>
            <ToggleGroup
              type="single"
              value={compactPanel}
              onValueChange={(value) => value && setCompactPanel(value as 'actions' | 'preview')}
              className="justify-start"
            >
              <ToggleGroupItem value="actions">
                <Settings2 className="mr-2 h-4 w-4" />
                {t('common:actions.actions', 'Actions')}
              </ToggleGroupItem>
              <ToggleGroupItem value="preview">
                <Monitor className="mr-2 h-4 w-4" />
                {t('overview.openPreview', 'Preview Site')}
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden">
          {compactPanel === 'actions' ? (
            <ScrollArea className="h-full">
              {actionsContent}
            </ScrollArea>
          ) : (
            <div className="h-full p-4">
              <Card className="flex h-full min-h-0 flex-col overflow-hidden">
                <CardHeader className="border-b pb-4">
                  <CardTitle>{t('overview.openPreview', 'Preview Site')}</CardTitle>
                  <CardDescription>
                    {hasSuccessfulBuild
                      ? t('build.previewDescription', 'Preview the generated site')
                      : t('overview.previewDynamic', 'Preview the current site structure before generation')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="min-h-0 flex-1 p-0">
                  {previewContent}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>

      <Sheet open={activePanel === 'destinations'} onOpenChange={(open) => !open && closePanel()}>
        <SheetContent
          side="right"
          className="w-[min(96vw,1100px)] sm:max-w-[min(96vw,1100px)] overflow-y-auto"
        >
          <SheetHeader>
            <SheetTitle>{t('deploy.dashboard.manageDestinations', 'Manage Destinations')}</SheetTitle>
            <SheetDescription>
              {t('deploy.description', 'Configure and manage where your site is published.')}
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
            <PublishDeployContent embedded />
          </div>
        </SheetContent>
      </Sheet>

      <Sheet open={activePanel === 'history'} onOpenChange={(open) => !open && closePanel()}>
        <SheetContent
          side="right"
          className="w-[min(94vw,960px)] sm:max-w-[min(94vw,960px)] overflow-y-auto"
        >
          <SheetHeader>
            <SheetTitle>{t('history.title', 'History')}</SheetTitle>
            <SheetDescription>
              {t('history.description', 'View build and deployment history')}
            </SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
            <PublishHistoryContent embedded />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}

function localizeBackendMessage(
  message: string,
  t: (key: string, opts?: Record<string, unknown>) => string
): string {
  if (message.startsWith('transform:')) {
    const parts = message.split(':')
    const group = (parts[1] || '').replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
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
  return message
}
