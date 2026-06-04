// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PublishDeploy from './deploy'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const cleanupOrphanDeploysSpy = vi.hoisted(() => vi.fn())
const setBreadcrumbsSpy = vi.hoisted(() => vi.fn())

const publishStoreState = vi.hoisted(() => ({
  currentBuild: null,
  currentDeploy: {
    id: 'deploy-1',
    status: 'running',
    platform: 'github',
    projectName: 'arsis-dev/niamoto-test',
    branch: 'gh-pages',
    logs: [],
    startedAt: '2026-06-04T18:00:00.000Z',
  },
  buildHistory: [
    {
      id: 'build-1',
      status: 'completed',
      progress: 100,
      message: 'Done',
      startedAt: '2026-06-04T17:55:00.000Z',
      completedAt: '2026-06-04T17:56:00.000Z',
    },
  ],
  deployHistory: [],
  platformConfigs: {
    github: {
      repo: 'arsis-dev/niamoto-test',
      branch: 'gh-pages',
    },
  },
  preferredPlatform: 'github',
  startDeploy: vi.fn(),
  appendDeployLog: vi.fn(),
  setDeploymentUrl: vi.fn(),
  completeDeploy: vi.fn(),
  cancelDeploy: vi.fn(),
  savePlatformConfig: vi.fn(),
  setPreferredPlatform: vi.fn(),
  deletePlatformConfig: vi.fn(),
  cleanupOrphanDeploys: cleanupOrphanDeploysSpy,
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string | { defaultValue?: string }) => {
      if (typeof defaultValue === 'object') {
        return defaultValue.defaultValue ?? key
      }
      return defaultValue ?? key
    },
  }),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('@/stores/navigationStore', () => ({
  useNavigationStore: () => ({
    setBreadcrumbs: setBreadcrumbsSpy,
  }),
}))

vi.mock('@/features/publish/store/publishStore', () => ({
  usePublishStore: (selector?: (state: typeof publishStoreState) => unknown) =>
    selector ? selector(publishStoreState) : publishStoreState,
  selectIsDeploying: (state: typeof publishStoreState) =>
    state.currentDeploy !== null && state.currentDeploy.status === 'running',
  selectHasSuccessfulBuild: (state: typeof publishStoreState) =>
    state.buildHistory.some((build) => build.status === 'completed'),
}))

vi.mock('@/shared/hooks/useNetworkStatus', () => ({
  useNetworkStatus: () => ({
    checkConnectivity: vi.fn(async () => true),
  }),
}))

vi.mock('@/hooks/usePipelineStatus', () => ({
  usePipelineStatus: () => ({
    data: { publication: { status: 'fresh' } },
  }),
}))

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(async () => ({ data: { configured: true } })),
    post: vi.fn(async () => ({ data: {} })),
  },
}))

vi.mock('@/shared/lib/api/fetch', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('@/shared/desktop/openExternalUrl', () => ({
  openExternalUrl: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

vi.mock('./deployPlatformConfig', () => ({
  getProjectName: () => 'arsis-dev/niamoto-test',
  PLATFORM_ORDER: ['github'],
  PLATFORMS: {
    github: {
      name: 'GitHub Pages',
      color: 'bg-muted',
      icon: 'GH',
      fields: [],
      description: 'GitHub Pages',
      shortDescription: 'GitHub Pages',
    },
  },
}))

vi.mock('@/components/ui/card', () => ({
  Card: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  CardHeader: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  CardTitle: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  CardDescription: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  CardContent: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props}>{children}</button>
  ),
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: (props: { children: ReactNode; className?: string }) => <span className={props.className}>{props.children}</span>,
}))

vi.mock('@/components/ui/input', () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}))

vi.mock('@/components/ui/label', () => ({
  Label: (props: { children: ReactNode; htmlFor?: string; className?: string }) => (
    <label htmlFor={props.htmlFor} className={props.className}>{props.children}</label>
  ),
}))

vi.mock('@/components/ui/alert', () => ({
  Alert: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  AlertDescription: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DialogContent: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  DialogDescription: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DialogFooter: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  DialogHeader: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DialogTitle: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/alert-dialog', () => ({
  AlertDialog: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDialogAction: (props: { children: ReactNode }) => <button type="button">{props.children}</button>,
  AlertDialogCancel: (props: { children: ReactNode }) => <button type="button">{props.children}</button>,
  AlertDialogContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDialogDescription: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDialogFooter: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDialogHeader: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDialogTitle: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DropdownMenuContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DropdownMenuItem: (props: { children: ReactNode; onClick?: () => void; disabled?: boolean }) => (
    <button type="button" onClick={props.onClick} disabled={props.disabled}>{props.children}</button>
  ),
  DropdownMenuSeparator: () => <hr />,
  DropdownMenuTrigger: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

describe('PublishDeploy', () => {
  let container: HTMLDivElement
  let root: Root

  afterEach(async () => {
    cleanupOrphanDeploysSpy.mockClear()
    setBreadcrumbsSpy.mockClear()

    if (root) {
      await act(async () => {
        root.unmount()
      })
    }

    container.remove()
  })

  it('does not mark an active deployment as orphaned when the destinations panel mounts', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root.render(<PublishDeploy embedded />)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(cleanupOrphanDeploysSpy).not.toHaveBeenCalled()
  })
})
