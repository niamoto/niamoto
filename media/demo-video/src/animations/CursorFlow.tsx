import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";

export interface CursorWaypoint {
  x: number;
  y: number;
  hold?: number;  // frames to pause at this point (default: 15)
  click?: boolean; // show click ripple + scale spring
}

interface CursorFlowProps {
  waypoints: CursorWaypoint[];
  color?: string;
  size?: number;
  framesPerSegment?: number;
  startFrame?: number;
}

/**
 * Animated cursor that moves between waypoints along cubic Bézier curves.
 * Click waypoints trigger a spring scale + expanding ripple.
 * 100% interpolate()/spring() — no CSS animations.
 */
export const CursorFlow: React.FC<CursorFlowProps> = ({
  waypoints,
  color = "#FFFFFF",
  size = 20,
  framesPerSegment = 24,
  startFrame = 0,
}) => {
  const frame = useCurrentFrame() - startFrame;
  const { fps } = useVideoConfig();

  if (waypoints.length === 0) return null;
  if (frame < 0) return null;

  // Pointer tip inside the 24x24 SVG path.
  // Waypoint coordinates represent the actual click hotspot, not the SVG box.
  const hotspotX = size * (5.5 / 24);
  const hotspotY = size * (3.21 / 24);

  // Build timeline: [move to wp0] [hold wp0] [move to wp1] [hold wp1] ...
  const timeline: Array<{
    type: "move" | "hold";
    startFrame: number;
    endFrame: number;
    from: CursorWaypoint;
    to: CursorWaypoint;
  }> = [];

  let currentFrame = 0;
  for (let i = 0; i < waypoints.length; i++) {
    const wp = waypoints[i];
    const prev = i > 0 ? waypoints[i - 1] : wp;

    if (i > 0) {
      // Move segment
      timeline.push({
        type: "move",
        startFrame: currentFrame,
        endFrame: currentFrame + framesPerSegment,
        from: prev,
        to: wp,
      });
      currentFrame += framesPerSegment;
    }

    // Hold segment
    const holdFrames = wp.hold ?? 15;
    timeline.push({
      type: "hold",
      startFrame: currentFrame,
      endFrame: currentFrame + holdFrames,
      from: wp,
      to: wp,
    });
    currentFrame += holdFrames;
  }

  // Find current position
  let x = waypoints[0].x;
  let y = waypoints[0].y;
  let isClicking = false;
  let clickFrame = 0;

  for (const segment of timeline) {
    if (frame >= segment.startFrame && frame < segment.endFrame) {
      if (segment.type === "move") {
        const progress = interpolate(
          frame,
          [segment.startFrame, segment.endFrame],
          [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );
        // Ease for natural movement
        const eased = Easing.bezier(0.4, 0, 0.2, 1)(progress);
        x = interpolate(eased, [0, 1], [segment.from.x, segment.to.x]);
        y = interpolate(eased, [0, 1], [segment.from.y, segment.to.y]);
      } else {
        x = segment.to.x;
        y = segment.to.y;
        if (segment.to.click && frame === segment.startFrame) {
          isClicking = true;
          clickFrame = frame;
        }
      }
      // Check if we're in a hold with click
      if (segment.type === "hold" && segment.to.click) {
        isClicking = true;
        clickFrame = segment.startFrame;
      }
      break;
    }
    // Past all segments — stay at last position
    x = segment.to.x;
    y = segment.to.y;
  }

  // Click animation
  const clickAge = frame - clickFrame;
  const clickScale = isClicking && clickAge >= 0 && clickAge < 15
    ? spring({
        frame: clickAge,
        fps,
        config: { damping: 10, stiffness: 200, mass: 0.6 },
        from: 0.85,
        to: 1,
      })
    : 1;

  const rippleOpacity = isClicking && clickAge >= 0 && clickAge < 20
    ? interpolate(clickAge, [0, 20], [0.4, 0], { extrapolateRight: "clamp" })
    : 0;

  const rippleRadius = isClicking && clickAge >= 0 && clickAge < 20
    ? interpolate(clickAge, [0, 20], [4, 40], { extrapolateRight: "clamp" })
    : 0;

  return (
    <>
      {/* Click ripple */}
      {rippleOpacity > 0 && (
        <div
          style={{
            position: "absolute",
            left: x - rippleRadius,
            top: y - rippleRadius,
            width: rippleRadius * 2,
            height: rippleRadius * 2,
            borderRadius: "50%",
            border: `2px solid ${color}`,
            opacity: rippleOpacity,
            pointerEvents: "none",
          }}
        />
      )}
      {/* Cursor pointer */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        style={{
          position: "absolute",
          left: x - hotspotX,
          top: y - hotspotY,
          transform: `scale(${clickScale})`,
          transformOrigin: "top left",
          pointerEvents: "none",
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.5))",
        }}
      >
        {/* macOS-style pointer */}
        <path
          d="M5.5 3.21V20.8c0 .45.54.67.86.35l4.86-4.86h5.28c.45 0 .67-.54.35-.85L5.85 3.21c-.31-.31-.86-.1-.86.35z"
          fill={color}
          stroke="#000"
          strokeWidth={1}
        />
      </svg>
    </>
  );
};
