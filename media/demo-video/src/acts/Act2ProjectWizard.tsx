import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";
import { fontDisplay, fontMono } from "../shared/fonts";
import { MOCK_PROJECT } from "../shared/mockData";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { NiamotoLogo } from "../ui/NiamotoLogo";

const WizardButton: React.FC<{
  label: string;
  variant: "primary" | "secondary";
  icon: React.ReactNode;
  clickAtFrame?: number;
}> = ({ label, variant, icon, clickAtFrame }) => {
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
        height: 44,
        padding: isPrimary ? "0 18px" : "0 16px",
        borderRadius: 6,
        border: isPrimary ? "none" : `1px solid ${theme.borderStrong}`,
        background: isPrimary ? theme.forestGreen : "#FFFFFF",
        color: isPrimary ? "#FFFFFF" : theme.textDark,
        boxShadow: isPrimary ? "0 10px 26px rgba(46, 125, 50, 0.16)" : "none",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
        fontFamily: fontDisplay,
        fontSize: 16,
        fontWeight: 500,
        transform: `scale(${scale})`,
      }}
    >
      {icon}
      <span>{label}</span>
    </div>
  );
};

export const Act2ProjectWizard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardScale = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 120 },
    from: 0.975,
    to: 1,
  });

  const cardOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const typingStart = 58;
  const locationFocusFrame = 150;
  const locationTypingStart = 164;
  const pathRevealFrame = 236;
  const createClickFrame = 272;

  const nameLength = MOCK_PROJECT.name.length;
  const framesPerChar = Math.round(fps / 12);
  const typingFrame = Math.max(0, frame - typingStart);
  const revealedCount = Math.min(
    nameLength,
    Math.floor(typingFrame / framesPerChar),
  );
  const locationLength = MOCK_PROJECT.selectedParentPath.length;
  const locationTypingFrame = Math.max(0, frame - locationTypingStart);
  const revealedLocationCount = Math.min(
    locationLength,
    Math.floor(locationTypingFrame / framesPerChar),
  );
  const nameCursorVisible = revealedCount < nameLength || Math.floor(frame / 15) % 2 === 0;
  const locationCursorVisible =
    revealedLocationCount < locationLength || Math.floor(frame / 15) % 2 === 0;
  const isNameFieldFocused = frame < locationFocusFrame;
  const isLocationFieldFocused = frame >= locationFocusFrame && frame < pathRevealFrame;
  const parentPath = frame >= locationTypingStart
    ? MOCK_PROJECT.selectedParentPath.substring(0, revealedLocationCount)
    : "";
  const showFullPath = frame >= pathRevealFrame;

  const flashOpacity =
    frame >= createClickFrame + 5
      ? interpolate(frame, [createClickFrame + 5, createClickFrame + 25], [0.2, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

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
            alignItems: "center",
            justifyContent: "center",
            background: theme.windowBg,
          }}
        >
          <div
            style={{
              width: 640,
              opacity: cardOpacity,
              transform: `scale(${cardScale})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <NiamotoLogo width={96} />

            <div
              style={{
                marginTop: 28,
                fontFamily: fontDisplay,
                fontSize: 32,
                lineHeight: 1.05,
                fontWeight: 700,
                color: theme.textDark,
                letterSpacing: -0.8,
              }}
            >
              Créer un nouveau projet
            </div>

            <div
              style={{
                marginTop: 8,
                fontFamily: fontDisplay,
                fontSize: 16,
                color: theme.textMuted,
              }}
            >
              Configurer un nouveau projet Niamoto
            </div>

            <div
              style={{
                width: "100%",
                marginTop: 38,
                background: "#FFFFFF",
                borderRadius: 10,
                border: `1px solid ${theme.border}`,
                boxShadow: "0 12px 28px rgba(15, 23, 42, 0.06)",
                padding: "28px 26px 22px",
                boxSizing: "border-box",
              }}
            >
              <div
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 17,
                  fontWeight: 500,
                  color: theme.textDark,
                }}
              >
                Nom du projet
              </div>

              <div
                style={{
                  marginTop: 9,
                  height: 46,
                  borderRadius: 10,
                  border: isNameFieldFocused
                    ? `2px solid ${theme.forestGreen}`
                    : `1px solid ${theme.borderStrong}`,
                  background: "#FFFFFF",
                  boxShadow: isNameFieldFocused
                    ? "0 0 0 3px rgba(46, 125, 50, 0.08)"
                    : "none",
                  display: "flex",
                  alignItems: "center",
                  padding: "0 14px",
                  boxSizing: "border-box",
                }}
                >
                  <span
                    style={{
                      fontFamily: fontMono,
                      fontSize: 15,
                      color: revealedCount === 0 ? theme.textSoft : "#4B5563",
                    }}
                    >
                    {revealedCount === 0
                      ? "my-ecological-project"
                      : MOCK_PROJECT.name.substring(0, revealedCount)}
                  </span>
                  {isNameFieldFocused && nameCursorVisible && (
                    <span
                      style={{
                        width: 2,
                        height: 18,
                        marginLeft: 1,
                        background: theme.forestGreen,
                      }}
                    />
                  )}
                </div>

              <div
                style={{
                  marginTop: 24,
                  fontFamily: fontDisplay,
                  fontSize: 17,
                  fontWeight: 500,
                  color: theme.textDark,
                }}
              >
                Emplacement
              </div>

              <div
                style={{
                  marginTop: 9,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <div
                  style={{
                    flex: 1,
                    height: 46,
                    borderRadius: 10,
                    border: isLocationFieldFocused
                      ? `2px solid ${theme.forestGreen}`
                      : `1px solid ${theme.borderStrong}`,
                    background: "#FFFFFF",
                    boxShadow: isLocationFieldFocused
                      ? "0 0 0 3px rgba(46, 125, 50, 0.08)"
                      : "none",
                    display: "flex",
                    alignItems: "center",
                    padding: "0 14px",
                    boxSizing: "border-box",
                    fontFamily: fontMono,
                    fontSize: 15,
                    color: parentPath.length > 0 ? "#4B5563" : theme.textSoft,
                  }}
                >
                  <span>{parentPath.length > 0 ? parentPath : "Saisir un emplacement"}</span>
                  {isLocationFieldFocused && locationCursorVisible && (
                    <span
                      style={{
                        width: 2,
                        height: 18,
                        marginLeft: 1,
                        background: theme.forestGreen,
                      }}
                    />
                  )}
                </div>
                <div
                  style={{
                    width: 46,
                    height: 46,
                    borderRadius: 10,
                    border: `1px solid ${theme.borderStrong}`,
                    background: "#FFFFFF",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.9">
                    <path d="M20 18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
              </div>

              <div
                style={{
                  marginTop: 24,
                  fontFamily: fontDisplay,
                  fontSize: 17,
                  fontWeight: 500,
                  color: theme.textMuted,
                }}
              >
                Répertoire du projet
              </div>

              <div
                style={{
                  marginTop: 9,
                  height: 46,
                  borderRadius: 10,
                  border: `1px solid ${theme.borderStrong}`,
                  background: "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  padding: "0 14px",
                  boxSizing: "border-box",
                  fontFamily: fontMono,
                  fontSize: 15,
                  color: showFullPath ? "#4B5563" : theme.textSoft,
                }}
              >
                {showFullPath ? MOCK_PROJECT.fullPath : "/Users/username/Projects/my-ecology-project"}
              </div>
            </div>

            <div
              style={{
                width: "100%",
                marginTop: 24,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <WizardButton
                label="Annuler"
                variant="secondary"
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={theme.textDark} strokeWidth="2.1">
                    <path d="m15 18-6-6 6-6" />
                  </svg>
                }
              />

              <WizardButton
                label="Créer le projet"
                variant="primary"
                clickAtFrame={createClickFrame}
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.4">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                }
              />
            </div>
          </div>
        </div>
      </AppWindow>

      {flashOpacity > 0 && (
        <AbsoluteFill
          style={{
            background: "radial-gradient(circle at center, rgba(46, 125, 50, 0.18) 0%, transparent 68%)",
            opacity: flashOpacity,
          }}
        />
      )}

      <CursorOverlay waypoints={CURSOR_PATHS.act2} startFrame={56} />
    </AbsoluteFill>
  );
};
