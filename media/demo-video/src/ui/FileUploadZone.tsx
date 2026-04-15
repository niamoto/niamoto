import { useCurrentFrame, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

interface FileUploadZoneProps {
  /** Frame at which files start appearing */
  filesEnterFrame?: number;
  children?: React.ReactNode;
}

/**
 * Dashed-border upload zone with upload icon.
 * Transitions from empty state to filled state.
 */
export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  filesEnterFrame = 30,
  children,
}) => {
  const frame = useCurrentFrame();

  // Zone entrance
  const zoneOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Empty state fades out when files arrive
  const emptyOpacity = interpolate(
    frame,
    [filesEnterFrame - 5, filesEnterFrame + 5],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const hasFiles = frame >= filesEnterFrame;

  return (
    <div
      style={{
        border: `2px dashed rgba(255,255,255,${hasFiles ? 0.08 : 0.15})`,
        borderRadius: 12,
        padding: hasFiles ? "16px 20px" : "40px 20px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: hasFiles ? "auto" : 180,
        background: `rgba(255,255,255,${hasFiles ? 0.02 : 0.03})`,
        opacity: zoneOpacity,
        position: "relative",
        transition: "none", // Remotion-driven, no CSS transition
      }}
    >
      {/* Empty state */}
      {!hasFiles && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            opacity: emptyOpacity,
          }}
        >
          {/* Upload icon */}
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 14,
              color: theme.textMuted,
            }}
          >
            Drop your data files here
          </span>
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 12,
              color: theme.textMuted,
              opacity: 0.6,
            }}
          >
            CSV, GeoPackage, GeoJSON, GeoTIFF
          </span>
        </div>
      )}

      {/* Files content (rendered by parent via children) */}
      {hasFiles && children}
    </div>
  );
};
