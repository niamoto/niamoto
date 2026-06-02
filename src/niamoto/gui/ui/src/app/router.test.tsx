import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

const { capturedRoutes } = vi.hoisted(() => ({
  capturedRoutes: [] as Array<Record<string, unknown>>,
}))

vi.mock('react-router-dom', () => ({
  createBrowserRouter: vi.fn((routes: Array<Record<string, unknown>>) => {
    capturedRoutes.splice(0, capturedRoutes.length, ...routes)
    return { routes }
  }),
  Navigate: () => null,
  RouterProvider: () => null,
}))

vi.mock('@/components/layout/MainLayout', () => ({
  MainLayout: () => null,
}))

vi.mock('@/features/dashboard/views/ProjectHub', () => ({
  default: () => null,
}))

await import('./router')

describe('app router bootstrap', () => {
  it('provides a hydration fallback for lazy route startup', () => {
    expect(capturedRoutes[0]).toMatchObject({ path: '/' })
    expect(capturedRoutes[0].hydrateFallbackElement).toBeDefined()
  })

  it('does not eagerly preload route-dependent font files', () => {
    const indexHtml = readFileSync(resolve(__dirname, '../../index.html'), 'utf-8')

    expect(indexHtml).not.toMatch(/rel="preload"[^>]+as="font"/)
  })
})
