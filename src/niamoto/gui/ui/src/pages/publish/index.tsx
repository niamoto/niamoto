import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePublishStore, selectIsBuilding, selectIsDeploying } from '@/stores/publishStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Rocket,
  Package,
  Upload,
  History,
  CheckCircle,
  XCircle,
  Clock,
  ExternalLink,
  Globe,
  AlertCircle
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { formatDistanceToNow } from 'date-fns'
import { fr, enUS } from 'date-fns/locale'

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
  const dateLocale = i18n.language === 'fr' ? fr : enUS

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Publish', path: '/publish' },
      { label: t('overview.title', 'Vue d\'ensemble') }
    ])
  }, [setBreadcrumbs, t])

  const getStatusBadge = (status: string | undefined) => {
    if (!status) return null
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> {t('status.completed', 'Terminé')}</Badge>
      case 'failed':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" /> {t('status.failed', 'Échoué')}</Badge>
      case 'running':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1 animate-spin" /> {t('status.running', 'En cours')}</Badge>
      case 'cancelled':
        return <Badge variant="outline"><AlertCircle className="w-3 h-3 mr-1" /> {t('status.cancelled', 'Annulé')}</Badge>
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
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('title', 'Publication')}</h1>
          <p className="text-muted-foreground">{t('description', 'Générez et déployez votre site statique')}</p>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Last Build Card */}
        <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/publish/build')}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Package className="w-5 h-5" />
                {t('overview.lastBuild', 'Dernier Build')}
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
              <div className="text-sm text-muted-foreground">{t('overview.noBuild', 'Aucun build effectué')}</div>
            )}
          </CardContent>
        </Card>

        {/* Last Deploy Card */}
        <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => navigate('/publish/deploy')}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Upload className="w-5 h-5" />
                {t('overview.lastDeploy', 'Dernier Déploiement')}
              </CardTitle>
              {getStatusBadge(currentDeploy?.status || lastDeploy?.status)}
            </div>
          </CardHeader>
          <CardContent>
            {isDeploying ? (
              <div className="space-y-2">
                <div className="text-sm text-muted-foreground">
                  {t('deploy.deploying', 'Déploiement en cours sur')} {currentDeploy?.platform}...
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
              <div className="text-sm text-muted-foreground">{t('overview.noDeploy', 'Aucun déploiement effectué')}</div>
            )}
          </CardContent>
        </Card>

        {/* Preview Card */}
        <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => window.open('/preview', '_blank')}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Globe className="w-5 h-5" />
              {t('overview.sitePreview', 'Aperçu du site')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">
                {t('overview.previewDescription', 'Visualisez le site généré localement')}
              </div>
              <Button variant="outline" size="sm" className="gap-2">
                <ExternalLink className="w-4 h-4" />
                {t('overview.openPreview', 'Ouvrir l\'aperçu')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>{t('overview.quickActions', 'Actions rapides')}</CardTitle>
          <CardDescription>{t('overview.quickActionsDescription', 'Générez et déployez votre site en quelques clics')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button
              size="lg"
              onClick={() => navigate('/publish/build')}
              disabled={isBuilding}
            >
              <Package className="w-5 h-5 mr-2" />
              {isBuilding ? t('build.building', 'Build en cours...') : t('build.trigger', 'Générer le site')}
            </Button>

            <Button
              size="lg"
              variant="secondary"
              onClick={() => navigate('/publish/deploy')}
              disabled={isDeploying || (!lastBuild && !buildHistory.some(b => b.status === 'completed'))}
            >
              <Rocket className="w-5 h-5 mr-2" />
              {isDeploying ? t('deploy.deploying', 'Déploiement...') : t('deploy.trigger', 'Déployer')}
            </Button>

            <Button
              size="lg"
              variant="outline"
              onClick={() => navigate('/publish/history')}
            >
              <History className="w-5 h-5 mr-2" />
              {t('history.title', 'Historique')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      {(buildHistory.length > 0 || deployHistory.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>{t('overview.recentActivity', 'Activité récente')}</CardTitle>
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
  )
}
