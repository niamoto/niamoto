import { memo } from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import taxonData from "../data/taxon-vedette.json";

interface SubstrateDonutProps {
  startFrame?: number;
  /** Durée du reveal angulaire en frames. Default 30. */
  revealDurationFrames?: number;
}

/**
 * Distribution substrat — donut chart.
 * Référence visuelle : `/fr/taxons/948049381.html` widget « Distribution substrat »
 * (82.8% Ultramafique / 17.1% non-Ultramafique pour Araucariaceae).
 *
 * Le reveal s'effectue via `endAngle` interpolé de `startAngle` vers `endAngle` final.
 * Recharts Pie accepte `startAngle` et `endAngle` en degrés (trigonométrique standard,
 * 0 = droite, 90 = haut). On interpole `endAngle` frame-driven.
 */
export const SubstrateDonut = memo<SubstrateDonutProps>(({ startFrame = 0, revealDurationFrames = 30 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const segments = taxonData.substrate.segments;

  const localFrame = Math.max(0, frame - startFrame);
  const revealProgress = spring({
    frame: localFrame,
    fps,
    durationInFrames: revealDurationFrames,
    config: { damping: 18, stiffness: 120 },
  });
  const clampedProgress = interpolate(revealProgress, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Recharts : endAngle va de 90 (start position = 12h) à 90 - 360 = -270 (tour complet horaire)
  const startAngle = 90;
  const targetEndAngle = -270;
  const currentEndAngle = interpolate(clampedProgress, [0, 1], [startAngle, targetEndAngle], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Opacité des labels : apparaît une fois le reveal terminé (frame > startFrame + revealDuration)
  const labelOpacity = interpolate(
    localFrame,
    [revealDurationFrames, revealDurationFrames + 8],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={segments}
            dataKey="value"
            cx="50%"
            cy="50%"
            innerRadius="48%"
            outerRadius="80%"
            startAngle={startAngle}
            endAngle={currentEndAngle}
            isAnimationActive={false}
            stroke={teaserTheme.cardWhite}
            strokeWidth={2}
          >
            {segments.map((seg, idx) => (
              <Cell key={idx} fill={seg.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      {/* Labels flottants — positionnés manuellement pour contrôler l'apparition */}
      <div
        style={{
          position: "absolute",
          left: "14%",
          top: "18%",
          fontFamily: fontDisplay,
          fontSize: 13,
          fontWeight: 600,
          color: teaserTheme.textPrimary,
          opacity: labelOpacity,
          transform: `rotate(-22deg)`,
          transformOrigin: "left center",
          pointerEvents: "none",
        }}
      >
        {segments[1].label} {segments[1].value.toFixed(1)}%
      </div>
      <div
        style={{
          position: "absolute",
          left: "32%",
          bottom: "10%",
          fontFamily: fontDisplay,
          fontSize: 13,
          fontWeight: 600,
          color: teaserTheme.textPrimary,
          opacity: labelOpacity,
          transform: `rotate(12deg)`,
          transformOrigin: "left center",
          pointerEvents: "none",
        }}
      >
        {segments[0].label} {segments[0].value.toFixed(1)}%
      </div>
    </div>
  );
});

SubstrateDonut.displayName = "SubstrateDonut";
