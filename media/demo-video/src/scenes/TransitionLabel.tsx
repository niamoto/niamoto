import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

interface TransitionLabelProps {
  text: string;
  durationInFrames?: number;
}

/**
 * Contextual label shown at the start of an act.
 * Rendered as a <Sequence> within the first frames of Acts 3, 5, 6.
 * Fade-in 10f, hold, fade-out 10f.
 */
export const TransitionLabel: React.FC<TransitionLabelProps> = ({
  text,
  durationInFrames = 30,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [0, 10, durationInFrames - 10, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: theme.bgDark,
        opacity,
        zIndex: 50,
      }}
    >
      <span
        style={{
          fontFamily: fontDisplay,
          fontSize: 32,
          fontWeight: 500,
          color: theme.textMuted,
          letterSpacing: 0.5,
        }}
      >
        {text}
      </span>
    </AbsoluteFill>
  );
};
