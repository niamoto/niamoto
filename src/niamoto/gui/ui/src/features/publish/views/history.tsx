import { useEffect, useState } from 'react'
import { useNavigationStore } from '@/stores/navigationStore'
import {
  usePublishStore,
  type BuildJob,
  type DeployJob,
} from '@/features/publish/store/publishStore'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Package,
  Upload,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  MoreVertical,
  ExternalLink,
  FileText,
  RotateCcw,
  Trash2,
  Globe
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { formatDistanceToNow, format } from 'date-fns'
import { fr, enUS } from 'date-fns/locale'
import { toast } from 'sonner'
import { clearExportHistory } from '@/lib/api/export'

export default function PublishHistory() {
  const { t, i18n } = useTranslation('publish')
  const { setBreadcrumbs } = useNavigationStore()

  const {
    buildHistory,
    deployHistory,
    clearBuildHistory,
    clearDeployHistory,
  } = usePublishStore()

  const [selectedBuild, setSelectedBuild] = useState<BuildJob | null>(null)
  const [selectedDeploy, setSelectedDeploy] = useState<DeployJob | null>(null)
  const [showClearDialog, setShowClearDialog] = useState<'builds' | 'deploys' | null>(null)

  const dateLocale = i18n.language === 'fr' ? fr : enUS

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Publish', path: '/publish' },
      { label: t('history.title', 'History') }
    ])
  }, [setBreadcrumbs, t])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> {t('status.completed', 'Completed')}</Badge>
      case 'failed':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" /> {t('status.failed', 'Failed')}</Badge>
      case 'running':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1" /> {t('status.running', 'Running')}</Badge>
      case 'cancelled':
        return <Badge variant="outline"><AlertCircle className="w-3 h-3 mr-1" /> {t('status.cancelled', 'Cancelled')}</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return '—'
    try {
      return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: dateLocale })
    } catch {
      return dateStr
    }
  }

  const formatRelativeDate = (dateStr: string | undefined) => {
    if (!dateStr) return '—'
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: dateLocale })
    } catch {
      return dateStr
    }
  }

  const handleClearHistory = async () => {
    try {
      if (showClearDialog === 'builds') {
        await clearExportHistory()
        clearBuildHistory()
        toast.success(t('history.clearedBuilds', 'Build history cleared'))
      } else if (showClearDialog === 'deploys') {
        clearDeployHistory()
        toast.success(t('history.clearedDeploys', 'Deployment history cleared'))
      }
    } catch (error) {
      console.error('Failed to clear publish history:', error)
      toast.error(t('history.clearError', 'Failed to clear history'))
    } finally {
      setShowClearDialog(null)
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('history.title', 'History')}</h1>
          <p className="text-muted-foreground">{t('history.description', 'View build and deployment history')}</p>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{buildHistory.length}</div>
            <p className="text-xs text-muted-foreground">{t('history.totalBuilds', 'Builds')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-500">
              {buildHistory.filter(b => b.status === 'completed').length}
            </div>
            <p className="text-xs text-muted-foreground">{t('history.successfulBuilds', 'Successful Builds')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{deployHistory.length}</div>
            <p className="text-xs text-muted-foreground">{t('history.totalDeploys', 'Deployments')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-500">
              {deployHistory.filter(d => d.status === 'completed').length}
            </div>
            <p className="text-xs text-muted-foreground">{t('history.successfulDeploys', 'Successful Deployments')}</p>
          </CardContent>
        </Card>
      </div>

      {/* History Tabs */}
      <Tabs defaultValue="deploys">
        <TabsList>
          <TabsTrigger value="deploys" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            {t('history.deploys', 'Deployments')}
            <Badge variant="secondary" className="ml-1">{deployHistory.length}</Badge>
          </TabsTrigger>
          <TabsTrigger value="builds" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            {t('history.builds', 'Builds')}
            <Badge variant="secondary" className="ml-1">{buildHistory.length}</Badge>
          </TabsTrigger>
        </TabsList>

        {/* Deploys Tab */}
        <TabsContent value="deploys" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>{t('history.deploysTitle', 'Deployment History')}</CardTitle>
                <CardDescription>{t('history.deploysDescription', 'List of all deployments performed')}</CardDescription>
              </div>
              {deployHistory.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowClearDialog('deploys')}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  {t('history.clear', 'Effacer')}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {deployHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {t('history.noDeploysYet', 'No deployments performed')}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('history.date', 'Date')}</TableHead>
                      <TableHead>{t('history.platform', 'Plateforme')}</TableHead>
                      <TableHead>{t('history.project', 'Projet')}</TableHead>
                      <TableHead>{t('history.status', 'Statut')}</TableHead>
                      <TableHead>{t('history.url', 'URL')}</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {deployHistory.map((deploy) => (
                      <TableRow key={deploy.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{formatDate(deploy.completedAt || deploy.startedAt)}</div>
                            <div className="text-xs text-muted-foreground">{formatRelativeDate(deploy.completedAt || deploy.startedAt)}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="capitalize">{deploy.platform}</Badge>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{deploy.projectName}</div>
                            {deploy.branch && <div className="text-xs text-muted-foreground">{deploy.branch}</div>}
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(deploy.status)}</TableCell>
                        <TableCell>
                          {deploy.deploymentUrl ? (
                            <a
                              href={deploy.deploymentUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline flex items-center gap-1 text-sm"
                            >
                              <Globe className="w-3 h-3" />
                              {t('deploy.viewSite', 'View')}
                            </a>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <MoreVertical className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              {deploy.deploymentUrl && (
                                <DropdownMenuItem asChild>
                                  <a href={deploy.deploymentUrl} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="w-4 h-4 mr-2" />
                                    {t('history.openSite', 'Open site')}
                                  </a>
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuItem onClick={() => setSelectedDeploy(deploy)}>
                                <FileText className="w-4 h-4 mr-2" />
                                {t('history.viewLogs', 'View logs')}
                              </DropdownMenuItem>
                              {deploy.status === 'completed' && (
                                <DropdownMenuItem onClick={() => toast.info(t('history.rollbackSoon', 'Rollback coming soon'))}>
                                  <RotateCcw className="w-4 h-4 mr-2" />
                                  {t('history.rollback', 'Rollback')}
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Builds Tab */}
        <TabsContent value="builds" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>{t('history.buildsTitle', 'Build history')}</CardTitle>
                <CardDescription>{t('history.buildsDescription', 'List of all builds performed')}</CardDescription>
              </div>
              {buildHistory.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowClearDialog('builds')}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  {t('history.clear', 'Effacer')}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {buildHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {t('history.noBuildsYet', 'No builds performed')}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('history.date', 'Date')}</TableHead>
                      <TableHead>{t('history.status', 'Statut')}</TableHead>
                      <TableHead>{t('history.files', 'Files')}</TableHead>
                      <TableHead>{t('history.duration', 'Duration')}</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {buildHistory.map((build) => (
                      <TableRow key={build.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{formatDate(build.completedAt || build.startedAt)}</div>
                            <div className="text-xs text-muted-foreground">{formatRelativeDate(build.completedAt || build.startedAt)}</div>
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(build.status)}</TableCell>
                        <TableCell>
                          {build.metrics?.totalFiles ? (
                            <span className="font-medium">{build.metrics.totalFiles.toLocaleString()}</span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {build.metrics?.duration ? (
                            <span>{build.metrics.duration}s</span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <MoreVertical className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => setSelectedBuild(build)}>
                                <FileText className="w-4 h-4 mr-2" />
                                {t('history.viewDetails', 'View Details')}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Build Details Dialog */}
      <Dialog open={!!selectedBuild} onOpenChange={() => setSelectedBuild(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('history.buildDetails', 'Build Details')}</DialogTitle>
            <DialogDescription>
              {selectedBuild && formatDate(selectedBuild.completedAt || selectedBuild.startedAt)}
            </DialogDescription>
          </DialogHeader>
          {selectedBuild && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('history.status', 'Statut')}</span>
                {getStatusBadge(selectedBuild.status)}
              </div>
              {selectedBuild.metrics && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{t('history.files', 'Files Generated')}</span>
                    <span className="font-medium">{selectedBuild.metrics.totalFiles.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{t('history.duration', 'Duration')}</span>
                    <span className="font-medium">{selectedBuild.metrics.duration}s</span>
                  </div>
                  {selectedBuild.metrics.targets.length > 0 && (
                    <div className="pt-4 border-t">
                      <h4 className="text-sm font-medium mb-2">{t('history.breakdown', 'Breakdown')}</h4>
                      <div className="space-y-2">
                        {selectedBuild.metrics.targets.map((target) => (
                          <div key={target.name} className="flex items-center justify-between text-sm">
                            <span className="capitalize">{target.name.replace(/_/g, ' ')}</span>
                            <Badge variant="outline">{target.files} {t('files', 'fichiers')}</Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
              {selectedBuild.error && (
                <div className="pt-4 border-t">
                  <h4 className="text-sm font-medium mb-2 text-destructive">{t('history.error', 'Error')}</h4>
                  <p className="text-sm text-muted-foreground">{selectedBuild.error}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Deploy Logs Dialog */}
      <Dialog open={!!selectedDeploy} onOpenChange={() => setSelectedDeploy(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('history.deployLogs', 'Deployment Logs')}</DialogTitle>
            <DialogDescription>
              {selectedDeploy && `${selectedDeploy.platform} - ${selectedDeploy.projectName}`}
            </DialogDescription>
          </DialogHeader>
          {selectedDeploy && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('history.status', 'Statut')}</span>
                {getStatusBadge(selectedDeploy.status)}
              </div>
              {selectedDeploy.deploymentUrl && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">URL</span>
                  <a
                    href={selectedDeploy.deploymentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm"
                  >
                    {selectedDeploy.deploymentUrl}
                  </a>
                </div>
              )}
              <div className="pt-4 border-t">
                <h4 className="text-sm font-medium mb-2">{t('history.logs', 'Logs')}</h4>
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs max-h-96 overflow-y-auto">
                  {selectedDeploy.logs.length > 0 ? (
                    selectedDeploy.logs.map((log, idx) => (
                      <div key={idx} className="mb-1">{log}</div>
                    ))
                  ) : (
                    <div className="text-muted-foreground">{t('history.noLogs', 'No logs available')}</div>
                  )}
                </div>
              </div>
              {selectedDeploy.error && (
                <div className="pt-4 border-t">
                  <h4 className="text-sm font-medium mb-2 text-destructive">{t('history.error', 'Error')}</h4>
                  <p className="text-sm text-muted-foreground">{selectedDeploy.error}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Clear History Confirmation Dialog */}
      <Dialog open={!!showClearDialog} onOpenChange={() => setShowClearDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('history.confirmClear', 'Confirmer la suppression')}</DialogTitle>
            <DialogDescription>
              {showClearDialog === 'builds'
                ? t('history.confirmClearBuilds', 'Are you sure you want to clear build history? This action cannot be undone.')
                : t('history.confirmClearDeploys', 'Are you sure you want to clear deployment history? This action cannot be undone.')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClearDialog(null)}>
              {t('cancel', 'Cancel')}
            </Button>
            <Button variant="destructive" onClick={handleClearHistory}>
              <Trash2 className="w-4 h-4 mr-2" />
              {t('history.clear', 'Effacer')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
