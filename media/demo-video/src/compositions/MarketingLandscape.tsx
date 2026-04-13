import { useState, useEffect } from "react";
import { AbsoluteFill, useVideoConfig, delayRender, continueRender } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { DURATIONS, TRANSITION_FRAMES } from "../shared/config";
import { ensureFontsLoaded } from "../shared/fonts";
import { theme } from "../shared/theme";

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
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [Act1Welcome placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 2 — Project Wizard */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act2ProjectWizard)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [Act2ProjectWizard placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 3 — Import */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act3Import)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [Act3Import placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 4 — Collections */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act4Collections)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [Act4Collections placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 5 — Site Builder */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act5SiteBuilder)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [Act5SiteBuilder placeholder]
            </span>
          </AbsoluteFill>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
        />

        {/* Act 6 — Publish */}
        <TransitionSeries.Sequence durationInFrames={sec(DURATIONS.act6Publish)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <span style={{ color: theme.textMuted, fontSize: 24 }}>
              [Act6Publish placeholder]
            </span>
          </AbsoluteFill>
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
