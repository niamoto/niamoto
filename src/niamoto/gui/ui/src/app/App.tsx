import { useEffect, useState } from 'react'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useWelcomeScreen } from '@/features/welcome/hooks/useWelcomeScreen'
import WelcomeScreen from '@/features/welcome/views/WelcomeScreen'
import { hasDesktopBridge, isDesktopTauri } from '@/shared/desktop/bridge'
import { reloadDesktopProject } from '@/shared/desktop/projectReload'
import {
  applyUiLanguagePreference,
  getAppSettings,
} from '@/shared/desktop/appSettings'
import {
  clearManualProjectOpenTarget,
  getManualProjectOpenTarget,
  markManualProjectOpen,
} from '@/shared/desktop/projectLaunchIntent'
import { listenDesktopProjectSelected } from '@/shared/shell/desktopMenu'
import { ThemeProvider } from '@/components/theme'
import { Toaster } from 'sonner'
import ProjectCreationWizard from '@/features/welcome/views/ProjectCreationWizard'
import { useProjectCreationStore } from '@/stores/projectCreationStore'
import { AppLoader } from '@/components/ui/app-loader'
import { AppRouterProvider } from './router'

function App() {
  const { data: projectInfo, refetch: refetchProjectInfo } = useProjectInfo()
  const [languageReady, setLanguageReady] = useState(false)
  const [initialized, setInitialized] = useState(() => !hasDesktopBridge())
  const [bootFallbackToWelcome, setBootFallbackToWelcome] = useState(false)
  const [bootError, setBootError] = useState<string | null>(null)
  const projectCreationOpen = useProjectCreationStore((state) => state.isOpen)
  const closeProjectCreation = useProjectCreationStore((state) => state.close)

  const {
    showWelcome,
    loading: welcomeLoading,
    error: welcomeError,
    settings,
    recentProjects,
    invalidProjects,
    isDesktop: isDesktopMode,
    createProject,
    openProject,
    browseAndOpen,
    browseFolder,
    removeProject,
    updateSettings,
  } = useWelcomeScreen()

  useEffect(() => {
    let cancelled = false

    const initializeLanguage = async () => {
      try {
        const settings = await getAppSettings()
        await applyUiLanguagePreference(settings.ui_language)
      } catch (err) {
        console.error('Failed to initialize UI language:', err)
        await applyUiLanguagePreference('auto')
      } finally {
        if (!cancelled) {
          setLanguageReady(true)
        }
      }
    }

    initializeLanguage()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!isDesktopMode || initialized || welcomeLoading) return
    const manualProjectTarget = getManualProjectOpenTarget()

    if (showWelcome && !manualProjectTarget) {
      setInitialized(true)
      return
    }

    const initializeProject = async () => {
      try {
        const result = await reloadDesktopProject({
          allowStates: manualProjectTarget
            ? ['loaded']
            : ['loaded', 'welcome', 'invalid-project'],
          expectedProject: manualProjectTarget ?? undefined,
        })

        if (result.state === 'loaded') {
          if (manualProjectTarget) {
            clearManualProjectOpenTarget()
          }
          await refetchProjectInfo()
          setBootFallbackToWelcome(false)
          setBootError(null)
        } else {
          clearManualProjectOpenTarget()
          setBootFallbackToWelcome(true)
          setBootError(result.message)
        }
      } catch (err) {
        clearManualProjectOpenTarget()
        console.error('Failed to initialize project:', err)
        setBootFallbackToWelcome(true)
        setBootError(
          err instanceof Error ? err.message : 'Failed to initialize project'
        )
      } finally {
        setInitialized(true)
      }
    }

    initializeProject()
  }, [initialized, isDesktopMode, refetchProjectInfo, showWelcome, welcomeLoading])

  useEffect(() => {
    if (projectInfo?.name) {
      document.title = `Niamoto - ${projectInfo.name}`
    } else {
      document.title = 'Niamoto'
    }
  }, [projectInfo?.name])

  useEffect(() => {
    if (!isDesktopTauri()) {
      return
    }

    let cancelled = false
    let unlisten: (() => void) | null = null

    void listenDesktopProjectSelected((path) => {
      void (async () => {
        try {
          const result = await reloadDesktopProject({
            allowStates: ['loaded'],
            expectedProject: path,
          })

          if (cancelled) {
            return
          }

          if (result.state === 'loaded') {
            markManualProjectOpen(path)
            window.location.reload()
            return
          }

          setBootFallbackToWelcome(true)
          setBootError(result.message)
        } catch (err) {
          if (cancelled) {
            return
          }

          console.error('Failed to activate desktop project from menu:', err)
          setBootFallbackToWelcome(true)
          setBootError(
            err instanceof Error ? err.message : 'Failed to open selected project'
          )
        }
      })()
    })
      .then((cleanup) => {
        if (cancelled) {
          cleanup?.()
          return
        }
        unlisten = cleanup
      })
      .catch((err) => {
        console.error('Failed to subscribe to desktop project menu events:', err)
      })

    return () => {
      cancelled = true
      unlisten?.()
    }
  }, [])

  const handleCreateProject = async (name: string, location: string) => {
    closeProjectCreation()
    return createProject(name, location)
  }

  const fullScreenLoader = (
    <ThemeProvider>
      <div className="flex h-screen items-center justify-center bg-background">
        <AppLoader />
      </div>
    </ThemeProvider>
  )

  if (!languageReady || (isDesktopMode && welcomeLoading)) {
    return fullScreenLoader
  }

  if (isDesktopMode && (showWelcome || bootFallbackToWelcome)) {
    return (
      <ThemeProvider>
        <WelcomeScreen
          recentProjects={recentProjects}
          invalidProjects={invalidProjects}
          settings={settings}
          error={bootError ?? welcomeError}
          onOpenProject={openProject}
          onBrowseProject={browseAndOpen}
          onCreateProject={createProject}
          onRemoveProject={removeProject}
          onUpdateSettings={updateSettings}
          onBrowseFolder={browseFolder}
        />
      </ThemeProvider>
    )
  }

  if (!initialized) {
    return fullScreenLoader
  }

  return (
    <ThemeProvider>
      <Toaster position="bottom-right" richColors />
      {isDesktopMode && projectCreationOpen && (
        <div className="fixed inset-0 z-50 bg-background">
          <ProjectCreationWizard
            onComplete={handleCreateProject}
            onCancel={closeProjectCreation}
            onBrowseFolder={browseFolder}
          />
        </div>
      )}
      <AppRouterProvider />
    </ThemeProvider>
  )
}

export default App
