import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { LAYOUT } from "../shared/layout";

/**
 * Top bar with fake search input.
 * Static — no animation needed.
 */
export const TopBar: React.FC = () => {
  return (
    <div
      style={{
        height: LAYOUT.topbar.height,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Search bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "rgba(255,255,255,0.04)",
          borderRadius: 8,
          padding: "6px 14px",
          minWidth: 240,
        }}
      >
        {/* Search icon */}
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
            opacity: 0.5,
            marginLeft: "auto",
            padding: "2px 6px",
            border: `1px solid rgba(255,255,255,0.1)`,
            borderRadius: 4,
          }}
        >
          ⌘K
        </span>
      </div>

      {/* Right icons placeholder */}
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        {/* Settings gear */}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.5">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      </div>
    </div>
  );
};
