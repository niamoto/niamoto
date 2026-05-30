import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { ProjectSwitcher } from './ProjectSwitcher'

const switcherState = vi.hoisted(() => ({
  value: {
    currentProject: null,
    recentProjects: [],
    invalidProjects: new Set<string>(),
    loading: true,
    error: null,
    switchProject: vi.fn(),
    removeProject: vi.fn(),
    browseProject: vi.fn(),
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

vi.mock('@/shared/hooks/useProjectSwitcher', () => ({
  useProjectSwitcher: () => switcherState.value,
}))

vi.mock('@/stores/projectCreationStore', () => ({
  useProjectCreationStore: () => vi.fn(),
}))

vi.mock('@/components/ui/button', () => ({
  Button: (props: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props} />
  ),
}))

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DropdownMenuTrigger: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DropdownMenuContent: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DropdownMenuLabel: (props: { children: ReactNode }) => <div>{props.children}</div>,
  DropdownMenuSeparator: () => <div />,
  DropdownMenuItem: (props: { children: ReactNode }) => <div>{props.children}</div>,
}))

describe('ProjectSwitcher', () => {
  it('keeps a stable full-width trigger while initially loading', () => {
    const html = renderToStaticMarkup(<ProjectSwitcher />)

    expect(html).toContain('aria-busy="true"')
    expect(html).toContain('disabled=""')
    expect(html).toContain('Loading project...')
  })

  it('keeps a stable compact trigger while initially loading', () => {
    const html = renderToStaticMarkup(<ProjectSwitcher compact />)

    expect(html).toContain('aria-busy="true"')
    expect(html).toContain('disabled=""')
    expect(html).toContain('title="Loading project..."')
  })
})
