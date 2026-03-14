/**
 * Herbarium Theme - Cabinet of Curiosities
 *
 * Inspired by historical botanical plates, museum herbarium collections,
 * and 18th-century scientific illustration traditions.
 *
 * Typography: Crimson Pro (elegant serif) + Cormorant Garamond (italics for Latin names)
 * Shapes: Sharp corners, no radius - like engraved plates
 * Shadows: Almost none - flat, printed look
 * Colors: Cream paper, sepia ink, black text, gold accents
 */

import type { Theme } from '../index'

export const herbariumTheme: Theme = {
  id: 'herbarium',
  name: 'Herbarium',
  description: 'Classic elegance of botanical plates and cabinets of curiosities',
  author: 'Niamoto Team',
  inspiration: 'Historical herbarium collections from natural history museums',
  tags: ['classic', 'serif', 'botanical', 'museum'],
  style: 'classic',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#2c1810',
    secondary: '#8b7355',
    accent: '#c9a227',
    background: '#faf6f0',
    fontDisplay: 'Crimson Pro',
    borderRadius: '0',
  },

  light: {
    // Core - Warm cream paper
    background: 'oklch(0.97 0.01 75)',
    foreground: 'oklch(0.18 0.03 45)',
    card: 'oklch(0.985 0.008 75)',
    cardForeground: 'oklch(0.18 0.03 45)',
    popover: 'oklch(0.985 0.008 75)',
    popoverForeground: 'oklch(0.18 0.03 45)',

    // Brand - Deep sepia/walnut
    primary: 'oklch(0.30 0.06 45)',
    primaryForeground: 'oklch(0.97 0.01 75)',
    secondary: 'oklch(0.92 0.015 75)',
    secondaryForeground: 'oklch(0.30 0.06 45)',

    // Neutral - Warm grays
    muted: 'oklch(0.94 0.01 75)',
    mutedForeground: 'oklch(0.45 0.02 45)',
    accent: 'oklch(0.75 0.08 85)',  // Gold accent
    accentForeground: 'oklch(0.20 0.04 45)',

    // Semantic - Muted, scholarly
    destructive: 'oklch(0.50 0.15 25)',
    destructiveForeground: 'oklch(0.97 0 0)',
    success: 'oklch(0.45 0.10 145)',
    successForeground: 'oklch(0.97 0 0)',
    warning: 'oklch(0.70 0.12 85)',
    warningForeground: 'oklch(0.20 0.04 45)',
    info: 'oklch(0.45 0.08 230)',
    infoForeground: 'oklch(0.97 0 0)',

    // Boundaries - Subtle, engraved lines
    border: 'oklch(0.85 0.02 75)',
    input: 'oklch(0.88 0.015 75)',
    ring: 'oklch(0.75 0.08 85)',  // Gold ring

    // Charts - Vintage botanical palette
    chart1: 'oklch(0.45 0.10 145)',  // Forest green
    chart2: 'oklch(0.70 0.12 85)',   // Gold
    chart3: 'oklch(0.50 0.08 25)',   // Rust
    chart4: 'oklch(0.45 0.08 230)',  // Navy
    chart5: 'oklch(0.55 0.06 45)',   // Sepia

    // Data sources
    dataSourcePrimary: 'oklch(0.45 0.08 230)',
    dataSourcePrimaryForeground: 'oklch(0.97 0 0)',
    dataSourceSecondary: 'oklch(0.50 0.10 300)',
    dataSourceSecondaryForeground: 'oklch(0.97 0 0)',

    // Sidebar - Slightly darker paper
    sidebar: 'oklch(0.95 0.012 75)',
    sidebarForeground: 'oklch(0.18 0.03 45)',
    sidebarPrimary: 'oklch(0.30 0.06 45)',
    sidebarPrimaryForeground: 'oklch(0.97 0.01 75)',
    sidebarAccent: 'oklch(0.92 0.015 75)',
    sidebarAccentForeground: 'oklch(0.30 0.06 45)',
    sidebarBorder: 'oklch(0.88 0.015 75)',
    sidebarRing: 'oklch(0.75 0.08 85)',

    // Typography - Serif elegance
    fontDisplay: '"Crimson Pro", Georgia, serif',
    fontBody: '"Crimson Pro", Georgia, serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes - Sharp, engraved
    radiusNone: '0',
    radiusSm: '0',
    radiusMd: '0',
    radiusLg: '2px',
    radiusXl: '2px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Almost none (flat, printed)
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0.18 0.03 45 / 0.03)',
    shadowMd: '0 2px 4px oklch(0.18 0.03 45 / 0.04)',
    shadowLg: '0 4px 8px oklch(0.18 0.03 45 / 0.05)',
    shadowXl: '0 8px 16px oklch(0.18 0.03 45 / 0.06)',

    // Effects - No blur (crisp, printed)
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation - Subtle, dignified
    transitionFast: '100ms',
    transitionBase: '150ms',
    transitionSlow: '250ms',
    transitionEasing: 'ease-out',
  },

  dark: {
    // Core - Dark aged paper
    background: 'oklch(0.16 0.02 45)',
    foreground: 'oklch(0.90 0.01 75)',
    card: 'oklch(0.20 0.025 45)',
    cardForeground: 'oklch(0.90 0.01 75)',
    popover: 'oklch(0.20 0.025 45)',
    popoverForeground: 'oklch(0.90 0.01 75)',

    // Brand
    primary: 'oklch(0.80 0.06 75)',
    primaryForeground: 'oklch(0.16 0.02 45)',
    secondary: 'oklch(0.25 0.02 45)',
    secondaryForeground: 'oklch(0.85 0.01 75)',

    // Neutral
    muted: 'oklch(0.25 0.015 45)',
    mutedForeground: 'oklch(0.65 0.02 75)',
    accent: 'oklch(0.65 0.10 85)',  // Gold
    accentForeground: 'oklch(0.16 0.02 45)',

    // Semantic
    destructive: 'oklch(0.60 0.15 25)',
    destructiveForeground: 'oklch(0.97 0 0)',
    success: 'oklch(0.55 0.10 145)',
    successForeground: 'oklch(0.16 0 0)',
    warning: 'oklch(0.75 0.12 85)',
    warningForeground: 'oklch(0.16 0.04 45)',
    info: 'oklch(0.55 0.08 230)',
    infoForeground: 'oklch(0.16 0 0)',

    // Boundaries
    border: 'oklch(0.30 0.02 45)',
    input: 'oklch(0.30 0.02 45)',
    ring: 'oklch(0.65 0.10 85)',

    // Charts
    chart1: 'oklch(0.55 0.10 145)',
    chart2: 'oklch(0.75 0.12 85)',
    chart3: 'oklch(0.60 0.10 25)',
    chart4: 'oklch(0.55 0.08 230)',
    chart5: 'oklch(0.65 0.06 45)',

    // Data sources
    dataSourcePrimary: 'oklch(0.55 0.08 230)',
    dataSourcePrimaryForeground: 'oklch(0.16 0 0)',
    dataSourceSecondary: 'oklch(0.60 0.10 300)',
    dataSourceSecondaryForeground: 'oklch(0.16 0 0)',

    // Sidebar
    sidebar: 'oklch(0.18 0.025 45)',
    sidebarForeground: 'oklch(0.90 0.01 75)',
    sidebarPrimary: 'oklch(0.80 0.06 75)',
    sidebarPrimaryForeground: 'oklch(0.16 0.02 45)',
    sidebarAccent: 'oklch(0.25 0.02 45)',
    sidebarAccentForeground: 'oklch(0.85 0.01 75)',
    sidebarBorder: 'oklch(0.28 0.02 45)',
    sidebarRing: 'oklch(0.65 0.10 85)',

    // Typography
    fontDisplay: '"Crimson Pro", Georgia, serif',
    fontBody: '"Crimson Pro", Georgia, serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '0',
    radiusMd: '0',
    radiusLg: '2px',
    radiusXl: '2px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0 0 0 / 0.15)',
    shadowMd: '0 2px 4px oklch(0 0 0 / 0.20)',
    shadowLg: '0 4px 8px oklch(0 0 0 / 0.25)',
    shadowXl: '0 8px 16px oklch(0 0 0 / 0.30)',

    // Effects
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '150ms',
    transitionSlow: '250ms',
    transitionEasing: 'ease-out',
  },
}
