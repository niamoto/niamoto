import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { theme } from "../shared/theme";
import { fontDisplay } from "../shared/fonts";

export const IntroLogo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo scale: spring entrance
  const logoScale = spring({ frame, fps, config: { damping: 200 } });

  // Logo opacity: quick fade in
  const logoOpacity = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Tagline: delayed fade in + slide up
  const taglineProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
    delay: Math.round(0.6 * fps),
  });
  const taglineY = interpolate(taglineProgress, [0, 1], [20, 0]);
  const taglineOpacity = interpolate(taglineProgress, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bgDark,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <Img
        src={staticFile("logo/niamoto_logo.png")}
        style={{
          width: 200,
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
        }}
      />
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 28,
          fontWeight: 500,
          color: theme.textMuted,
          marginTop: 24,
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          letterSpacing: 1,
        }}
      >
        Your ecological data platform
      </div>
    </AbsoluteFill>
  );
};
