import { useCurrentFrame, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";

interface FileTypeChipProps {
  label: string;
  color: string;
  extensions: string[];
  enterAtFrame?: number;
}

/**
 * Colored chip for file type display.
 * Slides in from left with fade.
 */
export const FileTypeChip: React.FC<FileTypeChipProps> = ({
  label,
  color,
  extensions,
  enterAtFrame = 0,
}) => {
  const frame = useCurrentFrame();

  const progress = interpolate(frame, [enterAtFrame, enterAtFrame + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateX = interpolate(progress, [0, 1], [-30, 0]);
  const opacity = progress;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 14px",
        borderRadius: 20,
        background: `${color}18`,
        border: `1px solid ${color}40`,
        transform: `translateX(${translateX}px)`,
        opacity,
      }}
    >
      {/* Dot indicator */}
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: color,
        }}
      />
      <span
        style={{
          fontFamily: fontDisplay,
          fontSize: 13,
          fontWeight: 500,
          color,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: fontDisplay,
          fontSize: 11,
          color: `${color}99`,
        }}
      >
        {extensions.join(", ")}
      </span>
    </div>
  );
};
