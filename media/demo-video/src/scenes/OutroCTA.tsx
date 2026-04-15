import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { theme } from "../shared/theme";
import { fontDisplay, fontMono } from "../shared/fonts";

export const OutroCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo entrance
  const logoProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });
  const logoScale = interpolate(logoProgress, [0, 1], [0.8, 1]);
  const logoOpacity = interpolate(logoProgress, [0, 1], [0, 1]);

  // GitHub: delayed entrance
  const ghProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
    delay: Math.round(0.4 * fps),
  });
  const ghOpacity = interpolate(ghProgress, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bgDark,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 24,
      }}
    >
      <Img
        src={staticFile("logo/niamoto_logo.png")}
        style={{
          width: 160,
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
        }}
      />

      <div
        style={{
          fontFamily: fontMono,
          fontSize: 20,
          fontWeight: 400,
          color: theme.textMuted,
          opacity: ghOpacity,
        }}
      >
        github.com/niamoto/niamoto
      </div>
    </AbsoluteFill>
  );
};
