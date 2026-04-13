import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Img, staticFile } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { MockButton } from "../ui/MockButton";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";

/**
 * Act 1 — Welcome screen.
 * Full-screen (no AppWindow), logo centered, two CTA buttons.
 * Cursor arrives and clicks "Create New Project".
 * Duration: 8s (240 frames @ 30fps)
 */
export const Act1Welcome: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo entrance: spring scale
  const logoScale = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 100 },
    from: 0.8,
    to: 1,
  });

  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Tagline: fade in delayed
  const taglineOpacity = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Buttons: fade in after tagline
  const buttonsOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const buttonsY = interpolate(frame, [30, 45], [15, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Cursor clicks "Create New Project" at ~frame 150 (5s)
  const clickFrame = 150;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 30%, #252530 0%, ${theme.bgDark} 70%)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          transform: `scale(${logoScale})`,
          opacity: logoOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* Logo icon — gradient square with N */}
        <div
          style={{
            width: 96,
            height: 96,
            borderRadius: 20,
            background: `linear-gradient(135deg, ${theme.forestGreen}, #26A69A)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 8px 32px rgba(46, 125, 50, 0.3)",
          }}
        >
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 48,
              fontWeight: 700,
              color: "white",
            }}
          >
            N
          </span>
        </div>
      </div>

      {/* Title */}
      <div style={{ opacity: logoOpacity, marginTop: 20 }}>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 42,
            fontWeight: 700,
            background: `linear-gradient(135deg, ${theme.lightGreen}, #26A69A)`,
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Niamoto
        </span>
      </div>

      {/* Tagline */}
      <div style={{ opacity: taglineOpacity, marginTop: 8 }}>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 18,
            color: theme.textMuted,
            fontWeight: 400,
          }}
        >
          Ecological Data Platform
        </span>
      </div>

      {/* Buttons */}
      <div
        style={{
          display: "flex",
          gap: 16,
          marginTop: 48,
          opacity: buttonsOpacity,
          transform: `translateY(${buttonsY}px)`,
        }}
      >
        <MockButton
          label="Create New Project"
          variant="gradient"
          clickAtFrame={clickFrame}
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          }
        />
        <MockButton
          label="Open Project"
          variant="outline"
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          }
        />
      </div>

      {/* Cursor */}
      <CursorOverlay waypoints={CURSOR_PATHS.act1} />
    </AbsoluteFill>
  );
};
