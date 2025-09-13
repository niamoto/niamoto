import { useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { ImportPage } from '@/pages/import'
import { TransformPage } from '@/pages/transform'
import { ExportPage } from '@/pages/export'
import { VisualizePage } from '@/pages/visualize'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { ThemeProvider } from '@/hooks/use-theme'
import './App.css'

// Lazy load pages
const DataExplorer = lazy(() => import('@/pages/data-explorer').then(m => ({ default: m.DataExplorer })))
const LivePreview = lazy(() => import('@/pages/live-preview').then(m => ({ default: m.LivePreview })))
const Settings = lazy(() => import('@/pages/settings').then(m => ({ default: m.Settings })))
const Plugins = lazy(() => import('@/pages/plugins').then(m => ({ default: m.Plugins })))
const Documentation = lazy(() => import('@/pages/documentation').then(m => ({ default: m.Documentation })))

function App() {
  const { data: projectInfo } = useProjectInfo()

  useEffect(() => {
    // Update document title based on project name
    if (projectInfo?.name) {
      document.title = `Niamoto - ${projectInfo.name}`
    } else {
      document.title = 'Niamoto'
    }
  }, [projectInfo?.name])

  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/import" replace />} />
            <Route path="import" element={<ImportPage />} />
            <Route path="transform" element={<TransformPage />} />
            <Route path="export" element={<ExportPage />} />
            <Route path="visualize" element={<VisualizePage />} />
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
            <Route path="settings" element={
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
                <Documentation />
              </Suspense>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
