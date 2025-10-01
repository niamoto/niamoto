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
const ApiDocs = lazy(() => import('@/pages/api-docs').then(m => ({ default: m.ApiDocs })))
const PipelineEditor = lazy(() => import('@/pages/PipelineEditor'))
const Bootstrap = lazy(() => import('@/components/pipeline/Bootstrap').then(m => ({ default: m.Bootstrap })))

// Demo pages for transform/export interface options
const EntityCentricDemo = lazy(() => import('@/pages/demos/EntityCentricDemo').then(m => ({ default: m.EntityCentricDemo })))
const PipelineVisualDemo = lazy(() => import('@/pages/demos/PipelineVisualDemo').then(m => ({ default: m.PipelineVisualDemo })))
const WizardFormDemo = lazy(() => import('@/pages/demos/WizardFormDemo').then(m => ({ default: m.WizardFormDemo })))
const Showcase = lazy(() => import('@/pages/showcase'))

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
            <Route index element={<Navigate to="showcase" replace />} />
            <Route path="setup/pipeline" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <PipelineEditor />
              </Suspense>
            } />
            <Route path="setup/bootstrap" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <Bootstrap />
              </Suspense>
            } />
            <Route path="setup/import" element={<ImportPage />} />
            <Route path="setup/transform" element={<TransformPage />} />
            <Route path="setup/export" element={<ExportPage />} />
            <Route path="setup/visualize" element={<VisualizePage />} />
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


            {/* Showcase page */}
            <Route path="showcase" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <Showcase />
              </Suspense>
            } />

            {/* Demo pages for transform/export interface options */}
            <Route path="demos/entity-centric" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <EntityCentricDemo />
              </Suspense>
            } />
            <Route path="demos/pipeline-visual" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <PipelineVisualDemo />
              </Suspense>
            } />
            <Route path="demos/wizard-form" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <WizardFormDemo />
              </Suspense>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
