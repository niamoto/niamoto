import { memo } from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { BarChart, Bar, XAxis, YAxis, Cell, LabelList, ResponsiveContainer } from "recharts";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import taxonData from "../data/taxon-vedette.json";

interface OccurrencesBarChartProps {
  startFrame?: number;
  staggerFrames?: number;
  /** Nombre max de sous-taxons à afficher. Default 10 (= tous). */
  limit?: number;
}

/**
 * Sous-taxons principaux d'Araucariaceae — bar chart horizontal multicolore.
 * Référence visuelle : `/fr/taxons/948049381.html` widget « Sous-taxons principaux ».
 *
 * Chaque Cell a sa propre couleur (extrait de `subTaxons[].color` dans taxon-vedette.json).
 * Animation scaleX frame-driven stagger.
 */
export const OccurrencesBarChart = memo<OccurrencesBarChartProps>(({ startFrame = 0, staggerFrames = 4, limit = 10 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const data = taxonData.subTaxons.slice(0, limit);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 48, left: 8, bottom: 8 }}>
        <XAxis
          type="number"
          tick={{ fill: teaserTheme.textSecondary, fontSize: 10, fontFamily: fontDisplay }}
          tickLine={false}
          axisLine={{ stroke: teaserTheme.border }}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={132}
          tick={{ fill: teaserTheme.textPrimary, fontSize: 11, fontFamily: fontDisplay, fontStyle: "italic" }}
          tickLine={false}
          axisLine={false}
        />
        <Bar dataKey="count" isAnimationActive={false} barSize={14} radius={[0, 2, 2, 0]}>
          {data.map((subTaxon, idx) => {
            const localFrame = Math.max(0, frame - startFrame - idx * staggerFrames);
            const scale = spring({
              frame: localFrame,
              fps,
              config: { damping: 14, stiffness: 180 },
            });
            const clampedScale = interpolate(scale, [0, 1], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });

            return (
              <Cell
                key={idx}
                fill={subTaxon.color}
                style={{
                  transform: `scaleX(${clampedScale})`,
                  transformOrigin: "left center",
                  transition: "none",
                }}
              />
            );
          })}
          <LabelList
            dataKey="count"
            position="right"
            fill={teaserTheme.textPrimary}
            fontSize={11}
            fontFamily={fontDisplay}
            fontWeight={600}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
});

OccurrencesBarChart.displayName = "OccurrencesBarChart";
