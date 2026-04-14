import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";
import { AppWindow } from "../ui/AppWindow";
import { NiamotoLogo } from "../ui/NiamotoLogo";

const WelcomeActionCard: React.FC<{
  label: string;
  icon: React.ReactNode;
  variant: "primary" | "secondary";
  clickAtFrame?: number;
}> = ({ label, icon, variant, clickAtFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let scale = 1;
  if (clickAtFrame !== undefined && frame >= clickAtFrame) {
    scale = spring({
      frame: frame - clickAtFrame,
      fps,
      config: { damping: 12, stiffness: 210, mass: 0.55 },
      from: 0.95,
      to: 1,
    });
  }

  const isPrimary = variant === "primary";

  return (
    <div
      style={{
        width: 330,
        height: 144,
        borderRadius: 8,
        border: isPrimary ? "none" : `1px solid ${theme.borderStrong}`,
        background: isPrimary ? theme.forestGreen : "#FFFFFF",
        boxShadow: isPrimary
          ? "0 14px 34px rgba(46, 125, 50, 0.18)"
          : "0 8px 24px rgba(15, 23, 42, 0.06)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 18,
        color: isPrimary ? "#FFFFFF" : "#111827",
        fontFamily: fontDisplay,
        fontSize: 17,
        fontWeight: 500,
        transform: `scale(${scale})`,
      }}
    >
      {icon}
      <div>{label}</div>
    </div>
  );
};

export const Act1Welcome: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

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

  const taglineOpacity = interpolate(frame, [15, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const buttonsOpacity = interpolate(frame, [28, 42], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const buttonsY = interpolate(frame, [28, 42], [18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const toggleOpacity = interpolate(frame, [42, 54], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const clickFrame = 39;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${theme.canvasGradientStart}, ${theme.canvasGradientEnd})`,
      }}
    >
      <AppWindow showSidebar={false} showTopBar={false}>
        <div
          style={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: theme.windowBg,
          }}
        >
          <div
            style={{
              transform: `scale(${logoScale})`,
              opacity: logoOpacity,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <NiamotoLogo width={112} />
          </div>

          <div
            style={{
              opacity: logoOpacity,
              marginTop: 26,
              fontFamily: fontDisplay,
              fontSize: 56,
              fontWeight: 700,
              color: theme.charcoal,
              letterSpacing: -1.5,
            }}
          >
            Niamoto
          </div>

          <div
            style={{
              opacity: taglineOpacity,
              marginTop: 8,
              fontFamily: fontDisplay,
              fontSize: 16,
              fontWeight: 400,
              color: theme.textMuted,
            }}
          >
            Plateforme de données écologiques
          </div>

          <div
            style={{
              display: "flex",
              gap: 18,
              marginTop: 62,
              opacity: buttonsOpacity,
              transform: `translateY(${buttonsY}px)`,
            }}
          >
            <WelcomeActionCard
              label="Créer un nouveau projet"
              variant="primary"
              clickAtFrame={clickFrame}
              icon={
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              }
            />
            <WelcomeActionCard
              label="Ouvrir un projet"
              variant="secondary"
              icon={
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={theme.textDark} strokeWidth="1.9">
                  <path d="M20 18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2z" />
                </svg>
              }
            />
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              width: 678,
              marginTop: 42,
              opacity: toggleOpacity,
              fontFamily: fontDisplay,
              fontSize: 14,
              color: theme.textDark,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.9">
                <line x1="5" y1="6" x2="19" y2="6" />
                <line x1="5" y1="18" x2="19" y2="18" />
                <line x1="5" y1="12" x2="12" y2="12" />
                <circle cx="15.5" cy="6" r="1.8" fill="#FFFFFF" />
                <circle cx="8.5" cy="12" r="1.8" fill="#FFFFFF" />
                <circle cx="14.5" cy="18" r="1.8" fill="#FFFFFF" />
              </svg>
              <span>Charger automatiquement le dernier projet au démarrage</span>
            </div>
            <div
              style={{
                width: 42,
                height: 24,
                borderRadius: 12,
                background: "#0B8E34",
                padding: 2,
                display: "flex",
                justifyContent: "flex-end",
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 10,
                  background: "#FFFFFF",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.18)",
                }}
              />
            </div>
          </div>
        </div>
      </AppWindow>

      <CursorOverlay waypoints={CURSOR_PATHS.act1} />
    </AbsoluteFill>
  );
};
