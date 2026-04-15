import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import { PublicSiteChrome } from "../ui/PublicSiteChrome";
import { TaxonomicNav } from "../widgets/TaxonomicNav";
import { BubbleMapNC } from "../widgets/BubbleMapNC";
import { OccurrencesBarChart } from "../widgets/OccurrencesBarChart";
import { DBHDistribution } from "../widgets/DBHDistribution";
import { PhenologyCalendar } from "../widgets/PhenologyCalendar";
import { SubstrateDonut } from "../widgets/SubstrateDonut";
import { WidgetCard } from "../widgets/WidgetCard";
import { SimulatedCursor } from "../ui/SimulatedCursor";
import { teaserCopy } from "../copy";
import taxonData from "../data/taxon-vedette.json";

/**
 * Acte Publish — le payoff final sur la page taxon publiée.
 * Durée : 10s (300 frames à 30fps).
 *
 * Narration :
 *  - 0-30f (1s)   : Eyebrow + title + curseur arrive sur bouton "Publier"
 *  - 30-45f       : Click ripple + transition
 *  - 45-300f (8s) : PublicSiteChrome avec le vrai look du site Niamoto, widgets assemblés
 */

const CURSOR_PATH_PUBLISH = "M 1800 160 Q 1650 200 1520 250";
const CURSOR_START_FRAME = 0;
const CURSOR_TRAVEL_FRAMES = 24;
const CLICK_FRAME = CURSOR_START_FRAME + CURSOR_TRAVEL_FRAMES;
const SITE_REVEAL_FRAME = CLICK_FRAME + 6;

export const TeaserPublish: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const eyebrowOpacity = interpolate(frame, [0, 12, SITE_REVEAL_FRAME - 4, SITE_REVEAL_FRAME + 8], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Bouton "Publier" en haut-droit (apparait jusqu'au click)
  const publishButtonOpacity = interpolate(frame, [0, 8, CLICK_FRAME - 2, CLICK_FRAME + 4], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Site reveal progress (spring pour un feel premium)
  const siteSpring = spring({
    frame: frame - SITE_REVEAL_FRAME,
    fps,
    config: { damping: 22, stiffness: 120 },
  });
  const siteProgress = interpolate(siteSpring, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: teaserTheme.pageBg }}>
      {/* Eyebrow + title pendant les 1-2 premières secondes */}
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: eyebrowOpacity,
          zIndex: 10,
        }}
      >
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: 1.2,
            textTransform: "uppercase",
            color: teaserTheme.primary,
          }}
        >
          {teaserCopy.publish.eyebrow}
        </div>
        <div
          style={{
            marginTop: 10,
            fontFamily: fontDisplay,
            fontSize: 32,
            fontWeight: 700,
            color: teaserTheme.textPrimary,
          }}
        >
          {teaserCopy.publish.title}
        </div>
      </div>

      {/* Bouton "Publier" au-dessus du chrome (visible avant le click) */}
      <div
        style={{
          position: "absolute",
          top: 200,
          right: 220,
          opacity: publishButtonOpacity,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "12px 24px",
          background: teaserTheme.primary,
          color: teaserTheme.cardWhite,
          fontFamily: fontDisplay,
          fontSize: 14,
          fontWeight: 700,
          borderRadius: 10,
          boxShadow: "0 6px 20px rgba(34, 139, 34, 0.35)",
          zIndex: 20,
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M22 2 11 13" />
          <path d="M22 2 15 22 11 13 2 9 22 2z" />
        </svg>
        Publier le site
      </div>

      {/* PublicSiteChrome — site publié */}
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 120,
          right: 100,
          bottom: 80,
          opacity: siteProgress,
          transform: `translateY(${interpolate(siteProgress, [0, 1], [40, 0])}px) scale(${interpolate(siteProgress, [0, 1], [0.96, 1])})`,
          transformOrigin: "50% 50%",
        }}
      >
        <PublicSiteChrome url={`niamoto.example/fr/taxons/${taxonData.name.toLowerCase()}`}>
          <PublicSiteContent revealFrame={SITE_REVEAL_FRAME + 18} />
        </PublicSiteChrome>
      </div>

      {/* Curseur sur le bouton Publier */}
      <Sequence from={CURSOR_START_FRAME} durationInFrames={CLICK_FRAME + 24}>
        <SimulatedCursor
          path={CURSOR_PATH_PUBLISH}
          startFrame={0}
          travelDurationFrames={CURSOR_TRAVEL_FRAMES}
          clickFrameOffset={2}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

/* -------------------------- helpers -------------------------- */

const PublicSiteContent: React.FC<{ revealFrame: number }> = ({ revealFrame }) => {
  const frame = useCurrentFrame();

  // Compact widget grid inside site chrome (mirrors /fr/taxons/948049381.html layout)
  const revealContent = (order: number) => {
    const localFrame = frame - revealFrame - order * 6;
    const opacity = interpolate(localFrame, [0, 12], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const translateY = interpolate(localFrame, [0, 12], [16, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return { opacity, transform: `translateY(${translateY}px)` };
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        padding: 16,
        gap: 16,
        overflow: "hidden",
        background: teaserTheme.pageBg,
      }}
    >
      <div style={{ ...revealContent(0), flexShrink: 0 }}>
        <TaxonomicNav startFrame={revealFrame + 6} width={210} />
      </div>

      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gridTemplateRows: "1.3fr 1fr 1fr",
          gap: 12,
          minHeight: 0,
        }}
      >
        <div style={{ gridColumn: "1 / span 2", gridRow: "1", ...revealContent(1) }}>
          <WidgetCard title="Distribution géographique" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 0 }}>
            <BubbleMapNC startFrame={revealFrame + 12} />
          </WidgetCard>
        </div>
        <div style={{ gridColumn: "1", gridRow: "2", ...revealContent(2) }}>
          <WidgetCard title="Sous-taxons principaux" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 10 }}>
            <OccurrencesBarChart startFrame={revealFrame + 24} limit={6} />
          </WidgetCard>
        </div>
        <div style={{ gridColumn: "2", gridRow: "2", ...revealContent(3) }}>
          <WidgetCard title="Distribution DBH" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 10 }}>
            <DBHDistribution startFrame={revealFrame + 32} />
          </WidgetCard>
        </div>
        <div style={{ gridColumn: "1", gridRow: "3", ...revealContent(4) }}>
          <WidgetCard title="Phénologie" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 10 }}>
            <PhenologyCalendar startFrame={revealFrame + 40} />
          </WidgetCard>
        </div>
        <div style={{ gridColumn: "2", gridRow: "3", ...revealContent(5) }}>
          <WidgetCard title="Distribution substrat" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 10 }}>
            <SubstrateDonut startFrame={revealFrame + 48} />
          </WidgetCard>
        </div>
      </div>
    </div>
  );
};
