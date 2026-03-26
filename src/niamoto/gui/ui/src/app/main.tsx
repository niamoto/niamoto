import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/index.css'
import '@/i18n'
import App from './App'
import { RootProviders } from './providers/RootProviders'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RootProviders>
        <App />
    </RootProviders>
  </StrictMode>,
)
