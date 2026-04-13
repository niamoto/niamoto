import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { theme } from "../shared/theme";
import { fontDisplay, fontMono } from "../shared/fonts";

const STATS = [
  { value: "3,500+", label: "Species documented" },
  { value: "120k+", label: "Occurrences recorded" },
  { value: "450+", label: "Study plots" },
  { value: "100%", label: "Open source" },
] as const;

export const StatsOrMap: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title entrance
  const titleProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bgDark,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 60,
      }}
    >
      {/* Section title */}
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 40,
          fontWeight: 600,
          color: theme.lightGreen,
          opacity: interpolate(titleProgress, [0, 1], [0, 1]),
          transform: `translateY(${interpolate(titleProgress, [0, 1], [20, 0])}px)`,
        }}
      >
        Built for real-world ecological data
      </div>

      {/* Stats grid */}
      <div
        style={{
          display: "flex",
          gap: 80,
        }}
      >
        {STATS.map((stat, i) => {
          const delay = Math.round((0.3 + i * 0.2) * fps);
          const progress = spring({
            frame,
            fps,
            config: { damping: 15, stiffness: 200 },
            delay,
          });
          const scale = interpolate(progress, [0, 1], [0.8, 1]);
          const opacity = interpolate(progress, [0, 1], [0, 1]);

          return (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 12,
                opacity,
                transform: `scale(${scale})`,
              }}
            >
              <span
                style={{
                  fontFamily: fontMono,
                  fontSize: 52,
                  fontWeight: 500,
                  color: theme.textWhite,
                }}
              >
                {stat.value}
              </span>
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 20,
                  fontWeight: 400,
                  color: theme.textMuted,
                }}
              >
                {stat.label}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
