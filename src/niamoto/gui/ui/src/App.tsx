import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/main-layout'
import { ImportPage } from '@/pages/import'
import { ImportV2Page } from '@/pages/import-v2'
import { TransformPage } from '@/pages/transform'
import { ExportPage } from '@/pages/export'
import { VisualizePage } from '@/pages/visualize'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/import" replace />} />
          <Route path="import" element={<ImportPage />} />
          <Route path="import-v2" element={<ImportV2Page />} />
          <Route path="transform" element={<TransformPage />} />
          <Route path="export" element={<ExportPage />} />
          <Route path="visualize" element={<VisualizePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
