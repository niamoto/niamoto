import { MARKETING } from "../shared/config";

export const LANDING_TEASER = {
  id: "LandingTeaser",
  width: MARKETING.width,
  height: MARKETING.height,
  fps: MARKETING.fps,
  output: "out/landing-teaser.mp4",
} as const;

export const TEASER_SEGMENT_ORDER = [
  "opener",
  "dataIntake",
  "structure",
  "publish",
  "endCard",
] as const;

export type TeaserSegmentId = (typeof TEASER_SEGMENT_ORDER)[number];

export const TEASER_DURATIONS: Record<TeaserSegmentId, number> = {
  opener: 5,
  dataIntake: 9,
  structure: 17,
  publish: 10,
  endCard: 5,
};

export const TEASER_TRANSITION_FRAMES = 15;

export const teaserSec = (seconds: number) => Math.round(seconds * LANDING_TEASER.fps);

export const landingTeaserDurationSeconds = TEASER_SEGMENT_ORDER.reduce(
  (total, segmentId) => total + TEASER_DURATIONS[segmentId],
  0,
);

export const landingTeaserFrames =
  teaserSec(landingTeaserDurationSeconds) -
  (TEASER_SEGMENT_ORDER.length - 1) * TEASER_TRANSITION_FRAMES;
