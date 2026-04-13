import { useState, useEffect } from "react";
import { AbsoluteFill, useVideoConfig, delayRender, continueRender } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { DURATIONS, TRANSITION_FRAMES } from "../shared/config";
import { ensureFontsLoaded } from "../shared/fonts";
import { theme } from "../shared/theme";
import { Act1Welcome } from "../acts/Act1Welcome";
import { Act2ProjectWizard } from "../acts/Act2ProjectWizard";
import { Act3Import } from "../acts/Act3Import";
import { Act4Collections } from "../acts/Act4Collections";
import { Act5SiteBuilder } from "../acts/Act5SiteBuilder";
import { Act6Publish } from "../acts/Act6Publish";

export const MarketingLandscape: React.FC = () => {
  const { fps } = useVideoConfig();
  const [handle] = useState(() => delayRender("Loading fonts"));

  useEffect(() => {
    ensureFontsLoaded().then(() => continueRender(handle));
  }, [handle]);

  const sec = (s: number) => Math.round(s * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgDark }}>
      <TransitionSeries>
        {/* Intro */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.intro)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [IntroScene placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 1 — Welcome */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act1Welcome)}>
          <Act1Welcome />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 2 — Project Wizard */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act2ProjectWizard)}>
          <Act2ProjectWizard />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({ direction: "from-right" })}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 3 — Import */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act3Import)}>
          <Act3Import />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 4 — Collections */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act4Collections)}>
          <Act4Collections />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 5 — Site Builder */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act5SiteBuilder)}>
          <Act5SiteBuilder />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 6 — Publish */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act6Publish)}>
          <Act6Publish />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Outro */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.outro)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [OutroScene placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
