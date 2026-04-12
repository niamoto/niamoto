/**
 * Herbier Theme - Serif Academic
 *
 * The visual language of botanical plates, scientific publications,
 * and illustrated floras. Warm ivory surfaces, sepia ink, and
 * vert-de-gris (copper patina) accents.
 *
 * Typography: Crimson Pro (display serif) + Source Serif 4 (body serif)
 * Shapes: Moderate radius (4-6px), fine visible borders
 * Shadows: Warm sepia, like layered paper
 * Effects: Opaque surfaces, no blur — crisp like print
 * Dark mode: Deep warm brown, not cold gray
 */

import type { Theme } from '../index'

export const herbierTheme: Theme = {
  id: 'herbier',
  name: 'Herbier',
  description: 'Serif academic theme — botanical plates, warm ivory, copper patina accents',
  author: 'Niamoto Team',
  inspiration: 'Botanical illustrations, scientific publications, herbarium specimens',
  tags: ['academic', 'serif', 'warm', 'ivory', 'botanical'],
  style: 'classic',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600;700&family=Source+Serif+4:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#5a8a7a',
    secondary: '#9a7a55',
    accent: '#7a8a5a',
    background: '#f5f2ec',
    fontDisplay: 'Crimson Pro',
    borderRadius: '4px',
  },

  light: {
    // Core — Warm ivory paper
    background: 'oklch(0.97 0.008 80)',
    foreground: 'oklch(0.20 0.02 55)',
    card: 'oklch(0.985 0.006 80)',
    cardForeground: 'oklch(0.20 0.02 55)',
    popover: 'oklch(0.985 0.006 80)',
    popoverForeground: 'oklch(0.20 0.02 55)',

    // Brand — Vert-de-gris (copper patina)
    primary: 'oklch(0.42 0.08 170)',
    primaryForeground: 'oklch(0.97 0.005 80)',
    secondary: 'oklch(0.93 0.01 80)',
    secondaryForeground: 'oklch(0.30 0.02 55)',

    // Neutral — Warm parchment tones
    muted: 'oklch(0.93 0.008 80)',
    mutedForeground: 'oklch(0.52 0.015 55)',
    accent: 'oklch(0.58 0.08 50)',  // Copper
    accentForeground: 'oklch(0.97 0 0)',

    // Semantic
    destructive: 'oklch(0.50 0.14 25)',
    destructiveForeground: 'oklch(0.97 0 0)',
    success: 'oklch(0.50 0.10 150)',
    successForeground: 'oklch(0.97 0 0)',
    warning: 'oklch(0.75 0.12 80)',
    warningForeground: 'oklch(0.20 0.04 80)',
    info: 'oklch(0.50 0.08 240)',
    infoForeground: 'oklch(0.97 0 0)',

    // Boundaries — Fine, warm
    border: 'oklch(0.86 0.01 80)',
    input: 'oklch(0.88 0.008 80)',
    ring: 'oklch(0.42 0.08 170)',

    // Charts — Herbarium palette
    chart1: 'oklch(0.42 0.08 170)',  // Patina green
    chart2: 'oklch(0.58 0.08 50)',   // Copper
    chart3: 'oklch(0.50 0.08 240)',  // Muted blue
    chart4: 'oklch(0.75 0.12 80)',   // Warm amber
    chart5: 'oklch(0.45 0.06 320)',  // Muted mauve

    // Data sources
    dataSourcePrimary: 'oklch(0.50 0.08 240)',
    dataSourcePrimaryForeground: 'oklch(0.97 0 0)',
    dataSourceSecondary: 'oklch(0.42 0.08 170)',
    dataSourceSecondaryForeground: 'oklch(0.97 0 0)',

    // Sidebar — Slightly darker parchment
    sidebar: 'oklch(0.96 0.01 80)',
    sidebarForeground: 'oklch(0.20 0.02 55)',
    sidebarPrimary: 'oklch(0.42 0.08 170)',
    sidebarPrimaryForeground: 'oklch(0.97 0.005 80)',
    sidebarAccent: 'oklch(0.92 0.01 80)',
    sidebarAccentForeground: 'oklch(0.30 0.02 55)',
    sidebarBorder: 'oklch(0.84 0.01 80)',
    sidebarRing: 'oklch(0.42 0.08 170)',

    // Typography — Serif pair
    fontDisplay: '"Crimson Pro", Georgia, serif',
    fontBody: '"Source Serif 4", Georgia, serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Moderate, refined
    radiusNone: '0',
    radiusSm: '3px',
    radiusMd: '4px',
    radiusLg: '6px',
    radiusXl: '8px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Warm sepia, like layered paper
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0.30 0.02 55 / 0.06), 0 0 0 1px oklch(0.30 0.02 55 / 0.03)',
    shadowMd: '0 4px 10px oklch(0.30 0.02 55 / 0.08), 0 0 0 1px oklch(0.30 0.02 55 / 0.03)',
    shadowLg: '0 8px 20px oklch(0.30 0.02 55 / 0.10), 0 0 0 1px oklch(0.30 0.02 55 / 0.03)',
    shadowXl: '0 16px 36px oklch(0.30 0.02 55 / 0.12), 0 0 0 1px oklch(0.30 0.02 55 / 0.03)',

    // Effects — Opaque, crisp like print
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation — Measured, scholarly
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },

  dark: {
    // Core — Deep warm brown, not cold gray
    background: 'oklch(0.15 0.02 55)',
    foreground: 'oklch(0.90 0.01 80)',
    card: 'oklch(0.19 0.02 55)',
    cardForeground: 'oklch(0.90 0.01 80)',
    popover: 'oklch(0.19 0.02 55)',
    popoverForeground: 'oklch(0.90 0.01 80)',

    // Brand — Lighter patina for dark mode
    primary: 'oklch(0.62 0.08 170)',
    primaryForeground: 'oklch(0.15 0.02 55)',
    secondary: 'oklch(0.23 0.015 55)',
    secondaryForeground: 'oklch(0.85 0.01 80)',

    // Neutral
    muted: 'oklch(0.23 0.012 55)',
    mutedForeground: 'oklch(0.58 0.012 55)',
    accent: 'oklch(0.68 0.08 50)',  // Lighter copper
    accentForeground: 'oklch(0.15 0 0)',

    // Semantic
    destructive: 'oklch(0.58 0.14 25)',
    destructiveForeground: 'oklch(0.15 0 0)',
    success: 'oklch(0.60 0.10 150)',
    successForeground: 'oklch(0.15 0 0)',
    warning: 'oklch(0.80 0.12 80)',
    warningForeground: 'oklch(0.15 0.04 80)',
    info: 'oklch(0.60 0.08 240)',
    infoForeground: 'oklch(0.15 0 0)',

    // Boundaries
    border: 'oklch(0.30 0.015 55)',
    input: 'oklch(0.26 0.015 55)',
    ring: 'oklch(0.62 0.08 170)',

    // Charts
    chart1: 'oklch(0.62 0.08 170)',
    chart2: 'oklch(0.68 0.08 50)',
    chart3: 'oklch(0.60 0.08 240)',
    chart4: 'oklch(0.80 0.12 80)',
    chart5: 'oklch(0.55 0.06 320)',

    // Data sources
    dataSourcePrimary: 'oklch(0.60 0.08 240)',
    dataSourcePrimaryForeground: 'oklch(0.15 0 0)',
    dataSourceSecondary: 'oklch(0.62 0.08 170)',
    dataSourceSecondaryForeground: 'oklch(0.15 0 0)',

    // Sidebar — Deeper brown
    sidebar: 'oklch(0.12 0.02 55)',
    sidebarForeground: 'oklch(0.90 0.01 80)',
    sidebarPrimary: 'oklch(0.62 0.08 170)',
    sidebarPrimaryForeground: 'oklch(0.15 0.02 55)',
    sidebarAccent: 'oklch(0.23 0.015 55)',
    sidebarAccentForeground: 'oklch(0.85 0.01 80)',
    sidebarBorder: 'oklch(0.20 0.015 55)',
    sidebarRing: 'oklch(0.62 0.08 170)',

    // Typography
    fontDisplay: '"Crimson Pro", Georgia, serif',
    fontBody: '"Source Serif 4", Georgia, serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '3px',
    radiusMd: '4px',
    radiusLg: '6px',
    radiusXl: '8px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Subtle patina glow
    shadowNone: 'none',
    shadowSm: '0 2px 4px oklch(0 0 0 / 0.25), 0 0 1px oklch(0.62 0.05 170 / 0.06)',
    shadowMd: '0 4px 12px oklch(0 0 0 / 0.30), 0 0 2px oklch(0.62 0.05 170 / 0.06)',
    shadowLg: '0 8px 24px oklch(0 0 0 / 0.35), 0 0 4px oklch(0.62 0.05 170 / 0.06)',
    shadowXl: '0 16px 40px oklch(0 0 0 / 0.40), 0 0 8px oklch(0.62 0.05 170 / 0.08)',

    // Effects
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },
}
