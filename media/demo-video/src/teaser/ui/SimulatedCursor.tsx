import { memo } from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate, Easing } from "remotion";
import { getPointAtLength } from "@remotion/paths";
import { teaserTheme } from "../theme";

interface SimulatedCursorProps {
  /** SVG path string (ex : "M 100 100 Q 300 50 500 300"). Le curseur suit ce chemin. */
  path: string;
  /** Frame où le curseur commence à bouger. Default 0. */
  startFrame?: number;
  /** Frames pour parcourir le chemin entièrement. Default 30. */
  travelDurationFrames?: number;
  /** Frame relative à la fin du parcours où le click ripple apparaît. Default 0 (juste à l'arrivée). */
  clickFrameOffset?: number;
  /** Taille du curseur (px). Default 32. */
  size?: number;
  /** Couleur du ripple de click. Default vert Niamoto. */
  rippleColor?: string;
}

/**
 * Curseur simulé qui suit un path SVG Bézier + click ripple à l'arrivée.
 *
 * Pattern inspiré de `@remotion/paths` (getPointAtLength) + patterns remocn.
 * Exemple path pour aller de (100,100) vers (500,300) avec courbe :
 *   "M 100 100 Q 300 50 500 300"
 *
 * Easing sur le progress : `Easing.bezier(0.25, 0.1, 0.25, 1)` (cubic out — naturel
 * pour un mouvement humain).
 */
export const SimulatedCursor = memo<SimulatedCursorProps>(
  ({ path, startFrame = 0, travelDurationFrames = 30, clickFrameOffset = 0, size = 32, rippleColor = teaserTheme.primary }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const localFrame = frame - startFrame;

    // Progress [0, 1] avec easing cubic out
    const rawProgress = interpolate(localFrame, [0, travelDurationFrames], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
    });

    // Longueur du path → point à cette position
    const pathLength = getPathLengthSafe(path);
    const point = getPointAtLength(path, pathLength * rawProgress);

    // Apparition : fade-in sur 6 frames au début
    const appearOpacity = interpolate(localFrame, [-3, 3], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    // Click ripple : démarre à travelDurationFrames + clickFrameOffset
    const clickStartFrame = travelDurationFrames + clickFrameOffset;
    const clickFrame = localFrame - clickStartFrame;
    const rippleScale = spring({
      frame: clickFrame,
      fps,
      config: { damping: 10, stiffness: 140 },
      durationInFrames: 18,
    });
    const clampedRippleScale = interpolate(rippleScale, [0, 1], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const rippleOpacity = interpolate(clickFrame, [0, 4, 18], [0, 0.7, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    // Click press : curseur se rétrécit légèrement au moment du clic
    const pressScale = interpolate(clickFrame, [0, 3, 10], [1, 0.9, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    return (
      <svg
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 50,
        }}
      >
        {/* Click ripple */}
        {clickFrame >= 0 && clickFrame < 22 && (
          <circle
            cx={point.x}
            cy={point.y}
            r={28 * clampedRippleScale}
            fill="none"
            stroke={rippleColor}
            strokeWidth={2}
            opacity={rippleOpacity}
          />
        )}

        {/* Curseur */}
        <g
          transform={`translate(${point.x}, ${point.y}) scale(${pressScale})`}
          opacity={appearOpacity}
          style={{ filter: "drop-shadow(0 3px 6px rgba(0,0,0,0.25))" }}
        >
          <path
            d="M 0 0 L 0 18 L 5 14 L 9 22 L 11 21 L 7 13 L 14 13 Z"
            fill={teaserTheme.textPrimary}
            stroke={teaserTheme.cardWhite}
            strokeWidth={1.5}
            strokeLinejoin="round"
            transform={`scale(${size / 18})`}
          />
        </g>
      </svg>
    );
  },
);

SimulatedCursor.displayName = "SimulatedCursor";

/**
 * Helper — retourne la longueur approximative d'un SVG path string.
 * `@remotion/paths` a `getLength(d)`, mais via le DOM c'est plus fiable.
 * Ici on utilise une approximation via sampling de `getPointAtLength` via estimation.
 */
function getPathLengthSafe(path: string): number {
  // Estimation naive : on part du principe que le path encapsule les points de bezier
  // On compte les points M, L, Q, C et on prend la distance max comme approximation
  // Pour un path simple M x1 y1 Q cx cy x2 y2, longueur ≈ distance(x1y1 → cx cy → x2y2)
  // Pour les cas complexes, on fait du path parsing basique
  const segments = path.match(/[MLQCHVSTA][^MLQCHVSTA]*/gi) ?? [];
  let cx = 0;
  let cy = 0;
  let total = 0;
  for (const seg of segments) {
    const type = seg[0];
    const nums = seg
      .slice(1)
      .trim()
      .split(/[\s,]+/)
      .map(Number)
      .filter((n) => !Number.isNaN(n));
    if (type === "M" && nums.length >= 2) {
      cx = nums[0];
      cy = nums[1];
    } else if (type === "L" && nums.length >= 2) {
      total += Math.hypot(nums[0] - cx, nums[1] - cy);
      cx = nums[0];
      cy = nums[1];
    } else if (type === "Q" && nums.length >= 4) {
      // Approximation : somme des 2 segments
      total += Math.hypot(nums[0] - cx, nums[1] - cy) + Math.hypot(nums[2] - nums[0], nums[3] - nums[1]);
      cx = nums[2];
      cy = nums[3];
    } else if (type === "C" && nums.length >= 6) {
      total += Math.hypot(nums[0] - cx, nums[1] - cy) + Math.hypot(nums[2] - nums[0], nums[3] - nums[1]) + Math.hypot(nums[4] - nums[2], nums[5] - nums[3]);
      cx = nums[4];
      cy = nums[5];
    }
  }
  return total || 100;
}
