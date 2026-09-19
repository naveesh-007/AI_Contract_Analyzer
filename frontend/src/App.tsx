import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { UploadPage } from './pages/UploadPage'
import { DocumentAnalysisPage } from './pages/DocumentAnalysisPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<UploadPage />} />
          <Route path="/documents/:documentId" element={<DocumentAnalysisPage />} />
          <Route path="/dashboard" element={<DocumentAnalysisPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
