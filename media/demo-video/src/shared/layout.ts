/**
 * Layout constants for the demo video.
 * All dimensions in pixels at 1920x1080.
 */

export const LAYOUT = {
  canvas: { width: 1920, height: 1080 },

  // AppWindow — large centered desktop frame
  window: {
    x: 100,
    y: 40,
    width: 1720,
    height: 980,
    borderRadius: 20,
  },

  // macOS traffic lights
  trafficLights: {
    x: 84,
    y: 60,
    size: 14,
    gap: 8,
    colors: ["#FF5F57", "#FEBC2E", "#28C840"] as const,
  },

  titlebar: { height: 44 },

  // Sidebar (full mode, hidden for acts 1-2)
  sidebar: {
    width: 230,
    bgColor: "#EEF2F6",
  },

  topbar: { height: 58 },

  // Content area varies by sidebar visibility:
  // With sidebar: x=240, y=80, w=1600, h=940
  // Without:      x=40,  y=80, w=1800, h=940
} as const;

/** Navigation items matching the real Niamoto sidebar */
export const NAV_ITEMS = [
  { id: "home", label: "Accueil", icon: "house" },
  { id: "data", label: "Données", icon: "database" },
  { id: "collections", label: "Collections", icon: "layers" },
  { id: "site", label: "Site", icon: "globe" },
  { id: "publish", label: "Publication", icon: "send" },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]["id"];
