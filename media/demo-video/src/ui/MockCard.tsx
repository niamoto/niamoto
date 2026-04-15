import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

interface MockCardProps {
  name: string;
  count: number;
  status: "fresh" | "stale" | "error";
  widgets: number;
  exports: number;
}

const statusColors = {
  fresh: theme.lightGreen,
  stale: "#F59E0B",
  error: "#EF4444",
};

const statusLabels = {
  fresh: "Up to date",
  stale: "Needs refresh",
  error: "Error",
};

/**
 * Collection card showing name, count, status, and stats.
 * Static rendering — animation handled by parent via SpringPopIn.
 */
export const MockCard: React.FC<MockCardProps> = ({
  name,
  count,
  status,
  widgets,
  exports,
}) => {
  const statusColor = statusColors[status];

  return (
    <div
      style={{
        background: theme.cardDark,
        borderRadius: 7,
        padding: "20px",
        border: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        gap: 14,
        minWidth: 260,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 17,
            fontWeight: 600,
            color: theme.textWhite,
          }}
        >
          {name}
        </span>
        {/* Status badge */}
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 11,
            fontWeight: 500,
            color: statusColor,
            background: `${statusColor}18`,
            padding: "3px 10px",
            borderRadius: 12,
          }}
        >
          {statusLabels[status]}
        </span>
      </div>

      {/* Count */}
      <div>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 28,
            fontWeight: 700,
            color: theme.textWhite,
          }}
        >
          {count.toLocaleString()}
        </span>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 13,
            color: theme.textMuted,
            marginLeft: 6,
          }}
        >
          records
        </span>
      </div>

      {/* Stats grid */}
      <div
        style={{
          display: "flex",
          gap: 16,
          borderTop: "1px solid rgba(255,255,255,0.06)",
          paddingTop: 12,
        }}
      >
        <StatItem label="Widgets" value={widgets} />
        <StatItem label="Exports" value={exports} />
      </div>
    </div>
  );
};

const StatItem: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
    <span style={{ fontFamily: fontDisplay, fontSize: 11, color: theme.textMuted }}>{label}</span>
    <span style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 600, color: theme.textWhite }}>{value}</span>
  </div>
);
