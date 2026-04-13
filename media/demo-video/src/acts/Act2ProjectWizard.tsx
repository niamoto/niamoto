import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { MockButton } from "../ui/MockButton";
import { MockInput } from "../ui/MockInput";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";
import { MOCK_PROJECT } from "../shared/mockData";

/**
 * Act 2 — Project creation wizard.
 * No AppWindow (overlay card on Welcome-style background).
 * Cursor clicks input, types name, then clicks "Create".
 * Duration: 12s (360 frames @ 30fps)
 */
export const Act2ProjectWizard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Card entrance: spring scale
  const cardScale = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 120 },
    from: 0.9,
    to: 1,
  });

  const cardOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Typing starts after cursor clicks input (~frame 60 = 2s)
  const typingStart = 60;

  // Create button click at ~frame 260 (8.7s)
  const createClickFrame = 260;

  // Path display appears as name is typed
  const nameLength = MOCK_PROJECT.name.length;
  const framesPerChar = Math.round(fps / 12);
  const typingEndFrame = typingStart + nameLength * framesPerChar;

  const pathOpacity = interpolate(frame, [typingStart + 30, typingStart + 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Green flash on create
  const flashOpacity =
    frame >= createClickFrame + 5
      ? interpolate(frame, [createClickFrame + 5, createClickFrame + 25], [0.3, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 30%, #252530 0%, ${theme.bgDark} 70%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Card */}
      <div
        style={{
          transform: `scale(${cardScale})`,
          opacity: cardOpacity,
          background: theme.cardDark,
          borderRadius: 14,
          padding: "40px 48px",
          width: 500,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
        }}
      >
        {/* Mini logo */}
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: `linear-gradient(135deg, ${theme.forestGreen}, #26A69A)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 24,
              fontWeight: 700,
              color: "white",
            }}
          >
            N
          </span>
        </div>

        {/* Title */}
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 22,
              fontWeight: 700,
              color: theme.textWhite,
              marginBottom: 4,
            }}
          >
            Create New Project
          </div>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 14,
              color: theme.textMuted,
            }}
          >
            Set up a new Niamoto project
          </div>
        </div>

        {/* Form */}
        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
          <MockInput
            label="Project Name"
            text={MOCK_PROJECT.name}
            typingStartFrame={typingStart}
            placeholder="my-ecological-project"
            mono
          />

          {/* Path display */}
          <div
            style={{
              opacity: pathOpacity,
              background: "rgba(255,255,255,0.03)",
              borderRadius: 6,
              padding: "8px 12px",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            <span
              style={{
                fontFamily: fontDisplay,
                fontSize: 12,
                color: theme.textMuted,
              }}
            >
              {MOCK_PROJECT.path}
            </span>
          </div>
        </div>

        {/* Buttons */}
        <div style={{ display: "flex", gap: 12, width: "100%", justifyContent: "flex-end", marginTop: 8 }}>
          <MockButton label="Cancel" variant="outline" />
          <MockButton
            label="Create Project"
            variant="gradient"
            clickAtFrame={createClickFrame}
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            }
          />
        </div>
      </div>

      {/* Green flash overlay */}
      {flashOpacity > 0 && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(circle at center, ${theme.lightGreen}40 0%, transparent 70%)`,
            opacity: flashOpacity,
          }}
        />
      )}

      {/* Cursor */}
      <CursorOverlay waypoints={CURSOR_PATHS.act2} />
    </AbsoluteFill>
  );
};
