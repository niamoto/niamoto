/**
 * Desktop Pro Theme - VS Code Dark Refined
 *
 * A professional IDE-inspired theme with layered surfaces,
 * vibrancy effects, and precise micro-interactions.
 * Inspired by VS Code, Figma, and Slack.
 *
 * Typography: Geist (Vercel's font)
 * Shapes: Medium rounded (6-8px), clean lines
 * Shadows: Multi-layer with inset highlights
 * Effects: Strong vibrancy/backdrop blur
 * Colors: Slate-tinged neutrals with cyan-teal accent
 */

import type { Theme } from '../index'

export const desktopProTheme: Theme = {
  id: 'desktop-pro',
  name: 'Desktop Pro',
  description: 'Professional IDE-inspired dark theme',
  author: 'Niamoto Team',
  inspiration: 'VS Code, Figma, Slack - Modern desktop applications',
  tags: ['desktop', 'native', 'professional', 'ide', 'dark'],
  style: 'scientific',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#38bdf8',  // Cyan-teal
    secondary: '#334155', // Slate
    accent: '#22d3d1',   // Teal
    background: '#0f172a', // Dark slate
    fontDisplay: 'Geist',
    borderRadius: '6px',
  },

  light: {
    // Core - Light variant (professional light)
    background: 'oklch(0.98 0.005 265)',
    foreground: 'oklch(0.15 0.015 265)',
    card: 'oklch(1 0 0)',
    cardForeground: 'oklch(0.15 0.015 265)',
    popover: 'oklch(1 0 0)',
    popoverForeground: 'oklch(0.15 0.015 265)',

    // Brand - Cyan-teal
    primary: 'oklch(0.65 0.15 195)',
    primaryForeground: 'oklch(0.12 0 0)',
    secondary: 'oklch(0.94 0.005 265)',
    secondaryForeground: 'oklch(0.25 0.015 265)',

    // Neutral
    muted: 'oklch(0.95 0.005 265)',
    mutedForeground: 'oklch(0.45 0.01 265)',
    accent: 'oklch(0.70 0.12 180)',
    accentForeground: 'oklch(0.12 0 0)',

    // Semantic
    destructive: 'oklch(0.58 0.22 25)',
    destructiveForeground: 'oklch(1 0 0)',
    success: 'oklch(0.58 0.16 150)',
    successForeground: 'oklch(1 0 0)',
    warning: 'oklch(0.78 0.16 75)',
    warningForeground: 'oklch(0.14 0 0)',
    info: 'oklch(0.65 0.15 195)',
    infoForeground: 'oklch(0.12 0 0)',

    // Boundaries
    border: 'oklch(0.90 0.005 265)',
    input: 'oklch(0.92 0.005 265)',
    ring: 'oklch(0.65 0.15 195)',

    // Charts
    chart1: 'oklch(0.65 0.15 195)',
    chart2: 'oklch(0.58 0.16 150)',
    chart3: 'oklch(0.78 0.16 75)',
    chart4: 'oklch(0.62 0.22 290)',
    chart5: 'oklch(0.58 0.22 25)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.15 195)',
    dataSourcePrimaryForeground: 'oklch(0.12 0 0)',
    dataSourceSecondary: 'oklch(0.70 0.12 180)',
    dataSourceSecondaryForeground: 'oklch(0.12 0 0)',

    // Sidebar
    sidebar: 'oklch(0.96 0.003 265)',
    sidebarForeground: 'oklch(0.15 0.015 265)',
    sidebarPrimary: 'oklch(0.65 0.15 195)',
    sidebarPrimaryForeground: 'oklch(0.12 0 0)',
    sidebarAccent: 'oklch(0.93 0.005 265)',
    sidebarAccentForeground: 'oklch(0.25 0.015 265)',
    sidebarBorder: 'oklch(0.90 0.005 265)',
    sidebarRing: 'oklch(0.65 0.15 195)',

    // Typography - Geist
    fontDisplay: 'Geist, -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
    fontBody: 'Geist, -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
    fontMono: '"Geist Mono", "JetBrains Mono", Consolas, monospace',

    // Shapes - Desktop balanced
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '8px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Clean
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0 0 0 / 0.05)',
    shadowMd: '0 2px 4px oklch(0 0 0 / 0.05), 0 4px 6px oklch(0 0 0 / 0.05)',
    shadowLg: '0 4px 6px oklch(0 0 0 / 0.05), 0 10px 15px oklch(0 0 0 / 0.08)',
    shadowXl: '0 10px 15px oklch(0 0 0 / 0.05), 0 20px 25px oklch(0 0 0 / 0.10)',

    // Effects
    backdropBlur: '16px',
    surfaceOpacity: '0.92',

    // Animation - Snappy
    transitionFast: '80ms',
    transitionBase: '120ms',
    transitionSlow: '200ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },

  dark: {
    // Core - IDE Dark with surface hierarchy
    background: 'oklch(0.12 0.015 265)',     // Base
    foreground: 'oklch(0.92 0 0)',
    card: 'oklch(0.16 0.012 265)',           // Raised
    cardForeground: 'oklch(0.92 0 0)',
    popover: 'oklch(0.20 0.010 265)',        // Elevated
    popoverForeground: 'oklch(0.92 0 0)',

    // Brand - Cyan-teal (brighter for dark)
    primary: 'oklch(0.72 0.15 195)',
    primaryForeground: 'oklch(0.12 0 0)',
    secondary: 'oklch(0.24 0.008 265)',      // Surface
    secondaryForeground: 'oklch(0.85 0 0)',

    // Neutral
    muted: 'oklch(0.24 0.008 265)',
    mutedForeground: 'oklch(0.55 0.01 265)',
    accent: 'oklch(0.68 0.12 180)',
    accentForeground: 'oklch(0.12 0 0)',

    // Semantic
    destructive: 'oklch(0.65 0.22 25)',
    destructiveForeground: 'oklch(0.12 0 0)',
    success: 'oklch(0.65 0.16 150)',
    successForeground: 'oklch(0.12 0 0)',
    warning: 'oklch(0.80 0.16 75)',
    warningForeground: 'oklch(0.12 0 0)',
    info: 'oklch(0.72 0.15 195)',
    infoForeground: 'oklch(0.12 0 0)',

    // Boundaries - Subtle white overlays
    border: 'oklch(1 0 0 / 0.06)',
    input: 'oklch(1 0 0 / 0.08)',
    ring: 'oklch(0.72 0.15 195)',

    // Charts
    chart1: 'oklch(0.72 0.15 195)',
    chart2: 'oklch(0.65 0.16 150)',
    chart3: 'oklch(0.80 0.16 75)',
    chart4: 'oklch(0.68 0.20 290)',
    chart5: 'oklch(0.65 0.22 25)',

    // Data sources
    dataSourcePrimary: 'oklch(0.72 0.15 195)',
    dataSourcePrimaryForeground: 'oklch(0.12 0 0)',
    dataSourceSecondary: 'oklch(0.68 0.12 180)',
    dataSourceSecondaryForeground: 'oklch(0.12 0 0)',

    // Sidebar - Vibrancy ready
    sidebar: 'oklch(0.14 0.012 265 / 0.85)',
    sidebarForeground: 'oklch(0.92 0 0)',
    sidebarPrimary: 'oklch(0.72 0.15 195)',
    sidebarPrimaryForeground: 'oklch(0.12 0 0)',
    sidebarAccent: 'oklch(1 0 0 / 0.08)',
    sidebarAccentForeground: 'oklch(0.85 0 0)',
    sidebarBorder: 'oklch(1 0 0 / 0.06)',
    sidebarRing: 'oklch(0.72 0.15 195)',

    // Typography - Geist
    fontDisplay: 'Geist, -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
    fontBody: 'Geist, -apple-system, BlinkMacSystemFont, system-ui, sans-serif',
    fontMono: '"Geist Mono", "JetBrains Mono", Consolas, monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '8px',
    radiusXl: '10px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Multi-layer with highlights
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0 0 0 / 0.15), inset 0 1px 0 oklch(1 0 0 / 0.04)',
    shadowMd: '0 2px 4px oklch(0 0 0 / 0.15), 0 4px 8px oklch(0 0 0 / 0.10), inset 0 1px 0 oklch(1 0 0 / 0.04)',
    shadowLg: '0 4px 8px oklch(0 0 0 / 0.20), 0 8px 16px oklch(0 0 0 / 0.15)',
    shadowXl: '0 8px 16px oklch(0 0 0 / 0.25), 0 16px 32px oklch(0 0 0 / 0.20)',

    // Effects - Strong vibrancy
    backdropBlur: '20px',
    surfaceOpacity: '0.85',

    // Animation - Snappy desktop feel
    transitionFast: '80ms',
    transitionBase: '120ms',
    transitionSlow: '200ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },
}
