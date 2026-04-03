/**
 * Ink Theme - Editorial Monochrome
 *
 * Pure black ink on warm white paper — ZERO color accent.
 * Radical monochrome: everything is black, white, or gray.
 * Sharp corners, assertive borders, no shadows, opaque surfaces.
 *
 * Typography: Inter (clean, editorial)
 * Shapes: All zero radius — sharp corners everywhere
 * Shadows: None
 * Effects: Opaque surfaces, no blur
 */

import type { Theme } from '../index'

export const inkTheme: Theme = {
  id: 'ink',
  name: 'Ink',
  description: 'Pure black ink on warm white paper — radical monochrome, sharp corners, no frills',
  author: 'Niamoto Team',
  inspiration: 'Printed matter, editorial design, newspaper typography',
  tags: ['editorial', 'monochrome', 'minimal', 'sharp', 'print'],
  style: 'editorial',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#111111',
    secondary: '#999999',
    accent: '#666666',
    background: '#fcfcfa',
    fontDisplay: 'Inter',
    borderRadius: '0',
  },

  light: {
    // Core — Warm white paper, near-black ink
    background: 'oklch(0.99 0.005 90)',
    foreground: 'oklch(0.15 0 0)',
    card: 'oklch(0.98 0.003 90)',
    cardForeground: 'oklch(0.15 0 0)',
    popover: 'oklch(0.98 0.003 90)',
    popoverForeground: 'oklch(0.15 0 0)',

    // Brand — Pure black as primary
    primary: 'oklch(0.15 0 0)',
    primaryForeground: 'oklch(0.99 0.005 90)',
    secondary: 'oklch(0.93 0.003 90)',
    secondaryForeground: 'oklch(0.25 0 0)',

    // Neutral — Grayscale muted tones
    muted: 'oklch(0.93 0.003 90)',
    mutedForeground: 'oklch(0.50 0 0)',
    accent: 'oklch(0.45 0 0)',
    accentForeground: 'oklch(0.99 0.005 90)',

    // Semantic — Grayscale only, no color
    destructive: 'oklch(0.30 0 0)',
    destructiveForeground: 'oklch(0.99 0 0)',
    success: 'oklch(0.50 0 0)',
    successForeground: 'oklch(0.99 0 0)',
    warning: 'oklch(0.62 0 0)',
    warningForeground: 'oklch(0.15 0 0)',
    info: 'oklch(0.50 0 0)',
    infoForeground: 'oklch(0.99 0 0)',

    // Boundaries — Assertive black-ish borders
    border: 'oklch(0.25 0 0 / 0.25)',
    input: 'oklch(0.80 0 0)',
    ring: 'oklch(0.15 0 0)',

    // Charts — 5 shades of gray from dark to light
    chart1: 'oklch(0.20 0 0)',
    chart2: 'oklch(0.38 0 0)',
    chart3: 'oklch(0.55 0 0)',
    chart4: 'oklch(0.70 0 0)',
    chart5: 'oklch(0.82 0 0)',

    // Data sources
    dataSourcePrimary: 'oklch(0.20 0 0)',
    dataSourcePrimaryForeground: 'oklch(0.99 0 0)',
    dataSourceSecondary: 'oklch(0.55 0 0)',
    dataSourceSecondaryForeground: 'oklch(0.99 0 0)',

    // Sidebar — Slightly off-white
    sidebar: 'oklch(0.98 0.003 90)',
    sidebarForeground: 'oklch(0.15 0 0)',
    sidebarPrimary: 'oklch(0.15 0 0)',
    sidebarPrimaryForeground: 'oklch(0.99 0.005 90)',
    sidebarAccent: 'oklch(0.93 0.003 90)',
    sidebarAccentForeground: 'oklch(0.25 0 0)',
    sidebarBorder: 'oklch(0.86 0 0)',
    sidebarRing: 'oklch(0.15 0 0)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — All zero, sharp corners
    radiusNone: '0',
    radiusSm: '0',
    radiusMd: '0',
    radiusLg: '0',
    radiusXl: '0',
    radiusFull: '9999px',
    borderWidth: '1.5px',

    // Shadows — None
    shadowNone: 'none',
    shadowSm: 'none',
    shadowMd: 'none',
    shadowLg: 'none',
    shadowXl: 'none',

    // Effects — Opaque, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation — Crisp, immediate
    transitionFast: '80ms',
    transitionBase: '150ms',
    transitionSlow: '250ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core — Near-black background, warm white text
    background: 'oklch(0.13 0 0)',
    foreground: 'oklch(0.92 0.005 90)',
    card: 'oklch(0.17 0 0)',
    cardForeground: 'oklch(0.92 0.005 90)',
    popover: 'oklch(0.17 0 0)',
    popoverForeground: 'oklch(0.92 0.005 90)',

    // Brand — White as primary on dark
    primary: 'oklch(0.92 0.005 90)',
    primaryForeground: 'oklch(0.13 0 0)',
    secondary: 'oklch(0.22 0 0)',
    secondaryForeground: 'oklch(0.85 0 0)',

    // Neutral
    muted: 'oklch(0.22 0 0)',
    mutedForeground: 'oklch(0.58 0 0)',
    accent: 'oklch(0.62 0 0)',
    accentForeground: 'oklch(0.13 0 0)',

    // Semantic — Grayscale only, no color
    destructive: 'oklch(0.75 0 0)',
    destructiveForeground: 'oklch(0.13 0 0)',
    success: 'oklch(0.58 0 0)',
    successForeground: 'oklch(0.13 0 0)',
    warning: 'oklch(0.68 0 0)',
    warningForeground: 'oklch(0.13 0 0)',
    info: 'oklch(0.58 0 0)',
    infoForeground: 'oklch(0.13 0 0)',

    // Boundaries
    border: 'oklch(0.80 0 0 / 0.20)',
    input: 'oklch(0.28 0 0)',
    ring: 'oklch(0.92 0.005 90)',

    // Charts — 5 shades of gray from light to dark (inverted)
    chart1: 'oklch(0.85 0 0)',
    chart2: 'oklch(0.70 0 0)',
    chart3: 'oklch(0.55 0 0)',
    chart4: 'oklch(0.42 0 0)',
    chart5: 'oklch(0.30 0 0)',

    // Data sources
    dataSourcePrimary: 'oklch(0.85 0 0)',
    dataSourcePrimaryForeground: 'oklch(0.13 0 0)',
    dataSourceSecondary: 'oklch(0.55 0 0)',
    dataSourceSecondaryForeground: 'oklch(0.13 0 0)',

    // Sidebar
    sidebar: 'oklch(0.10 0 0)',
    sidebarForeground: 'oklch(0.92 0.005 90)',
    sidebarPrimary: 'oklch(0.92 0.005 90)',
    sidebarPrimaryForeground: 'oklch(0.13 0 0)',
    sidebarAccent: 'oklch(0.22 0 0)',
    sidebarAccentForeground: 'oklch(0.85 0 0)',
    sidebarBorder: 'oklch(0.18 0 0)',
    sidebarRing: 'oklch(0.92 0.005 90)',

    // Typography
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — All zero, sharp corners
    radiusNone: '0',
    radiusSm: '0',
    radiusMd: '0',
    radiusLg: '0',
    radiusXl: '0',
    radiusFull: '9999px',
    borderWidth: '1.5px',

    // Shadows — None
    shadowNone: 'none',
    shadowSm: 'none',
    shadowMd: 'none',
    shadowLg: 'none',
    shadowXl: 'none',

    // Effects — Opaque, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation — Crisp, immediate
    transitionFast: '80ms',
    transitionBase: '150ms',
    transitionSlow: '250ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
