import { useEffect, lazy, Suspense, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useWelcomeScreen } from '@/hooks/useWelcomeScreen'
import { ThemeProvider } from '@/components/theme'
import './App.css'

// Lazy load pages
const WelcomeScreen = lazy(() => import('@/pages/welcome'))
const DataExplorer = lazy(() => import('@/pages/data-explorer').then(m => ({ default: m.DataExplorer })))
const LivePreview = lazy(() => import('@/pages/live-preview').then(m => ({ default: m.LivePreview })))
const Settings = lazy(() => import('@/pages/settings').then(m => ({ default: m.Settings })))
const Plugins = lazy(() => import('@/pages/plugins').then(m => ({ default: m.Plugins })))
const ApiDocs = lazy(() => import('@/pages/api-docs').then(m => ({ default: m.ApiDocs })))
const ConfigEditor = lazy(() => import('@/pages/config-editor').then(m => ({ default: m.ConfigEditor })))
const Showcase = lazy(() => import('@/pages/showcase'))
const FlowPage = lazy(() => import('@/pages/flow'))

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
            <Route index element={<Navigate to="flow" replace />} />
            <Route path="data/explorer" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <DataExplorer />
              </Suspense>
            } />
            <Route path="data/preview" element={
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

            {/* Showcase page */}
            <Route path="showcase" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <Showcase />
              </Suspense>
            } />

            {/* Niamoto Flow - unified configuration interface */}
            <Route path="flow" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <FlowPage />
              </Suspense>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
