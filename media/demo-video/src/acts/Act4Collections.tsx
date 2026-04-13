import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { MockCard } from "../ui/MockCard";
import { SpringPopIn } from "../animations/SpringPopIn";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";
import { MOCK_COLLECTIONS } from "../shared/mockData";

/**
 * Act 4 — Collections overview.
 * AppWindow with sidebar ("Collections" active).
 * 3 cards appear staggered via SpringPopIn.
 * Duration: 14s (420 frames @ 30fps)
 */
export const Act4Collections: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sec = (s: number) => Math.round(s * fps);

  // Header fade-in
  const headerOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Cards stagger delay (0.3s apart)
  const cardStagger = sec(0.3);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgDark }}>
      <AppWindow showSidebar activeSidebarItem="collections">
        <div style={{ padding: "28px 32px", height: "100%", display: "flex", flexDirection: "column" }}>
          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 28,
              opacity: headerOpacity,
            }}
          >
            <h1
              style={{
                fontFamily: fontDisplay,
                fontSize: 22,
                fontWeight: 700,
                color: theme.textWhite,
                margin: 0,
              }}
            >
              Collections
            </h1>
            <span
              style={{
                fontFamily: fontDisplay,
                fontSize: 12,
                fontWeight: 500,
                color: theme.textMuted,
                background: "rgba(255,255,255,0.06)",
                padding: "3px 10px",
                borderRadius: 12,
              }}
            >
              {MOCK_COLLECTIONS.length} configured
            </span>
          </div>

          {/* Card grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 20,
            }}
          >
            {MOCK_COLLECTIONS.map((coll, i) => (
              <SpringPopIn key={coll.name} delayInFrames={sec(0.5) + i * cardStagger}>
                <MockCard
                  name={coll.name}
                  count={coll.count}
                  status={coll.status}
                  widgets={coll.widgets}
                  exports={coll.exports}
                />
              </SpringPopIn>
            ))}
          </div>
        </div>
      </AppWindow>

      {/* Cursor */}
      <CursorOverlay waypoints={CURSOR_PATHS.act4} />
    </AbsoluteFill>
  );
};
