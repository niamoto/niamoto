/**
 * Composition configuration for the marketing video.
 */

export const MARKETING = {
  id: "MarketingLandscape",
  width: 1920,
  height: 1080,
  fps: 30,
} as const;

// Scene durations in seconds — 6 acts + intro/outro
export const DURATIONS = {
  intro: 4,
  act1Welcome: 8,
  act2ProjectWizard: 12,
  act3Import: 20,
  act4Collections: 14,
  act5SiteBuilder: 20,
  act6Publish: 12,
  outro: 6,
} as const;

// Transition duration in frames (fade or slide)
export const TRANSITION_FRAMES = 15;

// 8 sequences = 7 transitions
const TRANSITION_COUNT = 7;

/** Convert seconds to frames at the marketing fps */
export const sec = (s: number) => Math.round(s * MARKETING.fps);

/** Total raw duration in seconds */
export const totalDurationSeconds = Object.values(DURATIONS).reduce(
  (sum, d) => sum + d,
  0,
);

/** Total frames accounting for transition overlaps */
export const totalFrames =
  sec(totalDurationSeconds) - TRANSITION_COUNT * TRANSITION_FRAMES;
