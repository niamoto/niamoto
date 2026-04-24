import { useEffect } from 'react'

import { listenDesktopMenuAction } from './desktopMenu'
import {
  isShellActionId,
  SHELL_ACTION_IDS,
  type ShellActionId,
  useShellActionRunner,
} from './shellActions'

interface ShellBindingsOptions {
  isDesktop: boolean
  isTauri: boolean
}

function getDomShortcutAction(
  event: KeyboardEvent,
  allowDevtoolsShortcut: boolean
): ShellActionId | null {
  if (event.defaultPrevented) {
    return null
  }

  const key = event.key.toLowerCase()
  const hasPrimaryModifier = event.metaKey || event.ctrlKey

  if (hasPrimaryModifier && !event.shiftKey && !event.altKey && key === 'k') {
    return SHELL_ACTION_IDS.COMMAND_PALETTE_OPEN
  }

  if (
    hasPrimaryModifier &&
    !event.shiftKey &&
    !event.altKey &&
    event.key === ','
  ) {
    return SHELL_ACTION_IDS.SETTINGS_OPEN
  }

  if (!allowDevtoolsShortcut) {
    return null
  }

  const isMacShortcut = event.metaKey && event.altKey && key === 'i'
  const isWindowsLinuxShortcut =
    (event.ctrlKey && event.shiftKey && key === 'i') || event.key === 'F12'

  return isMacShortcut || isWindowsLinuxShortcut
    ? SHELL_ACTION_IDS.DEVTOOLS_OPEN
    : null
}

export function useShellBindings({
  isDesktop,
  isTauri,
}: ShellBindingsOptions) {
  const { runShellAction } = useShellActionRunner()
  const useDomShortcuts = !isDesktop || !isTauri

  useEffect(() => {
    if (!useDomShortcuts) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      const actionId = getDomShortcutAction(event, isDesktop && !isTauri)
      if (!actionId) {
        return
      }

      event.preventDefault()
      void runShellAction(actionId)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isDesktop, isTauri, runShellAction, useDomShortcuts])

  useEffect(() => {
    if (!isDesktop || !isTauri) {
      return
    }

    let cancelled = false
    let unlisten: (() => void) | null = null

    void listenDesktopMenuAction((actionId) => {
      if (!isShellActionId(actionId)) {
        return
      }

      void runShellAction(actionId)
    })
      .then((cleanup) => {
        if (cancelled) {
          cleanup?.()
          return
        }
        unlisten = cleanup
      })
      .catch((error) => {
        console.error('Failed to subscribe to desktop menu events:', error)
      })

    return () => {
      cancelled = true
      unlisten?.()
    }
  }, [isDesktop, isTauri, runShellAction])
}
