import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/main-layout'
import { ImportPage } from '@/pages/import'
import { TransformPage } from '@/pages/transform'
import { ExportPage } from '@/pages/export'
import { VisualizePage } from '@/pages/visualize'
import { useProjectInfo } from '@/hooks/useProjectInfo'
import './App.css'

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
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/import" replace />} />
          <Route path="import" element={<ImportPage />} />
          <Route path="transform" element={<TransformPage />} />
          <Route path="export" element={<ExportPage />} />
          <Route path="visualize" element={<VisualizePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
