import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePublishStore, selectIsDeploying, selectHasSuccessfulBuild } from '@/stores/publishStore'
import { useNetworkStatus } from '@/hooks/useNetworkStatus'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Rocket,
  Cloud,
  Server,
  CheckCircle,
  XCircle,
  Globe,
  ExternalLink,
  Terminal,
  AlertCircle,
  Package
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

// GitHub icon SVG
const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
  </svg>
)

type Platform = 'cloudflare' | 'github' | 'netlify' | 'ssh'

export default function PublishDeploy() {
  const { t } = useTranslation('publish')
  const navigate = useNavigate()
  const { setBreadcrumbs } = useNavigationStore()
  const logsEndRef = useRef<HTMLDivElement>(null)

  const {
    currentDeploy,
    deployHistory,
    platformConfigs,
    preferredPlatform,
    startDeploy,
    appendDeployLog,
    setDeploymentUrl,
    completeDeploy,
    savePlatformConfig,
    setPreferredPlatform,
  } = usePublishStore()

  const isDeploying = usePublishStore(selectIsDeploying)
  const hasSuccessfulBuild = usePublishStore(selectHasSuccessfulBuild)
  const lastDeploy = deployHistory[0]
  const { isOffline } = useNetworkStatus()

  const [selectedPlatform, setSelectedPlatform] = useState<Platform>(preferredPlatform || 'cloudflare')

  // Cloudflare config state
  const [cloudflareProject, setCloudflareProject] = useState(platformConfigs.cloudflare?.projectName || '')
  const [cloudflareBranch, setCloudflareBranch] = useState(platformConfigs.cloudflare?.defaultBranch || '')

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Publish', path: '/publish' },
      { label: t('deploy.title', 'Deploy') }
    ])
  }, [setBreadcrumbs, t])

  // Auto-scroll logs
  useEffect(() => {
    if (currentDeploy?.logs.length) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [currentDeploy?.logs.length])

  const handleDeployCloudflare = async () => {
    if (!cloudflareProject.trim()) {
      toast.error(t('deploy.errors.projectName', 'Veuillez entrer un nom de projet'))
      return
    }

    // Save config for future use
    savePlatformConfig('cloudflare', {
      projectName: cloudflareProject,
      defaultBranch: cloudflareBranch || undefined
    })
    setPreferredPlatform('cloudflare')

    startDeploy('cloudflare', cloudflareProject, cloudflareBranch || undefined)

    try {
      const eventSource = new EventSource(
        `/api/deploy/cloudflare/deploy?project_name=${encodeURIComponent(cloudflareProject)}&branch=${encodeURIComponent(cloudflareBranch)}`,
        { withCredentials: false }
      )

      eventSource.onmessage = (event) => {
        const data = event.data

        if (data === 'DONE') {
          eventSource.close()
          completeDeploy()
          toast.success(t('deploy.success', 'Déploiement réussi !'))
          return
        }

        if (data.startsWith('URL: ')) {
          const url = data.substring(5)
          setDeploymentUrl(url)
        } else if (data.startsWith('ERROR: ')) {
          appendDeployLog(`❌ ${data}`)
        } else if (data.startsWith('SUCCESS: ')) {
          appendDeployLog(`✅ ${data}`)
        } else {
          appendDeployLog(data)
        }
      }

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error)
        eventSource.close()
        completeDeploy('Connection error')
        toast.error(t('deploy.errors.connection', 'Erreur de connexion au serveur'))
      }
    } catch (error) {
      console.error('Deploy error:', error)
      completeDeploy(String(error))
      toast.error(t('deploy.error', 'Erreur lors du déploiement'))
    }
  }

  const canDeploy = hasSuccessfulBuild && !isDeploying

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('deploy.title', 'Déploiement')}</h1>
          <p className="text-muted-foreground">{t('deploy.description', 'Publiez votre site en ligne')}</p>
        </div>
      </div>

      {/* No Build Warning */}
      {!hasSuccessfulBuild && (
        <Alert>
          <AlertCircle className="w-4 h-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{t('deploy.noBuild', 'Vous devez d\'abord générer le site avant de pouvoir le déployer.')}</span>
            <Button size="sm" variant="outline" onClick={() => navigate('/publish/build')}>
              <Package className="w-4 h-4 mr-2" />
              {t('deploy.goToBuild', 'Aller au Build')}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Platform Selection */}
      <Card>
        <CardHeader>
          <CardTitle>{t('deploy.platforms.title', 'Plateforme de déploiement')}</CardTitle>
          <CardDescription>{t('deploy.platforms.description', 'Choisissez où déployer votre site')}</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedPlatform} onValueChange={(v) => setSelectedPlatform(v as Platform)}>
            <TabsList className="grid grid-cols-4 w-full">
              <TabsTrigger value="cloudflare" className="flex items-center gap-2">
                <Cloud className="w-4 h-4" />
                <span className="hidden sm:inline">Cloudflare</span>
              </TabsTrigger>
              <TabsTrigger value="github" className="flex items-center gap-2">
                <GitHubIcon />
                <span className="hidden sm:inline">GitHub</span>
              </TabsTrigger>
              <TabsTrigger value="netlify" className="flex items-center gap-2">
                <Cloud className="w-4 h-4" />
                <span className="hidden sm:inline">Netlify</span>
              </TabsTrigger>
              <TabsTrigger value="ssh" className="flex items-center gap-2">
                <Server className="w-4 h-4" />
                <span className="hidden sm:inline">SSH</span>
              </TabsTrigger>
            </TabsList>

            {/* Cloudflare Tab */}
            <TabsContent value="cloudflare" className="space-y-4 mt-4">
              <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
                <div className="w-12 h-12 rounded-full bg-[#F38020] flex items-center justify-center shrink-0">
                  <Cloud className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold">Cloudflare Pages</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('deploy.platforms.cloudflareDescription', 'Déploiement sur le réseau edge mondial de Cloudflare avec HTTPS automatique')}
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="cf-project">{t('deploy.config.projectName', 'Nom du projet')}</Label>
                  <Input
                    id="cf-project"
                    placeholder="mon-site-niamoto"
                    value={cloudflareProject}
                    onChange={(e) => setCloudflareProject(e.target.value)}
                    disabled={isDeploying}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('deploy.config.projectNameHint', 'Le projet sera créé automatiquement s\'il n\'existe pas')}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="cf-branch">{t('deploy.config.branch', 'Branche')} ({t('optional', 'optionnel')})</Label>
                  <Input
                    id="cf-branch"
                    placeholder={t('deploy.config.branchPlaceholder', 'Laisser vide pour production')}
                    value={cloudflareBranch}
                    onChange={(e) => setCloudflareBranch(e.target.value)}
                    disabled={isDeploying}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('deploy.config.branchHint', 'Spécifier une branche crée un alias (branche.projet.pages.dev)')}
                  </p>
                </div>

                {isOffline && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {t('deploy.offline_warning', 'Déploiement indisponible hors connexion. Vérifiez votre connexion internet.')}
                    </AlertDescription>
                  </Alert>
                )}

                <Button
                  size="lg"
                  className="w-full"
                  onClick={handleDeployCloudflare}
                  disabled={!cloudflareProject.trim() || isOffline}
                  title={isOffline ? t('deploy.offline_tooltip', 'Connexion internet requise pour le déploiement') : undefined}
                >
                  <Rocket className="w-4 h-4 mr-2" />
                  {isDeploying ? t('deploy.deploying', 'Déploiement en cours...') : t('deploy.trigger', 'Déployer sur Cloudflare')}
                </Button>
              </div>
            </TabsContent>

            {/* GitHub Tab */}
            <TabsContent value="github" className="space-y-4 mt-4">
              <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
                <div className="w-12 h-12 rounded-full bg-gray-900 dark:bg-gray-100 flex items-center justify-center shrink-0">
                  <GitHubIcon />
                </div>
                <div>
                  <h3 className="font-semibold">GitHub Pages</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('deploy.platforms.githubDescription', 'Hébergement gratuit sur GitHub avec déploiement automatique')}
                  </p>
                </div>
              </div>

              <div className="bg-muted/50 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Terminal className="w-4 h-4" />
                  <span className="text-sm font-semibold">{t('deploy.command', 'Commande')}</span>
                </div>
                <code className="text-xs font-mono block">
                  niamoto deploy github \<br/>
                  &nbsp;&nbsp;--repo https://github.com/user/repo \<br/>
                  &nbsp;&nbsp;--branch gh-pages
                </code>
              </div>

              <Alert>
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>
                  {t('deploy.cliOnly', 'Ce déploiement est disponible uniquement via la ligne de commande pour le moment.')}
                </AlertDescription>
              </Alert>
            </TabsContent>

            {/* Netlify Tab */}
            <TabsContent value="netlify" className="space-y-4 mt-4">
              <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
                <div className="w-12 h-12 rounded-full bg-[#00C7B7] flex items-center justify-center shrink-0">
                  <Cloud className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold">Netlify</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('deploy.platforms.netlifyDescription', 'CDN mondial avec déploiement instantané et HTTPS automatique')}
                  </p>
                </div>
              </div>

              <div className="bg-muted/50 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Terminal className="w-4 h-4" />
                  <span className="text-sm font-semibold">{t('deploy.command', 'Commande')}</span>
                </div>
                <code className="text-xs font-mono block">
                  niamoto deploy netlify \<br/>
                  &nbsp;&nbsp;--site-id your-site-id
                </code>
              </div>

              <Alert>
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>
                  {t('deploy.cliOnly', 'Ce déploiement est disponible uniquement via la ligne de commande pour le moment.')}
                </AlertDescription>
              </Alert>
            </TabsContent>

            {/* SSH Tab */}
            <TabsContent value="ssh" className="space-y-4 mt-4">
              <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center shrink-0">
                  <Server className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold">SSH/rsync</h3>
                  <p className="text-sm text-muted-foreground">
                    {t('deploy.platforms.sshDescription', 'Déployez sur votre propre serveur via SSH et rsync')}
                  </p>
                </div>
              </div>

              <div className="bg-muted/50 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Terminal className="w-4 h-4" />
                  <span className="text-sm font-semibold">{t('deploy.command', 'Commande')}</span>
                </div>
                <code className="text-xs font-mono block">
                  niamoto deploy ssh \<br/>
                  &nbsp;&nbsp;--host user@server.com \<br/>
                  &nbsp;&nbsp;--path /var/www/html \<br/>
                  &nbsp;&nbsp;--port 22
                </code>
              </div>

              <Alert>
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>
                  {t('deploy.cliOnly', 'Ce déploiement est disponible uniquement via la ligne de commande pour le moment.')}
                </AlertDescription>
              </Alert>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Deploy Progress */}
      {(isDeploying || (currentDeploy?.logs && currentDeploy.logs.length > 0)) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{t('deploy.logs', 'Logs de déploiement')}</CardTitle>
              {isDeploying && (
                <Badge variant="secondary" className="animate-pulse">
                  <span className="w-2 h-2 bg-primary rounded-full mr-2 animate-ping" />
                  {t('deploy.deploying', 'En cours...')}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs max-h-96 overflow-y-auto">
              {currentDeploy?.logs.map((log, idx) => (
                <div key={idx} className="mb-1">{log}</div>
              ))}
              <div ref={logsEndRef} />
            </div>

            {/* Success with URL */}
            {currentDeploy?.deploymentUrl && (
              <Alert className="border-green-500/20 bg-green-500/10">
                <CheckCircle className="w-4 h-4 text-green-500" />
                <AlertDescription className="flex items-center justify-between">
                  <span>{t('deploy.success', 'Déploiement réussi !')}</span>
                  <Button size="sm" variant="outline" asChild>
                    <a href={currentDeploy.deploymentUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      {currentDeploy.deploymentUrl}
                    </a>
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Last Deploy Info */}
      {!isDeploying && lastDeploy && (
        <Card>
          <CardHeader>
            <CardTitle>{t('deploy.lastDeploy', 'Dernier déploiement')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
              <div className="flex items-center gap-4">
                {lastDeploy.status === 'completed' ? (
                  <CheckCircle className="w-6 h-6 text-green-500" />
                ) : (
                  <XCircle className="w-6 h-6 text-destructive" />
                )}
                <div>
                  <div className="font-medium capitalize">{lastDeploy.platform}</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(lastDeploy.completedAt || lastDeploy.startedAt).toLocaleString()}
                  </div>
                </div>
              </div>
              {lastDeploy.deploymentUrl && (
                <Button variant="outline" asChild>
                  <a href={lastDeploy.deploymentUrl} target="_blank" rel="noopener noreferrer">
                    <Globe className="w-4 h-4 mr-2" />
                    {t('deploy.viewSite', 'Voir le site')}
                  </a>
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
