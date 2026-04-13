/**
 * Composition configuration for the marketing video.
 */

export const MARKETING = {
  id: "MarketingLandscape",
  width: 1920,
  height: 1080,
  fps: 30,
} as const;

// Scene durations in seconds
export const DURATIONS = {
  introLogo: 3,
  problemStatement: 5,
  pipelineAnimated: 7,
  screencastImport: 25,
  screencastTransform: 30,
  screencastExport: 25,
  statsOrMap: 10,
  outroCta: 10,
} as const;

// Transition duration in frames
export const TRANSITION_FRAMES = 15;

// Total duration in seconds
export const totalDurationSeconds = Object.values(DURATIONS).reduce(
  (sum, d) => sum + d,
  0
);

// Total duration in frames (approximate, before transition adjustments)
export const totalDurationFrames = totalDurationSeconds * MARKETING.fps;

/** Convert seconds to frames at the marketing fps */
export const sec = (s: number) => Math.round(s * MARKETING.fps);
