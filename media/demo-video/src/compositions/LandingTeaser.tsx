import { useEffect, useState } from "react";
import { AbsoluteFill, continueRender, delayRender } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { ensureFontsLoaded } from "../shared/fonts";
import { teaserTheme } from "../teaser/theme";
import { TEASER_DURATIONS, TEASER_TRANSITION_FRAMES, teaserSec } from "../teaser/config";
import { TeaserOpener } from "../teaser/scenes/TeaserOpener";
import { TeaserDataIntake } from "../teaser/scenes/TeaserDataIntake";
import { TeaserStructure } from "../teaser/scenes/TeaserStructure";
import { TeaserPublish } from "../teaser/scenes/TeaserPublish";
import { TeaserEndCard } from "../teaser/scenes/TeaserEndCard";

/**
 * Composition principale du teaser hybride.
 *
 * Corrections vs v1 (cf. revue Remotion-best-practices) :
 *  - `premountFor={30}` sur chaque Sequence (évite les frames blanches à la transition)
 *  - Background gradient migré vers `teaserTheme` (palette produit verte)
 *  - Fonts bloquent le render via delayRender (pattern officiel conservé)
 *  - Toutes les scènes utilisent `teaserTheme` et les vrais widgets Niamoto
 */
export const LandingTeaser: React.FC = () => {
  const [handle] = useState(() => delayRender("Loading landing teaser fonts"));

  useEffect(() => {
    ensureFontsLoaded().then(() => continueRender(handle));
  }, [handle]);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${teaserTheme.cardWhite}, ${teaserTheme.pageBg})`,
      }}
    >
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={teaserSec(TEASER_DURATIONS.opener)} premountFor={30}>
          <TeaserOpener />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TEASER_TRANSITION_FRAMES })}
        />

        <TransitionSeries.Sequence durationInFrames={teaserSec(TEASER_DURATIONS.dataIntake)} premountFor={30}>
          <TeaserDataIntake />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TEASER_TRANSITION_FRAMES })}
        />

        <TransitionSeries.Sequence durationInFrames={teaserSec(TEASER_DURATIONS.structure)} premountFor={30}>
          <TeaserStructure />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TEASER_TRANSITION_FRAMES })}
        />

        <TransitionSeries.Sequence durationInFrames={teaserSec(TEASER_DURATIONS.publish)} premountFor={30}>
          <TeaserPublish />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TEASER_TRANSITION_FRAMES })}
        />

        <TransitionSeries.Sequence durationInFrames={teaserSec(TEASER_DURATIONS.endCard)} premountFor={30}>
          <TeaserEndCard />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
