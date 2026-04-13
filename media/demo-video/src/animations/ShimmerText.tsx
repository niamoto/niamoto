import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";

interface ShimmerTextProps {
  text: string;
  baseColor?: string;
  shineColor?: string;
  fontSize?: number;
  fontWeight?: number;
}

/**
 * Text with an animated gradient shimmer sweeping left to right.
 * Uses interpolate() on backgroundPosition — no CSS @keyframes.
 */
export const ShimmerText: React.FC<ShimmerTextProps> = ({
  text,
  baseColor = "#3f3f46",
  shineColor = "#fafafa",
  fontSize = 32,
  fontWeight = 600,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Sweep from -100% to 200% over 80% of the scene duration
  const sweepDuration = Math.round(durationInFrames * 0.8);
  const position = interpolate(frame, [0, sweepDuration], [-100, 200], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <span
      style={{
        fontFamily: fontDisplay,
        fontSize,
        fontWeight,
        background: `linear-gradient(90deg, ${baseColor} 0%, ${shineColor} ${position}%, ${baseColor} ${position + 30}%)`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        WebkitTextFillColor: "transparent",
        display: "inline-block",
      }}
    >
      {text}
    </span>
  );
};
