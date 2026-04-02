/**
 * Frond Theme - Brand Identity
 *
 * Fusion of the Mist style (translucent surfaces, backdrop blur, glowing dots)
 * with Niamoto logo colors: charcoal #2a2a2a, forest green #2d7a3a,
 * ocean blue #2d8fcf, cyan #4bb8d4.
 *
 * Typography: Inter (clean, professional)
 * Shapes: Refined radius (6-7px), near-invisible borders
 * Shadows: Green-tinted, layered
 * Effects: Translucent surfaces with subtle blur
 */

import type { Theme } from '../index'

export const frondTheme: Theme = {
  id: 'frond',
  name: 'Frond',
  description: 'Niamoto brand theme — translucent surfaces with logo colors',
  author: 'Niamoto Team',
  inspiration: 'Niamoto logo: fern, forest, ocean waves',
  tags: ['brand', 'translucent', 'green', 'blue', 'ecological'],
  style: 'brand',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#2d7a3a',
    secondary: '#2d8fcf',
    accent: '#4bb8d4',
    background: '#eef3ee',
    fontDisplay: 'Inter',
    borderRadius: '7px',
  },

  light: {
    // Core — Soft green-tinted atmosphere
    background: 'oklch(0.96 0.012 150)',
    foreground: 'oklch(0.20 0.02 150)',
    card: 'oklch(0.99 0.005 150)',
    cardForeground: 'oklch(0.20 0.02 150)',
    popover: 'oklch(0.99 0.005 150)',
    popoverForeground: 'oklch(0.20 0.02 150)',

    // Brand — Forest green from logo
    primary: 'oklch(0.47 0.12 152)',
    primaryForeground: 'oklch(0.98 0.005 150)',
    secondary: 'oklch(0.94 0.018 150)',
    secondaryForeground: 'oklch(0.25 0.04 150)',

    // Neutral — Green-tinted muted tones
    muted: 'oklch(0.94 0.012 150)',
    mutedForeground: 'oklch(0.50 0.02 150)',
    accent: 'oklch(0.60 0.12 230)',  // Ocean blue from logo
    accentForeground: 'oklch(0.98 0 0)',

    // Semantic
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.50 0.14 152)',
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.58 0.14 230)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — Near-invisible, green-tinted
    border: 'oklch(0.90 0.01 150 / 0.6)',
    input: 'oklch(0.90 0.012 150)',
    ring: 'oklch(0.47 0.12 152)',

    // Charts — Logo palette
    chart1: 'oklch(0.47 0.12 152)',  // Forest green
    chart2: 'oklch(0.58 0.14 230)',  // Ocean blue
    chart3: 'oklch(0.62 0.12 195)',  // Cyan/teal
    chart4: 'oklch(0.78 0.14 85)',   // Warm accent
    chart5: 'oklch(0.50 0.10 280)',  // Complementary purple

    // Data sources
    dataSourcePrimary: 'oklch(0.58 0.14 230)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.47 0.12 152)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Subtle green tint
    sidebar: 'oklch(0.95 0.010 150)',
    sidebarForeground: 'oklch(0.20 0.02 150)',
    sidebarPrimary: 'oklch(0.47 0.12 152)',
    sidebarPrimaryForeground: 'oklch(0.98 0.005 150)',
    sidebarAccent: 'oklch(0.92 0.015 150)',
    sidebarAccentForeground: 'oklch(0.25 0.04 150)',
    sidebarBorder: 'oklch(0.90 0.01 150 / 0.5)',
    sidebarRing: 'oklch(0.47 0.12 152)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Refined, not playful
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '7px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Green-tinted, layered
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0.47 0.06 152 / 0.04), 0 0 0 1px oklch(0.47 0.06 152 / 0.02)',
    shadowMd: '0 4px 12px oklch(0.47 0.06 152 / 0.06), 0 0 0 1px oklch(0.47 0.06 152 / 0.02)',
    shadowLg: '0 8px 24px oklch(0.47 0.06 152 / 0.08), 0 0 0 1px oklch(0.47 0.06 152 / 0.02)',
    shadowXl: '0 16px 40px oklch(0.47 0.06 152 / 0.10), 0 0 0 1px oklch(0.47 0.06 152 / 0.02)',

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
    // Core — Deep forest night with green undertone
    background: 'oklch(0.13 0.02 150)',
    foreground: 'oklch(0.90 0.015 150)',
    card: 'oklch(0.17 0.025 150)',
    cardForeground: 'oklch(0.90 0.015 150)',
    popover: 'oklch(0.17 0.025 150)',
    popoverForeground: 'oklch(0.90 0.015 150)',

    // Brand — Lighter green for dark mode
    primary: 'oklch(0.65 0.16 152)',
    primaryForeground: 'oklch(0.13 0.02 150)',
    secondary: 'oklch(0.22 0.03 150)',
    secondaryForeground: 'oklch(0.88 0.015 150)',

    // Neutral
    muted: 'oklch(0.22 0.025 150)',
    mutedForeground: 'oklch(0.60 0.02 150)',
    accent: 'oklch(0.65 0.12 230)',  // Ocean blue lighter
    accentForeground: 'oklch(0.13 0 0)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.13 0 0)',
    success: 'oklch(0.65 0.16 152)',
    successForeground: 'oklch(0.13 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.13 0.04 85)',
    info: 'oklch(0.65 0.14 230)',
    infoForeground: 'oklch(0.13 0 0)',

    // Boundaries
    border: 'oklch(0.30 0.02 150 / 0.6)',
    input: 'oklch(0.25 0.025 150)',
    ring: 'oklch(0.65 0.16 152)',

    // Charts
    chart1: 'oklch(0.65 0.16 152)',
    chart2: 'oklch(0.65 0.14 230)',
    chart3: 'oklch(0.68 0.12 195)',
    chart4: 'oklch(0.82 0.14 85)',
    chart5: 'oklch(0.60 0.10 280)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.14 230)',
    dataSourcePrimaryForeground: 'oklch(0.13 0 0)',
    dataSourceSecondary: 'oklch(0.65 0.16 152)',
    dataSourceSecondaryForeground: 'oklch(0.13 0 0)',

    // Sidebar
    sidebar: 'oklch(0.15 0.025 150)',
    sidebarForeground: 'oklch(0.90 0.015 150)',
    sidebarPrimary: 'oklch(0.65 0.16 152)',
    sidebarPrimaryForeground: 'oklch(0.13 0.02 150)',
    sidebarAccent: 'oklch(0.22 0.03 150)',
    sidebarAccentForeground: 'oklch(0.88 0.015 150)',
    sidebarBorder: 'oklch(0.28 0.02 150 / 0.5)',
    sidebarRing: 'oklch(0.65 0.16 152)',

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

    // Shadows — Glow accents in dark
    shadowNone: 'none',
    shadowSm: '0 2px 6px oklch(0 0 0 / 0.25), 0 0 1px oklch(0.65 0.1 152 / 0.08)',
    shadowMd: '0 4px 16px oklch(0 0 0 / 0.30), 0 0 2px oklch(0.65 0.1 152 / 0.08)',
    shadowLg: '0 8px 32px oklch(0 0 0 / 0.35), 0 0 4px oklch(0.65 0.1 152 / 0.08)',
    shadowXl: '0 16px 48px oklch(0 0 0 / 0.40), 0 0 8px oklch(0.65 0.1 152 / 0.10)',

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
