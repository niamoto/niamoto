import { useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { TransformPage } from '@/pages/transform'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import { ThemeProvider } from '@/components/theme'
import './App.css'

// Lazy load pages
const DataExplorer = lazy(() => import('@/pages/data-explorer').then(m => ({ default: m.DataExplorer })))
const LivePreview = lazy(() => import('@/pages/live-preview').then(m => ({ default: m.LivePreview })))
const Settings = lazy(() => import('@/pages/settings').then(m => ({ default: m.Settings })))
const Plugins = lazy(() => import('@/pages/plugins').then(m => ({ default: m.Plugins })))
const ApiDocs = lazy(() => import('@/pages/api-docs').then(m => ({ default: m.ApiDocs })))
const ConfigEditor = lazy(() => import('@/pages/config-editor').then(m => ({ default: m.ConfigEditor })))
const Showcase = lazy(() => import('@/pages/showcase'))
const OnboardingWizard = lazy(() => import('@/pages/onboarding'))
const FlowPage = lazy(() => import('@/pages/flow'))

// Legacy pages (moved to _legacy/)
const ExportPage = lazy(() => import('@/pages/_legacy/export').then(m => ({ default: m.ExportPage })))
const VisualizePage = lazy(() => import('@/pages/_legacy/visualize').then(m => ({ default: m.VisualizePage })))
const EntityCentricDemo = lazy(() => import('@/pages/_legacy/demos/EntityCentricDemo').then(m => ({ default: m.EntityCentricDemo })))
const PipelineVisualDemo = lazy(() => import('@/pages/_legacy/demos/PipelineVisualDemo').then(m => ({ default: m.PipelineVisualDemo })))
const WizardFormDemo = lazy(() => import('@/pages/_legacy/demos/WizardFormDemo').then(m => ({ default: m.WizardFormDemo })))
const GoalDrivenPageBuilder = lazy(() => import('@/pages/_legacy/demos/GoalDrivenPageBuilder'))

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
            <Route index element={<Navigate to="flow" replace />} />
            <Route path="setup/import" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <OnboardingWizard />
              </Suspense>
            } />
            <Route path="setup/transform" element={<TransformPage />} />
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

            {/* Legacy pages - archived but still accessible */}
            <Route path="legacy/export" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <ExportPage />
              </Suspense>
            } />
            <Route path="legacy/visualize" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <VisualizePage />
              </Suspense>
            } />
            <Route path="legacy/demos/entity-centric" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <EntityCentricDemo />
              </Suspense>
            } />
            <Route path="legacy/demos/pipeline-visual" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <PipelineVisualDemo />
              </Suspense>
            } />
            <Route path="legacy/demos/wizard-form" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <WizardFormDemo />
              </Suspense>
            } />
            <Route path="legacy/demos/goal-driven" element={
              <Suspense fallback={<div className="flex items-center justify-center h-full">Loading...</div>}>
                <GoalDrivenPageBuilder />
              </Suspense>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
