import { memo } from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer } from "recharts";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import taxonData from "../data/taxon-vedette.json";

interface PhenologyCalendarProps {
  startFrame?: number;
  /** Frames pour révéler tous les mois. Default 24 (= 0.8 s à 30fps). */
  revealDurationFrames?: number;
}

/**
 * Phénologie 12 mois — bar chart empilé.
 * Référence visuelle : `/fr/taxons/948049381.html` widget « Phénologie ».
 *
 * Reveal gauche → droite : `clip-path: inset()` animé frame-driven.
 * Plus simple et performant qu'un stagger sur chaque Cell.
 */
export const PhenologyCalendar = memo<PhenologyCalendarProps>(({ startFrame = 0, revealDurationFrames = 24 }) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);

  const revealProgress = interpolate(localFrame, [0, revealDurationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Transpose data pour recharts stacked : [{ month: "Jan", fruit: 2, fleur: 3, autre: 1 }, ...]
  const months = taxonData.phenology.months;
  const series = taxonData.phenology.series;
  const data = months.map((month, idx) => {
    const row: Record<string, number | string> = { month };
    for (const s of series) {
      row[s.name] = s.values[idx];
    }
    return row;
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        clipPath: `inset(0 ${(1 - revealProgress) * 100}% 0 0)`,
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 8, left: 0, bottom: 16 }}>
          <XAxis
            dataKey="month"
            tick={{ fill: teaserTheme.textSecondary, fontSize: 11, fontFamily: fontDisplay }}
            tickLine={false}
            axisLine={{ stroke: teaserTheme.border }}
          />
          <YAxis
            tick={{ fill: teaserTheme.textSecondary, fontSize: 11, fontFamily: fontDisplay }}
            tickLine={false}
            axisLine={{ stroke: teaserTheme.border }}
            width={32}
          />
          {series.map((s) => (
            <Bar key={s.name} dataKey={s.name} stackId="pheno" fill={s.color} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
});

PhenologyCalendar.displayName = "PhenologyCalendar";
