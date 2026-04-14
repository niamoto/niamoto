import { AbsoluteFill } from "remotion";
import { CursorFlow, CursorWaypoint } from "../animations/CursorFlow";

interface CursorOverlayProps {
  waypoints: CursorWaypoint[];
  color?: string;
  startFrame?: number;
}

/**
 * Full-screen overlay that positions the cursor above all content.
 * Coordinates are relative to the canvas (not the window).
 */
export const CursorOverlay: React.FC<CursorOverlayProps> = ({
  waypoints,
  color,
  startFrame,
}) => {
  if (waypoints.length === 0) return null;

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 100 }}>
      <CursorFlow waypoints={waypoints} color={color} startFrame={startFrame} />
    </AbsoluteFill>
  );
};
