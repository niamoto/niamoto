import { useCallback, useEffect, useState } from 'react'

import { invokeDesktop } from '@/shared/desktop/bridge'
import { markManualProjectOpen } from '@/shared/desktop/projectLaunchIntent'
import { reloadDesktopProject } from '@/shared/desktop/projectReload'
import { getDesktopShell } from '@/shared/desktop/runtime'

export interface ProjectEntry {
  path: string
  name: string
  last_accessed: string
}

interface RecentProjectStatus {
  path: string
  valid: boolean
}

/**
 * Hook to manage project switching in desktop mode
 * Uses the active desktop shell bridge to interact with the native backend.
 */
export function useProjectSwitcher() {
  const [storedCurrentProject, setStoredCurrentProject] = useState<string | null>(
    null
  )
  const [currentProject, setCurrentProject] = useState<string | null>(null)
  const [hasInvalidCurrentProject, setHasInvalidCurrentProject] = useState(false)
  const [recentProjects, setRecentProjects] = useState<ProjectEntry[]>([])
  const [invalidProjects, setInvalidProjects] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const desktopShell = getDesktopShell()
  const isDesktop = desktopShell !== null

  const invoke = useCallback(
    async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
      if (!isDesktop) {
        throw new Error('Desktop commands only available in desktop mode')
      }
      return invokeDesktop<T>(cmd, args)
    },
    [isDesktop]
  )

  const loadProjects = useCallback(async () => {
    if (!isDesktop) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const [current, recent, validationResults] = await Promise.all([
        invoke<string | null>('get_current_project'),
        invoke<ProjectEntry[]>('get_recent_projects'),
        invoke<RecentProjectStatus[]>('validate_recent_projects'),
      ])

      const invalid = new Set(
        validationResults
          .filter((project) => !project.valid)
          .map((project) => project.path)
      )

      let currentProjectInvalid = false
      if (current) {
        currentProjectInvalid = invalid.has(current)

        if (!currentProjectInvalid) {
          try {
            await invoke<boolean>('validate_project', { path: current })
          } catch {
            currentProjectInvalid = true
            invalid.add(current)
          }
        }
      }

      setStoredCurrentProject(current)
      setHasInvalidCurrentProject(currentProjectInvalid)
      setInvalidProjects(invalid)
      setCurrentProject(currentProjectInvalid ? null : current)
      setRecentProjects(recent)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMsg)
      console.error('Failed to load projects:', err)
    } finally {
      setLoading(false)
    }
  }, [isDesktop, invoke])

  const switchProject = useCallback(
    async (projectPath: string) => {
      if (!isDesktop) {
        throw new Error('Project switching only available in desktop mode')
      }

      try {
        setLoading(true)
        setError(null)

        if (invalidProjects.has(projectPath)) {
          throw new Error('This project is no longer available')
        }

        await invoke('set_current_project', { path: projectPath })

        await reloadDesktopProject({
          allowStates: ['loaded'],
          expectedProject: projectPath,
        })

        markManualProjectOpen(projectPath)
        window.location.reload()
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to switch project'
        setError(errorMsg)
        console.error('Failed to switch project:', err)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [invalidProjects, isDesktop, invoke]
  )

  const removeProject = useCallback(
    async (projectPath: string) => {
      if (!isDesktop) {
        throw new Error('Project management only available in desktop mode')
      }

      try {
        await invoke('remove_recent_project', { path: projectPath })
        await loadProjects()
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'Failed to remove project'
        setError(errorMsg)
        console.error('Failed to remove project:', err)
        throw err
      }
    },
    [isDesktop, invoke, loadProjects]
  )

  const validateProject = useCallback(
    async (projectPath: string): Promise<boolean> => {
      if (!isDesktop) {
        return false
      }

      try {
        return await invoke<boolean>('validate_project', { path: projectPath })
      } catch (err) {
        console.error('Failed to validate project:', err)
        return false
      }
    },
    [isDesktop, invoke]
  )

  const browseProject = useCallback(async (): Promise<string | null> => {
    if (!isDesktop) {
      throw new Error('Project browsing only available in desktop mode')
    }

    try {
      return await invoke<string | null>('browse_project_folder')
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Failed to browse project'
      setError(errorMsg)
      console.error('Failed to browse project:', err)
      throw err
    }
  }, [isDesktop, invoke])

  useEffect(() => {
    void loadProjects()
  }, [loadProjects])

  return {
    storedCurrentProject,
    currentProject,
    hasInvalidCurrentProject,
    recentProjects,
    invalidProjects,
    loading,
    error,
    isDesktop,
    desktopShell,
    switchProject,
    removeProject,
    validateProject,
    browseProject,
    reload: loadProjects,
  }
}
