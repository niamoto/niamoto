/**
 * Niamoto Theme System
 *
 * A complete theming system inspired by New Caledonian ecosystems.
 * Uses oklch color space for perceptual uniformity and accessible contrasts.
 *
 * Beyond colors: typography, shapes, shadows, effects, and animations.
 */

// ============================================================================
// TYPES
// ============================================================================

export interface ThemeTokens {
  // Core UI
  background: string
  foreground: string
  card: string
  cardForeground: string
  popover: string
  popoverForeground: string

  // Brand
  primary: string
  primaryForeground: string
  secondary: string
  secondaryForeground: string

  // Neutral
  muted: string
  mutedForeground: string
  accent: string
  accentForeground: string

  // Semantic
  destructive: string
  destructiveForeground: string
  success: string
  successForeground: string
  warning: string
  warningForeground: string
  info: string
  infoForeground: string

  // Boundaries
  border: string
  input: string
  ring: string

  // Data visualization
  chart1: string
  chart2: string
  chart3: string
  chart4: string
  chart5: string

  // Data sources (for widget gallery)
  dataSourcePrimary: string
  dataSourcePrimaryForeground: string
  dataSourceSecondary: string
  dataSourceSecondaryForeground: string

  // Sidebar
  sidebar: string
  sidebarForeground: string
  sidebarPrimary: string
  sidebarPrimaryForeground: string
  sidebarAccent: string
  sidebarAccentForeground: string
  sidebarBorder: string
  sidebarRing: string

  // ========================================
  // TYPOGRAPHY
  // ========================================
  fontDisplay: string       // Display/heading font family
  fontBody: string          // Body text font family
  fontMono: string          // Monospace font for code/data

  // ========================================
  // SHAPES
  // ========================================
  radiusNone: string        // 0
  radiusSm: string          // Small radius (2px - 8px)
  radiusMd: string          // Medium radius (4px - 12px)
  radiusLg: string          // Large radius (8px - 20px)
  radiusXl: string          // Extra large radius (12px - 24px)
  radiusFull: string        // Full radius (9999px)
  borderWidth: string       // Default border width

  // ========================================
  // SHADOWS
  // ========================================
  shadowNone: string        // No shadow
  shadowSm: string          // Subtle shadow
  shadowMd: string          // Medium shadow (cards)
  shadowLg: string          // Large shadow (dropdowns)
  shadowXl: string          // Dramatic shadow (modals)

  // ========================================
  // EFFECTS
  // ========================================
  backdropBlur: string      // Backdrop blur amount
  surfaceOpacity: string    // Glass effect opacity

  // ========================================
  // ANIMATION
  // ========================================
  transitionFast: string    // Fast transitions (hover)
  transitionBase: string    // Base transitions
  transitionSlow: string    // Slow transitions (page)
  transitionEasing: string  // Easing function
}

export interface ThemeMetadata {
  id: string
  name: string
  description: string
  author: string
  inspiration: string
  tags: string[]
  // Style category for visual distinction
  style: 'classic' | 'scientific' | 'organic' | 'natural'
}

export interface Theme extends ThemeMetadata {
  light: ThemeTokens
  dark: ThemeTokens
  // Preview for theme selector
  preview: {
    primary: string
    secondary: string
    accent: string
    background: string
    // Typography preview
    fontDisplay: string
    // Shape preview
    borderRadius: string
  }
  // Google Fonts URL to load
  fontsUrl: string
}

export type ThemeMode = 'light' | 'dark' | 'system'

export interface ThemeState {
  themeId: string
  mode: ThemeMode
}

// ============================================================================
// REGISTRY
// ============================================================================

const themeRegistry = new Map<string, Theme>()

export function registerTheme(theme: Theme): void {
  themeRegistry.set(theme.id, theme)
}

export function getTheme(id: string): Theme | undefined {
  return themeRegistry.get(id)
}

export function getAllThemes(): Theme[] {
  return Array.from(themeRegistry.values())
}

export function getThemeIds(): string[] {
  return Array.from(themeRegistry.keys())
}

// ============================================================================
// CSS VARIABLE APPLICATION
// ============================================================================

function tokenToCssVar(key: string): string {
  // Convert camelCase to kebab-case
  return key.replace(/([A-Z])/g, '-$1').toLowerCase()
}

// Track loaded font URLs to avoid duplicates
const loadedFonts = new Set<string>()
let localFontsLoaded = false

/**
 * Load local fonts CSS for desktop mode (offline-ready).
 * The fonts.css file in /fonts/ contains @font-face rules pointing to
 * locally bundled WOFF2 files for all theme fonts.
 */
function loadLocalFonts(): void {
  if (localFontsLoaded) return

  const existingLink = document.querySelector('link[href="/fonts/fonts.css"]')
  if (existingLink) {
    localFontsLoaded = true
    return
  }

  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = '/fonts/fonts.css'
  document.head.appendChild(link)
  localFontsLoaded = true
}

/**
 * Detect if running in Tauri desktop mode.
 * Checks for the __TAURI__ global or the NIAMOTO_RUNTIME_MODE cookie/flag.
 */
function isDesktopMode(): boolean {
  return '__TAURI__' in window || '__TAURI_INTERNALS__' in window
}

export function loadThemeFonts(theme: Theme): void {
  if (!theme.fontsUrl) return

  // In desktop mode: use local fonts (offline-ready)
  if (isDesktopMode()) {
    loadLocalFonts()
    return
  }

  // In web mode: use Google Fonts CDN
  if (loadedFonts.has(theme.fontsUrl)) return

  const existingLink = document.querySelector(`link[href="${theme.fontsUrl}"]`)
  if (existingLink) {
    loadedFonts.add(theme.fontsUrl)
    return
  }

  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = theme.fontsUrl
  document.head.appendChild(link)
  loadedFonts.add(theme.fontsUrl)
}

export function applyTheme(theme: Theme, mode: 'light' | 'dark'): void {
  const tokens = mode === 'dark' ? theme.dark : theme.light
  const root = document.documentElement

  // Load fonts first
  loadThemeFonts(theme)

  // Apply each token as a CSS variable
  Object.entries(tokens).forEach(([key, value]) => {
    const cssVar = `--${tokenToCssVar(key)}`
    root.style.setProperty(cssVar, value as string)
  })

  // Set theme style attribute for CSS selectors
  root.setAttribute('data-theme-style', theme.style)

  // Update dark class
  root.classList.remove('light', 'dark')
  root.classList.add(mode)
}

export function getSystemMode(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// ============================================================================
// RE-EXPORTS
// ============================================================================

export { laboratoryTheme } from './presets/laboratory'
export { forestTheme } from './presets/forest'
