/**
 * Slate Theme - Minimal Tool Identity
 *
 * Monochrome, compact, sharp — the tool that disappears.
 * Blue-slate accent on neutral gray surfaces, opaque with micro shadows.
 * Designed to stay out of the way and let data speak.
 *
 * Typography: Inter (clean, invisible) + JetBrains Mono
 * Shapes: Tight radius (4-5px), subtle borders
 * Shadows: Micro, neutral gray — no color tint
 * Effects: Fully opaque surfaces, no blur
 */

import type { Theme } from '../index'

export const slateTheme: Theme = {
  id: 'slate',
  name: 'Slate',
  description: 'Monochrome minimal theme — compact, sharp, disappears into the background',
  author: 'Niamoto Team',
  inspiration: 'Utility-first tools: terminal UIs, IDE sidebars, data dashboards',
  tags: ['minimal', 'monochrome', 'compact', 'sharp', 'tool'],
  style: 'minimal',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#0f172a',
    secondary: '#64748b',
    accent: '#3b82f6',
    background: '#f8f8fa',
    fontDisplay: 'Inter',
    borderRadius: '4px',
  },

  light: {
    // Core — Cool neutral surfaces
    background: 'oklch(0.98 0.002 265)',
    foreground: 'oklch(0.13 0.02 260)',
    card: 'oklch(1.00 0 0)',
    cardForeground: 'oklch(0.13 0.02 260)',
    popover: 'oklch(1.00 0 0)',
    popoverForeground: 'oklch(0.13 0.02 260)',

    // Brand — Deep slate primary
    primary: 'oklch(0.20 0.02 260)',
    primaryForeground: 'oklch(0.98 0 0)',
    secondary: 'oklch(0.95 0.004 265)',
    secondaryForeground: 'oklch(0.30 0.015 260)',

    // Neutral — Pure gray muted tones
    muted: 'oklch(0.95 0.004 265)',
    mutedForeground: 'oklch(0.55 0.01 260)',
    accent: 'oklch(0.60 0.16 255)',
    accentForeground: 'oklch(0.98 0 0)',

    // Semantic
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.52 0.14 152)',
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.60 0.16 255)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — Subtle, near-invisible
    border: 'oklch(0.88 0.004 265 / 0.7)',
    input: 'oklch(0.91 0.004 265)',
    ring: 'oklch(0.60 0.16 255)',

    // Charts — Slate-blue monochrome palette
    chart1: 'oklch(0.60 0.16 255)',
    chart2: 'oklch(0.45 0.12 260)',
    chart3: 'oklch(0.55 0.08 265)',
    chart4: 'oklch(0.72 0.10 250)',
    chart5: 'oklch(0.35 0.06 260)',

    // Data sources
    dataSourcePrimary: 'oklch(0.60 0.16 255)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.45 0.12 260)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Barely tinted neutral
    sidebar: 'oklch(0.91 0.002 265)',
    sidebarForeground: 'oklch(0.13 0.02 260)',
    sidebarPrimary: 'oklch(0.20 0.02 260)',
    sidebarPrimaryForeground: 'oklch(0.98 0 0)',
    sidebarAccent: 'oklch(0.94 0.004 265)',
    sidebarAccentForeground: 'oklch(0.30 0.015 260)',
    sidebarBorder: 'oklch(0.85 0.003 265)',
    sidebarRing: 'oklch(0.60 0.16 255)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Tight, compact
    radiusNone: '0',
    radiusSm: '3px',
    radiusMd: '4px',
    radiusLg: '5px',
    radiusXl: '8px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Micro, neutral gray
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0.20 0 0 / 0.04)',
    shadowMd: '0 2px 6px oklch(0.20 0 0 / 0.06)',
    shadowLg: '0 4px 12px oklch(0.20 0 0 / 0.08)',
    shadowXl: '0 8px 24px oklch(0.20 0 0 / 0.10)',

    // Effects — Opaque, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation — Snappy
    transitionFast: '100ms',
    transitionBase: '150ms',
    transitionSlow: '250ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core — Pure dark grays, no color tint
    background: 'oklch(0.13 0.005 265)',
    foreground: 'oklch(0.90 0.005 265)',
    card: 'oklch(0.17 0.005 265)',
    cardForeground: 'oklch(0.90 0.005 265)',
    popover: 'oklch(0.17 0.005 265)',
    popoverForeground: 'oklch(0.90 0.005 265)',

    // Brand — Lighter slate for dark mode
    primary: 'oklch(0.90 0.005 265)',
    primaryForeground: 'oklch(0.13 0.005 265)',
    secondary: 'oklch(0.22 0.005 265)',
    secondaryForeground: 'oklch(0.85 0.005 265)',

    // Neutral
    muted: 'oklch(0.22 0.005 265)',
    mutedForeground: 'oklch(0.58 0.008 265)',
    accent: 'oklch(0.65 0.16 255)',
    accentForeground: 'oklch(0.13 0 0)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.13 0 0)',
    success: 'oklch(0.62 0.14 152)',
    successForeground: 'oklch(0.13 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.13 0.04 85)',
    info: 'oklch(0.65 0.16 255)',
    infoForeground: 'oklch(0.13 0 0)',

    // Boundaries
    border: 'oklch(0.28 0.005 265 / 0.7)',
    input: 'oklch(0.24 0.005 265)',
    ring: 'oklch(0.65 0.16 255)',

    // Charts
    chart1: 'oklch(0.65 0.16 255)',
    chart2: 'oklch(0.52 0.12 260)',
    chart3: 'oklch(0.60 0.08 265)',
    chart4: 'oklch(0.75 0.10 250)',
    chart5: 'oklch(0.42 0.06 260)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.16 255)',
    dataSourcePrimaryForeground: 'oklch(0.13 0 0)',
    dataSourceSecondary: 'oklch(0.52 0.12 260)',
    dataSourceSecondaryForeground: 'oklch(0.13 0 0)',

    // Sidebar
    sidebar: 'oklch(0.09 0.005 265)',
    sidebarForeground: 'oklch(0.90 0.005 265)',
    sidebarPrimary: 'oklch(0.90 0.005 265)',
    sidebarPrimaryForeground: 'oklch(0.13 0.005 265)',
    sidebarAccent: 'oklch(0.22 0.005 265)',
    sidebarAccentForeground: 'oklch(0.85 0.005 265)',
    sidebarBorder: 'oklch(0.15 0.005 265)',
    sidebarRing: 'oklch(0.65 0.16 255)',

    // Typography
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '3px',
    radiusMd: '4px',
    radiusLg: '5px',
    radiusXl: '8px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Pure dark, no color glow
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0 0 0 / 0.30)',
    shadowMd: '0 3px 8px oklch(0 0 0 / 0.35)',
    shadowLg: '0 6px 16px oklch(0 0 0 / 0.40)',
    shadowXl: '0 12px 32px oklch(0 0 0 / 0.45)',

    // Effects — Opaque, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '150ms',
    transitionSlow: '250ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
