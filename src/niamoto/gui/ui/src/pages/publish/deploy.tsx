import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePublishStore, selectIsDeploying, selectHasSuccessfulBuild, type DeployPlatform } from '@/stores/publishStore'
import { useNetworkStatus } from '@/hooks/useNetworkStatus'
import { usePipelineStatus, type StageStatus } from '@/hooks/usePipelineStatus'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Send,
  Cloud,
  Server,
  CheckCircle,
  XCircle,
  Globe,
  ExternalLink,
  AlertCircle,
  Package,
  Key,
  Loader2,
  Link2,
  Triangle,
  X,
  AlertTriangle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import axios from 'axios'

// Platform icons
const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
  </svg>
)

const VercelIcon = () => (
  <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
    <path d="M12 1L24 22H0L12 1z"/>
  </svg>
)

// Platform metadata
const PLATFORMS: Record<DeployPlatform, {
  name: string
  icon: React.ReactNode
  color: string
  description: string
  tokenUrl: string
  tokenLabel: string
  tokenHint: string
  fields: Array<{ key: string; label: string; placeholder: string; required: boolean; isSecret?: boolean }>
}> = {
  cloudflare: {
    name: 'Cloudflare Workers',
    icon: <Cloud className="w-6 h-6 text-white" />,
    color: 'bg-[#F38020]',
    description: 'deploy.platforms.cloudflareDescription',
    tokenUrl: 'https://dash.cloudflare.com/profile/api-tokens',
    tokenLabel: 'API Token',
    tokenHint: 'Permissions: Workers Scripts Edit',
    fields: [
      { key: 'account-id', label: 'Account ID', placeholder: 'abc123...', required: true },
      { key: 'api-token', label: 'API Token', placeholder: 'Votre token Cloudflare', required: true, isSecret: true },
      { key: 'projectName', label: 'deploy.config.projectName', placeholder: 'mon-site-niamoto', required: true },
      { key: 'branch', label: 'deploy.config.branch', placeholder: 'deploy.config.branchPlaceholder', required: false },
    ],
  },
  github: {
    name: 'GitHub Pages',
    icon: <GitHubIcon />,
    color: 'bg-gray-900 dark:bg-gray-100',
    description: 'deploy.platforms.githubDescription',
    tokenUrl: 'https://github.com/settings/tokens?type=beta',
    tokenLabel: 'Personal Access Token (Fine-Grained)',
    tokenHint: 'Scope: contents:write on target repo',
    fields: [
      { key: 'token', label: 'Personal Access Token', placeholder: 'github_pat_...', required: true, isSecret: true },
      { key: 'repo', label: 'Repository (owner/repo)', placeholder: 'user/my-site', required: true },
      { key: 'branch', label: 'Branch', placeholder: 'gh-pages', required: false },
    ],
  },
  netlify: {
    name: 'Netlify',
    icon: <Cloud className="w-6 h-6 text-white" />,
    color: 'bg-[#00C7B7]',
    description: 'deploy.platforms.netlifyDescription',
    tokenUrl: 'https://app.netlify.com/user/applications#personal-access-tokens',
    tokenLabel: 'Personal Access Token',
    tokenHint: '',
    fields: [
      { key: 'token', label: 'Personal Access Token', placeholder: 'Votre token Netlify', required: true, isSecret: true },
      { key: 'siteId', label: 'Site ID', placeholder: 'abc123-def456...', required: true },
    ],
  },
  vercel: {
    name: 'Vercel',
    icon: <VercelIcon />,
    color: 'bg-black dark:bg-white',
    description: 'deploy.platforms.vercelDescription',
    tokenUrl: 'https://vercel.com/account/tokens',
    tokenLabel: 'Personal Access Token',
    tokenHint: '',
    fields: [
      { key: 'token', label: 'Personal Access Token', placeholder: 'Votre token Vercel', required: true, isSecret: true },
      { key: 'projectName', label: 'deploy.config.projectName', placeholder: 'mon-site-niamoto', required: true },
    ],
  },
  render: {
    name: 'Render',
    icon: <Cloud className="w-6 h-6 text-white" />,
    color: 'bg-[#46E3B7]',
    description: 'deploy.platforms.renderDescription',
    tokenUrl: 'https://dashboard.render.com/settings#api-keys',
    tokenLabel: 'API Key',
    tokenHint: '',
    fields: [
      { key: 'deployHookUrl', label: 'Deploy Hook URL', placeholder: 'https://api.render.com/deploy/...', required: false },
      { key: 'token', label: 'API Key (alternative)', placeholder: 'Votre API Key Render', required: false, isSecret: true },
      { key: 'serviceId', label: 'Service ID (avec API Key)', placeholder: 'srv-...', required: false },
    ],
  },
  ssh: {
    name: 'SSH / rsync',
    icon: <Server className="w-6 h-6 text-white" />,
    color: 'bg-gradient-to-br from-gray-700 to-gray-900',
    description: 'deploy.platforms.sshDescription',
    tokenUrl: '',
    tokenLabel: '',
    tokenHint: '',
    fields: [
      { key: 'host', label: 'Host', placeholder: 'user@server.com', required: true },
      { key: 'path', label: 'Remote Path', placeholder: '/var/www/html', required: true },
      { key: 'port', label: 'Port', placeholder: '22', required: false },
      { key: 'keyPath', label: 'SSH Key Path', placeholder: '~/.ssh/id_ed25519', required: false },
    ],
  },
}

