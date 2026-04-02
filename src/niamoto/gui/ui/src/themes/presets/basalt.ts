/**
 * Basalt Theme - Cartographic Identity
 *
 * Stone gray (Tailwind stone palette) + forest green accent.
 * Sharp corners, no shadows, opaque surfaces — borders define structure.
 * Inspired by topographic maps and geological survey prints.
 *
 * Typography: Inter (clean, neutral)
 * Shapes: Zero radius — sharp, angular, utilitarian
 * Shadows: None — structure comes from borders alone
 * Effects: Fully opaque surfaces, no blur
 */

import type { Theme } from '../index'

export const basaltTheme: Theme = {
  id: 'basalt',
  name: 'Basalt',
  description: 'Cartographic theme — stone gray surfaces with sharp borders and forest green accent',
  author: 'Niamoto Team',
  inspiration: 'Topographic maps, geological surveys, volcanic stone',
  tags: ['cartographic', 'stone', 'green', 'sharp', 'opaque'],
  style: 'cartographic',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#166534',
    secondary: '#78716c',
    accent: '#4ade80',
    background: '#fafaf9',
    fontDisplay: 'Inter',
    borderRadius: '0',
  },

  light: {
    // Core — Warm off-white stone surfaces
    background: 'oklch(0.985 0.005 60)',
    foreground: 'oklch(0.18 0.01 50)',
    card: 'oklch(0.98 0.004 60)',
    cardForeground: 'oklch(0.18 0.01 50)',
    popover: 'oklch(0.98 0.004 60)',
    popoverForeground: 'oklch(0.18 0.01 50)',

    // Brand — Forest green
    primary: 'oklch(0.40 0.12 150)',
    primaryForeground: 'oklch(0.98 0.003 60)',
    secondary: 'oklch(0.92 0.008 60)',
    secondaryForeground: 'oklch(0.30 0.01 50)',

    // Neutral — Warm stone muted tones
    muted: 'oklch(0.93 0.006 60)',
    mutedForeground: 'oklch(0.55 0.01 50)',
    accent: 'oklch(0.72 0.17 150)',
    accentForeground: 'oklch(0.15 0.02 150)',

    // Semantic
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.45 0.14 150)',
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.55 0.14 240)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — Visible warm stone borders
    border: 'oklch(0.82 0.01 60)',
    input: 'oklch(0.85 0.008 60)',
    ring: 'oklch(0.40 0.12 150)',

    // Charts — Stone and green palette
    chart1: 'oklch(0.40 0.12 150)',
    chart2: 'oklch(0.55 0.01 50)',
    chart3: 'oklch(0.72 0.17 150)',
    chart4: 'oklch(0.75 0.12 85)',
    chart5: 'oklch(0.45 0.08 30)',

    // Data sources
    dataSourcePrimary: 'oklch(0.40 0.12 150)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.55 0.01 50)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Slightly cooler stone
    sidebar: 'oklch(0.96 0.005 60)',
    sidebarForeground: 'oklch(0.18 0.01 50)',
    sidebarPrimary: 'oklch(0.40 0.12 150)',
    sidebarPrimaryForeground: 'oklch(0.98 0.003 60)',
    sidebarAccent: 'oklch(0.92 0.008 60)',
    sidebarAccentForeground: 'oklch(0.30 0.01 50)',
    sidebarBorder: 'oklch(0.82 0.01 60)',
    sidebarRing: 'oklch(0.40 0.12 150)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Sharp corners, no rounding
    radiusNone: '0',
    radiusSm: '0',
    radiusMd: '0',
    radiusLg: '0',
    radiusXl: '2px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — None, borders define structure
    shadowNone: 'none',
    shadowSm: 'none',
    shadowMd: 'none',
    shadowLg: 'none',
    shadowXl: 'none',

    // Effects — Opaque surfaces, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation — Crisp, mechanical
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },

  dark: {
    // Core — Warm dark stone
    background: 'oklch(0.13 0.01 50)',
    foreground: 'oklch(0.88 0.008 60)',
    card: 'oklch(0.17 0.012 50)',
    cardForeground: 'oklch(0.88 0.008 60)',
    popover: 'oklch(0.17 0.012 50)',
    popoverForeground: 'oklch(0.88 0.008 60)',

    // Brand — Lighter green for dark mode
    primary: 'oklch(0.62 0.16 150)',
    primaryForeground: 'oklch(0.13 0.01 50)',
    secondary: 'oklch(0.22 0.01 50)',
    secondaryForeground: 'oklch(0.85 0.008 60)',

    // Neutral
    muted: 'oklch(0.22 0.008 50)',
    mutedForeground: 'oklch(0.58 0.01 50)',
    accent: 'oklch(0.72 0.15 150)',
    accentForeground: 'oklch(0.13 0.01 50)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.13 0 0)',
    success: 'oklch(0.62 0.16 150)',
    successForeground: 'oklch(0.13 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.13 0.04 85)',
    info: 'oklch(0.62 0.14 240)',
    infoForeground: 'oklch(0.13 0 0)',

    // Boundaries — Visible warm stone borders
    border: 'oklch(0.30 0.01 50)',
    input: 'oklch(0.25 0.01 50)',
    ring: 'oklch(0.62 0.16 150)',

    // Charts
    chart1: 'oklch(0.62 0.16 150)',
    chart2: 'oklch(0.60 0.01 50)',
    chart3: 'oklch(0.72 0.15 150)',
    chart4: 'oklch(0.80 0.12 85)',
    chart5: 'oklch(0.55 0.08 30)',

    // Data sources
    dataSourcePrimary: 'oklch(0.62 0.16 150)',
    dataSourcePrimaryForeground: 'oklch(0.13 0 0)',
    dataSourceSecondary: 'oklch(0.60 0.01 50)',
    dataSourceSecondaryForeground: 'oklch(0.13 0 0)',

    // Sidebar
    sidebar: 'oklch(0.15 0.01 50)',
    sidebarForeground: 'oklch(0.88 0.008 60)',
    sidebarPrimary: 'oklch(0.62 0.16 150)',
    sidebarPrimaryForeground: 'oklch(0.13 0.01 50)',
    sidebarAccent: 'oklch(0.22 0.01 50)',
    sidebarAccentForeground: 'oklch(0.85 0.008 60)',
    sidebarBorder: 'oklch(0.28 0.01 50)',
    sidebarRing: 'oklch(0.62 0.16 150)',

    // Typography
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '0',
    radiusMd: '0',
    radiusLg: '0',
    radiusXl: '2px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — None
    shadowNone: 'none',
    shadowSm: 'none',
    shadowMd: 'none',
    shadowLg: 'none',
    shadowXl: 'none',

    // Effects — Opaque surfaces, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },
}
