import { useCallback, useEffect, useState } from 'react'

import { invokeDesktop } from '@/shared/desktop/bridge'
import {
  getManualProjectOpenTarget,
  markManualProjectOpen,
} from '@/shared/desktop/projectLaunchIntent'
import { reloadDesktopProject } from '@/shared/desktop/projectReload'
import {
  DEFAULT_APP_SETTINGS,
  getAppSettings,
  setAppSettings as persistAppSettings,
  type AppSettings,
} from '@/shared/desktop/appSettings'
import { useProjectSwitcher } from '@/shared/hooks/useProjectSwitcher'

interface WelcomeScreenState {
  showWelcome: boolean
  loading: boolean
  error: string | null
  settings: AppSettings
}

/**
 * Hook to manage the welcome screen flow in desktop mode.
 * Handles auto-loading of last project and project creation.
 */
export function useWelcomeScreen() {
  const {
    currentProject,
    hasInvalidCurrentProject,
    recentProjects,
    invalidProjects,
    loading: projectsLoading,
    isDesktop,
    desktopShell,
    switchProject,
    browseProject,
    removeProject,
    reload: reloadProjects,
  } = useProjectSwitcher()

  const [state, setState] = useState<WelcomeScreenState>({
    showWelcome: false,
    loading: true,
    error: null,
    settings: DEFAULT_APP_SETTINGS,
  })

  const invoke = useCallback(
    async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
      if (!isDesktop) {
        throw new Error('Desktop commands only available in desktop mode')
      }
      return invokeDesktop<T>(cmd, args)
    },
    [isDesktop]
  )

  useEffect(() => {
    if (!isDesktop) {
      setState((s) => ({ ...s, showWelcome: false, loading: false }))
      return
    }

    if (projectsLoading) {
      return
    }

    const initialize = async () => {
      try {
        const settings = await getAppSettings()
        const manualProjectTarget = getManualProjectOpenTarget()
        const manualProjectOpen = manualProjectTarget !== null
        const unavailableProjectMessage =
          'The last project you opened is no longer available. Remove it from the list or open another folder.'
        const lastProject = recentProjects[0] ?? null
        const lastProjectInvalid = lastProject
          ? invalidProjects.has(lastProject.path)
          : false
        const currentProjectValid = currentProject !== null

        let showWelcome = !settings.auto_load_last_project && !manualProjectOpen
        let error: string | null = null

        if (settings.auto_load_last_project && lastProject) {
          showWelcome = !currentProjectValid
          if (lastProjectInvalid) {
            error = unavailableProjectMessage
          } else if (currentProject === lastProject.path) {
            showWelcome = false
          } else {
            try {
              await switchProject(lastProject.path)
              return
            } catch {
              showWelcome = true
            }
          }
        }

        if (hasInvalidCurrentProject) {
          error = unavailableProjectMessage
          showWelcome = true
        }

        if (manualProjectOpen && currentProjectValid) {
          showWelcome = false
        }

        if (settings.auto_load_last_project && currentProjectValid) {
          showWelcome = false
        }

        setState({
          showWelcome,
          loading: false,
          error,
          settings,
        })
      } catch (err) {
        console.error('Failed to initialize welcome screen:', err)
        setState((s) => ({
          ...s,
          loading: false,
          showWelcome: true,
          error: err instanceof Error ? err.message : 'Unknown error',
        }))
      }
    }

    void initialize()
  }, [
    isDesktop,
    projectsLoading,
    recentProjects,
    currentProject,
    hasInvalidCurrentProject,
    invalidProjects,
    invoke,
    switchProject,
  ])

  const createProject = useCallback(
    async (name: string, location: string): Promise<string> => {
      try {
        const projectPath = await invoke<string>('create_project', {
          name,
          location,
        })

        await reloadDesktopProject({
          allowStates: ['loaded'],
          expectedProject: projectPath,
        })

        markManualProjectOpen(projectPath)
        window.location.reload()

        return projectPath
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to create project'
        setState((s) => ({ ...s, error: errorMsg }))
        throw err
      }
    },
    [invoke]
  )

  const openProject = useCallback(
    async (path: string) => {
      try {
        await switchProject(path)
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to open project'
        setState((s) => ({ ...s, error: errorMsg }))
        throw err
      }
    },
    [switchProject]
  )

  const browseAndOpen = useCallback(async (): Promise<string | null> => {
    const path = await browseProject()
    if (path) {
      await openProject(path)
    }
    return path
  }, [browseProject, openProject])

  const browseFolder = useCallback(async (): Promise<string | null> => {
    try {
      return await invoke<string | null>('browse_folder')
    } catch (err) {
      console.error('Failed to browse folder:', err)
      return null
    }
  }, [invoke])

  const updateSettings = useCallback(
    async (patch: Partial<AppSettings>) => {
      const nextSettings = { ...state.settings, ...patch }
      try {
        await persistAppSettings(nextSettings)
        setState((s) => ({ ...s, settings: nextSettings }))
      } catch (err) {
        console.error('Failed to update settings:', err)
        throw err
      }
    },
    [state.settings]
  )

  const dismissWelcome = useCallback(() => {
    setState((s) => ({ ...s, showWelcome: false }))
  }, [])

  return {
    showWelcome: state.showWelcome,
    loading: state.loading || projectsLoading,
    error: state.error,
    settings: state.settings,
    recentProjects,
    invalidProjects,
    isDesktop,
    desktopShell,
    createProject,
    openProject,
    browseAndOpen,
    browseFolder,
    removeProject,
    updateSettings,
    dismissWelcome,
    reloadProjects,
  }
}
