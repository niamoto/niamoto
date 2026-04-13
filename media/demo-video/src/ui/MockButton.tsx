import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

interface MockButtonProps {
  label: string;
  variant?: "gradient" | "outline" | "default";
  icon?: React.ReactNode;
  clickAtFrame?: number;
  width?: number;
}

/**
 * Animated button with spring click effect.
 * Click is frame-driven (not event-driven).
 */
export const MockButton: React.FC<MockButtonProps> = ({
  label,
  variant = "default",
  icon,
  clickAtFrame,
  width,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Spring scale on click
  let scale = 1;
  if (clickAtFrame !== undefined && frame >= clickAtFrame) {
    const clickAge = frame - clickAtFrame;
    scale = spring({
      frame: clickAge,
      fps,
      config: { damping: 12, stiffness: 200, mass: 0.5 },
      from: 0.92,
      to: 1,
    });
  }

  const bgStyles: Record<string, React.CSSProperties> = {
    gradient: {
      background: "linear-gradient(to right, #2E7D32, #26A69A)",
      color: theme.textWhite,
      border: "none",
    },
    outline: {
      background: "transparent",
      color: theme.textWhite,
      border: `1.5px solid ${theme.textMuted}`,
    },
    default: {
      background: theme.cardDark,
      color: theme.textWhite,
      border: `1px solid rgba(255,255,255,0.1)`,
    },
  };

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        padding: "12px 28px",
        borderRadius: 8,
        fontFamily: fontDisplay,
        fontSize: 16,
        fontWeight: 600,
        cursor: "pointer",
        transform: `scale(${scale})`,
        width,
        ...bgStyles[variant],
      }}
    >
      {icon}
      {label}
    </div>
  );
};
