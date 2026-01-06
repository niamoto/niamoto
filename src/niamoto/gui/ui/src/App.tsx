import { useEffect, lazy, Suspense, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useWelcomeScreen } from '@/hooks/useWelcomeScreen'
import { ThemeProvider } from '@/components/theme'
import './App.css'

// Lazy load pages
const WelcomeScreen = lazy(() => import('@/pages/welcome'))
const Showcase = lazy(() => import('@/pages/showcase'))

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
const SiteStructurePage = lazy(() => import('@/pages/site/structure'))
const SitePagesPage = lazy(() => import('@/pages/site/pages'))
const SiteThemePage = lazy(() => import('@/pages/site/theme'))

// Tools pages
const DataExplorer = lazy(() => import('@/pages/tools/explorer').then(m => ({ default: m.DataExplorer })))
const LivePreview = lazy(() => import('@/pages/tools/preview').then(m => ({ default: m.LivePreview })))
const Settings = lazy(() => import('@/pages/tools/settings').then(m => ({ default: m.Settings })))
const Plugins = lazy(() => import('@/pages/tools/plugins').then(m => ({ default: m.Plugins })))
const ApiDocs = lazy(() => import('@/pages/tools/docs/index').then(m => ({ default: m.ApiDocs })))
const ConfigEditor = lazy(() => import('@/pages/tools/config-editor').then(m => ({ default: m.ConfigEditor })))

// Labs pages - UX mockups
const LabsIndex = lazy(() => import('@/pages/labs'))
const MockupWidgetsHybrid = lazy(() => import('@/pages/labs/mockup-widgets-hybrid'))
const MockupCanvasBuilder = lazy(() => import('@/pages/labs/mockup-canvas-builder'))
const MockupWidgetsInline = lazy(() => import('@/pages/labs/mockup-widgets-inline'))

// Check if running in Tauri
const isTauri = typeof window !== 'undefined' && '__TAURI__' in window

function App() {
  const { data: projectInfo, refetch: refetchProjectInfo } = useProjectInfo()
  const [initialized, setInitialized] = useState(!isTauri) // Skip init for web mode

  // Welcome screen state (only for Tauri mode)
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

  // Initialize project context for Tauri mode (only if not showing welcome)
  useEffect(() => {
    if (!isTauri) return
    if (showWelcome) {
      setInitialized(true)
      return
    }

    const initializeProject = async () => {
      try {
        // Tell the FastAPI server to reload project from desktop config
        const response = await fetch('/api/health/reload-project', {
          method: 'POST',
        })

        if (response.ok) {
          // Refetch project info after reload
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
    // Update document title based on project name
    if (projectInfo?.name) {
      document.title = `Niamoto - ${projectInfo.name}`
    } else {
      document.title = 'Niamoto'
    }
  }, [projectInfo?.name])

  // Show loading while welcome screen is initializing
  if (isTauriMode && welcomeLoading) {
    return (
      <ThemeProvider>
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </ThemeProvider>
    )
  }

  // Show Welcome Screen in Tauri mode when no project
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

  // Show loading while initializing in Tauri mode
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
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/sources" replace />} />

            {/* Sources - Import & Data */}
            <Route path="sources" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <SourcesPage />
              </Suspense>
            } />
            <Route path="sources/import" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <ImportPage />
              </Suspense>
            } />
            <Route path="sources/dataset/:name" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <DatasetPage />
              </Suspense>
            } />
            <Route path="sources/reference/:name" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <ReferencePage />
              </Suspense>
            } />

            {/* Groups - Widget configuration */}
            <Route path="groups" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <GroupsPage />
              </Suspense>
            } />
            <Route path="groups/:name" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <GroupDetailPage />
              </Suspense>
            } />

            {/* Site - Static site configuration */}
            <Route path="site" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <SiteIndexPage />
              </Suspense>
            } />
            <Route path="site/structure" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <SiteStructurePage />
              </Suspense>
            } />
            <Route path="site/pages" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <SitePagesPage />
              </Suspense>
            } />
            <Route path="site/theme" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <SiteThemePage />
              </Suspense>
            } />

            {/* Tools */}
            <Route path="tools/explorer" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <DataExplorer />
              </Suspense>
            } />
            <Route path="tools/preview" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <LivePreview />
              </Suspense>
            } />
            <Route path="tools/settings" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <Settings />
              </Suspense>
            } />
            <Route path="tools/plugins" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <Plugins />
              </Suspense>
            } />
            <Route path="tools/docs" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <ApiDocs />
              </Suspense>
            } />
            <Route path="tools/config-editor" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <ConfigEditor />
              </Suspense>
            } />

            {/* Showcase */}
            <Route path="showcase" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <Showcase />
              </Suspense>
            } />

            {/* Labs - UX Mockups */}
            <Route path="labs" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <LabsIndex />
              </Suspense>
            } />
            <Route path="labs/mockup-widgets-hybrid" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <MockupWidgetsHybrid />
              </Suspense>
            } />
            <Route path="labs/mockup-canvas-builder" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <MockupCanvasBuilder />
              </Suspense>
            } />
            <Route path="labs/mockup-widgets-inline" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <MockupWidgetsInline />
              </Suspense>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
