import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import { WidgetCard } from "../widgets/WidgetCard";
import { TaxonomicNav } from "../widgets/TaxonomicNav";
import { BubbleMapNC } from "../widgets/BubbleMapNC";
import { OccurrencesBarChart } from "../widgets/OccurrencesBarChart";
import { DBHDistribution } from "../widgets/DBHDistribution";
import { PhenologyCalendar } from "../widgets/PhenologyCalendar";
import { SubstrateDonut } from "../widgets/SubstrateDonut";
import { SimulatedCursor } from "../ui/SimulatedCursor";
import { teaserCopy } from "../copy";
import taxonData from "../data/taxon-vedette.json";

/**
 * Acte Structure — la collection qui se construit.
 * Durée : 17s (510 frames à 30fps).
 *
 * Narration :
 *  - 0-60f (2s) : Empty canvas + eyebrow "Structured collections" + TaxonomicNav slide-in
 *  - 60-90f (1s) : Curseur arrive vers bouton "+ Ajouter widget" + click ripple (R12)
 *  - 90-510f (14s) : 6 widgets s'assemblent en mosaïque avec stagger — ref cap `/fr/taxons/948049381.html`
 */

const CURSOR_PATH = "M 1700 -50 Q 1500 80 1280 150";
const CURSOR_START_FRAME = 60;
const CURSOR_TRAVEL_FRAMES = 24;

export const TeaserStructure: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const eyebrowOpacity = interpolate(frame, [0, 18, 90, 110], [0, 1, 1, 0.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const canvasProgress = spring({
    frame: frame - 6,
    fps,
    config: { damping: 20, stiffness: 100 },
  });
  const canvasClampedProgress = interpolate(canvasProgress, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const clickFrame = CURSOR_START_FRAME + CURSOR_TRAVEL_FRAMES;
  const assembleStart = clickFrame + 6;

  return (
    <AbsoluteFill style={{ background: teaserTheme.pageBg }}>
      <div
        style={{
          position: "absolute",
          top: 58,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: eyebrowOpacity,
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
          {teaserCopy.structure.eyebrow}
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
          {teaserCopy.structure.title}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 100,
          top: 180,
          right: 100,
          bottom: 80,
          display: "flex",
          gap: 24,
          opacity: canvasClampedProgress,
          transform: `translateY(${interpolate(canvasClampedProgress, [0, 1], [30, 0])}px)`,
        }}
      >
        <TaxonomicNav startFrame={20} />

        <div
          style={{
            flex: 1,
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gridTemplateRows: "1.2fr 1fr 1fr",
            gap: 18,
            position: "relative",
          }}
        >
          <AddWidgetButton frame={frame} clickFrame={clickFrame} />

          <AssembledWidget frame={frame} order={0} assembleStart={assembleStart} style={{ gridColumn: "1 / span 3", gridRow: "1" }}>
            <WidgetCard title="Distribution géographique" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 0 }}>
              <BubbleMapNC startFrame={assembleStart + 2} />
            </WidgetCard>
          </AssembledWidget>

          <AssembledWidget frame={frame} order={1} assembleStart={assembleStart} style={{ gridColumn: "1", gridRow: "2" }}>
            <WidgetCard title="Sous-taxons principaux" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 12 }}>
              <OccurrencesBarChart startFrame={assembleStart + 12} limit={6} />
            </WidgetCard>
          </AssembledWidget>

          <AssembledWidget frame={frame} order={2} assembleStart={assembleStart} style={{ gridColumn: "2", gridRow: "2" }}>
            <WidgetCard title="Distribution DBH" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 12 }}>
              <DBHDistribution startFrame={assembleStart + 20} />
            </WidgetCard>
          </AssembledWidget>

          <AssembledWidget frame={frame} order={3} assembleStart={assembleStart} style={{ gridColumn: "3", gridRow: "2" }}>
            <WidgetCard title="Phénologie" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 12 }}>
              <PhenologyCalendar startFrame={assembleStart + 28} />
            </WidgetCard>
          </AssembledWidget>

          <AssembledWidget frame={frame} order={4} assembleStart={assembleStart} style={{ gridColumn: "1", gridRow: "3" }}>
            <WidgetCard title="Distribution substrat" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 12 }}>
              <SubstrateDonut startFrame={assembleStart + 36} />
            </WidgetCard>
          </AssembledWidget>

          <AssembledWidget frame={frame} order={5} assembleStart={assembleStart} style={{ gridColumn: "2 / span 2", gridRow: "3" }}>
            <WidgetCard title="Informations générales" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 20, display: "flex", alignItems: "center", justifyContent: "space-around" }}>
              <StatBlock label="Taxon" value={taxonData.name} italic />
              <StatBlock label="Rang" value={taxonData.rank} />
              <StatBlock label="Occurrences" value={taxonData.occurrences.toLocaleString("fr-FR")} strong />
            </WidgetCard>
          </AssembledWidget>
        </div>
      </div>

      <Sequence from={CURSOR_START_FRAME} durationInFrames={120}>
        <SimulatedCursor
          path={CURSOR_PATH}
          startFrame={0}
          travelDurationFrames={CURSOR_TRAVEL_FRAMES}
          clickFrameOffset={2}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

/* -------------------------- helpers -------------------------- */

const AddWidgetButton: React.FC<{ frame: number; clickFrame: number }> = ({ frame, clickFrame }) => {
  const buttonOpacity = interpolate(frame, [0, 6, clickFrame - 2, clickFrame + 4], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        right: 0,
        top: -52,
        opacity: buttonOpacity,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 18px",
        background: teaserTheme.primary,
        color: teaserTheme.cardWhite,
        fontFamily: fontDisplay,
        fontSize: 13,
        fontWeight: 600,
        borderRadius: 8,
        boxShadow: "0 2px 8px rgba(34, 139, 34, 0.3)",
      }}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <line x1="12" y1="5" x2="12" y2="19" />
        <line x1="5" y1="12" x2="19" y2="12" />
      </svg>
      Ajouter un widget
    </div>
  );
};

const AssembledWidget: React.FC<{
  frame: number;
  order: number;
  assembleStart: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ frame, order, assembleStart, style, children }) => {
  const stagger = 8;
  const localFrame = frame - assembleStart - order * stagger;
  const opacity = interpolate(localFrame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(localFrame, [0, 15], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(localFrame, [0, 15], [0.97, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        ...style,
        opacity,
        transform: `translateY(${translateY}px) scale(${scale})`,
        transformOrigin: "top left",
      }}
    >
      {children}
    </div>
  );
};

const StatBlock: React.FC<{ label: string; value: string; italic?: boolean; strong?: boolean }> = ({ label, value, italic, strong }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <span style={{ fontFamily: fontDisplay, fontSize: 11, color: teaserTheme.textSecondary, textTransform: "uppercase", letterSpacing: 0.4 }}>
      {label}
    </span>
    <span
      style={{
        fontFamily: fontDisplay,
        fontSize: strong ? 28 : 18,
        fontWeight: 700,
        color: teaserTheme.textPrimary,
        fontStyle: italic ? "italic" : "normal",
      }}
    >
      {value}
    </span>
  </div>
);
