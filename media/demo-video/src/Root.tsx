import { Composition, Folder } from "remotion";
import { MarketingLandscape } from "./compositions/MarketingLandscape";
import { LandingTeaser } from "./compositions/LandingTeaser";
import { IntroLogo } from "./scenes/IntroLogo";
import { OutroCTA } from "./scenes/OutroCTA";
import { Act1Welcome } from "./acts/Act1Welcome";
import { Act2ProjectWizard } from "./acts/Act2ProjectWizard";
import { Act3Import } from "./acts/Act3Import";
import { Act4Collections } from "./acts/Act4Collections";
import { Act5SiteBuilder } from "./acts/Act5SiteBuilder";
import { Act6Publish } from "./acts/Act6Publish";
import { MARKETING, DURATIONS, sec, totalFrames } from "./shared/config";
import { LANDING_TEASER, TEASER_DURATIONS, landingTeaserFrames, teaserSec } from "./teaser/config";
import { TeaserOpener } from "./teaser/scenes/TeaserOpener";
import { TeaserDataIntake } from "./teaser/scenes/TeaserDataIntake";
import { TeaserStructure } from "./teaser/scenes/TeaserStructure";
import { TeaserPublish } from "./teaser/scenes/TeaserPublish";
import { TeaserEndCard } from "./teaser/scenes/TeaserEndCard";
import {
  PreviewDBHDistribution,
  PreviewSubstrateDonut,
  PreviewOccurrencesBarChart,
  PreviewPhenologyCalendar,
  PreviewTaxonomicNav,
  PreviewBubbleMapNC,
} from "./teaser/widgets/previews";

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

      <Composition
        id={LANDING_TEASER.id}
        component={LandingTeaser}
        durationInFrames={landingTeaserFrames}
        fps={LANDING_TEASER.fps}
        width={LANDING_TEASER.width}
        height={LANDING_TEASER.height}
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

      <Folder name="Landing-Teaser">
        <Composition
          id="TeaserOpener"
          component={TeaserOpener}
          durationInFrames={teaserSec(TEASER_DURATIONS.opener)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="TeaserDataIntake"
          component={TeaserDataIntake}
          durationInFrames={teaserSec(TEASER_DURATIONS.dataIntake)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="TeaserStructure"
          component={TeaserStructure}
          durationInFrames={teaserSec(TEASER_DURATIONS.structure)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="TeaserPublish"
          component={TeaserPublish}
          durationInFrames={teaserSec(TEASER_DURATIONS.publish)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="TeaserEndCard"
          component={TeaserEndCard}
          durationInFrames={teaserSec(TEASER_DURATIONS.endCard)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
      </Folder>

      <Folder name="Teaser-Widgets">
        <Composition
          id="WidgetBubbleMapNC"
          component={PreviewBubbleMapNC}
          durationInFrames={teaserSec(4)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="WidgetDBHDistribution"
          component={PreviewDBHDistribution}
          durationInFrames={teaserSec(3)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="WidgetSubstrateDonut"
          component={PreviewSubstrateDonut}
          durationInFrames={teaserSec(3)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="WidgetOccurrencesBarChart"
          component={PreviewOccurrencesBarChart}
          durationInFrames={teaserSec(4)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="WidgetPhenologyCalendar"
          component={PreviewPhenologyCalendar}
          durationInFrames={teaserSec(3)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
        <Composition
          id="WidgetTaxonomicNav"
          component={PreviewTaxonomicNav}
          durationInFrames={teaserSec(3)}
          fps={LANDING_TEASER.fps}
          width={LANDING_TEASER.width}
          height={LANDING_TEASER.height}
        />
      </Folder>
    </>
  );
};
