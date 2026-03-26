import { useEffect, lazy, Suspense, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useWelcomeScreen } from '@/features/welcome/hooks/useWelcomeScreen'
import { ThemeProvider } from '@/components/theme'
import { Toaster } from 'sonner'

// Lazy load pages
const WelcomeScreen = lazy(() => import('@/features/welcome/views'))
const ProjectHub = lazy(() =>
  import('@/features/dashboard').then((m) => ({ default: m.ProjectHub }))
)

// Module components (not lazy — they manage their own content)
const DataModule = lazy(() =>
  import('@/features/import').then((m) => ({ default: m.DataModule }))
)
const GroupsModule = lazy(() =>
  import('@/features/groups').then((m) => ({ default: m.GroupsModule }))
)
const PublishModule = lazy(() =>
  import('@/features/publish').then((m) => ({ default: m.PublishModule }))
)

// Site pages
const SiteIndexPage = lazy(() => import('@/features/site/views/SiteIndexPage'))
const SitePagesPage = lazy(() => import('@/features/site/views/SitePagesPage'))
const SiteNavigationPage = lazy(() =>
  import('@/features/site/views/SiteNavigationPage')
)
const SiteGeneralPage = lazy(() => import('@/features/site/views/SiteGeneralPage'))
const SiteAppearancePage = lazy(() =>
  import('@/features/site/views/SiteAppearancePage')
)

// Tools pages (accessible via Cmd+K)
const DataExplorer = lazy(() =>
  import('@/features/tools/views/DataExplorer').then((m) => ({
    default: m.DataExplorer,
  }))
)
const LivePreview = lazy(() =>
  import('@/features/tools/views/LivePreview').then((m) => ({
    default: m.LivePreview,
  }))
)
const Settings = lazy(() =>
  import('@/features/tools/views/Settings').then((m) => ({
    default: m.Settings,
  }))
)
const Plugins = lazy(() =>
  import('@/features/tools/views/Plugins').then((m) => ({
    default: m.Plugins,
  }))
)
const ApiDocs = lazy(() =>
  import('@/features/tools/views/ApiDocs').then((m) => ({
    default: m.ApiDocs,
  }))
)
const ConfigEditor = lazy(() =>
  import('@/features/tools/views/ConfigEditor').then((m) => ({
    default: m.ConfigEditor,
  }))
)

// Publish pages (used by PublishModule internally)

const PageFallback = () => (
  <div className="flex items-center justify-center h-full">Loading...</div>
)

// Check if running in Tauri
const isTauri = typeof window !== 'undefined' && '__TAURI__' in window

function App() {
  const { data: projectInfo, refetch: refetchProjectInfo } = useProjectInfo()
  const [initialized, setInitialized] = useState(!isTauri)

  const {
    showWelcome,
    loading: welcomeLoading,
    error: welcomeError,
    settings,
    recentProjects,
    isTauri: isTauriMode,
    createProject,
    openProject,
    browseAndOpen,
    browseFolder,
    removeProject,
    updateSettings,
  } = useWelcomeScreen()

  useEffect(() => {
    if (!isTauri) return
    if (showWelcome) {
      setInitialized(true)
      return
    }

    const initializeProject = async () => {
      try {
        const response = await fetch('/api/health/reload-project', {
          method: 'POST',
        })

        if (response.ok) {
          await refetchProjectInfo()
        }
      } catch (err) {
        console.error('Failed to initialize project:', err)
      } finally {
        setInitialized(true)
      }
    }

    initializeProject()
  }, [refetchProjectInfo, showWelcome])

  useEffect(() => {
    if (projectInfo?.name) {
      document.title = `Niamoto - ${projectInfo.name}`
    } else {
      document.title = 'Niamoto'
    }
  }, [projectInfo?.name])

  if (isTauriMode && welcomeLoading) {
    return (
      <ThemeProvider>
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </ThemeProvider>
    )
  }

  if (isTauriMode && showWelcome) {
    return (
      <ThemeProvider>
        <Suspense
          fallback={
            <div className="flex h-screen items-center justify-center bg-background">
              <div className="text-muted-foreground">Loading...</div>
            </div>
          }
        >
          <WelcomeScreen
            recentProjects={recentProjects}
            settings={settings}
            error={welcomeError}
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
    return (
      <ThemeProvider>
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="text-muted-foreground">Loading project...</div>
        </div>
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider>
      <Toaster position="bottom-right" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Suspense fallback={<PageFallback />}><ProjectHub /></Suspense>} />

            {/* Sources - Import & Data (sidebar module) */}
            <Route
              path="sources/*"
              element={<Suspense fallback={<PageFallback />}><DataModule /></Suspense>}
            />

            {/* Groups - Widget configuration (sidebar module) */}
            <Route
              path="groups/*"
              element={<Suspense fallback={<PageFallback />}><GroupsModule /></Suspense>}
            />

            {/* Site - Static site configuration */}
            <Route path="site" element={<Suspense fallback={<PageFallback />}><SiteIndexPage /></Suspense>} />
            <Route path="site/pages" element={<Suspense fallback={<PageFallback />}><SitePagesPage /></Suspense>} />
            <Route path="site/navigation" element={<Suspense fallback={<PageFallback />}><SiteNavigationPage /></Suspense>} />
            <Route path="site/general" element={<Suspense fallback={<PageFallback />}><SiteGeneralPage /></Suspense>} />
            <Route path="site/appearance" element={<Suspense fallback={<PageFallback />}><SiteAppearancePage /></Suspense>} />

            {/* Tools (no sidebar entry — accessible via Cmd+K) */}
            <Route path="tools/explorer" element={<Suspense fallback={<PageFallback />}><DataExplorer /></Suspense>} />
            <Route path="tools/preview" element={<Suspense fallback={<PageFallback />}><LivePreview /></Suspense>} />
            <Route path="tools/settings" element={<Suspense fallback={<PageFallback />}><Settings /></Suspense>} />
            <Route path="tools/plugins" element={<Suspense fallback={<PageFallback />}><Plugins /></Suspense>} />
            <Route path="tools/docs" element={<Suspense fallback={<PageFallback />}><ApiDocs /></Suspense>} />
            <Route path="tools/config-editor" element={<Suspense fallback={<PageFallback />}><ConfigEditor /></Suspense>} />

            {/* Publish - Build & Deploy (sidebar module) */}
            <Route
              path="publish/*"
              element={<Suspense fallback={<PageFallback />}><PublishModule /></Suspense>}
            />

            {/* Catch-all: redirect 404s */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
