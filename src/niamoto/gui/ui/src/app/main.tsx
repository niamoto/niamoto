import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/index.css'
import '@/i18n'
import { initErrorBuffer } from '@/features/feedback/lib/error-buffer'
import { initApiTracker } from '@/features/feedback/lib/api-tracker'
import App from './App'
import { RootProviders } from './providers/RootProviders'

// Initialize diagnostic trackers before React mount
initErrorBuffer()
initApiTracker()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RootProviders>
        <App />
    </RootProviders>
  </StrictMode>,
)
