/**
 * Neutral Theme - Clean & Professional
 *
 * A clean, modern theme with no strong visual identity.
 * Inspired by Linear, Notion, and shadcn/ui defaults.
 *
 * Typography: Inter (or system fonts) - universally readable
 * Shapes: Medium rounded (6px) - modern but professional
 * Shadows: Subtle, clean - not dramatic
 * Colors: Pure grays with subtle blue accent
 */

import type { Theme } from '../index'

export const neutralTheme: Theme = {
  id: 'neutral',
  name: 'Neutral',
  description: 'Clean and professional, no visual distraction',
  author: 'Niamoto Team',
  inspiration: 'Linear, Notion, shadcn/ui - Modern productivity tools',
  tags: ['neutral', 'clean', 'minimal', 'professional'],
  style: 'scientific',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#18181b',
    secondary: '#f4f4f5',
    accent: '#71717a',  // Zinc-500 gray
    background: '#ffffff',
    fontDisplay: 'Inter',
    borderRadius: '6px',
  },

  light: {
    // Core - Pure white/gray
    background: 'oklch(1 0 0)',
    foreground: 'oklch(0.145 0 0)',
    card: 'oklch(1 0 0)',
    cardForeground: 'oklch(0.145 0 0)',
    popover: 'oklch(1 0 0)',
    popoverForeground: 'oklch(0.145 0 0)',

    // Brand - Near black primary
    primary: 'oklch(0.205 0 0)',
    primaryForeground: 'oklch(0.985 0 0)',
    secondary: 'oklch(0.965 0 0)',
    secondaryForeground: 'oklch(0.205 0 0)',

    // Neutral - Pure grays
    muted: 'oklch(0.965 0 0)',
    mutedForeground: 'oklch(0.45 0 0)',
    accent: 'oklch(0.94 0 0)',  // Light gray background
    accentForeground: 'oklch(0.205 0 0)',

    // Semantic - Standard colors
    destructive: 'oklch(0.55 0.20 25)',
    destructiveForeground: 'oklch(1 0 0)',
    success: 'oklch(0.52 0.14 145)',
    successForeground: 'oklch(1 0 0)',
    warning: 'oklch(0.75 0.15 70)',
    warningForeground: 'oklch(0.20 0 0)',
    info: 'oklch(0.60 0.16 250)',
    infoForeground: 'oklch(1 0 0)',

    // Boundaries - Subtle
    border: 'oklch(0.92 0 0)',
    input: 'oklch(0.92 0 0)',
    ring: 'oklch(0.50 0 0)',  // Dark gray ring

    // Charts - Balanced palette
    chart1: 'oklch(0.60 0.16 250)',  // Blue
    chart2: 'oklch(0.52 0.14 145)',  // Green
    chart3: 'oklch(0.75 0.15 70)',   // Yellow
    chart4: 'oklch(0.60 0.20 300)',  // Purple
    chart5: 'oklch(0.55 0.20 25)',   // Red

    // Data sources
    dataSourcePrimary: 'oklch(0.60 0.16 250)',
    dataSourcePrimaryForeground: 'oklch(1 0 0)',
    dataSourceSecondary: 'oklch(0.60 0.20 300)',
    dataSourceSecondaryForeground: 'oklch(1 0 0)',

    // Sidebar - Slightly off-white
    sidebar: 'oklch(0.985 0 0)',
    sidebarForeground: 'oklch(0.145 0 0)',
    sidebarPrimary: 'oklch(0.205 0 0)',
    sidebarPrimaryForeground: 'oklch(0.985 0 0)',
    sidebarAccent: 'oklch(0.965 0 0)',
    sidebarAccentForeground: 'oklch(0.205 0 0)',
    sidebarBorder: 'oklch(0.92 0 0)',
    sidebarRing: 'oklch(0.60 0.16 250)',

    // Typography - Inter (clean sans-serif)
    fontDisplay: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    fontBody: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',

    // Shapes - Modern rounded
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '8px',
    radiusXl: '12px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows - Subtle, clean
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0 0 0 / 0.04)',
    shadowMd: '0 2px 4px oklch(0 0 0 / 0.06), 0 1px 2px oklch(0 0 0 / 0.04)',
    shadowLg: '0 4px 8px oklch(0 0 0 / 0.08), 0 2px 4px oklch(0 0 0 / 0.04)',
    shadowXl: '0 8px 16px oklch(0 0 0 / 0.10), 0 4px 8px oklch(0 0 0 / 0.06)',

    // Effects - None
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation - Smooth
    transitionFast: '100ms',
    transitionBase: '150ms',
    transitionSlow: '200ms',
    transitionEasing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },

  dark: {
    // Core - Deep dark
    background: 'oklch(0.13 0 0)',
    foreground: 'oklch(0.95 0 0)',
    card: 'oklch(0.17 0 0)',
    cardForeground: 'oklch(0.95 0 0)',
    popover: 'oklch(0.17 0 0)',
    popoverForeground: 'oklch(0.95 0 0)',

    // Brand
    primary: 'oklch(0.95 0 0)',
    primaryForeground: 'oklch(0.13 0 0)',
    secondary: 'oklch(0.22 0 0)',
    secondaryForeground: 'oklch(0.95 0 0)',

    // Neutral
    muted: 'oklch(0.22 0 0)',
    mutedForeground: 'oklch(0.60 0 0)',
    accent: 'oklch(0.26 0 0)',  // Dark gray background
    accentForeground: 'oklch(0.95 0 0)',

    // Semantic
    destructive: 'oklch(0.60 0.20 25)',
    destructiveForeground: 'oklch(0.95 0 0)',
    success: 'oklch(0.58 0.14 145)',
    successForeground: 'oklch(0.13 0 0)',
    warning: 'oklch(0.78 0.14 70)',
    warningForeground: 'oklch(0.13 0 0)',
    info: 'oklch(0.65 0.16 250)',
    infoForeground: 'oklch(0.13 0 0)',

    // Boundaries
    border: 'oklch(0.26 0 0)',
    input: 'oklch(0.26 0 0)',
    ring: 'oklch(0.55 0 0)',  // Medium gray ring

    // Charts
    chart1: 'oklch(0.65 0.16 250)',
    chart2: 'oklch(0.58 0.14 145)',
    chart3: 'oklch(0.78 0.14 70)',
    chart4: 'oklch(0.65 0.18 300)',
    chart5: 'oklch(0.60 0.20 25)',

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.16 250)',
    dataSourcePrimaryForeground: 'oklch(0.13 0 0)',
    dataSourceSecondary: 'oklch(0.65 0.18 300)',
    dataSourceSecondaryForeground: 'oklch(0.13 0 0)',

    // Sidebar
    sidebar: 'oklch(0.15 0 0)',
    sidebarForeground: 'oklch(0.95 0 0)',
    sidebarPrimary: 'oklch(0.95 0 0)',
    sidebarPrimaryForeground: 'oklch(0.13 0 0)',
    sidebarAccent: 'oklch(0.22 0 0)',
    sidebarAccentForeground: 'oklch(0.95 0 0)',
    sidebarBorder: 'oklch(0.26 0 0)',
    sidebarRing: 'oklch(0.55 0 0)',  // Gray ring

    // Typography
    fontDisplay: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    fontBody: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '4px',
    radiusMd: '6px',
    radiusLg: '8px',
    radiusXl: '12px',
    radiusFull: '9999px',
    borderWidth: '1px',

    // Shadows
    shadowNone: 'none',
    shadowSm: '0 1px 2px oklch(0 0 0 / 0.20)',
    shadowMd: '0 2px 4px oklch(0 0 0 / 0.25), 0 1px 2px oklch(0 0 0 / 0.15)',
    shadowLg: '0 4px 8px oklch(0 0 0 / 0.30), 0 2px 4px oklch(0 0 0 / 0.20)',
    shadowXl: '0 8px 16px oklch(0 0 0 / 0.35), 0 4px 8px oklch(0 0 0 / 0.25)',

    // Effects
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '150ms',
    transitionSlow: '200ms',
    transitionEasing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
}
