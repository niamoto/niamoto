/**
 * Mist Theme - Vitreous Identity
 *
 * Zero visible borders, layered transparency, fading gradient separators.
 * Softer and more ethereal than Frost — weaker boundaries, near-imperceptible
 * shadows, translucent surfaces with generous backdrop blur.
 *
 * Accent: blue-gray #3b82f6 (primary), slate #64748b (secondary)
 * Typography: Inter (clean, neutral)
 * Shapes: Refined radius (7px), near-invisible borders (0.03-0.04 alpha)
 * Shadows: Ultra-light, near imperceptible
 * Effects: High translucency (0.55 opacity, 10px blur)
 */

import type { Theme } from '../index'

export const mistTheme: Theme = {
  id: 'mist',
  name: 'Mist',
  description: 'Vitreous theme — zero borders, layered transparency, ethereal surfaces',
  author: 'Niamoto Team',
  inspiration: 'Morning fog, frosted glass, vanishing boundaries',
  tags: ['vitreous', 'translucent', 'minimal', 'blue-gray', 'ethereal'],
  style: 'vitreous',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#3b82f6',
    secondary: '#64748b',
    accent: '#10b981',
    background: '#f0eff2',
    fontDisplay: 'Inter',
    borderRadius: '7px',
  },

  light: {
    // Core — Cool lavender-gray mist
    background: 'oklch(0.955 0.008 270)',
    foreground: 'oklch(0.18 0.01 260)',
    card: 'oklch(0.99 0.004 270)',
    cardForeground: 'oklch(0.18 0.01 260)',
    popover: 'oklch(0.99 0.004 270)',
    popoverForeground: 'oklch(0.18 0.01 260)',

    // Brand — Blue-gray primary
    primary: 'oklch(0.59 0.16 260)',
    primaryForeground: 'oklch(0.98 0.003 260)',
    secondary: 'oklch(0.93 0.008 260)',
    secondaryForeground: 'oklch(0.35 0.02 260)',

    // Neutral — Slate-tinted muted tones
    muted: 'oklch(0.93 0.006 260)',
    mutedForeground: 'oklch(0.52 0.015 260)',
    accent: 'oklch(0.62 0.14 165)',
    accentForeground: 'oklch(0.98 0 0)',

    // Semantic
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.55 0.14 165)',
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.59 0.16 260)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — Near-invisible, ghostly
    border: 'oklch(0.88 0.006 260 / 0.04)',
    input: 'oklch(0.92 0.006 260)',
    ring: 'oklch(0.59 0.16 260)',

    // Charts — Blue-gray palette
    chart1: 'oklch(0.59 0.16 260)',
    chart2: 'oklch(0.55 0.10 220)',
    chart3: 'oklch(0.62 0.14 165)',
    chart4: 'oklch(0.78 0.14 85)',
    chart5: 'oklch(0.52 0.10 300)',

    // Data sources
    dataSourcePrimary: 'oklch(0.59 0.16 260)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.52 0.06 250)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Barely-there tint
    sidebar: 'oklch(0.88 0.010 260)',
    sidebarForeground: 'oklch(0.18 0.01 260)',
    sidebarPrimary: 'oklch(0.59 0.16 260)',
    sidebarPrimaryForeground: 'oklch(0.98 0.003 260)',
    sidebarAccent: 'oklch(0.92 0.008 260)',
    sidebarAccentForeground: 'oklch(0.35 0.02 260)',
    sidebarBorder: 'oklch(0.82 0.008 260)',
    sidebarRing: 'oklch(0.59 0.16 260)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Refined, smooth
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '7px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Ultra-light, near imperceptible
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0.50 0.02 260 / 0.02)',
    shadowMd: '0 3px 8px oklch(0.50 0.02 260 / 0.03)',
    shadowLg: '0 6px 18px oklch(0.50 0.02 260 / 0.04)',
    shadowXl: '0 12px 32px oklch(0.50 0.02 260 / 0.05)',

    // Effects — Translucent, misty surfaces
    backdropBlur: '10px',
    surfaceOpacity: '0.55',

    // Animation — Smooth, gentle
    transitionFast: '120ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core — Deep charcoal gradient feel
    background: 'oklch(0.14 0.01 260)',
    foreground: 'oklch(0.88 0.008 260)',
    card: 'oklch(0.18 0.012 260)',
    cardForeground: 'oklch(0.88 0.008 260)',
    popover: 'oklch(0.18 0.012 260)',
    popoverForeground: 'oklch(0.88 0.008 260)',

    // Brand — Lighter blue-gray for dark mode
    primary: 'oklch(0.68 0.16 260)',
    primaryForeground: 'oklch(0.14 0.01 260)',
    secondary: 'oklch(0.22 0.015 260)',
    secondaryForeground: 'oklch(0.85 0.008 260)',

    // Neutral
    muted: 'oklch(0.22 0.012 260)',
    mutedForeground: 'oklch(0.58 0.015 260)',
    accent: 'oklch(0.68 0.14 165)',
    accentForeground: 'oklch(0.14 0 0)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.14 0 0)',
    success: 'oklch(0.65 0.14 165)',
    successForeground: 'oklch(0.14 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.14 0.04 85)',
    info: 'oklch(0.68 0.16 260)',
    infoForeground: 'oklch(0.14 0 0)',

    // Boundaries — Ghostly, near-zero visibility
    border: 'oklch(0.30 0.01 260 / 0.04)',
    input: 'oklch(0.25 0.012 260)',
    ring: 'oklch(0.68 0.16 260)',

    // Charts
    chart1: 'oklch(0.68 0.16 260)',
    chart2: 'oklch(0.62 0.10 220)',
    chart3: 'oklch(0.68 0.14 165)',
    chart4: 'oklch(0.82 0.14 85)',
    chart5: 'oklch(0.60 0.10 300)',

    // Data sources
    dataSourcePrimary: 'oklch(0.68 0.16 260)',
    dataSourcePrimaryForeground: 'oklch(0.14 0 0)',
    dataSourceSecondary: 'oklch(0.58 0.06 250)',
    dataSourceSecondaryForeground: 'oklch(0.14 0 0)',

    // Sidebar
    sidebar: 'oklch(0.11 0.015 260)',
    sidebarForeground: 'oklch(0.88 0.008 260)',
    sidebarPrimary: 'oklch(0.68 0.16 260)',
    sidebarPrimaryForeground: 'oklch(0.14 0.01 260)',
    sidebarAccent: 'oklch(0.22 0.015 260)',
    sidebarAccentForeground: 'oklch(0.85 0.008 260)',
    sidebarBorder: 'oklch(0.18 0.010 260)',
    sidebarRing: 'oklch(0.68 0.16 260)',

    // Typography
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '7px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Barely-there glow in dark
    shadowNone: 'none',
    shadowSm: '0 2px 4px oklch(0 0 0 / 0.18)',
    shadowMd: '0 4px 12px oklch(0 0 0 / 0.22)',
    shadowLg: '0 8px 24px oklch(0 0 0 / 0.26)',
    shadowXl: '0 16px 40px oklch(0 0 0 / 0.30)',

    // Effects
    backdropBlur: '10px',
    surfaceOpacity: '0.55',

    // Animation
    transitionFast: '120ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
