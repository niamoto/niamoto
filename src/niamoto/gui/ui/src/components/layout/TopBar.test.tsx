import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { TopBar } from './TopBar'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValue?: string | Record<string, unknown>,
      options?: Record<string, unknown>
    ) => {
      if (typeof defaultValue === 'string') {
        return defaultValue.replace(/\{\{(\w+)\}\}/g, (_match, token: string) =>
          String(options?.[token] ?? '')
        )
      }
      return key
    },
  }),
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

const mockNavigationState = {
  sidebarMode: 'full',
}

vi.mock('@/stores/navigationStore', () => ({
  useNavigationStore: (selector?: (state: typeof mockNavigationState) => unknown) =>
    selector ? selector(mockNavigationState) : mockNavigationState,
}))

vi.mock('@/shared/hooks/usePlatform', () => ({
  usePlatform: () => ({ isMac: false, isDesktop: false }),
}))

vi.mock('@/shared/shell/shellActions', () => ({
  SHELL_ACTION_IDS: {
    COMMAND_PALETTE_OPEN: 'command_palette.open',
    SHELL_TOGGLE_SIDEBAR: 'shell.toggle_sidebar',
    HELP_DOCUMENTATION: 'help.documentation',
    HELP_SHORTCUTS: 'help.shortcuts',
    HELP_ABOUT: 'help.about',
  },
  useShellActionRunner: () => ({
    runShellAction: vi.fn(),
  }),
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

vi.mock('./NotificationDropdown', () => ({
  NotificationDropdown: () => <div>Notifications</div>,
}))

describe('TopBar', () => {
  it('does not render a global offline badge', () => {
    const html = renderToStaticMarkup(<TopBar />)

    expect(html).not.toContain('Offline mode')
    expect(html).not.toContain('API enrichment: unavailable')
    expect(html).toContain('Notifications')
  })
})
