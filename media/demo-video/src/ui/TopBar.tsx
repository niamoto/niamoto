import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { LAYOUT } from "../shared/layout";

export const TopBar: React.FC = () => {
  return (
    <div
      style={{
        height: LAYOUT.topbar.height,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 18px 0 16px",
        borderBottom: `1px solid ${theme.border}`,
        background: theme.topbarBg,
      }}
    >
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 9,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: theme.textMuted,
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.8">
          <rect x="4" y="5" width="16" height="14" rx="2" />
          <path d="M10 5v14" />
        </svg>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "rgba(255,255,255,0.94)",
          borderRadius: 10,
          padding: "9px 14px",
          minWidth: 330,
          border: `1px solid ${theme.border}`,
          marginLeft: "auto",
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 13,
            color: theme.textMuted,
          }}
        >
          Search...
        </span>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 11,
            color: theme.textMuted,
            opacity: 0.8,
            marginLeft: "auto",
            padding: "2px 6px",
            border: `1px solid ${theme.border}`,
            borderRadius: 4,
          }}
        >
          ⌘K
        </span>
      </div>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginLeft: 16 }}>
        <div
          style={{
            width: 26,
            height: 26,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={theme.textDark} strokeWidth="1.8">
            <path d="M15 17h5l-1.4-1.4a2 2 0 0 1-.6-1.4V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5" />
            <path d="M10 21a2 2 0 0 0 4 0" />
          </svg>
        </div>

        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.5">
          <circle cx="12" cy="12" r="9" />
          <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4" />
          <path d="M12 17h.01" />
        </svg>
      </div>
    </div>
  );
};
