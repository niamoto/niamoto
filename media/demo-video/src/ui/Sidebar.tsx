import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { LAYOUT, NAV_ITEMS, NavItemId } from "../shared/layout";

interface SidebarProps {
  activeItem?: NavItemId;
}

/** SVG icons for sidebar navigation — simple geometric shapes */
const icons: Record<string, React.FC<{ color: string }>> = {
  house: ({ color }) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" />
      <path d="M9 21V12h6v9" />
    </svg>
  ),
  database: ({ color }) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
    </svg>
  ),
  layers: ({ color }) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <path d="M12 2 2 7l10 5 10-5-10-5z" />
      <path d="m2 17 10 5 10-5" />
      <path d="m2 12 10 5 10-5" />
    </svg>
  ),
  globe: ({ color }) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  ),
  send: ({ color }) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <path d="m22 2-7 20-4-9-9-4z" />
      <path d="m22 2-11 11" />
    </svg>
  ),
};

/**
 * Navigation sidebar matching Niamoto's sidebar layout.
 * Static rendering — active item highlight is prop-driven.
 */
export const Sidebar: React.FC<SidebarProps> = ({ activeItem }) => {
  return (
    <div
      style={{
        width: LAYOUT.sidebar.width,
        height: "100%",
        backgroundColor: LAYOUT.sidebar.bgColor,
        display: "flex",
        flexDirection: "column",
        paddingTop: LAYOUT.titlebar.height + 12,
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Logo area */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "0 16px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          marginBottom: 8,
        }}
      >
        {/* Niamoto logo placeholder — small green circle */}
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            background: `linear-gradient(135deg, ${theme.forestGreen}, ${theme.lightGreen})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ color: "white", fontSize: 14, fontWeight: 700, fontFamily: fontDisplay }}>
            N
          </span>
        </div>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 14,
            fontWeight: 600,
            color: theme.textWhite,
          }}
        >
          Niamoto
        </span>
      </div>

      {/* Nav items */}
      <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "0 8px" }}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === activeItem;
          const IconComponent = icons[item.icon];
          const color = isActive ? theme.lightGreen : theme.textMuted;

          return (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 12px",
                borderRadius: 6,
                background: isActive ? "rgba(75, 175, 80, 0.1)" : "transparent",
              }}
            >
              {IconComponent && <IconComponent color={color} />}
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 400,
                  color,
                }}
              >
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
