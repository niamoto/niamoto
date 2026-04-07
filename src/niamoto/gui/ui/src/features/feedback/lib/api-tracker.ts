/**
 * Tracks failed/slow API requests for debug context.
 * Wraps fetch and axios to intercept errors and slow responses.
 */

import axios from 'axios'
import type { AxiosInstance } from 'axios'
import { apiClient } from '@/shared/lib/api/client'
import { promptServerErrorBugReport } from './server-error-feedback'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: {
      startedAt?: number
      trackedUrl?: string
    }
  }
}

interface FailedRequest {
  url: string
  status: number
  duration: number
  timestamp: string
}

const MAX_ENTRIES = 10
const failures: FailedRequest[] = []
let initialized = false

function pushFailure(entry: FailedRequest): void {
  if (failures.length >= MAX_ENTRIES) failures.shift()
  failures.push(entry)
}

function normalizeApiUrl(url?: string, baseURL?: string): string | null {
  if (!url) return null

  if (url.startsWith('/api/')) return url

  if (baseURL === '/api') {
    return url.startsWith('/') ? `/api${url}` : `/api/${url}`
  }

  if (baseURL?.endsWith('/api')) {
    try {
      const resolved = new URL(url, `${baseURL}/`)
      return resolved.pathname.startsWith('/api/') ? resolved.pathname : null
    } catch {
      return null
    }
  }

  return null
}

function attachAxiosTracking(client: AxiosInstance): void {
  client.interceptors.request.use((config) => {
    const trackedUrl = normalizeApiUrl(config.url, config.baseURL)
    if (trackedUrl) {
      config.metadata = {
        ...config.metadata,
        startedAt: performance.now(),
        trackedUrl,
      }
    }

    return config
  })

  client.interceptors.response.use(
    (response) => {
      const metadata = response.config.metadata
      if (!metadata?.trackedUrl || metadata.startedAt == null) {
        return response
      }

      const duration = Math.round(performance.now() - metadata.startedAt)
      if (!response.status || duration > 5000) {
        pushFailure({
          url: metadata.trackedUrl,
          status: response.status,
          duration,
          timestamp: new Date().toISOString(),
        })
      }

      return response
    },
    (error: unknown) => {
      const axiosError = error as {
        config?: { metadata?: { startedAt?: number; trackedUrl?: string } }
        response?: { status?: number }
      }

      const metadata = axiosError.config?.metadata
      if (metadata?.trackedUrl) {
        const duration = Math.round(performance.now() - (metadata.startedAt ?? performance.now()))
        pushFailure({
          url: metadata.trackedUrl,
          status: axiosError.response?.status ?? 0,
          duration,
          timestamp: new Date().toISOString(),
        })
      }

      return Promise.reject(error)
    }
  )
}

export function initApiTracker(): void {
  if (initialized) return
  initialized = true

  const originalFetch = window.fetch
  window.fetch = async function (...args: Parameters<typeof fetch>) {
    const url = typeof args[0] === 'string' ? args[0] : args[0] instanceof Request ? args[0].url : String(args[0])

    if (!url.startsWith('/api/')) return originalFetch.apply(this, args)

    const start = performance.now()
    try {
      const response = await originalFetch.apply(this, args)
      const duration = Math.round(performance.now() - start)

      if (!response.ok || duration > 5000) {
        pushFailure({
          url,
          status: response.status,
          duration,
          timestamp: new Date().toISOString(),
        })
      }

      if (response.status === 500) {
        let detail = ''
        try {
          const clone = response.clone()
          const payload = await clone.json().catch(() => null) as { detail?: string } | null
          detail = payload?.detail || ''
        } catch {
          detail = ''
        }
        promptServerErrorBugReport(url, detail)
      }

      return response
    } catch (err) {
      const duration = Math.round(performance.now() - start)
      pushFailure({
        url,
        status: 0,
        duration,
        timestamp: new Date().toISOString(),
      })
      throw err
    }
  }

  attachAxiosTracking(axios)
  attachAxiosTracking(apiClient)
}

export function getFailedRequests(): FailedRequest[] {
  return [...failures]
}
