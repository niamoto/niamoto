/**
 * Lapis Theme - Classic Precision
 *
 * Micro-gradients on surfaces conveyed via layered blue-tinted shadows.
 * Opaque surfaces, no blur — shadows define edges instead of borders.
 * Inspired by the Stripe design language: slate-blue palette, clean geometry.
 *
 * Accent: slate-blue (#32325d primary, #525f7f secondary, #8898aa muted)
 * Typography: Inter (clean, neutral)
 * Shapes: Tight radius (5px), precise corners
 * Shadows: Blue-slate tinted, multi-layered for micro-gradient feel
 * Dark mode: Deep navy #0a2540, NOT generic dark gray
 */

import type { Theme } from '../index'

export const lapisTheme: Theme = {
  id: 'lapis',
  name: 'Lapis',
  description: 'Classic precision — blue-tinted shadows define edges on opaque surfaces',
  author: 'Niamoto Team',
  inspiration: 'Stripe design language, lapis lazuli mineral, deep navy nights',
  tags: ['classic', 'slate-blue', 'opaque', 'precision', 'shadows'],
  style: 'classic',

  fontsUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',

  preview: {
    primary: '#32325d',
    secondary: '#525f7f',
    accent: '#3ecf8e',
    background: '#f6f9fc',
    fontDisplay: 'Inter',
    borderRadius: '5px',
  },

  light: {
    // Core — Cool blue-white atmosphere
    background: 'oklch(0.975 0.005 250)',
    foreground: 'oklch(0.25 0.04 270)',
    card: 'oklch(1.0 0 0)',
    cardForeground: 'oklch(0.25 0.04 270)',
    popover: 'oklch(1.0 0 0)',
    popoverForeground: 'oklch(0.25 0.04 270)',

    // Brand — Slate-blue from #32325d
    primary: 'oklch(0.32 0.06 275)',
    primaryForeground: 'oklch(0.98 0 0)',
    secondary: 'oklch(0.93 0.008 250)',
    secondaryForeground: 'oklch(0.38 0.04 260)',

    // Neutral — Blue-tinted muted tones (#8898aa range)
    muted: 'oklch(0.94 0.006 250)',
    mutedForeground: 'oklch(0.60 0.02 250)',
    accent: 'oklch(0.72 0.16 160)',  // Vivid green #3ecf8e
    accentForeground: 'oklch(0.15 0.03 270)',

    // Semantic
    destructive: 'oklch(0.55 0.22 25)',
    destructiveForeground: 'oklch(0.98 0 0)',
    success: 'oklch(0.72 0.16 160)',
    successForeground: 'oklch(0.15 0.03 160)',
    warning: 'oklch(0.78 0.14 80)',
    warningForeground: 'oklch(0.20 0.06 80)',
    info: 'oklch(0.55 0.12 250)',
    infoForeground: 'oklch(0.98 0 0)',

    // Boundaries — No visible borders, shadows define edges
    border: 'oklch(0.92 0.005 250 / 0.5)',
    input: 'oklch(0.93 0.006 250)',
    ring: 'oklch(0.32 0.06 275)',

    // Charts — Slate-blue palette with green accent
    chart1: 'oklch(0.32 0.06 275)',   // Primary slate-blue
    chart2: 'oklch(0.72 0.16 160)',   // Green accent
    chart3: 'oklch(0.55 0.12 250)',   // Info blue
    chart4: 'oklch(0.78 0.14 80)',    // Warm amber
    chart5: 'oklch(0.50 0.10 320)',   // Purple complement

    // Data sources
    dataSourcePrimary: 'oklch(0.55 0.12 250)',
    dataSourcePrimaryForeground: 'oklch(0.98 0 0)',
    dataSourceSecondary: 'oklch(0.32 0.06 275)',
    dataSourceSecondaryForeground: 'oklch(0.98 0 0)',

    // Sidebar — Faint blue tint
    sidebar: 'oklch(0.97 0.006 250)',
    sidebarForeground: 'oklch(0.25 0.04 270)',
    sidebarPrimary: 'oklch(0.32 0.06 275)',
    sidebarPrimaryForeground: 'oklch(0.98 0 0)',
    sidebarAccent: 'oklch(0.94 0.008 250)',
    sidebarAccentForeground: 'oklch(0.38 0.04 260)',
    sidebarBorder: 'oklch(0.84 0.008 250)',
    sidebarRing: 'oklch(0.32 0.06 275)',

    // Typography — Inter everywhere
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes — Tight, precise
    radiusNone: '0',
    radiusSm: '3px',
    radiusMd: '5px',
    radiusLg: '5px',
    radiusXl: '8px',
    radiusFull: '9999px',
    borderWidth: '0px',

    // Shadows — Blue-slate tinted, multi-layered micro-gradients
    shadowNone: 'none',
    shadowSm: '0 1px 3px oklch(0.30 0.04 270 / 0.07), 0 1px 2px oklch(0.30 0.04 270 / 0.04)',
    shadowMd: '0 4px 6px oklch(0.30 0.04 270 / 0.07), 0 2px 4px oklch(0.30 0.04 270 / 0.04), 0 0 1px oklch(0.30 0.04 270 / 0.06)',
    shadowLg: '0 10px 20px oklch(0.30 0.04 270 / 0.07), 0 3px 6px oklch(0.30 0.04 270 / 0.05), 0 0 1px oklch(0.30 0.04 270 / 0.06)',
    shadowXl: '0 20px 40px oklch(0.30 0.04 270 / 0.10), 0 8px 16px oklch(0.30 0.04 270 / 0.06), 0 0 1px oklch(0.30 0.04 270 / 0.06)',

    // Effects — Opaque surfaces, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation — Crisp, professional
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },

  dark: {
    // Core — Deep navy #0a2540
    background: 'oklch(0.18 0.04 250)',
    foreground: 'oklch(0.90 0.01 250)',
    card: 'oklch(0.22 0.04 250)',
    cardForeground: 'oklch(0.90 0.01 250)',
    popover: 'oklch(0.22 0.04 250)',
    popoverForeground: 'oklch(0.90 0.01 250)',

    // Brand — Lighter slate-blue for dark mode
    primary: 'oklch(0.60 0.10 270)',
    primaryForeground: 'oklch(0.15 0.04 250)',
    secondary: 'oklch(0.25 0.035 250)',
    secondaryForeground: 'oklch(0.85 0.01 250)',

    // Neutral
    muted: 'oklch(0.25 0.03 250)',
    mutedForeground: 'oklch(0.62 0.02 250)',
    accent: 'oklch(0.75 0.16 160)',  // Vivid green, brighter for dark
    accentForeground: 'oklch(0.15 0.03 270)',

    // Semantic
    destructive: 'oklch(0.62 0.22 25)',
    destructiveForeground: 'oklch(0.15 0 0)',
    success: 'oklch(0.75 0.16 160)',
    successForeground: 'oklch(0.15 0.03 160)',
    warning: 'oklch(0.82 0.14 80)',
    warningForeground: 'oklch(0.18 0.06 80)',
    info: 'oklch(0.65 0.12 250)',
    infoForeground: 'oklch(0.15 0 0)',

    // Boundaries — Barely visible, shadow-driven
    border: 'oklch(0.30 0.03 250 / 0.5)',
    input: 'oklch(0.26 0.035 250)',
    ring: 'oklch(0.60 0.10 270)',

    // Charts
    chart1: 'oklch(0.60 0.10 270)',   // Lighter slate-blue
    chart2: 'oklch(0.75 0.16 160)',   // Green accent
    chart3: 'oklch(0.65 0.12 250)',   // Info blue
    chart4: 'oklch(0.82 0.14 80)',    // Warm amber
    chart5: 'oklch(0.58 0.10 320)',   // Purple complement

    // Data sources
    dataSourcePrimary: 'oklch(0.65 0.12 250)',
    dataSourcePrimaryForeground: 'oklch(0.15 0 0)',
    dataSourceSecondary: 'oklch(0.60 0.10 270)',
    dataSourceSecondaryForeground: 'oklch(0.15 0 0)',

    // Sidebar — Deeper navy
    sidebar: 'oklch(0.13 0.04 250)',
    sidebarForeground: 'oklch(0.90 0.01 250)',
    sidebarPrimary: 'oklch(0.60 0.10 270)',
    sidebarPrimaryForeground: 'oklch(0.15 0.04 250)',
    sidebarAccent: 'oklch(0.25 0.035 250)',
    sidebarAccentForeground: 'oklch(0.85 0.01 250)',
    sidebarBorder: 'oklch(0.20 0.03 250)',
    sidebarRing: 'oklch(0.60 0.10 270)',

    // Typography
    fontDisplay: 'Inter, system-ui, sans-serif',
    fontBody: 'Inter, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',

    // Shapes
    radiusNone: '0',
    radiusSm: '3px',
    radiusMd: '5px',
    radiusLg: '5px',
    radiusXl: '8px',
    radiusFull: '9999px',
    borderWidth: '0px',

    // Shadows — Deep blue glow on dark navy
    shadowNone: 'none',
    shadowSm: '0 2px 4px oklch(0.10 0.04 250 / 0.40), 0 0 1px oklch(0.50 0.06 270 / 0.08)',
    shadowMd: '0 4px 12px oklch(0.10 0.04 250 / 0.45), 0 0 2px oklch(0.50 0.06 270 / 0.08)',
    shadowLg: '0 8px 24px oklch(0.10 0.04 250 / 0.50), 0 0 4px oklch(0.50 0.06 270 / 0.10)',
    shadowXl: '0 16px 40px oklch(0.10 0.04 250 / 0.55), 0 0 8px oklch(0.50 0.06 270 / 0.12)',

    // Effects — Opaque surfaces, no blur
    backdropBlur: '0',
    surfaceOpacity: '1',

    // Animation
    transitionFast: '100ms',
    transitionBase: '180ms',
    transitionSlow: '300ms',
    transitionEasing: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
  },
}
