/**
 * Laboratory Theme - Scientific Precision
 *
 * Inspired by laboratory instruments, oscilloscopes, and scientific
 * measurement equipment. Dense information display with clinical precision.
 *
 * Typography: IBM Plex Sans (technical) + JetBrains Mono (data)
 * Shapes: Minimal radius, precise borders
 * Shadows: Hard, no blur - like instrument displays
 * Colors: Clinical white/deep black, cyan/green accents (LED-like)
 */

import type { Theme } from '../index'

export const laboratoryTheme: Theme = {
  id: 'laboratory',
  name: 'Laboratory',
  description: 'Scientific precision and information density',
  author: 'Niamoto Team',
  inspiration: 'Laboratory instruments and oscilloscopes',
  tags: ['scientific', 'monospace', 'dense', 'technical'],
  style: 'scientific',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap',

  preview: {
    primary: '#0a0a0a',
    secondary: '#404040',
    accent: '#00d4aa',
    background: '#fafafa',
    fontDisplay: 'IBM Plex Sans',
    borderRadius: '2px',
  },

  light: {
    // Core - Clinical white
    background: 'oklch(0.99 0 0)',
    foreground: 'oklch(0.12 0 0)',
    card: 'oklch(1 0 0)',
    cardForeground: 'oklch(0.12 0 0)',
    popover: 'oklch(1 0 0)',
    popoverForeground: 'oklch(0.12 0 0)',

    // Brand - Technical black
    primary: 'oklch(0.15 0 0)',
    primaryForeground: 'oklch(0.99 0 0)',
    secondary: 'oklch(0.96 0 0)',
    secondaryForeground: 'oklch(0.20 0 0)',

    // Neutral - Pure grays
    muted: 'oklch(0.96 0 0)',
    mutedForeground: 'oklch(0.45 0 0)',
    accent: 'oklch(0.70 0.15 175)',  // Cyan accent
    accentForeground: 'oklch(0.12 0 0)',

    // Semantic - High contrast indicators
    destructive: 'oklch(0.55 0.25 25)',
    destructiveForeground: 'oklch(0.99 0 0)',
    success: 'oklch(0.65 0.20 160)',  // Green LED
    successForeground: 'oklch(0.12 0 0)',
    warning: 'oklch(0.80 0.18 85)',   // Amber LED
    warningForeground: 'oklch(0.12 0 0)',
    info: 'oklch(0.60 0.18 230)',
    infoForeground: 'oklch(0.99 0 0)',

    // Boundaries - Precise lines
    border: 'oklch(0.88 0 0)',
    input: 'oklch(0.90 0 0)',
    ring: 'oklch(0.70 0.15 175)',  // Cyan ring

    // Charts - Instrument colors
    chart1: 'oklch(0.70 0.15 175)',  // Cyan
    chart2: 'oklch(0.65 0.20 160)',  // Green
    chart3: 'oklch(0.80 0.18 85)',   // Amber
    chart4: 'oklch(0.60 0.18 280)',  // Purple
    chart5: 'oklch(0.55 0.20 25)',   // Red

    // Data sources
    dataSourcePrimary: 'oklch(0.60 0.18 230)',
    dataSourcePrimaryForeground: 'oklch(0.99 0 0)',
    dataSourceSecondary: 'oklch(0.60 0.15 280)',
    dataSourceSecondaryForeground: 'oklch(0.99 0 0)',

    // Sidebar - Instrument panel
    sidebar: 'oklch(0.92 0 0)',
    sidebarForeground: 'oklch(0.12 0 0)',
    sidebarPrimary: 'oklch(0.15 0 0)',
    sidebarPrimaryForeground: 'oklch(0.99 0 0)',
    sidebarAccent: 'oklch(0.94 0 0)',
    sidebarAccentForeground: 'oklch(0.20 0 0)',
    sidebarBorder: 'oklch(0.86 0 0)',
    sidebarRing: 'oklch(0.70 0.15 175)',

    // Typography - Technical sans
    fontDisplay: '"IBM Plex Sans", system-ui, sans-serif',
    fontBody: '"IBM Plex Sans", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes - Minimal, precise
    radiusNone: '0',
    radiusSm: '2px',
    radiusMd: '3px',
    radiusLg: '4px',
    radiusXl: '6px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Hard, no blur (like LCD)
    shadowNone: 'none',
    shadowSm: '0 1px 0 oklch(0 0 0 / 0.08)',
    shadowMd: '0 2px 0 oklch(0 0 0 / 0.10)',
    shadowLg: '0 3px 0 oklch(0 0 0 / 0.12), 0 1px 0 oklch(0 0 0 / 0.08)',
    shadowXl: '0 4px 0 oklch(0 0 0 / 0.15), 0 2px 0 oklch(0 0 0 / 0.10)',

    // Effects - No blur (crisp)
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation - Quick, precise
    transitionFast: '75ms',
    transitionBase: '100ms',
    transitionSlow: '150ms',
    transitionEasing: 'linear',
  },

  dark: {
    // Core - Deep instrument black
    background: 'oklch(0.10 0 0)',
    foreground: 'oklch(0.92 0 0)',
    card: 'oklch(0.14 0 0)',
    cardForeground: 'oklch(0.92 0 0)',
    popover: 'oklch(0.14 0 0)',
    popoverForeground: 'oklch(0.92 0 0)',

    // Brand - Bright on dark
    primary: 'oklch(0.92 0 0)',
    primaryForeground: 'oklch(0.10 0 0)',
    secondary: 'oklch(0.20 0 0)',
    secondaryForeground: 'oklch(0.88 0 0)',

    // Neutral
    muted: 'oklch(0.20 0 0)',
    mutedForeground: 'oklch(0.60 0 0)',
    accent: 'oklch(0.75 0.18 175)',  // Bright cyan
    accentForeground: 'oklch(0.10 0 0)',

    // Semantic - Bright LEDs on black
    destructive: 'oklch(0.65 0.25 25)',
    destructiveForeground: 'oklch(0.10 0 0)',
    success: 'oklch(0.75 0.22 160)',  // Bright green LED
    successForeground: 'oklch(0.10 0 0)',
    warning: 'oklch(0.85 0.18 85)',   // Bright amber
    warningForeground: 'oklch(0.10 0 0)',
    info: 'oklch(0.70 0.18 230)',
    infoForeground: 'oklch(0.10 0 0)',

    // Boundaries
    border: 'oklch(0.25 0 0)',
    input: 'oklch(0.25 0 0)',
    ring: 'oklch(0.75 0.18 175)',

    // Charts - Bright instrument colors
    chart1: 'oklch(0.75 0.18 175)',
    chart2: 'oklch(0.75 0.22 160)',
    chart3: 'oklch(0.85 0.18 85)',
    chart4: 'oklch(0.70 0.18 280)',
    chart5: 'oklch(0.65 0.22 25)',

    // Data sources
    dataSourcePrimary: 'oklch(0.70 0.18 230)',
    dataSourcePrimaryForeground: 'oklch(0.10 0 0)',
    dataSourceSecondary: 'oklch(0.70 0.15 280)',
    dataSourceSecondaryForeground: 'oklch(0.10 0 0)',

    // Sidebar
    sidebar: 'oklch(0.08 0 0)',
    sidebarForeground: 'oklch(0.92 0 0)',
    sidebarPrimary: 'oklch(0.92 0 0)',
    sidebarPrimaryForeground: 'oklch(0.10 0 0)',
    sidebarAccent: 'oklch(0.20 0 0)',
    sidebarAccentForeground: 'oklch(0.88 0 0)',
    sidebarBorder: 'oklch(0.15 0 0)',
    sidebarRing: 'oklch(0.75 0.18 175)',

    // Typography
    fontDisplay: '"IBM Plex Sans", system-ui, sans-serif',
    fontBody: '"IBM Plex Sans", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '2px',
    radiusMd: '3px',
    radiusLg: '4px',
    radiusXl: '6px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Subtle glow effect
    shadowNone: 'none',
    shadowSm: '0 0 2px oklch(0.75 0.15 175 / 0.15)',
    shadowMd: '0 0 4px oklch(0.75 0.15 175 / 0.20)',
    shadowLg: '0 0 8px oklch(0.75 0.15 175 / 0.25)',
    shadowXl: '0 0 16px oklch(0.75 0.15 175 / 0.30)',

    // Effects
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '75ms',
    transitionBase: '100ms',
    transitionSlow: '150ms',
    transitionEasing: 'linear',
  },
}
