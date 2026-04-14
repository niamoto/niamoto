import { useCurrentFrame, interpolate } from "remotion";
import { LAYOUT, NavItemId } from "../shared/layout";
import { theme } from "../shared/theme";
import { fontDisplay } from "../shared/fonts";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

interface AppWindowProps {
  showSidebar?: boolean;
  showTopBar?: boolean;
  activeSidebarItem?: NavItemId;
  sidebarSlideInDuration?: number;
  title?: string | null;
  windowStyle?: React.CSSProperties;
  children: React.ReactNode;
}

export const AppWindow: React.FC<AppWindowProps> = ({
  showSidebar = true,
  showTopBar = true,
  activeSidebarItem,
  sidebarSlideInDuration = 20,
  title = null,
  windowStyle,
  children,
}) => {
  const frame = useCurrentFrame();
  const { window: win, trafficLights: tl, titlebar, sidebar } = LAYOUT;

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
        overflow: "hidden",
        backgroundColor: theme.windowBg,
        border: `1px solid ${theme.border}`,
        boxShadow: theme.shadowWindow,
        ...windowStyle,
      }}
    >
      <div
        style={{
          height: titlebar.height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          backgroundColor: theme.titlebarBg,
          borderBottom: `1px solid ${theme.border}`,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: tl.x - win.x,
            top: 0,
            height: "100%",
            display: "flex",
            alignItems: "center",
            gap: tl.gap,
          }}
        >
          {tl.colors.map((color, i) => (
            <div
              key={i}
              style={{
                width: tl.size,
                height: tl.size,
                borderRadius: "50%",
                backgroundColor: color,
                boxShadow: "inset 0 0 0 0.5px rgba(0,0,0,0.12)",
              }}
            />
          ))}
        </div>

        {title && (
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 12,
              fontWeight: 500,
              color: theme.textMuted,
            }}
          >
            {title}
          </span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          height: win.height - titlebar.height,
        }}
      >
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

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            background: theme.windowBg,
          }}
        >
          {showTopBar && <TopBar />}
          <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>{children}</div>
        </div>
      </div>
    </div>
  );
};
