import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Sequence } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { MockTree, TreeItem } from "../ui/MockTree";
import { MockPreviewPanel } from "../ui/MockPreviewPanel";
import { TransitionLabel } from "../scenes/TransitionLabel";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";
import { MOCK_SITE_TREE } from "../shared/mockData";

/**
 * Act 5 — Site Builder.
 * AppWindow with sidebar ("Site" active).
 * 3-panel layout: Tree | Editor | Preview.
 * Cursor clicks tree items, editor/preview update.
 * Duration: 20s (600 frames @ 30fps)
 */
export const Act5SiteBuilder: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sec = (s: number) => Math.round(s * fps);

  // Tree populates at start
  const treeExpandFrame = sec(0.5);

  // Cursor clicks "Species" at ~4s, then "Plots" at ~8s
  const speciesClickFrame = sec(4);
  const plotsClickFrame = sec(8);

  // Determine active tree item based on cursor timeline
  const activeItem =
    frame >= plotsClickFrame
      ? "Plots"
      : frame >= speciesClickFrame
        ? "Species"
        : "Home";

  // Editor title follows active item
  const editorTitle = activeItem;

  // Preview title with cross-fade timing
  const previewChangeFrame = frame >= plotsClickFrame ? plotsClickFrame : speciesClickFrame;
  const previewNextTitle = frame >= plotsClickFrame ? "Plot Map" : "Species";

  // Panel entrance
  const panelOpacity = interpolate(frame, [10, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgDark }}>
      <AppWindow showSidebar activeSidebarItem="site">
        <div
          style={{
            display: "flex",
            height: "100%",
            opacity: panelOpacity,
          }}
        >
          {/* Left panel — Tree (20%) */}
          <div
            style={{
              width: "20%",
              borderRight: "1px solid rgba(255,255,255,0.06)",
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                padding: "12px 12px 8px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  fontWeight: 600,
                  color: theme.textMuted,
                  textTransform: "uppercase",
                  letterSpacing: 0.5,
                }}
              >
                Pages
              </span>
            </div>
            <MockTree
              items={MOCK_SITE_TREE as TreeItem[]}
              activeItem={activeItem}
              expandAtFrame={treeExpandFrame}
            />
          </div>

          {/* Center panel — Editor (50%) */}
          <div
            style={{
              width: "50%",
              borderRight: "1px solid rgba(255,255,255,0.06)",
              padding: "20px 24px",
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            {/* Editor header */}
            <div>
              <h2
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 18,
                  fontWeight: 700,
                  color: theme.textWhite,
                  margin: 0,
                }}
              >
                {editorTitle}
              </h2>
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  color: theme.textMuted,
                }}
              >
                Configure widgets and layout
              </span>
            </div>

            {/* Mock editor fields */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <EditorField label="Title" value={editorTitle} />
              <EditorField label="Layout" value="Grid 2×2" />
              <EditorField label="Widgets" value="3 configured" />
            </div>

            {/* Mock widget slots */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
                marginTop: 8,
              }}
            >
              {["Map Overview", "Statistics", "Distribution", "Timeline"].map((name) => (
                <div
                  key={name}
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 6,
                    padding: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 4,
                      background: `${theme.steelBlue}20`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={theme.steelBlue} strokeWidth="1.5">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <path d="M3 9h18" />
                    </svg>
                  </div>
                  <span
                    style={{
                      fontFamily: fontDisplay,
                      fontSize: 12,
                      color: theme.textWhite,
                    }}
                  >
                    {name}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right panel — Preview (30%) */}
          <div style={{ width: "30%", display: "flex", flexDirection: "column" }}>
            <div
              style={{
                padding: "12px 12px 8px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  fontWeight: 600,
                  color: theme.textMuted,
                  textTransform: "uppercase",
                  letterSpacing: 0.5,
                }}
              >
                Preview
              </span>
            </div>
            <div style={{ flex: 1, padding: 8 }}>
              <MockPreviewPanel
                title="Home"
                changeAtFrame={frame >= speciesClickFrame ? speciesClickFrame : undefined}
                nextTitle={previewNextTitle}
              />
            </div>
          </div>
        </div>
      </AppWindow>

      {/* Cursor */}
      {/* Transition label — first 30 frames */}
      <Sequence from={0} durationInFrames={30}>
        <TransitionLabel text="Build your site" />
      </Sequence>

      <CursorOverlay waypoints={CURSOR_PATHS.act5} />
    </AbsoluteFill>
  );
};

/** Simple read-only field in the editor */
const EditorField: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <span style={{ fontFamily: fontDisplay, fontSize: 11, color: theme.textMuted, fontWeight: 500 }}>
      {label}
    </span>
    <div
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 6,
        padding: "7px 10px",
        fontFamily: fontDisplay,
        fontSize: 13,
        color: theme.textWhite,
      }}
    >
      {value}
    </div>
  </div>
);
