/**
 * Frond theme colors for video overlays.
 * Derived from src/niamoto/gui/ui/src/themes/presets/frond.ts
 * but simplified for video use (no oklch — plain hex for Remotion).
 */

export const theme = {
  // Brand colors from logo
  charcoal: "#1E1E22",
  forestGreen: "#2E7D32",
  lightGreen: "#4BAF50",
  steelBlue: "#3FA9F5",

  // Surfaces
  bgDark: "#1E1E22",
  bgLight: "#F5F6F8",
  cardDark: "#2A2A2E",

  // Text
  textWhite: "#FAFAFA",
  textMuted: "#9CA3AF",
  textDark: "#1E1E22",

  // Semantic
  success: "#4BAF50",
  accent: "#3FA9F5",
} as const;

export type ThemeColors = typeof theme;
