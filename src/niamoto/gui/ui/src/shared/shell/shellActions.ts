import { startTransition, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  getAppSettings,
  openDesktopDevtools,
} from '@/shared/desktop/appSettings'
import { useNavigationStore } from '@/stores/navigationStore'

export const SHELL_ACTION_IDS = {
  COMMAND_PALETTE_OPEN: 'command_palette.open',
  SETTINGS_OPEN: 'settings.open',
  SHELL_TOGGLE_SIDEBAR: 'shell.toggle_sidebar',
  HELP_DOCUMENTATION: 'help.documentation',
  HELP_SHORTCUTS: 'help.shortcuts',
  HELP_ABOUT: 'help.about',
  DEVTOOLS_OPEN: 'devtools.open',
} as const

export type ShellActionId =
  (typeof SHELL_ACTION_IDS)[keyof typeof SHELL_ACTION_IDS]

const SHELL_ACTION_SET = new Set<string>(Object.values(SHELL_ACTION_IDS))

export function isShellActionId(value: string): value is ShellActionId {
  return SHELL_ACTION_SET.has(value)
}

export function useShellActionRunner() {
  const navigate = useNavigate()
  const sidebarMode = useNavigationStore((state) => state.sidebarMode)
  const setSidebarMode = useNavigationStore((state) => state.setSidebarMode)
  const setCommandPaletteOpen = useNavigationStore(
    (state) => state.setCommandPaletteOpen
  )
  const toggleSidebar = useNavigationStore((state) => state.toggleSidebar)

  const navigateTo = useCallback(
    (path: string) => {
      startTransition(() => {
        navigate(path)
      })
    },
    [navigate]
  )

  const runShellAction = useCallback(
    async (actionId: ShellActionId) => {
      switch (actionId) {
        case SHELL_ACTION_IDS.COMMAND_PALETTE_OPEN:
          setCommandPaletteOpen(true)
          return

        case SHELL_ACTION_IDS.SETTINGS_OPEN:
        case SHELL_ACTION_IDS.HELP_ABOUT:
          navigateTo('/tools/settings')
          return

        case SHELL_ACTION_IDS.SHELL_TOGGLE_SIDEBAR:
          if (sidebarMode === 'hidden') {
            setSidebarMode('full')
            return
          }
          toggleSidebar()
          return

        case SHELL_ACTION_IDS.HELP_DOCUMENTATION:
          navigateTo('/help')
          return

        case SHELL_ACTION_IDS.HELP_SHORTCUTS:
          setCommandPaletteOpen(true)
          return

        case SHELL_ACTION_IDS.DEVTOOLS_OPEN: {
          const settings = await getAppSettings()
          if (!settings.debug_mode) {
            return
          }
          await openDesktopDevtools()
          return
        }
      }
    },
    [
      navigateTo,
      setCommandPaletteOpen,
      setSidebarMode,
      sidebarMode,
      toggleSidebar,
    ]
  )

  return { runShellAction }
}
