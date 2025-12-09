/**
 * Field Theme - Field Naturalist's Journal
 *
 * Inspired by expedition notebooks, pressed specimens, and the
 * authentic feel of botanical fieldwork in New Caledonia.
 *
 * Typography: Caveat (handwritten notes) + Source Sans 3 (readable body)
 * Shapes: Organic, slightly irregular, softly rounded
 * Shadows: Soft, like paper pages
 * Colors: Kraft paper, blue/black ink, graphite pencil
 */

import type { Theme } from '../index'

export const fieldTheme: Theme = {
  id: 'field',
  name: 'Field',
  description: 'Authenticity of the naturalist field notebook',
  author: 'Niamoto Team',
  inspiration: 'Botanical field notebooks from New Caledonia',
  tags: ['organic', 'handwritten', 'warm', 'fieldwork'],
  style: 'organic',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Caveat:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#3d3929',
    secondary: '#7a6f5d',
    accent: '#2563eb',
    background: '#f5f0e6',
    fontDisplay: 'Caveat',
    borderRadius: '8px',
  },

  light: {
    // Core - Kraft paper warmth
    background: 'oklch(0.95 0.02 80)',
    foreground: 'oklch(0.22 0.03 70)',
    card: 'oklch(0.97 0.015 80)',
    cardForeground: 'oklch(0.22 0.03 70)',
    popover: 'oklch(0.97 0.015 80)',
    popoverForeground: 'oklch(0.22 0.03 70)',

    // Brand - Ink and pencil
    primary: 'oklch(0.28 0.04 70)',
    primaryForeground: 'oklch(0.95 0.02 80)',
    secondary: 'oklch(0.90 0.02 80)',
    secondaryForeground: 'oklch(0.28 0.04 70)',

    // Neutral - Weathered paper
    muted: 'oklch(0.92 0.015 80)',
    mutedForeground: 'oklch(0.45 0.025 70)',
    accent: 'oklch(0.55 0.20 250)',  // Blue ink
    accentForeground: 'oklch(0.97 0 0)',

    // Semantic - Natural tones
    destructive: 'oklch(0.55 0.18 25)',
    destructiveForeground: 'oklch(0.97 0 0)',
    success: 'oklch(0.50 0.12 145)',
    successForeground: 'oklch(0.97 0 0)',
    warning: 'oklch(0.72 0.14 70)',
    warningForeground: 'oklch(0.22 0.04 70)',
    info: 'oklch(0.55 0.18 250)',  // Blue ink
    infoForeground: 'oklch(0.97 0 0)',

    // Boundaries - Pencil lines
    border: 'oklch(0.82 0.02 80)',
    input: 'oklch(0.85 0.018 80)',
    ring: 'oklch(0.55 0.18 250)',

    // Charts - Field naturalist palette
    chart1: 'oklch(0.50 0.12 145)',  // Forest observation
    chart2: 'oklch(0.55 0.18 250)',  // Blue ink annotation
    chart3: 'oklch(0.55 0.10 40)',   // Earth sample
    chart4: 'oklch(0.72 0.14 70)',   // Dried specimen
    chart5: 'oklch(0.45 0.06 280)',  // Faded violet

    // Data sources
    dataSourcePrimary: 'oklch(0.55 0.18 250)',
    dataSourcePrimaryForeground: 'oklch(0.97 0 0)',
    dataSourceSecondary: 'oklch(0.50 0.12 300)',
    dataSourceSecondaryForeground: 'oklch(0.97 0 0)',

    // Sidebar - Slightly aged margin
    sidebar: 'oklch(0.93 0.02 80)',
    sidebarForeground: 'oklch(0.22 0.03 70)',
    sidebarPrimary: 'oklch(0.28 0.04 70)',
    sidebarPrimaryForeground: 'oklch(0.95 0.02 80)',
    sidebarAccent: 'oklch(0.88 0.02 80)',
    sidebarAccentForeground: 'oklch(0.28 0.04 70)',
    sidebarBorder: 'oklch(0.85 0.018 80)',
    sidebarRing: 'oklch(0.55 0.18 250)',

    // Typography - Handwritten + readable
    fontDisplay: 'Caveat, cursive',
    fontBody: '"Source Sans 3", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes - Organic, soft
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '8px',
    radiusLg: '12px',
    radiusXl: '16px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Soft, paper-like
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0.22 0.03 70 / 0.06), 0 1px 2px oklch(0.22 0.03 70 / 0.04)',
    shadowMd: '0 3px 6px oklch(0.22 0.03 70 / 0.08), 0 2px 4px oklch(0.22 0.03 70 / 0.04)',
    shadowLg: '0 6px 12px oklch(0.22 0.03 70 / 0.10), 0 3px 6px oklch(0.22 0.03 70 / 0.05)',
    shadowXl: '0 12px 24px oklch(0.22 0.03 70 / 0.12), 0 6px 12px oklch(0.22 0.03 70 / 0.06)',

    // Effects - Subtle texture feel
    backdropBlur: '4px',
    surfaceOpacity: '0.98',

    // Animation - Natural, relaxed
    transitionFast: '150ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },

  dark: {
    // Core - Aged leather notebook
    background: 'oklch(0.16 0.02 70)',
    foreground: 'oklch(0.88 0.02 80)',
    card: 'oklch(0.20 0.025 70)',
    cardForeground: 'oklch(0.88 0.02 80)',
    popover: 'oklch(0.20 0.025 70)',
    popoverForeground: 'oklch(0.88 0.02 80)',

    // Brand
    primary: 'oklch(0.85 0.025 80)',
    primaryForeground: 'oklch(0.16 0.02 70)',
    secondary: 'oklch(0.25 0.02 70)',
    secondaryForeground: 'oklch(0.82 0.02 80)',

    // Neutral
    muted: 'oklch(0.24 0.018 70)',
    mutedForeground: 'oklch(0.62 0.02 80)',
    accent: 'oklch(0.65 0.18 250)',
    accentForeground: 'oklch(0.16 0 0)',

    // Semantic
    destructive: 'oklch(0.62 0.18 25)',
    destructiveForeground: 'oklch(0.16 0 0)',
    success: 'oklch(0.60 0.12 145)',
    successForeground: 'oklch(0.16 0 0)',
    warning: 'oklch(0.78 0.14 70)',
    warningForeground: 'oklch(0.16 0.04 70)',
    info: 'oklch(0.65 0.18 250)',
    infoForeground: 'oklch(0.16 0 0)',

    // Boundaries
    border: 'oklch(0.30 0.02 70)',
    input: 'oklch(0.30 0.02 70)',
    ring: 'oklch(0.65 0.18 250)',

    // Charts
    chart1: 'oklch(0.60 0.12 145)',
    chart2: 'oklch(0.65 0.18 250)',
    chart3: 'oklch(0.62 0.10 40)',
    chart4: 'oklch(0.78 0.14 70)',
    chart5: 'oklch(0.55 0.08 280)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.18 250)',
    dataSourcePrimaryForeground: 'oklch(0.16 0 0)',
    dataSourceSecondary: 'oklch(0.60 0.12 300)',
    dataSourceSecondaryForeground: 'oklch(0.16 0 0)',

    // Sidebar
    sidebar: 'oklch(0.18 0.025 70)',
    sidebarForeground: 'oklch(0.88 0.02 80)',
    sidebarPrimary: 'oklch(0.85 0.025 80)',
    sidebarPrimaryForeground: 'oklch(0.16 0.02 70)',
    sidebarAccent: 'oklch(0.25 0.02 70)',
    sidebarAccentForeground: 'oklch(0.82 0.02 80)',
    sidebarBorder: 'oklch(0.28 0.02 70)',
    sidebarRing: 'oklch(0.65 0.18 250)',

    // Typography
    fontDisplay: 'Caveat, cursive',
    fontBody: '"Source Sans 3", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '8px',
    radiusLg: '12px',
    radiusXl: '16px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0 0 0 / 0.20)',
    shadowMd: '0 3px 6px oklch(0 0 0 / 0.25)',
    shadowLg: '0 6px 12px oklch(0 0 0 / 0.30)',
    shadowXl: '0 12px 24px oklch(0 0 0 / 0.35)',

    // Effects
    backdropBlur: '4px',
    surfaceOpacity: '0.98',

    // Animation
    transitionFast: '150ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
}
