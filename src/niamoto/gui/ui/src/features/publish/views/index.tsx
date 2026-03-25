import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationStore } from '@/stores/navigationStore'
import {
  usePublishStore,
  selectIsBuilding,
  selectIsDeploying,
} from '@/features/publish/store/publishStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Send,
  Package,
  Upload,
  History,
  CheckCircle,
  XCircle,
  Clock,
  Globe,
  AlertCircle,
  Eye,
  EyeOff,
  Monitor,
  Tablet,
  Smartphone,
  RotateCcw,
  PanelRightClose,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { PreviewFrame, type DeviceSize, DEVICE_DIMENSIONS } from '@/components/ui/preview-frame'
import {
  useSiteConfig,
  useTemplatePreview,
  useGroups,
  useGroupIndexPreview,
} from '@/features/site/hooks/useSiteConfig'
import { formatDistanceToNow } from 'date-fns'
import { fr, enUS } from 'date-fns/locale'

/** Inline preview of the generated static site using a real iframe (not srcdoc). */
function StaticSitePreview({
  device,
  onDeviceChange,
  onClose,
  lang,
}: {
  device: DeviceSize
  onDeviceChange: (d: DeviceSize) => void
  onClose: () => void
  lang?: string
}) {
  const { t } = useTranslation('publish')
  const [iframeKey, setIframeKey] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const dims = DEVICE_DIMENSIONS[device]
  // Build preview URL: skip root redirect by going directly to the lang directory
  const previewUrl = lang ? `/preview/${lang}/index.html` : '/preview/index.html'

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
  }, [dims.width, dims.height])

  return (
    <div className="flex h-[600px] flex-col bg-muted/30">
      {/* Reuse PreviewFrame header style */}
      <div className="flex items-center justify-between border-b bg-background px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{t('overview.generatedSite', 'Generated site')}</span>
          <span className="text-xs text-muted-foreground">
            {dims.width}x{dims.height} ({Math.round(scale * 100)}%)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ToggleGroup type="single" value={device} onValueChange={(v) => v && onDeviceChange(v as DeviceSize)} size="sm">
            <ToggleGroupItem value="mobile" aria-label="Mobile"><Smartphone className="h-4 w-4" /></ToggleGroupItem>
            <ToggleGroupItem value="tablet" aria-label="Tablet"><Tablet className="h-4 w-4" /></ToggleGroupItem>
            <ToggleGroupItem value="desktop" aria-label="Desktop"><Monitor className="h-4 w-4" /></ToggleGroupItem>
          </ToggleGroup>
          <Button variant="ghost" size="sm" onClick={() => setIframeKey(k => k + 1)} title={t('common:actions.refresh', 'Refresh')}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={onClose} title={t('common:actions.close', 'Close')}>
            <PanelRightClose className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div ref={containerRef} className="flex-1 p-4 overflow-hidden flex items-center justify-center">
        <div
          className="relative flex items-center justify-center"
          style={{ width: dims.width * scale, height: dims.height * scale }}
        >
          <div
            className="absolute rounded-lg border bg-white shadow-sm overflow-hidden"
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
              className="w-full h-full border-0"
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
  const navigate = useNavigate()
  const { setBreadcrumbs } = useNavigationStore()

  const {
    currentBuild,
    currentDeploy,
    buildHistory,
    deployHistory,
  } = usePublishStore()

  const isBuilding = usePublishStore(selectIsBuilding)
  const isDeploying = usePublishStore(selectIsDeploying)

  const lastBuild = buildHistory[0]
  const lastDeploy = deployHistory[0]
  const hasBuild = lastBuild?.status === 'completed' || buildHistory.some(b => b.status === 'completed')
  const dateLocale = i18n.language === 'fr' ? fr : enUS

  // Preview state
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewDevice, setPreviewDevice] = useState<DeviceSize>('desktop')
  const [dynamicHtml, setDynamicHtml] = useState<string | null>(null)
  const { data: siteConfig } = useSiteConfig()
  const { data: groupsData } = useGroups()
  const groups = groupsData?.groups || []
  const previewMutation = useTemplatePreview()
  const groupIndexMutation = useGroupIndexPreview()

  const loadPagePreview = (page: typeof siteConfig extends { static_pages: (infer P)[] } | undefined ? P : never) => {
    if (!siteConfig || !page) return
    previewMutation.mutate({
      template: page.template || 'page.html',
      context: { ...(page.context || {}) },
      site: siteConfig.site as Record<string, unknown>,
      navigation: siteConfig.navigation.map(n => ({
        text: n.text,
        url: n.url,
        children: n.children,
      })),
      footer_navigation: siteConfig.footer_navigation.map(s => ({
        title: s.title,
        links: s.links,
      })),
      output_file: page.output_file,
      gui_lang: i18n.language?.split('-')[0] || 'fr',
    }, {
      onSuccess: (data) => setDynamicHtml(data.html),
    })
  }

  const loadDynamicPreview = () => {
    if (!siteConfig) return
    const indexPage = siteConfig.static_pages.find(p =>
      p.output_file === 'index.html' || p.name === 'index'
    ) || siteConfig.static_pages[0]
    if (indexPage) loadPagePreview(indexPage)
  }

  const handlePreviewLinkClick = (href: string) => {
    if (!siteConfig) return
    const normalized = href.replace(/^\//, '')
    const filename = normalized.split('/').pop() || href

    // 1. Check group index pages (e.g. "taxons/index.html")
    const groupByIndex = groups.find(g => {
      const indexPattern = g.index_output_pattern || `${g.name}/index.html`
      return normalized === indexPattern
    })
    if (groupByIndex) {
      groupIndexMutation.mutate({
        groupName: groupByIndex.name,
        request: {
          site: siteConfig.site as Record<string, unknown>,
          navigation: siteConfig.navigation.map(n => ({
            text: n.text as string,
            url: n.url,
            children: n.children,
          })),
          gui_lang: i18n.language?.split('-')[0] || 'fr',
        },
      }, {
        onSuccess: (data) => setDynamicHtml(data.html),
      })
      return
    }

    // 2. Check group detail pages (e.g. "taxons/123.html") — can't preview individually
    const groupByPath = groups.find(g =>
      normalized.startsWith(`${g.name}/`) && normalized !== `${g.name}/index.html`
    )
    if (groupByPath) return

    // 3. Static pages
    const targetPage = siteConfig.static_pages.find(p =>
      p.output_file === normalized || p.output_file === href
    ) || siteConfig.static_pages.find(p =>
      p.output_file === filename
    )
    if (targetPage) {
      loadPagePreview(targetPage)
    }
  }

  // Load dynamic preview when opened
  useEffect(() => {
    if (previewOpen && !hasBuild && siteConfig) {
      loadDynamicPreview()
    }
  }, [previewOpen, hasBuild, siteConfig])

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Publish', path: '/publish' },
      { label: t('overview.title', 'Overview') }
    ])
  }, [setBreadcrumbs, t])

  const getStatusBadge = (status: string | undefined) => {
    if (!status) return null
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> {t('status.completed', 'Completed')}</Badge>
      case 'failed':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" /> {t('status.failed', 'Failed')}</Badge>
      case 'running':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1 animate-spin" /> {t('status.running', 'Running')}</Badge>
      case 'cancelled':
        return <Badge variant="outline"><AlertCircle className="w-3 h-3 mr-1" /> {t('status.cancelled', 'Cancelled')}</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: dateLocale })
    } catch {
      return dateStr
    }
  }

  return (
    <div>
      <StalenessBanner stage="publication" />
      <div className="container mx-auto px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('title', 'Publish')}</h1>
          <p className="text-muted-foreground">{t('description', 'Generate and deploy your static site')}</p>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Last Build Card */}
        <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/publish/build')}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Package className="w-5 h-5" />
                {t('overview.lastBuild', 'Last Build')}
              </CardTitle>
              {getStatusBadge(currentBuild?.status || lastBuild?.status)}
            </div>
          </CardHeader>
          <CardContent>
            {isBuilding ? (
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">{currentBuild?.message}</div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${currentBuild?.progress || 0}%` }}
                  />
                </div>
              </div>
            ) : lastBuild ? (
              <div className="space-y-1">
                <div className="text-2xl font-bold">
                  {lastBuild.metrics?.totalFiles?.toLocaleString() || '—'} {t('files', 'fichiers')}
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatDate(lastBuild.completedAt || lastBuild.startedAt)}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">{t('overview.noBuild', 'No build performed')}</div>
            )}
          </CardContent>
        </Card>

        {/* Last Deploy Card */}
        <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/publish/deploy')}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Upload className="w-5 h-5" />
                {t('overview.lastDeploy', 'Last Deployment')}
              </CardTitle>
              {getStatusBadge(currentDeploy?.status || lastDeploy?.status)}
            </div>
          </CardHeader>
          <CardContent>
            {isDeploying ? (
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">
                  {t('deploy.deploying', 'Deploying to')} {currentDeploy?.platform}...
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary animate-pulse" style={{ width: '60%' }} />
                </div>
              </div>
            ) : lastDeploy ? (
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="capitalize">{lastDeploy.platform}</Badge>
                  {lastDeploy.deploymentUrl && (
                    <a
                      href={lastDeploy.deploymentUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline flex items-center gap-1 text-sm"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Globe className="w-3 h-3" />
                      {t('deploy.viewSite', 'Voir')}
                    </a>
                  )}
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatDate(lastDeploy.completedAt || lastDeploy.startedAt)}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">{t('overview.noDeploy', 'No deployment performed')}</div>
            )}
          </CardContent>
        </Card>

      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>{t('overview.quickActions', 'Actions rapides')}</CardTitle>
          <CardDescription>{t('overview.quickActionsDescription', 'Generate and deploy your site in a few clicks')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button
              size="lg"
              onClick={() => navigate('/publish/build')}
              disabled={isBuilding}
            >
              <Package className="w-5 h-5 mr-2" />
              {isBuilding ? t('build.building', 'Building...') : t('build.trigger', 'Generate Site')}
            </Button>

            <Button
              size="lg"
              variant="secondary"
              onClick={() => navigate('/publish/deploy')}
              disabled={isDeploying || (!lastBuild && !buildHistory.some(b => b.status === 'completed'))}
            >
              <Send className="w-5 h-5 mr-2" />
              {isDeploying ? t('deploy.deploying', 'Deploying...') : t('deploy.trigger', 'Deploy')}
            </Button>

            <Button
              size="lg"
              variant={previewOpen ? 'default' : 'outline'}
              onClick={() => setPreviewOpen(!previewOpen)}
            >
              {previewOpen ? <EyeOff className="w-5 h-5 mr-2" /> : <Eye className="w-5 h-5 mr-2" />}
              {t('overview.openPreview', 'Site Preview')}
            </Button>

            <Button
              size="lg"
              variant="outline"
              onClick={() => navigate('/publish/history')}
            >
              <History className="w-5 h-5 mr-2" />
              {t('history.title', 'History')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Site Preview */}
      {previewOpen && (
        <Card className="overflow-hidden">
          {hasBuild ? (
            // After build: show the actual generated static site in an iframe
            <StaticSitePreview
              device={previewDevice}
              onDeviceChange={setPreviewDevice}
              onClose={() => setPreviewOpen(false)}
              lang={siteConfig?.site?.lang as string || i18n.language?.split('-')[0] || 'fr'}
            />
          ) : (
            // Before build: dynamic template preview
            <PreviewFrame
              html={dynamicHtml}
              isLoading={previewMutation.isPending || groupIndexMutation.isPending}
              device={previewDevice}
              onDeviceChange={setPreviewDevice}
              onRefresh={loadDynamicPreview}
              onClose={() => setPreviewOpen(false)}
              onLinkClick={handlePreviewLinkClick}
              title={t('overview.previewDynamic', 'Dynamic preview')}
              emptyMessage={t('overview.noPreview', 'Configure your site to see the preview')}
              className="h-[600px]"
            />
          )}
        </Card>
      )}

      {/* Recent Activity */}
      {(buildHistory.length > 0 || deployHistory.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>{t('overview.recentActivity', 'Recent Activity')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[...buildHistory.slice(0, 3).map(b => ({ type: 'build' as const, ...b })),
                ...deployHistory.slice(0, 3).map(d => ({ type: 'deploy' as const, ...d }))]
                .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
                .slice(0, 5)
                .map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer"
                    onClick={() => navigate(`/publish/${item.type === 'build' ? 'build' : 'deploy'}`)}
                  >
                    <div className="flex items-center gap-3">
                      {item.type === 'build' ? (
                        <Package className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <Upload className="w-4 h-4 text-muted-foreground" />
                      )}
                      <div>
                        <div className="font-medium text-sm">
                          {item.type === 'build'
                            ? t('build.title', 'Build')
                            : `${t('deploy.title', 'Deploy')} - ${(item as typeof deployHistory[0]).platform}`}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDate(item.completedAt || item.startedAt)}
                        </div>
                      </div>
                    </div>
                    {getStatusBadge(item.status)}
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
    </div>
  )
}
