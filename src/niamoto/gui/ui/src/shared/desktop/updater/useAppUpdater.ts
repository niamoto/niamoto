import {
  createElement,
  lazy,
  Suspense,
  useContext,
  type ReactNode,
} from 'react'

import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'

import {
  AppUpdaterContext,
  APP_VERSION,
  createStaticAppUpdaterValue,
} from './context'

const LazyTauriAppUpdaterProvider = lazy(async () => {
  const module = await import('./providers/tauri')
  return {
    default: module.TauriAppUpdaterProvider,
  }
})

function StaticAppUpdaterProvider({ children }: { children: ReactNode }) {
  const value = createStaticAppUpdaterValue(APP_VERSION)
  return createElement(AppUpdaterContext.Provider, { value }, children)
}

export function AppUpdaterProvider({ children }: { children: ReactNode }) {
  const { shell } = useRuntimeMode()

  if (shell === 'tauri') {
    return createElement(
      Suspense,
      {
        fallback: createElement(StaticAppUpdaterProvider, { children }),
      },
      createElement(LazyTauriAppUpdaterProvider, { children })
    )
  }

  return createElement(StaticAppUpdaterProvider, { children })
}

export function useAppUpdater() {
  const value = useContext(AppUpdaterContext)
  if (!value) {
    throw new Error('useAppUpdater must be used within an AppUpdaterProvider')
  }
  return value
}

export type { AppUpdaterValue, UpdateInfo } from './context'
