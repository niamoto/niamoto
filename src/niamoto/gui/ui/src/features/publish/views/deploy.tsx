import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNavigationStore } from '@/stores/navigationStore'
import {
  usePublishStore,
  selectIsDeploying,
  selectHasSuccessfulBuild,
  type DeployPlatform,
} from '@/features/publish/store/publishStore'
import { useNetworkStatus } from '@/hooks/useNetworkStatus'
import { usePipelineStatus } from '@/hooks/usePipelineStatus'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
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
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
  X,
  AlertTriangle,
  Info,
  Plus,
  MoreVertical,
  RefreshCw,
  Pencil,
  Trash2,
  ScrollText,
  CloudOff,
  Signal,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import axios from 'axios'

// Platform icons
const GitHubIcon = ({ className = 'w-5 h-5' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={`${className} fill-current`}>
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
  </svg>
)

const VercelIcon = ({ className = 'w-5 h-5' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={`${className} fill-current`}>
    <path d="M12 1L24 22H0L12 1z"/>
  </svg>
)

// Platform metadata
const PLATFORMS: Record<DeployPlatform, {
  name: string
  icon: React.ReactNode
  cardIcon: React.ReactNode
  color: string
  description: string
  shortDescription: string
  prerequisites?: string
  tokenUrl: string
  tokenLabel: string
  tokenHint: string
  fields: Array<{ key: string; label: string; placeholder: string; required: boolean; isSecret?: boolean; hint?: string }>
}> = {
  cloudflare: {
    name: 'Cloudflare Workers',
    icon: <Cloud className="w-6 h-6 text-white" />,
    cardIcon: <Cloud className="w-5 h-5" />,
    color: 'bg-[#F38020]',
    description: 'deploy.platforms.cloudflareDescription',
    shortDescription: 'Edge network, HTTPS auto',
    prerequisites: 'deploy.platforms.cloudflarePrerequisites',
    tokenUrl: 'https://dash.cloudflare.com/profile/api-tokens',
    tokenLabel: 'API Token',
    tokenHint: 'deploy.platforms.cloudflareTokenHint',
    fields: [
      { key: 'account-id', label: 'Account ID', placeholder: 'abc123...', required: true, hint: 'deploy.fields.cloudflare.accountIdHint' },
      { key: 'api-token', label: 'API Token', placeholder: 'Your Cloudflare token', required: true, isSecret: true, hint: 'deploy.fields.cloudflare.apiTokenHint' },
      { key: 'projectName', label: 'deploy.config.projectName', placeholder: 'my-niamoto-site', required: true, hint: 'deploy.fields.cloudflare.projectNameHint' },
      { key: 'branch', label: 'deploy.config.branch', placeholder: 'deploy.config.branchPlaceholder', required: false, hint: 'deploy.fields.cloudflare.branchHint' },
    ],
  },
  github: {
    name: 'GitHub Pages',
    icon: <GitHubIcon className="w-6 h-6 text-white dark:text-black" />,
    cardIcon: <GitHubIcon className="w-5 h-5" />,
    color: 'bg-gray-900 dark:bg-gray-100',
    description: 'deploy.platforms.githubDescription',
    shortDescription: 'Free, unlimited hosting',
    prerequisites: 'deploy.platforms.githubPrerequisites',
    tokenUrl: 'https://github.com/settings/tokens?type=beta',
    tokenLabel: 'Personal Access Token (Fine-Grained)',
    tokenHint: 'deploy.platforms.githubTokenHint',
    fields: [
      { key: 'token', label: 'Personal Access Token', placeholder: 'github_pat_...', required: true, isSecret: true, hint: 'deploy.fields.github.tokenHint' },
      { key: 'repo', label: 'Repository (owner/repo)', placeholder: 'user/my-site', required: true, hint: 'deploy.fields.github.repoHint' },
      { key: 'branch', label: 'Branch', placeholder: 'gh-pages', required: false, hint: 'deploy.fields.github.branchHint' },
    ],
  },
  netlify: {
    name: 'Netlify',
    icon: <Cloud className="w-6 h-6 text-white" />,
    cardIcon: <Cloud className="w-5 h-5" />,
    color: 'bg-[#00C7B7]',
    description: 'deploy.platforms.netlifyDescription',
    shortDescription: 'CDN mondial, HTTPS auto',
    prerequisites: 'deploy.platforms.netlifyPrerequisites',
    tokenUrl: 'https://app.netlify.com/user/applications#personal-access-tokens',
    tokenLabel: 'Personal Access Token',
    tokenHint: 'deploy.platforms.netlifyTokenHint',
    fields: [
      { key: 'token', label: 'Personal Access Token', placeholder: 'Your Netlify token', required: true, isSecret: true, hint: 'deploy.fields.netlify.tokenHint' },
      { key: 'siteId', label: 'Site ID', placeholder: 'abc123-def456...', required: true, hint: 'deploy.fields.netlify.siteIdHint' },
    ],
  },
  vercel: {
    name: 'Vercel',
    icon: <VercelIcon className="w-6 h-6" />,
    cardIcon: <VercelIcon className="w-5 h-5" />,
    color: 'bg-black dark:bg-white',
    description: 'deploy.platforms.vercelDescription',
    shortDescription: 'Edge network, previews auto',
    prerequisites: 'deploy.platforms.vercelPrerequisites',
    tokenUrl: 'https://vercel.com/account/tokens',
    tokenLabel: 'Personal Access Token',
    tokenHint: 'deploy.platforms.vercelTokenHint',
    fields: [
      { key: 'token', label: 'Personal Access Token', placeholder: 'Your Vercel token', required: true, isSecret: true, hint: 'deploy.fields.vercel.tokenHint' },
      { key: 'projectName', label: 'deploy.config.projectName', placeholder: 'my-niamoto-site', required: true, hint: 'deploy.fields.vercel.projectNameHint' },
    ],
  },
  render: {
    name: 'Render',
    icon: <Cloud className="w-6 h-6 text-white" />,
    cardIcon: <Cloud className="w-5 h-5" />,
    color: 'bg-[#46E3B7]',
    description: 'deploy.platforms.renderDescription',
    shortDescription: 'Free static sites',
    prerequisites: 'deploy.platforms.renderPrerequisites',
    tokenUrl: 'https://dashboard.render.com/settings#api-keys',
    tokenLabel: 'API Key',
    tokenHint: 'deploy.platforms.renderTokenHint',
    fields: [
      { key: 'deployHookUrl', label: 'Deploy Hook URL', placeholder: 'https://api.render.com/deploy/...', required: false, hint: 'deploy.fields.render.deployHookUrlHint' },
      { key: 'token', label: 'API Key (alternative)', placeholder: 'Your Render API Key', required: false, isSecret: true, hint: 'deploy.fields.render.tokenHint' },
      { key: 'serviceId', label: 'Service ID (with API Key)', placeholder: 'srv-...', required: false, hint: 'deploy.fields.render.serviceIdHint' },
    ],
  },
  ssh: {
    name: 'SSH / rsync',
    icon: <Server className="w-6 h-6 text-white" />,
    cardIcon: <Server className="w-5 h-5" />,
    color: 'bg-gradient-to-br from-gray-700 to-gray-900',
    description: 'deploy.platforms.sshDescription',
    shortDescription: 'Personal server, full control',
    prerequisites: 'deploy.platforms.sshPrerequisites',
    tokenUrl: '',
    tokenLabel: '',
    tokenHint: '',
    fields: [
      { key: 'host', label: 'Host', placeholder: 'user@server.com', required: true, hint: 'deploy.fields.ssh.hostHint' },
      { key: 'path', label: 'Remote Path', placeholder: '/var/www/html', required: true, hint: 'deploy.fields.ssh.pathHint' },
      { key: 'port', label: 'Port', placeholder: '22', required: false, hint: 'deploy.fields.ssh.portHint' },
      { key: 'keyPath', label: 'SSH Key Path', placeholder: '~/.ssh/id_ed25519', required: false, hint: 'deploy.fields.ssh.keyPathHint' },
    ],
  },
}

const PLATFORM_ORDER: DeployPlatform[] = ['cloudflare', 'github', 'netlify', 'vercel', 'render', 'ssh']

// Helper: get project display name from config
function getProjectName(platform: DeployPlatform, config: Record<string, string>): string {
  return config.repo || config.projectName || config.siteId || config.host || platform
}

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
    startDeploy,
    appendDeployLog,
    setDeploymentUrl,
    completeDeploy,
    cancelDeploy,
    savePlatformConfig,
    setPreferredPlatform,
    deletePlatformConfig,
    cleanupOrphanDeploys,
  } = usePublishStore()

  const isDeploying = usePublishStore(selectIsDeploying)
  const hasSuccessfulBuild = usePublishStore(selectHasSuccessfulBuild)
  const { isOffline } = useNetworkStatus()
  const { data: pipelineData } = usePipelineStatus()

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingPlatform, setEditingPlatform] = useState<DeployPlatform | null>(null)
  const [selectedNewPlatform, setSelectedNewPlatform] = useState<DeployPlatform | null>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [credentialStatus, setCredentialStatus] = useState<Record<string, { configured: boolean; validating?: boolean; valid?: boolean; user?: string }>>({})
  const [deleteConfirm, setDeleteConfirm] = useState<DeployPlatform | null>(null)
  const [unpublishConfirm, setUnpublishConfirm] = useState<DeployPlatform | null>(null)
  const [showLogs, setShowLogs] = useState<DeployPlatform | null>(null)
  const [healthStatus, setHealthStatus] = useState<Record<string, 'up' | 'down' | 'checking'>>({})
  const [isUnpublishing, setIsUnpublishing] = useState(false)

  // Configured platforms
  const configuredPlatforms = PLATFORM_ORDER.filter(p => platformConfigs[p])

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

  // Health check — manual only (CDN caches make automatic checks unreliable)
  const checkHealth = useCallback(async (platform: DeployPlatform, url?: string) => {
    const targetUrl = url || deployHistory.find(d => d.platform === platform)?.deploymentUrl
    if (!targetUrl) return

    setHealthStatus(prev => ({ ...prev, [platform]: 'checking' }))
    try {
      const { data } = await axios.get('/api/deploy/health', { params: { url: targetUrl } })
      setHealthStatus(prev => ({ ...prev, [platform]: data.status === 'up' ? 'up' : 'down' }))
    } catch {
      setHealthStatus(prev => ({ ...prev, [platform]: 'down' }))
    }
  }, [deployHistory])

  useEffect(() => {
    for (const platform of configuredPlatforms) {
      const lastPlatformDeploy = deployHistory.find(d => d.platform === platform)
      if (lastPlatformDeploy?.deploymentUrl) {
        checkHealth(platform)
      }
    }
  // Run only on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    if (currentDeploy?.logs.length) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [currentDeploy?.logs.length])

  // Check if publication is stale
  const publicationStage = pipelineData?.publication
  const isStale = publicationStage?.status === 'stale'

  // The active platform in the dialog (either editing or adding new)
  const dialogPlatform = editingPlatform || selectedNewPlatform

  // Check credential status when dialog platform changes
  useEffect(() => {
    if (!dialogPlatform || dialogPlatform === 'ssh') return
    const checkCredentials = async () => {
      try {
        const { data } = await axios.get(`/api/deploy/credentials/${dialogPlatform}/check`)
        setCredentialStatus(prev => ({ ...prev, [dialogPlatform]: { configured: data.configured } }))
      } catch {
        // Silently ignore
      }
    }
    checkCredentials()
  }, [dialogPlatform])

  const handleValidateCredentials = async (platform: string) => {
    setCredentialStatus(prev => ({ ...prev, [platform]: { ...prev[platform], validating: true } }))
    try {
      const { data } = await axios.post(`/api/deploy/credentials/${platform}/validate`)
      setCredentialStatus(prev => ({
        ...prev,
        [platform]: { configured: true, validating: false, valid: data.valid, user: data.user }
      }))
      if (data.valid) {
        toast.success(t('deploy.credentials.valid', 'Token valid') + (data.user ? ` (${data.user})` : ''))
      } else {
        toast.error(data.error || t('deploy.credentials.invalid', 'Token invalid or expired'))
      }
    } catch {
      setCredentialStatus(prev => ({ ...prev, [platform]: { ...prev[platform], validating: false, valid: false } }))
      toast.error(t('deploy.credentials.validateFailed', 'Validation failed'))
    }
  }

  // Deploy a platform using its saved config
  const handleDeploy = useCallback(async (platform: DeployPlatform, configOverride?: Record<string, string>) => {
    const config = configOverride || platformConfigs[platform] as Record<string, string> | undefined
    if (!config) return

    const projectName = getProjectName(platform, config)

    if (configOverride) {
      savePlatformConfig(platform, configOverride as any)
    }
    setPreferredPlatform(platform)
    startDeploy(platform, projectName, config.branch)

    try {
      // Auto-save secret fields to keyring before deploying
      const secretFields = PLATFORMS[platform].fields.filter(f => f.isSecret)
      for (const field of secretFields) {
        const value = config[field.key]
        if (value?.trim()) {
          try {
            await axios.post(`/api/deploy/credentials/${platform}`, { key: field.key, value })
          } catch {
            appendDeployLog(`❌ Failed to save ${field.key} to keyring`)
          }
        }
      }

      // Build extra config for the API (exclude secrets — they're in the keyring now)
      const extra: Record<string, string> = {}
      for (const [key, value] of Object.entries(config)) {
        if (key !== 'projectName' && key !== 'branch' && !secretFields.some(f => f.key === key) && value) {
          extra[key] = value
        }
      }

      const response = await fetch('/api/deploy/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          project_name: projectName,
          branch: config.branch || null,
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
      let deployedUrl = ''

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
              toast.success(t('deploy.success', 'Deployment successful!'), {
                description: t('deploy.propagationDelay', 'The site may take a few moments to become available.'),
              })
              // Mark as up — deploy succeeded (CDN caches make immediate checks unreliable)
              setHealthStatus(prev => ({ ...prev, [platform]: 'up' }))
            }
            return
          }

          if (data.startsWith('URL: ')) {
            deployedUrl = data.substring(5)
            setDeploymentUrl(deployedUrl)
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

      // If we get here without DONE, something went wrong
      if (usePublishStore.getState().currentDeploy?.status === 'running') {
        completeDeploy('Stream ended unexpectedly')
      }
    } catch (error) {
      console.error('Deploy error:', error)
      completeDeploy(String(error))
      toast.error(t('deploy.error', 'Deployment error'))
    }
  }, [platformConfigs, savePlatformConfig, setPreferredPlatform, startDeploy, completeDeploy, appendDeployLog, setDeploymentUrl, t])

  const handleCancel = () => {
    eventSourceRef.current?.close()
    cancelDeploy()
    toast.info(t('deploy.cancelled', 'Deployment cancelled'))
  }

  const updateField = (key: string, value: string) => {
    setFormData(prev => ({ ...prev, [key]: value }))
  }

  // Open dialog in add mode
  const openAddDialog = () => {
    setEditingPlatform(null)
    setSelectedNewPlatform(null)
    setFormData({})
    setDialogOpen(true)
  }

  // Open dialog in edit mode
  const openEditDialog = (platform: DeployPlatform) => {
    setEditingPlatform(platform)
    setSelectedNewPlatform(null)
    const config = platformConfigs[platform]
    setFormData(config ? { ...config as Record<string, string> } : {})
    setDialogOpen(true)
  }

  // Save config from dialog
  const handleSaveConfig = () => {
    if (!dialogPlatform) return
    savePlatformConfig(dialogPlatform, formData as any)
    toast.success(t('deploy.dashboard.configSaved', 'Configuration saved'))
    setDialogOpen(false)
  }

  // Save config and deploy from dialog
  const handleSaveAndDeploy = () => {
    if (!dialogPlatform) return
    savePlatformConfig(dialogPlatform, formData as any)
    setDialogOpen(false)
    handleDeploy(dialogPlatform, formData)
  }

  // Delete config
  const handleDelete = (platform: DeployPlatform) => {
    deletePlatformConfig(platform)
    toast.success(t('deploy.dashboard.configDeleted', 'Configuration deleted'))
    setDeleteConfirm(null)
  }

  // Unpublish a site
  const handleUnpublish = useCallback(async (platform: DeployPlatform) => {
    const config = platformConfigs[platform] as Record<string, string> | undefined
    if (!config) return

    setIsUnpublishing(true)
    setUnpublishConfirm(null)

    const projectName = getProjectName(platform, config)

    // Build extra config
    const extra: Record<string, string> = {}
    const secretFields = PLATFORMS[platform].fields.filter(f => f.isSecret)
    for (const [key, value] of Object.entries(config)) {
      if (key !== 'projectName' && key !== 'branch' && !secretFields.some(f => f.key === key) && value) {
        extra[key] = value
      }
    }

    try {
      const response = await fetch('/api/deploy/unpublish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          project_name: projectName,
          branch: config.branch || null,
          extra,
        }),
      })

      if (!response.ok || !response.body) {
        toast.error(t('deploy.error', 'Error'))
        setIsUnpublishing(false)
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
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
            if (hasSuccess) {
              toast.success(t('deploy.dashboard.unpublishSuccess', 'Site unpublished successfully'), {
                description: t('deploy.dashboard.unpublishDelay', 'The site may remain accessible for a few minutes due to CDN caching.'),
              })
              // Mark as down immediately — CDN caches make health checks unreliable after unpublish
              setHealthStatus(prev => ({ ...prev, [platform]: 'down' }))
            }
            setIsUnpublishing(false)
            return
          }

          if (data.startsWith('ERROR: ')) {
            toast.error(data.substring(7))
          } else if (data.startsWith('SUCCESS: ')) {
            hasSuccess = true
          }
        }
      }
    } catch (error) {
      console.error('Unpublish error:', error)
      toast.error(String(error))
    }
    setIsUnpublishing(false)
  }, [platformConfigs, t])

  // Get deploy status for a platform (considers health check)
  const getDeployStatus = (platform: DeployPlatform): 'configured' | 'deployed' | 'failed' | 'offline' => {
    const lastPlatformDeploy = deployHistory.find(d => d.platform === platform)
    if (!lastPlatformDeploy) return 'configured'
    if (lastPlatformDeploy.status !== 'completed') return 'failed'
    // If health check says down, show offline
    if (healthStatus[platform] === 'down') return 'offline'
    return 'deployed'
  }

  // Get last deploy for a platform
  const getLastDeploy = (platform: DeployPlatform) => {
    return deployHistory.find(d => d.platform === platform)
  }

  // Get last deploy logs for a platform
  const getLastDeployLogs = (platform: DeployPlatform) => {
    return deployHistory.find(d => d.platform === platform)
  }

  // Can deploy check
  const canDeployPlatform = !isDeploying && !isOffline && hasSuccessfulBuild

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('deploy.title', 'Deploy')}</h1>
          <p className="text-muted-foreground">{t('deploy.description', 'Publish your site online')}</p>
        </div>
        <Button onClick={openAddDialog}>
          <Plus className="w-4 h-4 mr-2" />
          {t('deploy.dashboard.addDeployment', 'Add a deployment')}
        </Button>
      </div>

      {/* No Build Warning */}
      {!hasSuccessfulBuild && (
        <Alert>
          <AlertCircle className="w-4 h-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{t('deploy.noBuild', 'You need to generate the site first before deploying.')}</span>
            <Button size="sm" variant="outline" onClick={() => navigate('/publish/build')}>
              <Package className="w-4 h-4 mr-2" />
              {t('deploy.goToBuild', 'Go to Build')}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Staleness Warning */}
      {isStale && (
        <Alert className="border-amber-500/20 bg-amber-500/10">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <AlertDescription className="flex items-center justify-between">
            <span>{t('deploy.staleWarning', 'The exported site is outdated. Data has changed since the last build.')}</span>
            <Button size="sm" variant="outline" onClick={() => navigate('/publish/build')}>
              <Package className="w-4 h-4 mr-2" />
              {t('deploy.rebuild', 'Rebuild')}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Offline Warning */}
      {isOffline && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {t('deploy.offline_warning', 'Deployment unavailable offline.')}
          </AlertDescription>
        </Alert>
      )}

      {/* Empty State */}
      {configuredPlatforms.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Send className="w-12 h-12 text-muted-foreground/40 mb-4" />
            <h3 className="text-lg font-semibold mb-1">{t('deploy.dashboard.emptyTitle', 'No deployments configured')}</h3>
            <p className="text-sm text-muted-foreground mb-6">{t('deploy.dashboard.emptyDescription', 'Configure a platform to publish your site online')}</p>
            <Button onClick={openAddDialog}>
              <Plus className="w-4 h-4 mr-2" />
              {t('deploy.dashboard.addDeployment', 'Add a deployment')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Site Cards Grid */}
      {configuredPlatforms.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {configuredPlatforms.map(platform => {
            const meta = PLATFORMS[platform]
            const config = platformConfigs[platform] as Record<string, string>
            const status = getDeployStatus(platform)
            const lastDeploy = getLastDeploy(platform)
            const isCurrentlyDeploying = currentDeploy?.platform === platform && isDeploying

            return (
              <Card key={platform} className="relative">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg ${meta.color} flex items-center justify-center shrink-0`}>
                        {meta.icon}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-base">{meta.name}</CardTitle>
                          <Badge
                            variant={status === 'deployed' ? 'default' : status === 'failed' || status === 'offline' ? 'destructive' : 'secondary'}
                            className="text-xs"
                          >
                            {status === 'deployed' && <CheckCircle className="w-3 h-3 mr-1" />}
                            {status === 'failed' && <XCircle className="w-3 h-3 mr-1" />}
                            {status === 'offline' && <CloudOff className="w-3 h-3 mr-1" />}
                            {t(`deploy.dashboard.${status}`, status)}
                          </Badge>
                          {healthStatus[platform] === 'up' && (
                            <span className="w-2 h-2 rounded-full bg-green-500" title={t('deploy.dashboard.healthOnline', 'Online')} />
                          )}
                          {healthStatus[platform] === 'checking' && (
                            <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" title={t('deploy.dashboard.healthChecking', 'Checking...')} />
                          )}
                        </div>
                        <CardDescription className="text-sm">
                          {getProjectName(platform, config)}
                        </CardDescription>
                      </div>
                    </div>

                    {/* Actions menu */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEditDialog(platform)}>
                          <Pencil className="w-4 h-4 mr-2" />
                          {t('deploy.dashboard.editConfig', 'Edit configuration')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setShowLogs(platform)}
                          disabled={!lastDeploy}
                        >
                          <ScrollText className="w-4 h-4 mr-2" />
                          {t('deploy.dashboard.viewLogs', 'View logs')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => checkHealth(platform)}
                          disabled={!getLastDeploy(platform)?.deploymentUrl}
                        >
                          <Signal className="w-4 h-4 mr-2" />
                          {t('deploy.dashboard.checkHealth', 'Check status')}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => setUnpublishConfirm(platform)}
                          disabled={platform === 'ssh' || isUnpublishing || !getLastDeploy(platform)}
                          className="text-destructive focus:text-destructive"
                        >
                          <CloudOff className="w-4 h-4 mr-2" />
                          {t('deploy.dashboard.unpublish', 'Unpublish')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setDeleteConfirm(platform)}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          {t('deploy.dashboard.deleteConfig', 'Delete')}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>

                <CardContent className="pt-0 space-y-4">
                  {/* Last deploy info */}
                  <div className="text-sm text-muted-foreground">
                    {lastDeploy ? (
                      <span>
                        {t('deploy.dashboard.lastDeployAt', 'Last deployment')} :{' '}
                        {new Date(lastDeploy.completedAt || lastDeploy.startedAt).toLocaleString()}
                        {' — '}
                        {lastDeploy.status === 'completed' ? (
                          <span className="text-green-600">✓ {t('deploy.success', 'Succeeded')}</span>
                        ) : (
                          <span className="text-destructive">✕ {t('deploy.error', 'Failed')}</span>
                        )}
                      </span>
                    ) : (
                      <span className="italic">{t('deploy.dashboard.noDeployYet', 'Never deployed')}</span>
                    )}
                  </div>

                  {/* Deployment URL */}
                  {lastDeploy?.deploymentUrl && (
                    <div className="flex items-center gap-2 text-sm">
                      <Globe className="w-3.5 h-3.5 text-muted-foreground" />
                      <a
                        href={lastDeploy.deploymentUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline truncate"
                      >
                        {lastDeploy.deploymentUrl}
                      </a>
                    </div>
                  )}

                  {/* Action buttons */}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => handleDeploy(platform)}
                      disabled={!canDeployPlatform || isCurrentlyDeploying}
                    >
                      {isCurrentlyDeploying ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          {t('deploy.deploying', 'Deploying...')}
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2" />
                          {t('deploy.dashboard.redeploy', 'Redeploy')}
                        </>
                      )}
                    </Button>
                    {lastDeploy?.deploymentUrl && (
                      <Button size="sm" variant="outline" asChild>
                        <a href={lastDeploy.deploymentUrl} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="w-4 h-4 mr-2" />
                          {t('deploy.viewSite', 'View Site')}
                        </a>
                      </Button>
                    )}
                    {isCurrentlyDeploying && (
                      <Button size="sm" variant="destructive" onClick={handleCancel}>
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Deploy Progress (streaming logs) */}
      {(isDeploying || (currentDeploy?.logs && currentDeploy.logs.length > 0)) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{t('deploy.logs', 'Deployment Logs')}</CardTitle>
              {isDeploying && (
                <Badge variant="secondary" className="animate-pulse">
                  <span className="w-2 h-2 bg-primary rounded-full mr-2 animate-ping" />
                  {t('deploy.deploying', 'Deploying...')}
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
                  <span>{t('deploy.success', 'Deployment successful!')}</span>
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

      {/* ========== Add/Edit Dialog ========== */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingPlatform
                ? `${t('deploy.dashboard.editConfig', 'Edit configuration')} — ${PLATFORMS[editingPlatform].name}`
                : t('deploy.dashboard.addDeployment', 'Add a deployment')
              }
            </DialogTitle>
            <DialogDescription>
              {editingPlatform
                ? t(PLATFORMS[editingPlatform].description)
                : t('deploy.dashboard.selectPlatform', 'Choose a platform')
              }
            </DialogDescription>
          </DialogHeader>

          {/* Platform selection (add mode only, before selecting) */}
          {!editingPlatform && !selectedNewPlatform && (
            <div className="grid grid-cols-2 gap-3 py-2">
              {PLATFORM_ORDER
                .filter(p => !platformConfigs[p])
                .map(platform => {
                  const meta = PLATFORMS[platform]
                  return (
                    <button
                      key={platform}
                      onClick={() => {
                        setSelectedNewPlatform(platform)
                        setFormData({})
                      }}
                      className="flex items-center gap-3 p-4 rounded-lg border hover:border-primary hover:bg-accent transition-colors text-left"
                    >
                      <div className={`w-10 h-10 rounded-lg ${meta.color} flex items-center justify-center shrink-0`}>
                        {meta.icon}
                      </div>
                      <div>
                        <div className="font-medium text-sm">{meta.name}</div>
                        <div className="text-xs text-muted-foreground">{meta.shortDescription}</div>
                      </div>
                    </button>
                  )
                })}
              {PLATFORM_ORDER.filter(p => !platformConfigs[p]).length === 0 && (
                <p className="col-span-2 text-sm text-muted-foreground text-center py-4">
                  Toutes les plateformes sont déjà configurées.
                </p>
              )}
            </div>
          )}

          {/* Platform form (add or edit) */}
          {dialogPlatform && (() => {
            const meta = PLATFORMS[dialogPlatform]
            const cred = credentialStatus[dialogPlatform]

            return (
              <div className="space-y-4">
                {/* Platform header (in add mode after selection) */}
                {!editingPlatform && (
                  <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
                    <div className={`w-12 h-12 rounded-full ${meta.color} flex items-center justify-center shrink-0`}>
                      {meta.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{meta.name}</h3>
                        {cred?.valid && (
                          <Badge variant="outline" className="text-green-600 border-green-300">
                            <CheckCircle className="w-3 h-3 mr-1" /> {t('deploy.credentials.connected', 'Connected')}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{t(meta.description)}</p>
                      {meta.prerequisites && (
                        <div className="flex items-start gap-1.5 mt-2 text-xs text-muted-foreground">
                          <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                          <span>{t(meta.prerequisites)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Credential Setup */}
                {meta.tokenUrl && (
                  <div className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4" />
                        <span className="text-sm font-medium">{t('deploy.credentials.title', 'Credentials')}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleValidateCredentials(dialogPlatform)}
                          disabled={!cred?.configured || cred?.validating}
                        >
                          {cred?.validating ? (
                            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          ) : cred?.valid ? (
                            <CheckCircle className="w-3 h-3 mr-1 text-green-500" />
                          ) : cred?.valid === false ? (
                            <XCircle className="w-3 h-3 mr-1 text-red-500" />
                          ) : null}
                          {t('deploy.credentials.validate', 'Verify')}
                        </Button>
                        <Button size="sm" variant="outline" asChild>
                          <a href={meta.tokenUrl} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="w-3 h-3 mr-1" />
                            {t('deploy.credentials.create', 'Create token')}
                          </a>
                        </Button>
                      </div>
                    </div>
                    {meta.tokenHint && (
                      <p className="text-xs text-muted-foreground">{t(meta.tokenHint)}</p>
                    )}
                  </div>
                )}

                {/* Platform Fields */}
                <div className="space-y-4">
                  {meta.fields.map(field => (
                    <div key={field.key} className="space-y-1.5">
                      <Label htmlFor={`dialog-${dialogPlatform}-${field.key}`}>
                        {field.label.startsWith('deploy.') ? t(field.label) : field.label}
                        {!field.required && <span className="text-muted-foreground ml-1">({t('optional', 'optionnel')})</span>}
                      </Label>
                      <Input
                        id={`dialog-${dialogPlatform}-${field.key}`}
                        type={field.isSecret ? 'password' : 'text'}
                        placeholder={field.placeholder.startsWith('deploy.') ? t(field.placeholder) : field.placeholder}
                        value={formData[field.key] || ''}
                        onChange={(e) => updateField(field.key, e.target.value)}
                      />
                      {field.hint && (
                        <p className="text-xs text-muted-foreground">{t(field.hint)}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}

          {/* Dialog Footer */}
          {dialogPlatform && (
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                {t('cancel', 'Cancel')}
              </Button>
              <Button variant="secondary" onClick={handleSaveConfig}>
                {t('deploy.dashboard.save', 'Save')}
              </Button>
              <Button onClick={handleSaveAndDeploy} disabled={!canDeployPlatform}>
                <Send className="w-4 h-4 mr-2" />
                {t('deploy.dashboard.saveAndDeploy', 'Save & Deploy')}
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>

      {/* ========== Delete Confirmation ========== */}
      <AlertDialog open={!!deleteConfirm} onOpenChange={(open) => !open && setDeleteConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deploy.dashboard.deleteConfirmTitle', 'Delete configuration')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deploy.dashboard.deleteConfirmDescription', {
                platform: deleteConfirm ? PLATFORMS[deleteConfirm].name : '',
                defaultValue: `Do you want to delete the ${deleteConfirm ? PLATFORMS[deleteConfirm].name : ''} configuration? The deployed site will not be affected.`
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel', 'Cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('deploy.dashboard.deleteConfig', 'Delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ========== Unpublish Confirmation ========== */}
      <AlertDialog open={!!unpublishConfirm} onOpenChange={(open) => !open && setUnpublishConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deploy.dashboard.unpublishConfirmTitle', 'Unpublish site')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deploy.dashboard.unpublishConfirmDescription', {
                platform: unpublishConfirm ? PLATFORMS[unpublishConfirm].name : '',
                defaultValue: `The site will be removed from the platform. Local configuration will be kept.`
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel', 'Cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => unpublishConfirm && handleUnpublish(unpublishConfirm)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              <CloudOff className="w-4 h-4 mr-2" />
              {t('deploy.dashboard.unpublish', 'Unpublish')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ========== Logs Dialog ========== */}
      <Dialog open={!!showLogs} onOpenChange={(open) => !open && setShowLogs(null)}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>
              {t('deploy.logs', 'Deployment Logs')} — {showLogs ? PLATFORMS[showLogs].name : ''}
            </DialogTitle>
          </DialogHeader>
          {showLogs && (() => {
            const deploy = getLastDeployLogs(showLogs)
            return deploy?.logs && deploy.logs.length > 0 ? (
              <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs max-h-96 overflow-y-auto">
                {deploy.logs.map((log, idx) => (
                  <div key={idx} className="mb-1">{log}</div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">
                {t('history.noLogs', 'No logs available')}
              </p>
            )
          })()}
        </DialogContent>
      </Dialog>
    </div>
  )
}