const PLATFORM_ORDER: DeployPlatform[] = ['cloudflare', 'github', 'netlify', 'vercel', 'render', 'ssh']

export default function PublishDeploy() {
  const { t } = useTranslation('publish')
  const navigate = useNavigate()
  const { setBreadcrumbs } = useNavigationStore()
  const logsEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const {
    currentDeploy,
    deployHistory,
    platformConfigs,
    preferredPlatform,
    startDeploy,
    appendDeployLog,
    setDeploymentUrl,
    completeDeploy,
    cancelDeploy,
    savePlatformConfig,
    setPreferredPlatform,
    cleanupOrphanDeploys,
  } = usePublishStore()

  const isDeploying = usePublishStore(selectIsDeploying)
  const hasSuccessfulBuild = usePublishStore(selectHasSuccessfulBuild)
  const lastDeploy = deployHistory[0]
  const { isOffline } = useNetworkStatus()
  const { data: pipelineData } = usePipelineStatus()

  const [selectedPlatform, setSelectedPlatform] = useState<DeployPlatform>(preferredPlatform || 'cloudflare')
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [credentialStatus, setCredentialStatus] = useState<Record<string, { configured: boolean; validating?: boolean; valid?: boolean; user?: string }>>({})

  // Cleanup orphan deploys on mount
  useEffect(() => {
    cleanupOrphanDeploys()
  }, [cleanupOrphanDeploys])

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

  // Load saved config when platform changes
  useEffect(() => {
    const config = platformConfigs[selectedPlatform]
    if (config) {
      setFormData(prev => ({ ...prev, ...config as Record<string, string> }))
    }
  }, [selectedPlatform, platformConfigs])

  // Check credential status for current platform
  useEffect(() => {
    const checkCredentials = async () => {
      try {
        const { data } = await axios.get(`/api/deploy/credentials/${selectedPlatform}/check`)
        setCredentialStatus(prev => ({ ...prev, [selectedPlatform]: { configured: data.configured } }))
      } catch {
        // Silently ignore — credentials might not be configured yet
      }
    }
    if (selectedPlatform !== 'ssh') {
      checkCredentials()
    }
  }, [selectedPlatform])

  // Check if publication is stale
  const publicationStage = pipelineData?.stages?.find((s: StageStatus) => s.name === 'publication')
  const isStale = publicationStage?.status === 'stale'

  const handleSaveCredential = async (platform: string, key: string, value: string) => {
    try {
      await axios.post(`/api/deploy/credentials/${platform}`, { key, value })
      setCredentialStatus(prev => ({ ...prev, [platform]: { configured: true } }))
      toast.success(t('deploy.credentials.saved', 'Identifiant sauvegardé'))
    } catch {
      toast.error(t('deploy.credentials.saveFailed', 'Erreur lors de la sauvegarde'))
    }
  }

  const handleValidateCredentials = async (platform: string) => {
    setCredentialStatus(prev => ({ ...prev, [platform]: { ...prev[platform], validating: true } }))
    try {
      const { data } = await axios.post(`/api/deploy/credentials/${platform}/validate`)
      setCredentialStatus(prev => ({
        ...prev,
        [platform]: { configured: true, validating: false, valid: data.valid, user: data.user }
      }))
      if (data.valid) {
        toast.success(t('deploy.credentials.valid', 'Token valide') + (data.user ? ` (${data.user})` : ''))
      } else {
        toast.error(data.error || t('deploy.credentials.invalid', 'Token invalide'))
      }
    } catch {
      setCredentialStatus(prev => ({ ...prev, [platform]: { ...prev[platform], validating: false, valid: false } }))
      toast.error(t('deploy.credentials.validateFailed', 'Erreur de validation'))
    }
  }

  const handleDeploy = useCallback(async () => {
    const platformMeta = PLATFORMS[selectedPlatform]
    const projectName = formData.projectName || formData.repo || formData.siteId || formData.host || selectedPlatform

    // Save config for future use
    savePlatformConfig(selectedPlatform, formData as any)
    setPreferredPlatform(selectedPlatform)

    startDeploy(selectedPlatform, projectName, formData.branch)

    try {
      // Build extra config for the API
      const extra: Record<string, string> = {}
      for (const [key, value] of Object.entries(formData)) {
        if (key !== 'projectName' && key !== 'branch' && value) {
          extra[key] = value
        }
      }

      const response = await fetch('/api/deploy/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: selectedPlatform,
          project_name: projectName,
          branch: formData.branch || null,
          extra,
        }),
      })

      if (!response.ok || !response.body) {
        completeDeploy(`HTTP ${response.status}: ${response.statusText}`)
        toast.error(t('deploy.error', 'Erreur lors du déploiement'))
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

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
            completeDeploy()
            toast.success(t('deploy.success', 'Déploiement réussi !'))
            return
          }

          if (data.startsWith('URL: ')) {
            setDeploymentUrl(data.substring(5))
          } else if (data.startsWith('ERROR: ')) {
            appendDeployLog(`❌ ${data}`)
          } else if (data.startsWith('SUCCESS: ')) {
            appendDeployLog(`✅ ${data}`)
          } else {
            appendDeployLog(data)
          }
        }
      }

      // If we get here without DONE, something went wrong
      if (usePublishStore.getState().currentDeploy?.status === 'running') {
        completeDeploy('Stream ended unexpectedly')
      }
    } catch (error) {
      console.error('Deploy error:', error)
      completeDeploy(String(error))
      toast.error(t('deploy.error', 'Erreur lors du déploiement'))
    }
  }, [selectedPlatform, formData, savePlatformConfig, setPreferredPlatform, startDeploy, completeDeploy, appendDeployLog, setDeploymentUrl, t])

  const handleCancel = () => {
    eventSourceRef.current?.close()
    cancelDeploy()
    toast.info(t('deploy.cancelled', 'Déploiement annulé'))
  }

  const updateField = (key: string, value: string) => {
    setFormData(prev => ({ ...prev, [key]: value }))
  }

  const canDeploy = () => {
    if (isDeploying || isOffline) return false
    const platform = PLATFORMS[selectedPlatform]
    return platform.fields
      .filter(f => f.required)
      .every(f => formData[f.key]?.trim())
  }

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

      {/* Staleness Warning */}
      {isStale && (
        <Alert className="border-amber-500/20 bg-amber-500/10">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <AlertDescription className="flex items-center justify-between">
            <span>{t('deploy.staleWarning', 'Le site exporté n\'est plus à jour. Les données ont changé depuis le dernier build.')}</span>
            <Button size="sm" variant="outline" onClick={() => navigate('/publish/build')}>
              <Package className="w-4 h-4 mr-2" />
              {t('deploy.rebuild', 'Reconstruire')}
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
          <Tabs value={selectedPlatform} onValueChange={(v) => setSelectedPlatform(v as DeployPlatform)}>
            <TabsList className="grid grid-cols-6 w-full">
              {PLATFORM_ORDER.map(p => (
                <TabsTrigger key={p} value={p} className="flex items-center gap-1.5 text-xs">
                  {p === 'github' ? <GitHubIcon /> :
                   p === 'vercel' ? <VercelIcon /> :
                   p === 'ssh' ? <Server className="w-4 h-4" /> :
                   <Cloud className="w-4 h-4" />}
                  <span className="hidden lg:inline">{PLATFORMS[p].name.split(' ')[0]}</span>
                </TabsTrigger>
              ))}
            </TabsList>

            {PLATFORM_ORDER.map(platform => {
              const meta = PLATFORMS[platform]
              const cred = credentialStatus[platform]

              return (
                <TabsContent key={platform} value={platform} className="space-y-4 mt-4">
                  {/* Platform Header */}
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
                    <div className={`w-12 h-12 rounded-full ${meta.color} flex items-center justify-center shrink-0`}>
                      {meta.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{meta.name}</h3>
                        {cred?.valid && (
                          <Badge variant="outline" className="text-green-600 border-green-300">
                            <CheckCircle className="w-3 h-3 mr-1" /> {t('deploy.credentials.connected', 'Connecté')}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {t(meta.description)}
                      </p>
                    </div>
                  </div>

                  {/* Credential Setup */}
                  {meta.tokenUrl && (
                    <div className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Key className="w-4 h-4" />
                          <span className="text-sm font-medium">{t('deploy.credentials.title', 'Identifiants')}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleValidateCredentials(platform)}
                            disabled={!cred?.configured || cred?.validating}
                          >
                            {cred?.validating ? (
                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                            ) : cred?.valid ? (
                              <CheckCircle className="w-3 h-3 mr-1 text-green-500" />
                            ) : cred?.valid === false ? (
                              <XCircle className="w-3 h-3 mr-1 text-red-500" />
                            ) : null}
                            {t('deploy.credentials.validate', 'Vérifier')}
                          </Button>
                          <Button size="sm" variant="outline" asChild>
                            <a href={meta.tokenUrl} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="w-3 h-3 mr-1" />
                              {t('deploy.credentials.create', 'Créer un token')}
                            </a>
                          </Button>
                        </div>
                      </div>
                      {meta.tokenHint && (
                        <p className="text-xs text-muted-foreground">{meta.tokenHint}</p>
                      )}
                    </div>
                  )}

                  {/* Platform Fields */}
                  <div className="space-y-4">
                    {meta.fields.map(field => (
                      <div key={field.key} className="space-y-2">
                        <Label htmlFor={`${platform}-${field.key}`}>
                          {field.label.startsWith('deploy.') ? t(field.label) : field.label}
                          {!field.required && <span className="text-muted-foreground ml-1">({t('optional', 'optionnel')})</span>}
                        </Label>
                        <div className="flex gap-2">
                          <Input
                            id={`${platform}-${field.key}`}
                            type={field.isSecret ? 'password' : 'text'}
                            placeholder={field.placeholder.startsWith('deploy.') ? t(field.placeholder) : field.placeholder}
                            value={formData[field.key] || ''}
                            onChange={(e) => updateField(field.key, e.target.value)}
                            disabled={isDeploying}
                          />
                          {field.isSecret && formData[field.key] && (
                            <Button
                              size="icon"
                              variant="outline"
                              onClick={() => handleSaveCredential(platform, field.key, formData[field.key])}
                              title={t('deploy.credentials.saveToKeyring', 'Sauvegarder dans le trousseau')}
                            >
                              <Key className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Offline Warning */}
                  {isOffline && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        {t('deploy.offline_warning', 'Déploiement indisponible hors connexion.')}
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Deploy Button */}
                  <div className="flex gap-2">
                    <Button
                      size="lg"
                      className="flex-1"
                      onClick={handleDeploy}
                      disabled={!canDeploy()}
                    >
                      {isDeploying ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          {t('deploy.deploying', 'Déploiement en cours...')}
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4 mr-2" />
                          {t('deploy.trigger', 'Déployer')} {meta.name.split(' ')[0]}
                        </>
                      )}
                    </Button>
                    {isDeploying && (
                      <Button size="lg" variant="destructive" onClick={handleCancel}>
                        <X className="w-4 h-4 mr-2" />
                        {t('cancel', 'Annuler')}
                      </Button>
                    )}
                  </div>
                </TabsContent>
              )
            })}
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
                  <div className="font-medium">{PLATFORMS[lastDeploy.platform as DeployPlatform]?.name || lastDeploy.platform}</div>
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
