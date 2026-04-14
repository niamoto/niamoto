import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { NiamotoLogo } from "../ui/NiamotoLogo";

const pulseRingEasing = Easing.bezier(0.4, 0, 0.2, 1);

const getPulseRingStyle = (frame: number, fps: number) => {
  if (frame < 0) {
    return {
      opacity: 0,
      transform: "scale(0.5)",
    };
  }

  const cycleFrames = Math.max(1, Math.round(1.6 * fps));
  const normalized = (frame % cycleFrames) / cycleFrames;
  const eased = pulseRingEasing(normalized);

  return {
    opacity: interpolate(eased, [0, 1], [1, 0]),
    transform: `scale(${interpolate(eased, [0, 1], [0.5, 1.6])})`,
  };
};

export const IntroLogo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 200 } });
  const logoOpacity = interpolate(frame, [0, 0.5 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  const spinnerProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
    delay: Math.round(0.6 * fps),
  });
  const spinnerY = interpolate(spinnerProgress, [0, 1], [20, 0]);
  const spinnerOpacity = interpolate(spinnerProgress, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${theme.canvasGradientStart}, ${theme.canvasGradientEnd})`,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <AppWindow showSidebar={false} showTopBar={false}>
        <div
          style={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: theme.windowBg,
          }}
        >
          <div
            style={{
              opacity: logoOpacity,
              transform: `scale(${logoScale})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <NiamotoLogo width={104} />
          </div>

          <div
            style={{
              width: 24,
              height: 24,
              marginTop: 18,
              opacity: spinnerOpacity,
              transform: `translateY(${spinnerY}px)`,
              position: "relative",
              color: theme.lightGreen,
            }}
          >
            {[0, Math.round(0.6 * fps)].map((ringDelay) => {
              const ringStyle = getPulseRingStyle(
                frame - Math.round(0.6 * fps) - ringDelay,
                fps
              );

              return (
                <div
                  key={ringDelay}
                  style={{
                    position: "absolute",
                    inset: 0,
                    border: "2px solid currentColor",
                    borderRadius: "50%",
                    opacity: ringStyle.opacity,
                    transform: ringStyle.transform,
                  }}
                />
              );
            })}
          </div>

        </div>
      </AppWindow>
    </AbsoluteFill>
  );
};
