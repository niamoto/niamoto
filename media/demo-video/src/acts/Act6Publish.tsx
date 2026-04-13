import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, Sequence } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { MockButton } from "../ui/MockButton";
import { ProgressBar } from "../ui/ProgressBar";
import { TransitionLabel } from "../scenes/TransitionLabel";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";

/**
 * Act 6 — Publish.
 * AppWindow with sidebar ("Publish" active).
 * Two phases: Build (0-7s) → Deploy (7-12s).
 * Duration: 12s (360 frames @ 30fps)
 */
export const Act6Publish: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sec = (s: number) => Math.round(s * fps);

  // Cursor clicks "Build & Publish" at ~1s
  const buttonClickFrame = sec(1);

  // Phase boundaries
  const buildStart = sec(1.5);
  const buildDuration = sec(5);
  const deployStart = sec(7);
  const deployDuration = sec(3.5);

  // Build phase starts after button click
  const isBuildPhase = frame >= buildStart;
  const isDeployPhase = frame >= deployStart;

  // Build complete
  const buildDone = frame >= deployStart;

  // Deploy complete — published badge appears
  const publishedFrame = deployStart + deployDuration + sec(0.5);
  const isPublished = frame >= publishedFrame;

  // Published badge entrance
  const badgeScale = isPublished
    ? spring({
        frame: frame - publishedFrame,
        fps,
        config: { damping: 12, stiffness: 150 },
        from: 0.8,
        to: 1,
      })
    : 0;

  const badgeOpacity = isPublished
    ? interpolate(frame, [publishedFrame, publishedFrame + 8], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgDark }}>
      <AppWindow showSidebar activeSidebarItem="publish">
        <div
          style={{
            padding: "28px 32px",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          {/* Header */}
          <div style={{ textAlign: "center", marginBottom: 32, width: "100%" }}>
            <h1
              style={{
                fontFamily: fontDisplay,
                fontSize: 22,
                fontWeight: 700,
                color: theme.textWhite,
                margin: 0,
              }}
            >
              Publish Site
            </h1>
            <p
              style={{
                fontFamily: fontDisplay,
                fontSize: 14,
                color: theme.textMuted,
                margin: "6px 0 0",
              }}
            >
              Build and deploy your ecological data portal
            </p>
          </div>

          {/* Button — visible before build starts */}
          {!isBuildPhase && (
            <div style={{ marginBottom: 32 }}>
              <MockButton
                label="Build & Publish"
                variant="gradient"
                clickAtFrame={buttonClickFrame}
                icon={
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                    <path d="m22 2-7 20-4-9-9-4z" />
                    <path d="m22 2-11 11" />
                  </svg>
                }
              />
            </div>
          )}

          {/* Build progress */}
          {isBuildPhase && (
            <div style={{ width: "100%", maxWidth: 500, marginBottom: 24 }}>
              <ProgressBar
                startFrame={buildStart}
                durationInFrames={buildDuration}
                label="Building site..."
                steps={["Generate pages", "Process assets", "Create index"]}
              />
            </div>
          )}

          {/* Deploy progress */}
          {isDeployPhase && (
            <div style={{ width: "100%", maxWidth: 500, marginTop: 20 }}>
              <ProgressBar
                startFrame={deployStart}
                durationInFrames={deployDuration}
                label="Deploying..."
              />
            </div>
          )}

          {/* Published badge */}
          {isPublished && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginTop: 28,
                padding: "14px 28px",
                borderRadius: 10,
                background: `${theme.lightGreen}15`,
                border: `1.5px solid ${theme.lightGreen}40`,
                transform: `scale(${badgeScale})`,
                opacity: badgeOpacity,
              }}
            >
              {/* Check circle */}
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: theme.lightGreen,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <div>
                <span
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 16,
                    fontWeight: 700,
                    color: theme.lightGreen,
                  }}
                >
                  Published!
                </span>
                <div
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 12,
                    color: theme.textMuted,
                    marginTop: 2,
                  }}
                >
                  my-ecology-project.niamoto.io
                </div>
              </div>
            </div>
          )}
        </div>
      </AppWindow>

      {/* Cursor */}
      {/* Transition label — first 30 frames */}
      <Sequence from={0} durationInFrames={30}>
        <TransitionLabel text="Publish to the web" />
      </Sequence>

      <CursorOverlay waypoints={CURSOR_PATHS.act6} />
    </AbsoluteFill>
  );
};
