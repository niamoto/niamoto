import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { LAYOUT } from "../shared/layout";
import { theme } from "../shared/theme";
import { fontDisplay } from "../shared/fonts";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { NavItemId } from "../shared/layout";

interface AppWindowProps {
  showSidebar?: boolean;
  activeSidebarItem?: NavItemId;
  sidebarSlideInDuration?: number;
  children: React.ReactNode;
}

/**
 * macOS-style application window frame.
 * Traffic lights, titlebar, optional sidebar with slide-in animation.
 */
export const AppWindow: React.FC<AppWindowProps> = ({
  showSidebar = true,
  activeSidebarItem,
  sidebarSlideInDuration = 20,
  children,
}) => {
  const frame = useCurrentFrame();
  const { window: win, trafficLights: tl, titlebar, sidebar } = LAYOUT;

  // Sidebar slide-in animation
  const sidebarProgress = showSidebar
    ? interpolate(frame, [0, sidebarSlideInDuration], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  const sidebarWidth = sidebar.width * sidebarProgress;

  return (
    <div
      style={{
        position: "absolute",
        left: win.x,
        top: win.y,
        width: win.width,
        height: win.height,
        borderRadius: win.borderRadius,
        boxShadow: win.shadow,
        overflow: "hidden",
        backgroundColor: theme.bgDark,
      }}
    >
      {/* Titlebar */}
      <div
        style={{
          height: titlebar.height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          backgroundColor: LAYOUT.sidebar.bgColor,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {/* Traffic lights */}
        <div style={{ position: "absolute", left: tl.x - win.x, top: 0, height: "100%", display: "flex", alignItems: "center", gap: tl.gap }}>
          {tl.colors.map((color, i) => (
            <div
              key={i}
              style={{
                width: tl.size,
                height: tl.size,
                borderRadius: "50%",
                backgroundColor: color,
              }}
            />
          ))}
        </div>

        {/* Title */}
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 12,
            fontWeight: 500,
            color: theme.textMuted,
          }}
        >
          Niamoto
        </span>
      </div>

      {/* Body */}
      <div
        style={{
          display: "flex",
          height: win.height - titlebar.height,
        }}
      >
        {/* Sidebar */}
        {showSidebar && (
          <div
            style={{
              width: sidebarWidth,
              overflow: "hidden",
              flexShrink: 0,
            }}
          >
            <Sidebar activeItem={activeSidebarItem} />
          </div>
        )}

        {/* Main content area */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <TopBar />
          <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};
