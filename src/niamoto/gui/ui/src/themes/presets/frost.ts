/**
 * Frost Theme - Vitreous Identity
 *
 * Translucent surfaces, backdrop blur 16px, layered depth like frosted glass.
 * Accent: Apple system blue #0071e3.
 * All colors in oklch format.
 *
 * Typography: Inter (clean, neutral)
 * Shapes: Smooth radius (8px), white glass borders
 * Shadows: Very light, no tint
 * Effects: High translucency with strong backdrop blur
 */

import type { Theme } from '../index'

export const frostTheme: Theme = {
  id: 'frost',
  name: 'Frost',
  description: 'Frosted glass surfaces with translucent depth and Apple blue accent',
  author: 'Niamoto Team',
  inspiration: 'Frosted glass, vitreous layers, clean Apple-style UI',
  tags: ['vitreous', 'translucent', 'glass', 'blue', 'minimal'],
  style: 'vitreous',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#0071e3',
    secondary: '#86868b',
    accent: '#34c759',
    background: '#f0eff3',
    fontDisplay: 'Inter',
    borderRadius: '8px',
  },

  light: {
    // Core — Gradient-ready light gray atmosphere
    background: 'oklch(0.96 0.005 270)',
    foreground: 'oklch(0.15 0 0)',
    card: 'oklch(1 0 0 / 0.65)',
    cardForeground: 'oklch(0.15 0 0)',
    popover: 'oklch(1 0 0 / 0.72)',
    popoverForeground: 'oklch(0.15 0 0)',

    // Brand — Apple system blue
    primary: 'oklch(0.52 0.18 255)',
    primaryForeground: 'oklch(1 0 0)',
    secondary: 'oklch(0.93 0.003 270)',
    secondaryForeground: 'oklch(0.30 0 0)',

    // Neutral — Pure neutral muted tones
    muted: 'oklch(0.94 0.003 270)',
    mutedForeground: 'oklch(0.55 0.005 270)',
    accent: 'oklch(0.63 0.17 145)',
    accentForeground: 'oklch(1 0 0)',

    // Semantic
    destructive: 'oklch(0.55 0.22 25)',
    destructiveForeground: 'oklch(1 0 0)',
    success: 'oklch(0.63 0.17 145)',
    successForeground: 'oklch(1 0 0)',
    warning: 'oklch(0.80 0.14 85)',
    warningForeground: 'oklch(0.20 0.04 85)',
    info: 'oklch(0.52 0.18 255)',
    infoForeground: 'oklch(1 0 0)',

    // Boundaries — White glass borders
    border: 'oklch(1 0 0 / 0.8)',
    input: 'oklch(0.92 0.003 270)',
    ring: 'oklch(0.52 0.18 255)',

    // Charts — Clean palette anchored on system blue
    chart1: 'oklch(0.52 0.18 255)',
    chart2: 'oklch(0.63 0.17 145)',
    chart3: 'oklch(0.72 0.15 45)',
    chart4: 'oklch(0.55 0.15 310)',
    chart5: 'oklch(0.60 0.14 195)',

    // Data sources
    dataSourcePrimary: 'oklch(0.52 0.18 255)',
    dataSourcePrimaryForeground: 'oklch(1 0 0)',
    dataSourceSecondary: 'oklch(0.63 0.17 145)',
    dataSourceSecondaryForeground: 'oklch(1 0 0)',

    // Sidebar — Subtle frosted panel
    sidebar: 'oklch(0.90 0.008 270)',
    sidebarForeground: 'oklch(0.15 0 0)',
    sidebarPrimary: 'oklch(0.52 0.18 255)',
    sidebarPrimaryForeground: 'oklch(1 0 0)',
    sidebarAccent: 'oklch(0.94 0.003 270)',
    sidebarAccentForeground: 'oklch(0.30 0 0)',
    sidebarBorder: 'oklch(0.84 0.006 270)',
    sidebarRing: 'oklch(0.52 0.18 255)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Smooth, rounded
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '8px',
    radiusXl: '12px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Very light, no tint
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0 0 0 / 0.03), 0 0 0 1px oklch(0 0 0 / 0.01)',
    shadowMd: '0 4px 12px oklch(0 0 0 / 0.05), 0 0 0 1px oklch(0 0 0 / 0.01)',
    shadowLg: '0 8px 24px oklch(0 0 0 / 0.07), 0 0 0 1px oklch(0 0 0 / 0.01)',
    shadowXl: '0 16px 40px oklch(0 0 0 / 0.09), 0 0 0 1px oklch(0 0 0 / 0.01)',

    // Effects — Frosted glass surfaces
    backdropBlur: '16px',
    surfaceOpacity: '0.65',

    // Animation — Smooth, natural
    transitionFast: '120ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  dark: {
    // Core — Deep neutral grays with glass surfaces
    background: 'oklch(0.14 0.005 270)',
    foreground: 'oklch(0.92 0 0)',
    card: 'oklch(0.20 0.005 270 / 0.65)',
    cardForeground: 'oklch(0.92 0 0)',
    popover: 'oklch(0.20 0.005 270 / 0.72)',
    popoverForeground: 'oklch(0.92 0 0)',

    // Brand — Brighter blue for dark mode
    primary: 'oklch(0.65 0.19 255)',
    primaryForeground: 'oklch(0.14 0 0)',
    secondary: 'oklch(0.22 0.005 270)',
    secondaryForeground: 'oklch(0.88 0 0)',

    // Neutral
    muted: 'oklch(0.22 0.005 270)',
    mutedForeground: 'oklch(0.60 0.005 270)',
    accent: 'oklch(0.68 0.17 145)',
    accentForeground: 'oklch(0.14 0 0)',

    // Semantic
    destructive: 'oklch(0.62 0.22 25)',
    destructiveForeground: 'oklch(0.14 0 0)',
    success: 'oklch(0.68 0.17 145)',
    successForeground: 'oklch(0.14 0 0)',
    warning: 'oklch(0.84 0.14 85)',
    warningForeground: 'oklch(0.14 0.04 85)',
    info: 'oklch(0.65 0.19 255)',
    infoForeground: 'oklch(0.14 0 0)',

    // Boundaries — Glass borders on dark
    border: 'oklch(1 0 0 / 0.12)',
    input: 'oklch(0.25 0.005 270)',
    ring: 'oklch(0.65 0.19 255)',

    // Charts
    chart1: 'oklch(0.65 0.19 255)',
    chart2: 'oklch(0.68 0.17 145)',
    chart3: 'oklch(0.75 0.15 45)',
    chart4: 'oklch(0.60 0.15 310)',
    chart5: 'oklch(0.65 0.14 195)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.19 255)',
    dataSourcePrimaryForeground: 'oklch(0.14 0 0)',
    dataSourceSecondary: 'oklch(0.68 0.17 145)',
    dataSourceSecondaryForeground: 'oklch(0.14 0 0)',

    // Sidebar
    sidebar: 'oklch(0.11 0.008 270)',
    sidebarForeground: 'oklch(0.92 0 0)',
    sidebarPrimary: 'oklch(0.65 0.19 255)',
    sidebarPrimaryForeground: 'oklch(0.14 0 0)',
    sidebarAccent: 'oklch(0.22 0.005 270)',
    sidebarAccentForeground: 'oklch(0.88 0 0)',
    sidebarBorder: 'oklch(0.18 0.006 270)',
    sidebarRing: 'oklch(0.65 0.19 255)',

    // Typography
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '8px',
    radiusXl: '12px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows — Subtle dark glow
    shadowNone: 'none',
    shadowSm: '0 2px 6px oklch(0 0 0 / 0.30), 0 0 1px oklch(1 0 0 / 0.04)',
    shadowMd: '0 4px 16px oklch(0 0 0 / 0.35), 0 0 2px oklch(1 0 0 / 0.04)',
    shadowLg: '0 8px 32px oklch(0 0 0 / 0.40), 0 0 4px oklch(1 0 0 / 0.04)',
    shadowXl: '0 16px 48px oklch(0 0 0 / 0.45), 0 0 8px oklch(1 0 0 / 0.06)',

    // Effects — Frosted glass surfaces
    backdropBlur: '16px',
    surfaceOpacity: '0.65',

    // Animation
    transitionFast: '120ms',
    transitionBase: '200ms',
    transitionSlow: '350ms',
    transitionEasing: 'cubic-bezier(0.22, 1, 0.36, 1)',
  },
}
