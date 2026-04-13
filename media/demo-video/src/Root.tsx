import { Composition, Folder } from "remotion";
import { MarketingLandscape } from "./compositions/MarketingLandscape";
import { IntroLogo } from "./scenes/IntroLogo";
import { OutroCTA } from "./scenes/OutroCTA";
import { MARKETING, DURATIONS, sec, totalFrames } from "./shared/config";

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

      {/* Preserved scenes for isolated preview */}
      <Folder name="Scenes">
        <Composition
          id="IntroLogo"
          component={IntroLogo}
          durationInFrames={sec(DURATIONS.intro)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="OutroCTA"
          component={OutroCTA}
          durationInFrames={sec(DURATIONS.outro)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
      </Folder>
    </>
  );
};
