/**
 * Forest Theme - Canopy Immersion
 *
 * Deep immersion in New Caledonian endemic forest.
 * Filtered golden light through Araucaria canopy, morning mist,
 * and the calm contemplative atmosphere of pristine forest.
 *
 * Typography: Nunito (rounded, organic) + DM Sans (modern readable)
 * Shapes: Very rounded, flowing, organic
 * Shadows: Soft and diffuse, atmospheric depth
 * Colors: Deep forest greens, golden filtered light, misty atmosphere
 */

import type { Theme } from '../index'

export const forestTheme: Theme = {
  id: 'forest',
  name: 'Forest',
  description: 'Immersion in the canopy of endemic forests',
  author: 'Niamoto Team',
  inspiration: 'Araucaria forests of New Caledonia',
  tags: ['natural', 'organic', 'green', 'immersive'],
  style: 'natural',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#2d5a3d',
    secondary: '#4a7c59',
    accent: '#d4a534',
    background: '#f7faf5',
    fontDisplay: 'Nunito',
    borderRadius: '16px',
  },

  light: {
    // Core - Misty forest morning
    background: 'oklch(0.98 0.008 145)',
    foreground: 'oklch(0.18 0.04 145)',
    card: 'oklch(0.995 0.005 145)',
    cardForeground: 'oklch(0.18 0.04 145)',
    popover: 'oklch(0.995 0.005 145)',
    popoverForeground: 'oklch(0.18 0.04 145)',

    // Brand - Deep forest
    primary: 'oklch(0.42 0.12 145)',
    primaryForeground: 'oklch(0.98 0.005 145)',
    secondary: 'oklch(0.94 0.025 145)',
    secondaryForeground: 'oklch(0.25 0.06 145)',

    // Neutral - Forest atmosphere
    muted: 'oklch(0.95 0.015 145)',
    mutedForeground: 'oklch(0.45 0.03 145)',
    accent: 'oklch(0.75 0.14 85)',  // Golden sunlight
    accentForeground: 'oklch(0.20 0.05 85)',

    // Semantic - Natural indicators
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.55 0.15 145)',
    successForeground: 'oklch(0.98 0 0)',
    warning: 'oklch(0.78 0.14 85)',
    warningForeground: 'oklch(0.20 0.05 85)',
    info: 'oklch(0.55 0.12 200)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries - Soft, organic
    border: 'oklch(0.90 0.02 145)',
    input: 'oklch(0.92 0.018 145)',
    ring: 'oklch(0.55 0.12 145)',

    // Charts - Forest ecosystem palette
    chart1: 'oklch(0.42 0.12 145)',  // Deep canopy
    chart2: 'oklch(0.75 0.14 85)',   // Sunlight
    chart3: 'oklch(0.55 0.10 180)',  // Fern
    chart4: 'oklch(0.50 0.08 40)',   // Bark
    chart5: 'oklch(0.65 0.10 100)',  // Moss

    // Data sources
    dataSourcePrimary: 'oklch(0.50 0.12 200)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.55 0.12 280)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar - Forest edge
    sidebar: 'oklch(0.97 0.015 145)',
    sidebarForeground: 'oklch(0.18 0.04 145)',
    sidebarPrimary: 'oklch(0.42 0.12 145)',
    sidebarPrimaryForeground: 'oklch(0.98 0.005 145)',
    sidebarAccent: 'oklch(0.92 0.025 145)',
    sidebarAccentForeground: 'oklch(0.25 0.06 145)',
    sidebarBorder: 'oklch(0.84 0.015 145)',
    sidebarRing: 'oklch(0.55 0.12 145)',

    // Typography - Rounded, organic
    fontDisplay: 'Nunito, system-ui, sans-serif',
    fontBody: '"DM Sans", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes - Very rounded, flowing
    radiusNone: '0',
    radiusSm: '8px',
    radiusMd: '12px',
    radiusLg: '16px',
    radiusXl: '24px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Soft, atmospheric
    shadowNone: 'none',
    shadowSm: '0 2px 8px oklch(0.42 0.08 145 / 0.06), 0 1px 3px oklch(0.42 0.08 145 / 0.04)',
    shadowMd: '0 4px 16px oklch(0.42 0.08 145 / 0.08), 0 2px 6px oklch(0.42 0.08 145 / 0.04)',
    shadowLg: '0 8px 32px oklch(0.42 0.08 145 / 0.10), 0 4px 12px oklch(0.42 0.08 145 / 0.05)',
    shadowXl: '0 16px 48px oklch(0.42 0.08 145 / 0.12), 0 8px 24px oklch(0.42 0.08 145 / 0.06)',

    // Effects - Glassmorphism, misty
    backdropBlur: '12px',
    surfaceOpacity: '0.85',

    // Animation - Smooth, natural flow
    transitionFast: '150ms',
    transitionBase: '250ms',
    transitionSlow: '400ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core - Forest night
    background: 'oklch(0.12 0.03 145)',
    foreground: 'oklch(0.92 0.015 145)',
    card: 'oklch(0.16 0.035 145)',
    cardForeground: 'oklch(0.92 0.015 145)',
    popover: 'oklch(0.16 0.035 145)',
    popoverForeground: 'oklch(0.92 0.015 145)',

    // Brand - Luminous green
    primary: 'oklch(0.65 0.15 145)',
    primaryForeground: 'oklch(0.12 0.03 145)',
    secondary: 'oklch(0.22 0.04 145)',
    secondaryForeground: 'oklch(0.88 0.02 145)',

    // Neutral
    muted: 'oklch(0.22 0.03 145)',
    mutedForeground: 'oklch(0.65 0.025 145)',
    accent: 'oklch(0.80 0.14 85)',  // Moonlit gold
    accentForeground: 'oklch(0.12 0.04 85)',

    // Semantic
    destructive: 'oklch(0.62 0.20 25)',
    destructiveForeground: 'oklch(0.12 0 0)',
    success: 'oklch(0.65 0.15 145)',
    successForeground: 'oklch(0.12 0 0)',
    warning: 'oklch(0.82 0.14 85)',
    warningForeground: 'oklch(0.12 0.04 85)',
    info: 'oklch(0.65 0.12 200)',
    infoForeground: 'oklch(0.12 0 0)',

    // Boundaries
    border: 'oklch(0.28 0.03 145)',
    input: 'oklch(0.28 0.03 145)',
    ring: 'oklch(0.65 0.15 145)',

    // Charts
    chart1: 'oklch(0.65 0.15 145)',
    chart2: 'oklch(0.80 0.14 85)',
    chart3: 'oklch(0.60 0.10 180)',
    chart4: 'oklch(0.55 0.08 40)',
    chart5: 'oklch(0.70 0.10 100)',

    // Data sources
    dataSourcePrimary: 'oklch(0.60 0.12 200)',
    dataSourcePrimaryForeground: 'oklch(0.12 0 0)',
    dataSourceSecondary: 'oklch(0.65 0.12 280)',
    dataSourceSecondaryForeground: 'oklch(0.12 0 0)',

    // Sidebar
    sidebar: 'oklch(0.10 0.03 145)',
    sidebarForeground: 'oklch(0.92 0.015 145)',
    sidebarPrimary: 'oklch(0.65 0.15 145)',
    sidebarPrimaryForeground: 'oklch(0.12 0.03 145)',
    sidebarAccent: 'oklch(0.22 0.04 145)',
    sidebarAccentForeground: 'oklch(0.88 0.02 145)',
    sidebarBorder: 'oklch(0.20 0.025 145)',
    sidebarRing: 'oklch(0.65 0.15 145)',

    // Typography
    fontDisplay: 'Nunito, system-ui, sans-serif',
    fontBody: '"DM Sans", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '8px',
    radiusMd: '12px',
    radiusLg: '16px',
    radiusXl: '24px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Luminous in dark
    shadowNone: 'none',
    shadowSm: '0 2px 8px oklch(0 0 0 / 0.25), 0 0 1px oklch(0.65 0.1 145 / 0.1)',
    shadowMd: '0 4px 16px oklch(0 0 0 / 0.30), 0 0 2px oklch(0.65 0.1 145 / 0.1)',
    shadowLg: '0 8px 32px oklch(0 0 0 / 0.35), 0 0 4px oklch(0.65 0.1 145 / 0.1)',
    shadowXl: '0 16px 48px oklch(0 0 0 / 0.40), 0 0 8px oklch(0.65 0.1 145 / 0.15)',

    // Effects
    backdropBlur: '12px',
    surfaceOpacity: '0.85',

    // Animation
    transitionFast: '150ms',
    transitionBase: '250ms',
    transitionSlow: '400ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
