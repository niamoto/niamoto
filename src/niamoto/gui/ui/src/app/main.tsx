import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/index.css'
import '@/i18n'
import { initErrorBuffer } from '@/features/feedback/lib/error-buffer'
import App from './App'
import { RootProviders } from './providers/RootProviders'

// Initialize error buffer before React mount to capture boot errors
initErrorBuffer()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RootProviders>
        <App />
    </RootProviders>
  </StrictMode>,
)
