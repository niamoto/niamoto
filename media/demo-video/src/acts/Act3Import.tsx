import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Sequence } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { FileUploadZone } from "../ui/FileUploadZone";
import { FileTypeChip } from "../ui/FileTypeChip";
import { YamlPreview } from "../ui/YamlPreview";
import { ShimmerText } from "../animations/ShimmerText";
import { TransitionLabel } from "../scenes/TransitionLabel";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";
import { FILE_TYPES, MOCK_YAML } from "../shared/mockData";

/**
 * Act 3 — Import data.
 * First act with AppWindow + sidebar (slide-in).
 * Three internal phases: Upload → Auto-config → YAML review.
 * Duration: 20s (600 frames @ 30fps)
 */
export const Act3Import: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sec = (s: number) => Math.round(s * fps);

  // Phase boundaries
  const PHASE_UPLOAD_END = sec(7);
  const PHASE_CONFIG_END = sec(13);

  // File chips enter staggered starting at frame 60 (2s)
  const chipStartFrame = 60;
  const chipStagger = sec(1);

  // Phase indicator
  const isUploadPhase = frame < PHASE_UPLOAD_END;
  const isConfigPhase = frame >= PHASE_UPLOAD_END && frame < PHASE_CONFIG_END;
  const isReviewPhase = frame >= PHASE_CONFIG_END;

  // Header text and subtitle
  const headerTitle = "Import Data";
  const headerSubtitle = isUploadPhase
    ? "Drop your data files to get started"
    : isConfigPhase
      ? "Analyzing your data..."
      : "Review your import configuration";

  // Phase transitions
  const uploadOpacity = interpolate(
    frame,
    [PHASE_UPLOAD_END - 10, PHASE_UPLOAD_END],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const configOpacity = isConfigPhase
    ? interpolate(
        frame,
        [PHASE_UPLOAD_END, PHASE_UPLOAD_END + 10, PHASE_CONFIG_END - 10, PHASE_CONFIG_END],
        [0, 1, 1, 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      )
    : 0;

  const reviewOpacity = isReviewPhase
    ? interpolate(frame, [PHASE_CONFIG_END, PHASE_CONFIG_END + 15], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  // Sparkle pulse for auto-config phase
  const sparkleScale = isConfigPhase
    ? 1 + 0.1 * Math.sin(((frame - PHASE_UPLOAD_END) / fps) * Math.PI * 3)
    : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgDark }}>
      <AppWindow showSidebar activeSidebarItem="data">
        <div style={{ padding: "28px 32px", height: "100%", display: "flex", flexDirection: "column" }}>
          {/* Header */}
          <div style={{ marginBottom: 24 }}>
            <h1
              style={{
                fontFamily: fontDisplay,
                fontSize: 22,
                fontWeight: 700,
                color: theme.textWhite,
                margin: 0,
              }}
            >
              {headerTitle}
            </h1>
            <p
              style={{
                fontFamily: fontDisplay,
                fontSize: 14,
                color: theme.textMuted,
                margin: "6px 0 0",
              }}
            >
              {headerSubtitle}
            </p>
          </div>

          {/* Content area */}
          <div style={{ flex: 1, position: "relative" }}>
            {/* Phase 1: Upload */}
            {frame < PHASE_UPLOAD_END + 10 && (
              <div style={{ opacity: uploadOpacity, position: "absolute", inset: 0 }}>
                <FileUploadZone filesEnterFrame={chipStartFrame}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {FILE_TYPES.map((ft, i) => (
                      <FileTypeChip
                        key={ft.type}
                        label={ft.label}
                        color={ft.color}
                        extensions={ft.extensions}
                        enterAtFrame={chipStartFrame + i * chipStagger}
                      />
                    ))}
                  </div>
                </FileUploadZone>
              </div>
            )}

            {/* Phase 2: Auto-configuration */}
            {isConfigPhase && (
              <div
                style={{
                  opacity: configOpacity,
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 20,
                }}
              >
                {/* Sparkle icon */}
                <div style={{ transform: `scale(${sparkleScale})` }}>
                  <svg width="48" height="48" viewBox="0 0 24 24" fill={theme.steelBlue} stroke="none">
                    <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />
                  </svg>
                </div>

                <Sequence from={0} durationInFrames={PHASE_CONFIG_END - PHASE_UPLOAD_END}>
                  <ShimmerText
                    text="Auto-configuration..."
                    fontSize={20}
                    fontWeight={600}
                    baseColor={theme.textMuted}
                    shineColor={theme.textWhite}
                  />
                </Sequence>

                <span
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 13,
                    color: theme.textMuted,
                  }}
                >
                  Detecting file types and mapping fields
                </span>
              </div>
            )}

            {/* Phase 3: YAML Review */}
            {isReviewPhase && (
              <div style={{ opacity: reviewOpacity, maxWidth: 600 }}>
                <YamlPreview yaml={MOCK_YAML} enterAtFrame={0} />
              </div>
            )}
          </div>
        </div>
      </AppWindow>

      {/* Transition label — first 30 frames */}
      <Sequence from={0} durationInFrames={30}>
        <TransitionLabel text="Import your data" />
      </Sequence>

      {/* Cursor */}
      <CursorOverlay waypoints={CURSOR_PATHS.act3} />
    </AbsoluteFill>
  );
};
