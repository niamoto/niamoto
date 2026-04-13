import { CursorWaypoint } from "../animations/CursorFlow";

/**
 * Cursor waypoints per act.
 * Coordinates are relative to the act's content area.
 * These are initial estimates — adjust visually in Remotion Studio.
 */
export const CURSOR_PATHS: Record<string, CursorWaypoint[]> = {
  act1: [
    { x: 960, y: 200, hold: 15 },
    { x: 920, y: 620, hold: 10, click: true }, // "Create New Project"
  ],

  act2: [
    { x: 700, y: 400, hold: 10, click: true }, // input name
    { x: 920, y: 580, hold: 15, click: true }, // "Create"
  ],

  act3: [
    { x: 800, y: 450, hold: 30 }, // hover upload zone
    { x: 800, y: 650, hold: 40 }, // observe YAML
  ],

  act4: [
    { x: 500, y: 400, hold: 20 },
    { x: 800, y: 400, hold: 20 },
    { x: 1100, y: 400, hold: 20 },
  ],

  act5: [
    { x: 300, y: 350, hold: 15, click: true }, // tree item
    { x: 300, y: 420, hold: 15, click: true }, // another item
    { x: 700, y: 400, hold: 20 }, // editor
    { x: 1200, y: 400, hold: 25 }, // preview
  ],

  act6: [
    { x: 920, y: 350, hold: 10, click: true }, // "Build & Publish"
    { x: 920, y: 500, hold: 60 }, // observe progress
  ],
};
