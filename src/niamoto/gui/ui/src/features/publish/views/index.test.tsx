// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PublishOverview from './index'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const navigateSpy = vi.hoisted(() => vi.fn())
const setBreadcrumbsSpy = vi.hoisted(() => vi.fn())
const setSearchParamsSpy = vi.hoisted(() => vi.fn())
const refetchSpy = vi.hoisted(() => vi.fn())
const apiGetSpy = vi.hoisted(() =>
  vi.fn(async () => ({ data: { working_directory: '/tmp/project' } }))
)

const publishStoreState = vi.hoisted(() => ({
  currentBuild: null,
  currentDeploy: null,
  buildHistory: [],
  deployHistory: [],
  platformConfigs: {},
  preferredPlatform: null,
  startBuild: vi.fn(),
  updateBuild: vi.fn(),
  completeBuild: vi.fn(),
  startDeploy: vi.fn(),
  appendDeployLog: vi.fn(),
  setDeploymentUrl: vi.fn(),
  setPreferredPlatform: vi.fn(),
  completeDeploy: vi.fn(),
}))

const pipelineState = vi.hoisted(() => ({
  value: {
    publication: { status: 'never_run' },
    site: { status: 'unconfigured' },
    groups: { status: 'fresh' },
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue ?? key,
    i18n: { language: 'en', resolvedLanguage: 'en' },
  }),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateSpy,
  useSearchParams: () => [new URLSearchParams(), setSearchParamsSpy],
}))

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({
    isLoading: false,
    isFetching: false,
    data: null,
    error: null,
    refetch: refetchSpy,
  }),
}))

vi.mock('@/stores/navigationStore', () => ({
  useNavigationStore: () => ({
    setBreadcrumbs: setBreadcrumbsSpy,
  }),
}))

vi.mock('@/features/publish/store/publishStore', () => ({
  usePublishStore: (selector?: (state: typeof publishStoreState) => unknown) =>
    selector ? selector(publishStoreState) : publishStoreState,
  selectIsBuilding: (state: typeof publishStoreState) => Boolean(state.currentBuild),
  selectIsDeploying: (state: typeof publishStoreState) => Boolean(state.currentDeploy),
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useSiteConfig: () => ({
    data: {
      site: { title: 'Niamoto', lang: 'en', languages: ['en'] },
      static_pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
      navigation: [],
      footer_navigation: [],
    },
  }),
  useGroups: () => ({
    data: { groups: [] },
  }),
}))

vi.mock('@/hooks/usePipelineStatus', () => ({
  usePipelineStatus: () => ({
    data: pipelineState.value,
  }),
}))

vi.mock('@/features/publish/api/export', () => ({
  executeExportAndWait: vi.fn(),
}))

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: apiGetSpy,
  },
}))

vi.mock('@/shared/lib/api/errors', () => ({
  getApiErrorMessage: () => 'Build error',
}))

vi.mock('@/shared/hooks/useRuntimeMode', () => ({
  useRuntimeMode: () => ({ isDesktop: false }),
}))

vi.mock('@/features/publish/views/deploy', () => ({
  default: () => <div>Deploy panel</div>,
}))

vi.mock('@/features/publish/views/history', () => ({
  default: () => <div>History panel</div>,
}))

vi.mock('@/features/publish/views/deployPlatformConfig', () => ({
  getProjectName: () => 'Demo project',
  PLATFORM_ORDER: ['cloudflare'],
  PLATFORMS: {
    cloudflare: {
      name: 'Cloudflare',
      fields: [],
    },
  },
}))

vi.mock('@/shared/desktop/openExternalUrl', () => ({
  openExternalUrl: vi.fn(),
}))

vi.mock('@/shared/hooks/site-config/siteConfigApi', () => ({
  previewGroupIndex: vi.fn(),
  previewTemplate: vi.fn(),
}))

vi.mock('@/components/ui/card', () => ({
  Card: (props: { children: ReactNode }) => <div>{props.children}</div>,
  CardHeader: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
  CardTitle: (props: { children: ReactNode }) => <div>{props.children}</div>,
  CardDescription: (props: { children: ReactNode }) => <div>{props.children}</div>,
  CardContent: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: (props: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props} />
  ),
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/alert', () => ({
  Alert: (props: { children: ReactNode }) => <div>{props.children}</div>,
  AlertDescription: (props: { children: ReactNode; className?: string }) => <div className={props.className}>{props.children}</div>,
}))

vi.mock('@/components/ui/label', () => ({
  Label: (props: { children: ReactNode; htmlFor?: string; className?: string }) => (
    <label htmlFor={props.htmlFor} className={props.className}>{props.children}</label>
  ),
}))

vi.mock('@/components/ui/switch', () => ({
  Switch: (props: { checked: boolean; onCheckedChange: (checked: boolean) => void; id?: string }) => (
    <input
      id={props.id}
      type="checkbox"
      checked={props.checked}
      onChange={(event) => props.onCheckedChange(event.currentTarget.checked)}
    />
  ),
}))

vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/sheet', () => ({
  Sheet: (props: { children: ReactNode }) => <div>{props.children}</div>,
  SheetContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
  SheetDescription: (props: { children: ReactNode }) => <div>{props.children}</div>,
  SheetHeader: (props: { children: ReactNode }) => <div>{props.children}</div>,
  SheetTitle: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/ui/toggle-group', () => ({
  ToggleGroup: (props: { children: ReactNode }) => <div>{props.children}</div>,
  ToggleGroupItem: (props: { children: ReactNode }) => <button type="button">{props.children}</button>,
}))

vi.mock('@/components/ui/preview-frame', () => ({
  DEVICE_DIMENSIONS: {
    mobile: { width: 375, height: 812 },
    tablet: { width: 768, height: 1024 },
    desktop: { width: 1440, height: 900 },
  },
  PreviewFrame: (props: { emptyMessage?: string | null; title?: string }) => (
    <div>
      <div>{props.title}</div>
      <div>{props.emptyMessage}</div>
    </div>
  ),
}))

describe('PublishOverview', () => {
  let container: HTMLDivElement
  let root: Root

  afterEach(async () => {
    navigateSpy.mockReset()
    setBreadcrumbsSpy.mockReset()
    setSearchParamsSpy.mockReset()
    refetchSpy.mockReset()
    apiGetSpy.mockClear()

    if (root) {
      await act(async () => {
        root.unmount()
      })
    }

    container.remove()
  })

  it('renders the site-builder blocking alert for a real unconfigured site and navigates on click', async () => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root.render(<PublishOverview />)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(container.textContent).toContain('Configure the site in Site Builder before launching a generation.')

    const cta = Array.from(container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('Open Site Builder')
    )

    expect(cta).not.toBeUndefined()

    await act(async () => {
      ;(cta as HTMLButtonElement).click()
    })

    expect(navigateSpy).toHaveBeenCalledWith('/site/pages')
  })
})
