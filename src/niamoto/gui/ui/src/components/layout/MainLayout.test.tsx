import { renderToStaticMarkup } from 'react-dom/server'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('react-router-dom', () => ({
  Outlet: () => <section data-outlet="true">Outlet</section>,
  useLocation: () => ({ pathname: '/sources/import' }),
}))

vi.mock('@/components/motion/PageTransition', () => ({
  PageTransition: (props: { transitionKey?: string; children: ReactNode }) => (
    <div data-page-transition={props.transitionKey}>{props.children}</div>
  ),
}))

vi.mock('@/features/feedback/components/FeedbackErrorBoundary', () => ({
  FeedbackErrorBoundary: (props: { children: ReactNode }) => (
    <div data-feedback-boundary="true">{props.children}</div>
  ),
}))

vi.mock('./NavigationSidebar', () => ({
  NavigationSidebar: () => <aside data-sidebar="true" />,
}))

vi.mock('./TopBar', () => ({
  TopBar: () => <header data-topbar="true" />,
}))

vi.mock('./DesktopStatusBar', () => ({
  DesktopStatusBar: () => <footer data-desktop-status="true" />,
}))

vi.mock('./CommandPalette', () => ({
  CommandPalette: () => <div data-command-palette="true" />,
}))

vi.mock('@/features/feedback', () => ({
  FeedbackModal: () => <div data-feedback-modal="true" />,
  FeedbackProvider: (props: { children: ReactNode }) => <>{props.children}</>,
}))

vi.mock('@/features/feedback/lib/navigation-tracker', () => ({
  recordNavigation: vi.fn(),
}))

vi.mock('@/stores/navigationStore', () => ({
  routeLabels: {},
  useNavigationStore: () => ({
    setBreadcrumbs: vi.fn(),
  }),
}))

vi.mock('@/hooks/useJobPolling', () => ({
  useJobPolling: vi.fn(),
}))

vi.mock('@/shared/desktop/updater/useAppUpdater', () => ({
  AppUpdaterProvider: (props: { children: ReactNode }) => <>{props.children}</>,
}))

vi.mock('@/shared/shell/useShellBindings', () => ({
  useShellBindings: vi.fn(),
}))

vi.mock('@/shared/hooks/useRuntimeMode', () => ({
  useRuntimeMode: () => ({
    isDesktop: false,
    isTauri: false,
    project: null,
  }),
}))

vi.mock('@/shared/hooks/useCurrentProjectScope', () => ({
  buildDesktopProjectScope: () => null,
}))

vi.mock('@/shared/hooks/useProjectDesktopRouteMemory', () => ({
  useProjectDesktopRouteMemory: vi.fn(),
}))

import { MainLayout } from './MainLayout'

describe('MainLayout', () => {
  it('keeps PageTransition mounted outside the route-reset error boundary', () => {
    const html = renderToStaticMarkup(<MainLayout />)

    const transitionIndex = html.indexOf('data-page-transition="/sources"')
    const boundaryIndex = html.indexOf('data-feedback-boundary="true"')

    expect(transitionIndex).toBeGreaterThanOrEqual(0)
    expect(boundaryIndex).toBeGreaterThan(transitionIndex)
  })
})
