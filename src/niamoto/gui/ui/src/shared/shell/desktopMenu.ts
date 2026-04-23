import { isDesktopTauri } from '@/shared/desktop/bridge'

export const DESKTOP_MENU_ACTION_EVENT = 'desktop://menu-action'
export const DESKTOP_PROJECT_SELECTED_EVENT = 'desktop://project-selected'

type UnlistenFn = () => void

interface DesktopMenuActionPayload {
  action: string
}

interface DesktopProjectSelectedPayload {
  path: string
}

async function listenToTauriEvent<TPayload>(
  eventName: string,
  onPayload: (payload: TPayload) => void
): Promise<UnlistenFn | null> {
  if (!isDesktopTauri()) {
    return null
  }

  const { listen } = await import('@tauri-apps/api/event')
  return listen<TPayload>(eventName, (event) => onPayload(event.payload))
}

export function listenDesktopMenuAction(
  onAction: (actionId: string) => void
): Promise<UnlistenFn | null> {
  return listenToTauriEvent<DesktopMenuActionPayload>(
    DESKTOP_MENU_ACTION_EVENT,
    (payload) => {
      if (typeof payload?.action === 'string') {
        onAction(payload.action)
      }
    }
  )
}

export function listenDesktopProjectSelected(
  onProjectSelected: (path: string) => void
): Promise<UnlistenFn | null> {
  return listenToTauriEvent<DesktopProjectSelectedPayload>(
    DESKTOP_PROJECT_SELECTED_EVENT,
    (payload) => {
      if (typeof payload?.path === 'string' && payload.path.length > 0) {
        onProjectSelected(payload.path)
      }
    }
  )
}
