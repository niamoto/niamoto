import { CursorWaypoint } from "../animations/CursorFlow";

/**
 * Cursor waypoints per act.
 * Coordinates are relative to the act's content area.
 * These are initial estimates — adjust visually in Remotion Studio.
 */
export const CURSOR_PATHS: Record<string, CursorWaypoint[]> = {
  act1: [
    { x: 960, y: 250, hold: 15 },
    { x: 786, y: 672, hold: 10, click: true },
  ],

  act2: [
    { x: 1048, y: 772, hold: 2 },
    { x: 1194, y: 826, hold: 12, click: true },
  ],

  act3: [
    { x: 1318, y: 276, hold: 28 }, // approche vers le CTA d'import
    { x: 1516, y: 350, hold: 22, click: true }, // "Ouvrir l'import"
    { x: 1118, y: 452, hold: 64, click: true }, // dropzone / upload zone
    { x: 1704, y: 886, hold: 48, click: true }, // "Télécharger 16 fichiers"
    { x: 1146, y: 352, hold: 96 }, // observer l'analyse
    { x: 1700, y: 946, hold: 50, click: true }, // "Lancer l'import"
  ],

  act4: [
    { x: 958, y: 282, hold: 78, click: true }, // ouvrir taxons
    { x: 362, y: 232, hold: 78, click: true }, // ajouter un widget
    { x: 600, y: 498, hold: 6, click: true }, // sélectionner Navigation Taxons
    { x: 1118, y: 498, hold: 6, click: true }, // sélectionner Informations générales
    { x: 600, y: 620, hold: 12, click: true }, // sélectionner Geo Pt map
    { x: 1690, y: 994, hold: 42, click: true }, // ajouter les widgets
    { x: 1738, y: 182, hold: 76, click: true }, // lancer le calcul
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
