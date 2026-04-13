import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring, staticFile, Sequence } from "remotion";
import { Video } from "@remotion/media";
import { theme } from "../shared/theme";
import { fontDisplay } from "../shared/fonts";

export type ScreencastBlockProps = {
  /** Filename in public/screencasts/ */
  src: string;
  /** Label overlay (e.g. "Import", "Transform", "Export") */
  label: string;
  /** Trim start in seconds */
  trimStart?: number;
  /** Trim end in seconds */
  trimEnd?: number;
};

export const ScreencastBlock: React.FC<ScreencastBlockProps> = ({
  src,
  label,
  trimStart = 0,
  trimEnd,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Label badge: spring entrance
  const badgeProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
    delay: Math.round(0.3 * fps),
  });
  const badgeOpacity = interpolate(badgeProgress, [0, 1], [0, 1]);
  const badgeY = interpolate(badgeProgress, [0, 1], [-20, 0]);

  // Video frame with slight padding on dark bg
  const videoScale = interpolate(frame, [0, 0.4 * fps], [0.95, 1], {
    extrapolateRight: "clamp",
  });
  const videoOpacity = interpolate(frame, [0, 0.3 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  const videoSrc = staticFile(`screencasts/${src}`);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bgDark,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Video container with padding */}
      <div
        style={{
          width: 1760,
          height: 990,
          borderRadius: 12,
          overflow: "hidden",
          opacity: videoOpacity,
          transform: `scale(${videoScale})`,
          boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        }}
      >
        <Video
          src={videoSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
          muted
          trimBefore={Math.round(trimStart * fps)}
          {...(trimEnd ? { trimAfter: Math.round(trimEnd * fps) } : {})}
        />
      </div>

      {/* Label badge top-left */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 80,
          opacity: badgeOpacity,
          transform: `translateY(${badgeY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 22,
            fontWeight: 600,
            color: theme.textWhite,
            backgroundColor: "rgba(46, 125, 50, 0.85)",
            padding: "8px 20px",
            borderRadius: 8,
            letterSpacing: 0.5,
          }}
        >
          {label}
        </div>
      </div>
    </AbsoluteFill>
  );
};
