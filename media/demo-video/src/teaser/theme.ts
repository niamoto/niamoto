/**
 * Palette teaser — extrait du vrai produit Niamoto.
 *
 * Sources de vérité :
 *  - src/niamoto/publish/templates/_base.html:43-48 (CSS vars du site publié)
 *  - src/niamoto/publish/assets/css/niamoto.css:313 (gradient widget headers)
 *  - src/niamoto/gui/ui/src/themes/presets/frond.ts (palette GUI Tauri)
 *
 * Ce theme est SÉPARÉ de `shared/theme.ts` (palette éditoriale du demo video
 * MarketingLandscape). Ne pas le fusionner tant que MarketingLandscape n'a pas
 * été migrée — modifier shared/theme.ts casserait visuellement la walkthrough.
 */

export const teaserTheme = {
  // Brand (extrait de _base.html + niamoto.css)
  primary: "#228b22", // vert nav header site publié
  primaryMid: "#2d8f47", // gradient mid widget headers
  primaryDark: "#1f7a1f", // gradient end widget headers
  secondary: "#4caf50", // accent
  widgetHeaderGradient: "linear-gradient(135deg, #228b22, #2d8f47, #1f7a1f)",

  // Surfaces
  pageBg: "#f9fafb",
  cardWhite: "#ffffff",
  sidebarBgDark: "#1e1e22", // sidebar GUI Tauri (eyedropper 06.dashboard-get-started.png)
  sidebarItemHover: "rgba(255,255,255,0.06)",
  sidebarItemActive: "rgba(34,139,34,0.14)", // vert semi-transparent
  titlebarBg: "#f7f8fa",
  topbarBg: "#ffffff",

  // Text
  textPrimary: "#111827",
  textSecondary: "#6b7280",
  textMuted: "#98a2b3",
  textOnPrimary: "#ffffff",
  textOnDark: "#e5e7eb", // sidebar dark

  // Borders & shadows — ombre triple-couche signature code vs screen recording
  border: "rgba(208, 213, 221, 0.78)",
  borderStrong: "#e5e7eb",
  shadowCard: [
    "0 2px 4px rgba(17, 24, 39, 0.12)",
    "0 16px 32px rgba(17, 24, 39, 0.06)",
    "0 32px 64px rgba(17, 24, 39, 0.04)",
  ].join(", "),
  shadowWindow: "0 24px 64px rgba(15, 23, 42, 0.14)",

  // Semantic
  success: "#4caf50",
  successBg: "#d1fae5",
  warning: "#f2b94b",
  danger: "#e85d5d",

  // Chart palette (extrait frond.ts oklch → hex approx + observation vraie page taxon)
  chart1: "#2E7D32", // vert Niamoto
  chart2: "#5B86B0", // steel blue
  chart3: "#7CB342", // vert clair
  chart4: "#F2B94B", // warm
  chart5: "#9333EA", // violet

  // Chart sub-taxons — observés sur page Araucariaceae (Araucaria montana bleu etc)
  subtaxonPalette: [
    "#4A90C5", // Araucaria montana bleu
    "#C2336A", // Agathis ovata magenta
    "#7CB342", // Agathis lanceolata vert clair
    "#6B46C1", // Araucaria rulei violet
    "#E08B3C", // Agathis moorei orange
    "#3FA89D", // Araucaria bernieri turquoise
    "#D4699B", // Araucaria luxurians rose
    "#7A8F3A", // Araucaria scopulorum vert olive
    "#6AA6D4", // Araucaria columnaris bleu clair
    "#B24642", // Araucaria biramulata rouge
  ],

  // DBH bars — observé page Araucariaceae (beige/brun gradient)
  dbhBarPrimary: "#C28E5F",
  dbhBarSecondary: "#A0693F",

  // Map count gradient (Plotly style observé)
  mapGradient: ["#0d0887", "#6a00a8", "#b12a90", "#e16462", "#fca636", "#f0f921"],
} as const;

export type TeaserThemeColors = typeof teaserTheme;
