import { useEffect, lazy, Suspense, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useWelcomeScreen } from '@/hooks/useWelcomeScreen'
import { ThemeProvider } from '@/components/theme'
import { Toaster } from 'sonner'
import './App.css'

// Lazy load pages
const WelcomeScreen = lazy(() => import('@/pages/welcome'))
const ProjectHub = lazy(() => import('@/pages/home'))

// Sources pages
const SourcesPage = lazy(() => import('@/pages/sources'))
const ImportPage = lazy(() => import('@/pages/sources/import'))
const DatasetPage = lazy(() => import('@/pages/sources/dataset/[name]'))
const ReferencePage = lazy(() => import('@/pages/sources/reference/[name]'))

// Groups pages
const GroupsPage = lazy(() => import('@/pages/groups'))
const GroupDetailPage = lazy(() => import('@/pages/groups/[name]'))

// Site pages
const SiteIndexPage = lazy(() => import('@/pages/site'))
const SitePagesPage = lazy(() => import('@/pages/site/pages'))
const SiteNavigationPage = lazy(() => import('@/pages/site/navigation'))
const SiteGeneralPage = lazy(() => import('@/pages/site/general'))
const SiteAppearancePage = lazy(() => import('@/pages/site/appearance'))

// Tools pages (accessible via Cmd+K)
const DataExplorer = lazy(() => import('@/pages/tools/explorer').then(m => ({ default: m.DataExplorer })))
const LivePreview = lazy(() => import('@/pages/tools/preview').then(m => ({ default: m.LivePreview })))
const Settings = lazy(() => import('@/pages/tools/settings').then(m => ({ default: m.Settings })))
const Plugins = lazy(() => import('@/pages/tools/plugins').then(m => ({ default: m.Plugins })))
const ApiDocs = lazy(() => import('@/pages/tools/docs/index').then(m => ({ default: m.ApiDocs })))
const ConfigEditor = lazy(() => import('@/pages/tools/config-editor').then(m => ({ default: m.ConfigEditor })))

// Publish pages
const PublishOverview = lazy(() => import('@/pages/publish'))
const PublishBuild = lazy(() => import('@/pages/publish/build'))
const PublishDeploy = lazy(() => import('@/pages/publish/deploy'))
const PublishHistory = lazy(() => import('@/pages/publish/history'))

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

            {/* Sources - Import & Data */}
            <Route path="sources" element={<Suspense fallback={<PageFallback />}><SourcesPage /></Suspense>} />
            <Route path="sources/import" element={<Suspense fallback={<PageFallback />}><ImportPage /></Suspense>} />
            <Route path="sources/dataset/:name" element={<Suspense fallback={<PageFallback />}><DatasetPage /></Suspense>} />
            <Route path="sources/reference/:name" element={<Suspense fallback={<PageFallback />}><ReferencePage /></Suspense>} />

            {/* Groups - Widget configuration */}
            <Route path="groups" element={<Suspense fallback={<PageFallback />}><GroupsPage /></Suspense>} />
            <Route path="groups/:name" element={<Suspense fallback={<PageFallback />}><GroupDetailPage /></Suspense>} />

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

            {/* Publish - Build & Deploy */}
            <Route path="publish" element={<Suspense fallback={<PageFallback />}><PublishOverview /></Suspense>} />
            <Route path="publish/build" element={<Suspense fallback={<PageFallback />}><PublishBuild /></Suspense>} />
            <Route path="publish/deploy" element={<Suspense fallback={<PageFallback />}><PublishDeploy /></Suspense>} />
            <Route path="publish/history" element={<Suspense fallback={<PageFallback />}><PublishHistory /></Suspense>} />

            {/* Catch-all: redirect old routes and 404s */}
            <Route path="labs/*" element={<Navigate to="/" replace />} />
            <Route path="showcase" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
