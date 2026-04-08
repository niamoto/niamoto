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

function renderApp(rootElement: HTMLElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <RootProviders>
        <App />
      </RootProviders>
    </StrictMode>,
  )
}

function mountWhenReady() {
  const existingRoot = document.getElementById('root')
  if (existingRoot) {
    renderApp(existingRoot)
    return
  }

  const observer = new MutationObserver(() => {
    const rootElement = document.getElementById('root')
    if (!rootElement) return

    observer.disconnect()
    renderApp(rootElement)
  })

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  })

  // Tauri dev reload can briefly execute the entrypoint before the root node exists.
  window.setTimeout(() => {
    observer.disconnect()
    const rootElement = document.getElementById('root')
    if (rootElement) {
      renderApp(rootElement)
    }
  }, 1000)
}

mountWhenReady()
