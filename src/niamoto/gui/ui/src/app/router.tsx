import type { ComponentType } from 'react'
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import ProjectHub from '@/features/dashboard/views/ProjectHub'

function lazyDefault(importer: () => Promise<{ default: ComponentType }>) {
  return async () => {
    const module = await importer()
    return { Component: module.default }
  }
}

function lazyNamed<TModule extends Record<string, unknown>>(
  importer: () => Promise<TModule>,
  exportName: keyof TModule,
) {
  return async () => {
    const module = await importer()
    return { Component: module[exportName] as ComponentType }
  }
}

const appRouter = createBrowserRouter([
  {
    path: '/',
    Component: MainLayout,
    children: [
      {
        index: true,
        Component: ProjectHub,
      },
      {
        path: 'sources/*',
        lazy: lazyNamed(
          () => import('@/features/import/module/DataModule'),
          'DataModule',
        ),
      },
      {
        path: 'groups/*',
        lazy: lazyNamed(
          () => import('@/features/collections/components/CollectionsModule'),
          'CollectionsModule',
        ),
      },
      {
        path: 'site',
        element: <Navigate to="/site/pages" replace />,
      },
      {
        path: 'site/pages',
        lazy: lazyDefault(() => import('@/features/site/views/SitePagesPage')),
      },
      {
        path: 'site/navigation',
        element: <Navigate to="/site/pages" replace />,
      },
      {
        path: 'site/general',
        lazy: lazyDefault(() => import('@/features/site/views/SiteGeneralPage')),
      },
      {
        path: 'site/appearance',
        lazy: lazyDefault(() => import('@/features/site/views/SiteAppearancePage')),
      },
      {
        path: 'tools/explorer',
        lazy: lazyNamed(
          () => import('@/features/tools/views/DataExplorer'),
          'DataExplorer',
        ),
      },
      {
        path: 'tools/preview',
        lazy: lazyNamed(
          () => import('@/features/tools/views/LivePreview'),
          'LivePreview',
        ),
      },
      {
        path: 'tools/settings',
        lazy: lazyNamed(
          () => import('@/features/tools/views/Settings'),
          'Settings',
        ),
      },
      {
        path: 'tools/plugins',
        lazy: lazyNamed(
          () => import('@/features/tools/views/Plugins'),
          'Plugins',
        ),
      },
      {
        path: 'tools/docs',
        lazy: lazyNamed(() => import('@/features/tools/views/ApiDocs'), 'ApiDocs'),
      },
      {
        path: 'help/*',
        lazy: lazyNamed(
          () => import('@/features/help/views/DocumentationCenter'),
          'DocumentationCenter',
        ),
      },
      {
        path: 'tools/config-editor',
        lazy: lazyNamed(
          () => import('@/features/tools/views/ConfigEditor'),
          'ConfigEditor',
        ),
      },
      {
        path: 'publish',
        lazy: lazyNamed(
          () => import('@/features/publish/components/PublishModule'),
          'PublishModule',
        ),
      },
      {
        path: 'publish/build',
        element: <Navigate to="/publish" replace />,
      },
      {
        path: 'publish/deploy',
        element: <Navigate to="/publish?panel=destinations" replace />,
      },
      {
        path: 'publish/history',
        element: <Navigate to="/publish?panel=history" replace />,
      },
      {
        path: 'publish/*',
        element: <Navigate to="/publish" replace />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
])

export function AppRouterProvider() {
  return <RouterProvider router={appRouter} />
}
