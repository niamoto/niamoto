import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { LAYOUT, NAV_ITEMS, NavItemId } from "../shared/layout";

interface SidebarProps {
  activeItem?: NavItemId;
}

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

export const Sidebar: React.FC<SidebarProps> = ({ activeItem }) => {
  return (
    <div
      style={{
        width: LAYOUT.sidebar.width,
        height: "100%",
        backgroundColor: LAYOUT.sidebar.bgColor,
        display: "flex",
        flexDirection: "column",
        borderRight: `1px solid ${theme.border}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          margin: "14px 14px 18px",
          padding: "10px 12px",
          borderRadius: 10,
          background: "rgba(255,255,255,0.68)",
          border: `1px solid ${theme.border}`,
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.8">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 14,
            fontWeight: 500,
            color: theme.textDark,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          nouvelle-cale...
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke={theme.textMuted}
          strokeWidth="1.8"
          style={{ marginLeft: "auto", flexShrink: 0 }}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "0 10px" }}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === activeItem;
          const IconComponent = icons[item.icon];
          const color = isActive ? theme.sidebarActiveText : "#667085";

          return (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "11px 12px",
                borderRadius: 9,
                background: isActive ? theme.sidebarActiveBg : "transparent",
              }}
            >
              {IconComponent && <IconComponent color={color} />}
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 14,
                  fontWeight: isActive ? 600 : 500,
                  color,
                }}
              >
                {item.label}
              </span>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: "auto", padding: "0 14px 14px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            color: theme.textMuted,
            fontFamily: fontDisplay,
            fontSize: 12,
            marginBottom: 14,
          }}
        >
          <span style={{ fontWeight: 600 }}>⌘ K</span>
          <span>Outils & recherche</span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            color: theme.textDark,
            fontFamily: fontDisplay,
            fontSize: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme.textDark} strokeWidth="1.8">
              <path d="M12.22 2h-.44a2 2 0 0 0-1.92 1.44l-.18.64a2 2 0 0 1-1.03 1.23l-.58.29a2 2 0 0 1-1.58.11l-.63-.2a2 2 0 0 0-2.24.9l-.22.38a2 2 0 0 0 .24 2.4l.42.5a2 2 0 0 1 .44 1.54l-.06.65a2 2 0 0 1-.78 1.37l-.52.4a2 2 0 0 0-.58 2.34l.17.41a2 2 0 0 0 2.04 1.22l.65-.05a2 2 0 0 1 1.5.48l.5.43a2 2 0 0 1 .63 1.42l.05.65A2 2 0 0 0 9.2 22h.42a2 2 0 0 0 1.88-1.35l.22-.64a2 2 0 0 1 1.08-1.18l.6-.28a2 2 0 0 1 1.57-.05l.63.22a2 2 0 0 0 2.27-.82l.23-.37a2 2 0 0 0-.14-2.41l-.4-.52a2 2 0 0 1-.38-1.55l.08-.65a2 2 0 0 1 .82-1.35l.53-.38a2 2 0 0 0 .66-2.31l-.15-.42a2 2 0 0 0-2-1.3l-.65.03a2 2 0 0 1-1.48-.52l-.48-.45a2 2 0 0 1-.6-1.43l-.03-.65A2 2 0 0 0 12.22 2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            <span>Paramètres</span>
          </div>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 6,
              border: `1px solid ${theme.borderStrong}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: theme.textMuted,
              fontWeight: 600,
            }}
          >
            +
          </div>
        </div>
      </div>
    </div>
  );
};
