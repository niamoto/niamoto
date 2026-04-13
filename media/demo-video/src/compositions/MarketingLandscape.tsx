import { useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { IntroLogo } from "../scenes/IntroLogo";
import { PipelineAnimated } from "../scenes/PipelineAnimated";
import { ScreencastBlock } from "../scenes/ScreencastBlock";
import { StatsOrMap } from "../scenes/StatsOrMap";
import { OutroCTA } from "../scenes/OutroCTA";
import { DURATIONS, TRANSITION_FRAMES } from "../shared/config";
import "../shared/fonts";

export const MarketingLandscape: React.FC = () => {
  const { fps } = useVideoConfig();

  const sec = (s: number) => Math.round(s * fps);

  return (
    <TransitionSeries>
      {/* 1. Intro Logo */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.introLogo)}>
        <IntroLogo />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 2. Problem statement */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.problemStatement)}>
        <PipelineAnimated mode="problem" />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 3. Pipeline animated diagram */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.pipelineAnimated)}>
        <PipelineAnimated mode="pipeline" />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 4. Screencast: Import */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.screencastImport)}>
        <ScreencastBlock src="01-import-flow.mp4" label="Import" />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 5. Screencast: Transform */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.screencastTransform)}>
        <ScreencastBlock src="02-transform-preview.mp4" label="Transform" />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 6. Screencast: Export */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.screencastExport)}>
        <ScreencastBlock src="03-publish-or-site-preview.mp4" label="Export" />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 7. Stats / Map */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.statsOrMap)}>
        <StatsOrMap />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
      />

      {/* 8. Outro CTA */}
      <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.outroCta)}>
        <OutroCTA />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
