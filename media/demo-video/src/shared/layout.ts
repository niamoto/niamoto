/**
 * Layout constants for the demo video.
 * All dimensions in pixels at 1920x1080.
 */

export const LAYOUT = {
  canvas: { width: 1920, height: 1080 },

  // AppWindow — centered with subtle margin
  window: {
    x: 40,
    y: 30,
    width: 1840,
    height: 1020,
    borderRadius: 12,
    shadow: "0 25px 80px rgba(0,0,0,0.6)",
  },

  // macOS traffic lights
  trafficLights: {
    x: 56,
    y: 46,
    size: 12,
    gap: 8,
    colors: ["#FF5F57", "#FEBC2E", "#28C840"] as const,
  },

  titlebar: { height: 32 },

  // Sidebar (full mode, hidden for acts 1-2)
  sidebar: {
    width: 200,
    bgColor: "#13131A",
  },

  topbar: { height: 48 },

  // Content area varies by sidebar visibility:
  // With sidebar: x=240, y=80, w=1600, h=940
  // Without:      x=40,  y=80, w=1800, h=940
} as const;

/** Navigation items matching the real Niamoto sidebar */
export const NAV_ITEMS = [
  { id: "home", label: "Home", icon: "house" },
  { id: "data", label: "Data", icon: "database" },
  { id: "collections", label: "Collections", icon: "layers" },
  { id: "site", label: "Site", icon: "globe" },
  { id: "publish", label: "Publish", icon: "send" },
] as const;

export type NavItemId = (typeof NAV_ITEMS)[number]["id"];
