/**
 * Tidal Theme - Cartographic Identity
 *
 * Nautical chart aesthetic with a blue-slate palette and dot-grid pattern.
 * Sharp corners evoke table cells on navigational maps; borders define
 * structure instead of shadows. Opaque surfaces, no blur.
 *
 * Typography: Inter (clean, legible at small scales)
 * Shapes: All zero radius — cartographic table-cell look
 * Shadows: None — borders carry all structural weight
 * Effects: Fully opaque surfaces, no backdrop blur
 */

import type { Theme } from '../index'

export const tidalTheme: Theme = {
  id: 'tidal',
  name: 'Tidal',
  description: 'Nautical chart theme — sharp edges, blue-slate palette, dot-grid ready',
  author: 'Niamoto Team',
  inspiration: 'Navigational charts, bathymetric maps, maritime cartography',
  tags: ['cartographic', 'nautical', 'teal', 'sharp', 'structured'],
  style: 'cartographic',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#0e7490',
    secondary: '#64748b',
    accent: '#22d3ee',
    background: '#f7f9fb',
    fontDisplay: 'Inter',
    borderRadius: '0',
  },

  light: {
    // Core — Cool blue-grey atmosphere, chart paper feel
    background: 'oklch(0.97 0.006 230)',
    foreground: 'oklch(0.18 0.02 240)',
    card: 'oklch(0.99 0.004 230)',
    cardForeground: 'oklch(0.18 0.02 240)',
    popover: 'oklch(0.99 0.004 230)',
    popoverForeground: 'oklch(0.18 0.02 240)',

    // Brand — Teal from nautical charts
    primary: 'oklch(0.49 0.13 200)',
    primaryForeground: 'oklch(0.98 0.004 230)',
    secondary: 'oklch(0.93 0.01 240)',
    secondaryForeground: 'oklch(0.35 0.03 240)',

    // Neutral — Slate-tinted muted tones
    muted: 'oklch(0.93 0.008 240)',
    mutedForeground: 'oklch(0.52 0.02 240)',
    accent: 'oklch(0.75 0.14 195)',  // Cyan highlight
    accentForeground: 'oklch(0.15 0.02 240)',

    // Semantic
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.52 0.14 165)',
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.49 0.13 200)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — Visible, structural
    border: 'oklch(0.85 0.012 240)',
    input: 'oklch(0.88 0.01 240)',
    ring: 'oklch(0.49 0.13 200)',

    // Charts — Maritime palette
    chart1: 'oklch(0.49 0.13 200)',  // Deep teal
    chart2: 'oklch(0.55 0.10 250)',  // Steel blue
    chart3: 'oklch(0.75 0.14 195)',  // Cyan
    chart4: 'oklch(0.78 0.14 85)',   // Warm sand
    chart5: 'oklch(0.50 0.10 310)',  // Dusk purple

    // Data sources
    dataSourcePrimary: 'oklch(0.49 0.13 200)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.55 0.10 250)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Slightly cooler than background
    sidebar: 'oklch(0.95 0.008 240)',
    sidebarForeground: 'oklch(0.18 0.02 240)',
    sidebarPrimary: 'oklch(0.49 0.13 200)',
    sidebarPrimaryForeground: 'oklch(0.98 0.004 230)',
    sidebarAccent: 'oklch(0.91 0.01 240)',
    sidebarAccentForeground: 'oklch(0.35 0.03 240)',
    sidebarBorder: 'oklch(0.85 0.012 240)',
    sidebarRing: 'oklch(0.49 0.13 200)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Sharp, cartographic
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

    // Animation — Precise, snappy
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core — Deep navy, ink-on-chart feel
    background: 'oklch(0.16 0.03 240)',
    foreground: 'oklch(0.90 0.01 230)',
    card: 'oklch(0.20 0.035 240)',
    cardForeground: 'oklch(0.90 0.01 230)',
    popover: 'oklch(0.20 0.035 240)',
    popoverForeground: 'oklch(0.90 0.01 230)',

    // Brand — Cyan accent for dark mode
    primary: 'oklch(0.72 0.15 195)',
    primaryForeground: 'oklch(0.16 0.03 240)',
    secondary: 'oklch(0.24 0.025 240)',
    secondaryForeground: 'oklch(0.88 0.01 230)',

    // Neutral
    muted: 'oklch(0.24 0.02 240)',
    mutedForeground: 'oklch(0.60 0.015 230)',
    accent: 'oklch(0.72 0.15 195)',  // Bright cyan
    accentForeground: 'oklch(0.16 0.03 240)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.16 0 0)',
    success: 'oklch(0.62 0.14 165)',
    successForeground: 'oklch(0.16 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.16 0.04 85)',
    info: 'oklch(0.72 0.15 195)',
    infoForeground: 'oklch(0.16 0 0)',

    // Boundaries — Visible on dark
    border: 'oklch(0.32 0.025 240)',
    input: 'oklch(0.28 0.03 240)',
    ring: 'oklch(0.72 0.15 195)',

    // Charts
    chart1: 'oklch(0.72 0.15 195)',  // Cyan
    chart2: 'oklch(0.62 0.10 250)',  // Steel blue
    chart3: 'oklch(0.65 0.13 200)',  // Teal
    chart4: 'oklch(0.82 0.14 85)',   // Sand
    chart5: 'oklch(0.60 0.10 310)',  // Dusk purple

    // Data sources
    dataSourcePrimary: 'oklch(0.72 0.15 195)',
    dataSourcePrimaryForeground: 'oklch(0.16 0 0)',
    dataSourceSecondary: 'oklch(0.62 0.10 250)',
    dataSourceSecondaryForeground: 'oklch(0.16 0 0)',

    // Sidebar
    sidebar: 'oklch(0.18 0.035 240)',
    sidebarForeground: 'oklch(0.90 0.01 230)',
    sidebarPrimary: 'oklch(0.72 0.15 195)',
    sidebarPrimaryForeground: 'oklch(0.16 0.03 240)',
    sidebarAccent: 'oklch(0.24 0.025 240)',
    sidebarAccentForeground: 'oklch(0.88 0.01 230)',
    sidebarBorder: 'oklch(0.30 0.025 240)',
    sidebarRing: 'oklch(0.72 0.15 195)',

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

    // Effects
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
