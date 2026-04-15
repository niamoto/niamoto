import { memo } from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, LabelList } from "recharts";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import taxonData from "../data/taxon-vedette.json";

interface DBHDistributionProps {
  /** Frame à partir de laquelle démarre la révélation. Default 0. */
  startFrame?: number;
  /** Frames entre chaque bin apparition. Default 3. */
  staggerFrames?: number;
}

/**
 * Distribution DBH d'Araucariaceae — bar chart vertical.
 * Référence visuelle : `/fr/taxons/948049381.html` widget « Distribution DBH ».
 *
 * Pattern Remotion :
 * - `recharts` en SVG pur, `isAnimationActive={false}` sur chaque Bar (règle skill)
 * - Animation frame-driven via `spring()` sur chaque Cell : transform `scaleY`
 * - Stagger `staggerFrames` entre bins = signature code vs screen recording
 */
export const DBHDistribution = memo<DBHDistributionProps>(({ startFrame = 0, staggerFrames = 3 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bins = taxonData.dbhDistribution.bins;
  const data = bins.map((b) => ({ range: b.range, value: b.value }));

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 24, right: 8, left: 0, bottom: 24 }}>
            <XAxis
              dataKey="range"
              tick={{ fill: teaserTheme.textSecondary, fontSize: 11, fontFamily: fontDisplay }}
              tickLine={false}
              axisLine={{ stroke: teaserTheme.border }}
              angle={-25}
              textAnchor="end"
              height={48}
            />
            <YAxis
              tick={{ fill: teaserTheme.textSecondary, fontSize: 11, fontFamily: fontDisplay }}
              tickLine={false}
              axisLine={{ stroke: teaserTheme.border }}
              width={32}
            />
            <Bar dataKey="value" isAnimationActive={false}>
              {data.map((_, idx) => {
                const localFrame = Math.max(0, frame - startFrame - idx * staggerFrames);
                const scale = spring({
                  frame: localFrame,
                  fps,
                  config: { damping: 14, stiffness: 200 },
                });
                const clampedScale = interpolate(scale, [0, 1], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });

                return (
                  <Cell
                    key={idx}
                    fill={teaserTheme.dbhBarPrimary}
                    style={{
                      transform: `scaleY(${clampedScale})`,
                      transformOrigin: "bottom",
                      transition: "none",
                    }}
                  />
                );
              })}
              <LabelList
                dataKey="value"
                position="top"
                fill={teaserTheme.textPrimary}
                fontSize={11}
                fontFamily={fontDisplay}
                formatter={(v: unknown) => (typeof v === "number" && v > 0 ? v.toFixed(2) : "")}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 11,
          color: teaserTheme.textSecondary,
          textAlign: "center",
          paddingTop: 4,
        }}
      >
        DBH (cm)
      </div>
    </div>
  );
});

DBHDistribution.displayName = "DBHDistribution";
