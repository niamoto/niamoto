import { Composition, Folder } from "remotion";
import { MarketingLandscape } from "./compositions/MarketingLandscape";
import { IntroLogo } from "./scenes/IntroLogo";
import { PipelineAnimated } from "./scenes/PipelineAnimated";
import { StatsOrMap } from "./scenes/StatsOrMap";
import { OutroCTA } from "./scenes/OutroCTA";
import { MARKETING, DURATIONS, TRANSITION_FRAMES, sec } from "./shared/config";

// Total frames: sum of all scene durations minus transitions between them
// 8 scenes = 7 transitions
const totalFrames =
  sec(
    DURATIONS.introLogo +
    DURATIONS.problemStatement +
    DURATIONS.pipelineAnimated +
    DURATIONS.screencastImport +
    DURATIONS.screencastTransform +
    DURATIONS.screencastExport +
    DURATIONS.statsOrMap +
    DURATIONS.outroCta
  ) - 7 * TRANSITION_FRAMES;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Main composition */}
      <Composition
        id={MARKETING.id}
        component={MarketingLandscape}
        durationInFrames={totalFrames}
        fps={MARKETING.fps}
        width={MARKETING.width}
        height={MARKETING.height}
      />

      {/* Individual scenes for isolated preview */}
      <Folder name="Scenes">
        <Composition
          id="IntroLogo"
          component={IntroLogo}
          durationInFrames={sec(DURATIONS.introLogo)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="ProblemStatement"
          component={PipelineAnimated}
          durationInFrames={sec(DURATIONS.problemStatement)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
          defaultProps={{ mode: "problem" as const }}
        />
        <Composition
          id="PipelineDiagram"
          component={PipelineAnimated}
          durationInFrames={sec(DURATIONS.pipelineAnimated)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
          defaultProps={{ mode: "pipeline" as const }}
        />
        <Composition
          id="StatsOrMap"
          component={StatsOrMap}
          durationInFrames={sec(DURATIONS.statsOrMap)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="OutroCTA"
          component={OutroCTA}
          durationInFrames={sec(DURATIONS.outroCta)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
      </Folder>
    </>
  );
};
