import { useEffect, lazy, Suspense, useState } from 'react'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useWelcomeScreen } from '@/features/welcome/hooks/useWelcomeScreen'
import { hasDesktopBridge } from '@/shared/desktop/bridge'
import { reloadDesktopProject } from '@/shared/desktop/projectReload'
import {
  applyUiLanguagePreference,
  getAppSettings,
  openDesktopDevtools,
} from '@/shared/desktop/appSettings'
import {
  clearManualProjectOpenTarget,
  getManualProjectOpenTarget,
} from '@/shared/desktop/projectLaunchIntent'
import { ThemeProvider } from '@/components/theme'
import { Toaster } from 'sonner'
import ProjectCreationWizard from '@/features/welcome/views/ProjectCreationWizard'
import { useProjectCreationStore } from '@/stores/projectCreationStore'
import { AppLoader } from '@/components/ui/app-loader'
import { AppRouterProvider } from './router'

// Lazy load pages
const WelcomeScreen = lazy(() => import('@/features/welcome/views/WelcomeScreen'))

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
    if (!isDesktopMode) {
      return
    }

    const handleDesktopDebugShortcut = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase()
      const isMacShortcut = event.metaKey && event.altKey && key === 'i'
      const isWindowsLinuxShortcut =
        (event.ctrlKey && event.shiftKey && key === 'i') || event.key === 'F12'

      if (!isMacShortcut && !isWindowsLinuxShortcut) {
        return
      }

      event.preventDefault()

      void (async () => {
        try {
          const settings = await getAppSettings()
          if (!settings.debug_mode) {
            return
          }
          await openDesktopDevtools()
        } catch (err) {
          console.error('Failed to open desktop DevTools from shortcut:', err)
        }
      })()
    }

    window.addEventListener('keydown', handleDesktopDebugShortcut)
    return () => {
      window.removeEventListener('keydown', handleDesktopDebugShortcut)
    }
  }, [isDesktopMode])

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
        <Suspense
          fallback={fullScreenLoader}
        >
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
        </Suspense>
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
