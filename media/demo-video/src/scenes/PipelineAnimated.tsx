import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { theme } from "../shared/theme";
import { fontDisplay } from "../shared/fonts";

type PipelineMode = "problem" | "pipeline";

export type PipelineAnimatedProps = {
  mode: PipelineMode;
};

const ProblemText: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const words = ["Ecological", "data", "is", "scattered,", "complex,", "and", "hard", "to", "publish."];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bgDark,
        justifyContent: "center",
        alignItems: "center",
        padding: 120,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 16,
        }}
      >
        {words.map((word, i) => {
          const delay = i * 3;
          const opacity = interpolate(frame, [delay, delay + 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const y = interpolate(frame, [delay, delay + 8], [12, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <span
              key={i}
              style={{
                fontFamily: fontDisplay,
                fontSize: 56,
                fontWeight: 600,
                color: theme.textWhite,
                opacity,
                transform: `translateY(${y}px)`,
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const STEPS = [
  { label: "Import", icon: "↓", color: theme.steelBlue },
  { label: "Transform", icon: "⚙", color: theme.forestGreen },
  { label: "Export", icon: "↗", color: theme.lightGreen },
] as const;

const PipelineDiagram: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bgDark,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
        }}
      >
        {STEPS.map((step, i) => {
          const stepDelay = Math.round(i * 0.8 * fps);
          const progress = spring({
            frame,
            fps,
            config: { damping: 200 },
            delay: stepDelay,
          });
          const scale = interpolate(progress, [0, 1], [0.7, 1]);
          const opacity = interpolate(progress, [0, 1], [0, 1]);

          // Arrow between steps
          const arrowDelay = Math.round((i * 0.8 + 0.4) * fps);
          const arrowProgress = spring({
            frame,
            fps,
            config: { damping: 200 },
            delay: arrowDelay,
          });
          const arrowWidth = interpolate(arrowProgress, [0, 1], [0, 80]);

          return (
            <div key={i} style={{ display: "flex", alignItems: "center" }}>
              {i > 0 && (
                <div
                  style={{
                    width: arrowWidth,
                    height: 3,
                    backgroundColor: theme.textMuted,
                    marginLeft: 8,
                    marginRight: 8,
                    borderRadius: 2,
                  }}
                />
              )}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 16,
                  opacity,
                  transform: `scale(${scale})`,
                }}
              >
                <div
                  style={{
                    width: 120,
                    height: 120,
                    borderRadius: 24,
                    backgroundColor: step.color,
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    fontSize: 48,
                  }}
                >
                  {step.icon}
                </div>
                <span
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 28,
                    fontWeight: 600,
                    color: theme.textWhite,
                  }}
                >
                  {step.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const PipelineAnimated: React.FC<PipelineAnimatedProps> = ({ mode }) => {
  if (mode === "problem") {
    return <ProblemText />;
  }
  return <PipelineDiagram />;
};
