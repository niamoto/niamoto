import { Composition, Folder } from "remotion";
import { MarketingLandscape } from "./compositions/MarketingLandscape";
import { IntroLogo } from "./scenes/IntroLogo";
import { OutroCTA } from "./scenes/OutroCTA";
import { Act1Welcome } from "./acts/Act1Welcome";
import { Act2ProjectWizard } from "./acts/Act2ProjectWizard";
import { Act3Import } from "./acts/Act3Import";
import { Act4Collections } from "./acts/Act4Collections";
import { Act5SiteBuilder } from "./acts/Act5SiteBuilder";
import { Act6Publish } from "./acts/Act6Publish";
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

      {/* Isolated scene previews */}
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

      {/* Isolated act previews */}
      <Folder name="Acts">
        <Composition
          id="Act1Welcome"
          component={Act1Welcome}
          durationInFrames={sec(DURATIONS.act1Welcome)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="Act2ProjectWizard"
          component={Act2ProjectWizard}
          durationInFrames={sec(DURATIONS.act2ProjectWizard)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="Act3Import"
          component={Act3Import}
          durationInFrames={sec(DURATIONS.act3Import)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="Act4Collections"
          component={Act4Collections}
          durationInFrames={sec(DURATIONS.act4Collections)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="Act5SiteBuilder"
          component={Act5SiteBuilder}
          durationInFrames={sec(DURATIONS.act5SiteBuilder)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
        <Composition
          id="Act6Publish"
          component={Act6Publish}
          durationInFrames={sec(DURATIONS.act6Publish)}
          fps={MARKETING.fps}
          width={MARKETING.width}
          height={MARKETING.height}
        />
      </Folder>
    </>
  );
};
