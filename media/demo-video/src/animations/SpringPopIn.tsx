import { spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

interface SpringPopInProps {
  children: React.ReactNode;
  delayInFrames?: number;
  damping?: number;
  stiffness?: number;
}

/**
 * Wraps children in a spring scale 0.85→1 + opacity 0→1 entrance.
 * Pure interpolate/spring — no CSS animations.
 */
export const SpringPopIn: React.FC<SpringPopInProps> = ({
  children,
  delayInFrames = 0,
  damping = 15,
  stiffness = 120,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    config: { damping, stiffness },
    delay: delayInFrames,
  });

  const scale = interpolate(progress, [0, 1], [0.85, 1]);
  const opacity = interpolate(progress, [0, 1], [0, 1]);

  return (
    <div style={{ transform: `scale(${scale})`, opacity }}>
      {children}
    </div>
  );
};
