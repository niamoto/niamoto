import { useCurrentFrame, interpolate, Easing } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

interface ProgressBarProps {
  startFrame: number;
  durationInFrames: number;
  label?: string;
  steps?: string[];
}

/**
 * Animated progress bar with optional step labels.
 * Interpolates from 0% to 100% with ease-out.
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  startFrame,
  durationInFrames,
  label,
  steps,
}) => {
  const frame = useCurrentFrame();

  const rawProgress = interpolate(
    frame,
    [startFrame, startFrame + durationInFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // Ease-out for natural feel
  const progress = Easing.out(Easing.cubic)(rawProgress);
  const percent = Math.round(progress * 100);

  // Which step is active (if steps provided)
  const activeStepIndex = steps
    ? Math.min(Math.floor(progress * steps.length), steps.length - 1)
    : -1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
      {/* Label + percentage */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {label && (
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 14,
              fontWeight: 500,
              color: theme.textWhite,
            }}
          >
            {label}
          </span>
        )}
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 13,
            fontWeight: 600,
            color: theme.lightGreen,
          }}
        >
          {percent}%
        </span>
      </div>

      {/* Bar track */}
      <div
        style={{
          height: 6,
          borderRadius: 3,
          background: theme.cardDark,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progress * 100}%`,
            borderRadius: 3,
            background: `linear-gradient(90deg, ${theme.forestGreen}, ${theme.lightGreen})`,
          }}
        />
      </div>

      {/* Steps */}
      {steps && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
          {steps.map((step, i) => {
            const isDone = i < activeStepIndex;
            const isActive = i === activeStepIndex;

            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {/* Step indicator */}
                <div
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isDone ? theme.lightGreen : isActive ? `${theme.lightGreen}30` : "rgba(255,255,255,0.06)",
                    border: isActive ? `1.5px solid ${theme.lightGreen}` : "none",
                  }}
                >
                  {isDone && (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </div>
                <span
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 13,
                    color: isDone ? theme.lightGreen : isActive ? theme.textWhite : theme.textMuted,
                    fontWeight: isActive ? 500 : 400,
                  }}
                >
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
