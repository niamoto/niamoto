import type { AnchorHTMLAttributes, ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { NavigationSidebar } from './NavigationSidebar'

const locationState = vi.hoisted(() => ({
  pathname: '/groups/species',
}))

const referencesState = vi.hoisted(() => ({
  value: {
    data: undefined,
    isLoading: true,
  },
}))

const catalogState = vi.hoisted(() => ({
  value: {
    data: undefined,
    isLoading: true,
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

vi.mock('react-router-dom', () => ({
  NavLink: (
    props: AnchorHTMLAttributes<HTMLAnchorElement> & {
      to: string
      prefetch?: string
      className?: string | ((state: { isActive: boolean }) => string)
    }
  ) => {
    const { children, className, prefetch: _prefetch, to, ...rest } = props
    return (
      <a
        href={to}
        className={typeof className === 'function' ? className({ isActive: false }) : className}
        {...rest}
      >
        {children}
      </a>
    )
  },
  useLocation: () => locationState,
}))

vi.mock('@/shared/hooks/usePlatform', () => ({
  usePlatform: () => ({ isMac: false, isDesktop: true }),
}))

vi.mock('@/shared/hooks/useRuntimeMode', () => ({
  useRuntimeMode: () => ({
    isDesktop: true,
    features: { project_switching: true },
  }),
}))

vi.mock('@/features/feedback', () => ({
  useFeedback: () => ({
    cooldownRemaining: 0,
    isPreparingScreenshot: false,
    openWithType: vi.fn(),
  }),
  useBrowserOnline: () => true,
}))

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: (props: { children: ReactNode }) => <div>{props.children}</div>,
  TooltipContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
  TooltipTrigger: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

vi.mock('@/components/common', () => ({
  ProjectSwitcher: () => <div data-project-switcher="true" />,
}))

vi.mock('@/hooks/useReferences', () => ({
  useReferences: () => referencesState.value,
}))

vi.mock('@/features/collections/hooks/useCollectionsCatalog', () => ({
  useCollectionsCatalog: () => catalogState.value,
}))

vi.mock('@/hooks/usePipelineStatus', () => ({
  usePipelineStatus: () => ({ data: undefined }),
}))

vi.mock('@/features/collections/hooks/useCollectionTransforms', () => ({
  applyCompletedTransformGroups: () => new Map(),
  getCurrentTransformBatchGroup: () => null,
  getTransformActivityByGroup: () => new Map(),
}))

vi.mock('@/stores/notificationStore', () => ({
  useNotificationStore: () => [],
}))

vi.mock('@/stores/themeStore', () => ({
  useTheme: () => ({ resolvedMode: 'light' }),
}))

vi.mock('@/shared/branding/niamotoLogo', () => ({
  getNiamotoLogoSrc: () => '/logo.svg',
}))

describe('NavigationSidebar', () => {
  it('keeps the collections child area mounted while collection navigation data loads', () => {
    const html = renderToStaticMarkup(<NavigationSidebar />)

    expect(html).toContain('data-project-switcher="true"')
    expect(html.match(/bg-muted\/70/g)).toHaveLength(3)
  })
})
