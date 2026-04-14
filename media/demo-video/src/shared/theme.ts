/**
 * Shared video theme derived from the current light "frond" UI.
 * Token names preserve the original mock-video API even when values are light.
 */

export const theme = {
  // Brand colors
  charcoal: "#1E1E22",
  forestGreen: "#2E7D32",
  lightGreen: "#4BAF50",
  steelBlue: "#5B86B0",

  // Canvas + window
  bgDark: "#F5F6F8",
  bgLight: "#FBFCFD",
  cardDark: "#FFFFFF",
  canvasGradientStart: "#F7F8FA",
  canvasGradientEnd: "#EEF2F5",
  windowBg: "#FCFDFE",
  titlebarBg: "#F7F8FA",
  topbarBg: "#FCFDFE",
  sidebarBg: "#F2F4F7",
  sidebarHoverBg: "#EAEEF3",
  sidebarActiveBg: "#5B86B0",
  sidebarActiveText: "#FFFFFF",
  surfaceSubtle: "#F6F7F9",
  surfaceMuted: "#EEF2F5",
  shadowWindow: "0 16px 44px rgba(15, 23, 42, 0.12)",

  // Text
  textWhite: "#1E293B",
  textDark: "#111827",
  textMuted: "#667085",
  textSoft: "#98A2B3",
  textOnPrimary: "#FFFFFF",

  // Boundaries
  border: "rgba(208, 213, 221, 0.78)",
  borderStrong: "rgba(208, 213, 221, 1)",

  // Semantic
  success: "#4BAF50",
  accent: "#5B86B0",
  danger: "#E85D5D",
  warning: "#F2B94B",
} as const;

export type ThemeColors = typeof theme;
