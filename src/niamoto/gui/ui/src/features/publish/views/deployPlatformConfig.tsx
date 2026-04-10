import {
  Cloud,
  Server,
} from 'lucide-react'
import type { ReactNode } from 'react'

import type { DeployPlatform } from '@/features/publish/store/publishStore'

const GitHubIcon = ({ className = 'w-5 h-5' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={`${className} fill-current`}>
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
  </svg>
)

const VercelIcon = ({ className = 'w-5 h-5' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={`${className} fill-current`}>
    <path d="M12 1L24 22H0L12 1z" />
  </svg>
)

interface PlatformFieldConfig {
  key: string
  label: string
  placeholder: string
  required: boolean
  isSecret?: boolean
  hint?: string
}

interface PlatformMeta {
  name: string
  icon: ReactNode
  cardIcon: ReactNode
  color: string
  description: string
  shortDescription: string
  prerequisites?: string
  tokenUrl: string
  tokenLabel: string
  tokenHint: string
  fields: PlatformFieldConfig[]
}

export const PLATFORMS: Record<DeployPlatform, PlatformMeta> = {
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

export const PLATFORM_ORDER: DeployPlatform[] = [
  'cloudflare',
  'github',
  'netlify',
  'vercel',
  'render',
  'ssh',
]

export function getProjectName(
  platform: DeployPlatform,
  config: Record<string, string>
): string {
  return config.repo || config.projectName || config.siteId || config.host || platform
}
