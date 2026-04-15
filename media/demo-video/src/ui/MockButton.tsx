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
      background: `linear-gradient(180deg, ${theme.lightGreen}, ${theme.forestGreen})`,
      color: theme.textOnPrimary,
      border: "none",
      boxShadow: "0 10px 24px rgba(46, 125, 50, 0.18)",
    },
    outline: {
      background: "rgba(255,255,255,0.96)",
      color: theme.textDark,
      border: `1px solid ${theme.borderStrong}`,
    },
    default: {
      background: theme.cardDark,
      color: theme.textDark,
      border: `1px solid ${theme.border}`,
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
        fontSize: 15,
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
