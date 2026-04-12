/**
 * Frond Theme - Brand Identity
 *
 * Derived from the Niamoto logo: charcoal N (#1E1E22), forest green
 * (#2E7D32 / #4BAF50), and ocean-blue wave (#3FA9F5).
 * Neutral base surfaces let the brand colors speak as accents.
 *
 * Typography: Plus Jakarta Sans (modern geometric, warm)
 * Shapes: Refined radius (6-7px), near-invisible borders
 * Shadows: Neutral, layered
 * Effects: Translucent surfaces with subtle blur
 */

import type { Theme } from '../index'

export const frondTheme: Theme = {
  id: 'frond',
  name: 'Frond',
  description: 'Niamoto brand theme — logo colors on neutral translucent surfaces',
  author: 'Niamoto Team',
  inspiration: 'Niamoto logo: charcoal N, forest green, ocean-blue wave',
  tags: ['brand', 'translucent', 'green', 'blue', 'ecological'],
  style: 'brand',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#2E7D32',
    secondary: '#5b86b0',
    accent: '#4BAF50',
    background: '#f5f6f8',
    fontDisplay: 'Plus Jakarta Sans',
    borderRadius: '7px',
  },

  light: {
    // Core — Neutral base, not green-tinted
    background: 'oklch(0.97 0.003 250)',
    foreground: 'oklch(0.16 0.005 270)',
    card: 'oklch(0.995 0.002 250)',
    cardForeground: 'oklch(0.16 0.005 270)',
    popover: 'oklch(0.995 0.002 250)',
    popoverForeground: 'oklch(0.16 0.005 270)',

    // Brand — Logo dark green #2E7D32
    primary: 'oklch(0.48 0.14 150)',
    primaryForeground: 'oklch(0.98 0 0)',
    secondary: 'oklch(0.94 0.008 250)',
    secondaryForeground: 'oklch(0.25 0.02 270)',

    // Neutral — Clean, not green-tinted
    muted: 'oklch(0.94 0.005 250)',
    mutedForeground: 'oklch(0.50 0.01 250)',
    accent: 'oklch(0.58 0.10 245)',  // Muted steel blue (logo reference)
    accentForeground: 'oklch(0.98 0 0)',

    // Semantic
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.64 0.16 145)',  // Logo light green #4BAF50
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.58 0.10 245)',  // Steel blue
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — Neutral, near-invisible
    border: 'oklch(0.88 0.005 250 / 0.6)',
    input: 'oklch(0.90 0.005 250)',
    ring: 'oklch(0.48 0.14 150)',

    // Charts — Logo palette
    chart1: 'oklch(0.48 0.14 150)',  // Dark green
    chart2: 'oklch(0.58 0.10 245)',  // Steel blue
    chart3: 'oklch(0.64 0.16 145)',  // Light green
    chart4: 'oklch(0.78 0.14 85)',   // Warm accent
    chart5: 'oklch(0.50 0.10 280)',  // Purple complement

    // Data sources
    dataSourcePrimary: 'oklch(0.58 0.10 245)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.48 0.14 150)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Neutral with green accent
    sidebar: 'oklch(0.96 0.004 250)',
    sidebarForeground: 'oklch(0.16 0.005 270)',
    sidebarPrimary: 'oklch(0.48 0.14 150)',
    sidebarPrimaryForeground: 'oklch(0.98 0 0)',
    sidebarAccent: 'oklch(0.93 0.005 250)',
    sidebarAccentForeground: 'oklch(0.25 0.02 270)',
    sidebarBorder: 'oklch(0.84 0.006 250)',
    sidebarRing: 'oklch(0.48 0.14 150)',

    // Typography — Inter everywhere
    fontDisplay: '"Plus Jakarta Sans", system-ui, sans-serif',
    fontBody: '"Plus Jakarta Sans", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Refined, not playful
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '7px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Neutral, layered
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0.20 0.01 250 / 0.05), 0 0 0 1px oklch(0.20 0.01 250 / 0.02)',
    shadowMd: '0 4px 12px oklch(0.20 0.01 250 / 0.07), 0 0 0 1px oklch(0.20 0.01 250 / 0.02)',
    shadowLg: '0 8px 24px oklch(0.20 0.01 250 / 0.09), 0 0 0 1px oklch(0.20 0.01 250 / 0.02)',
    shadowXl: '0 16px 40px oklch(0.20 0.01 250 / 0.11), 0 0 0 1px oklch(0.20 0.01 250 / 0.02)',

    // Effects — Translucent surfaces
    backdropBlur: '8px',
    surfaceOpacity: '0.55',

    // Animation — Smooth, natural
    transitionFast: '120ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core — Logo charcoal #1E1E22 as reference
    background: 'oklch(0.14 0.008 270)',
    foreground: 'oklch(0.92 0.005 250)',
    card: 'oklch(0.18 0.01 270)',
    cardForeground: 'oklch(0.92 0.005 250)',
    popover: 'oklch(0.18 0.01 270)',
    popoverForeground: 'oklch(0.92 0.005 250)',

    // Brand — Logo light green for dark mode
    primary: 'oklch(0.64 0.16 145)',
    primaryForeground: 'oklch(0.14 0.008 270)',
    secondary: 'oklch(0.22 0.012 270)',
    secondaryForeground: 'oklch(0.88 0.005 250)',

    // Neutral
    muted: 'oklch(0.22 0.01 270)',
    mutedForeground: 'oklch(0.60 0.01 250)',
    accent: 'oklch(0.65 0.12 245)',  // Steel blue, brighter
    accentForeground: 'oklch(0.14 0 0)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.14 0 0)',
    success: 'oklch(0.68 0.16 145)',
    successForeground: 'oklch(0.14 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.14 0.04 85)',
    info: 'oklch(0.65 0.12 245)',
    infoForeground: 'oklch(0.14 0 0)',

    // Boundaries
    border: 'oklch(0.30 0.008 270 / 0.6)',
    input: 'oklch(0.25 0.01 270)',
    ring: 'oklch(0.64 0.16 145)',

    // Charts
    chart1: 'oklch(0.64 0.16 145)',
    chart2: 'oklch(0.65 0.12 245)',
    chart3: 'oklch(0.68 0.14 145)',
    chart4: 'oklch(0.82 0.14 85)',
    chart5: 'oklch(0.60 0.10 280)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.12 245)',
    dataSourcePrimaryForeground: 'oklch(0.14 0 0)',
    dataSourceSecondary: 'oklch(0.64 0.16 145)',
    dataSourceSecondaryForeground: 'oklch(0.14 0 0)',

    // Sidebar — Darker charcoal
    sidebar: 'oklch(0.11 0.008 270)',
    sidebarForeground: 'oklch(0.92 0.005 250)',
    sidebarPrimary: 'oklch(0.64 0.16 145)',
    sidebarPrimaryForeground: 'oklch(0.14 0.008 270)',
    sidebarAccent: 'oklch(0.22 0.012 270)',
    sidebarAccentForeground: 'oklch(0.88 0.005 250)',
    sidebarBorder: 'oklch(0.20 0.008 270)',
    sidebarRing: 'oklch(0.64 0.16 145)',

    // Typography
    fontDisplay: '"Plus Jakarta Sans", system-ui, sans-serif',
    fontBody: '"Plus Jakarta Sans", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '7px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Subtle green glow accent on dark
    shadowNone: 'none',
    shadowSm: '0 2px 6px oklch(0 0 0 / 0.25), 0 0 1px oklch(0.64 0.08 145 / 0.06)',
    shadowMd: '0 4px 16px oklch(0 0 0 / 0.30), 0 0 2px oklch(0.64 0.08 145 / 0.06)',
    shadowLg: '0 8px 32px oklch(0 0 0 / 0.35), 0 0 4px oklch(0.64 0.08 145 / 0.06)',
    shadowXl: '0 16px 48px oklch(0 0 0 / 0.40), 0 0 8px oklch(0.64 0.08 145 / 0.08)',

    // Effects
    backdropBlur: '8px',
    surfaceOpacity: '0.55',

    // Animation
    transitionFast: '120ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
