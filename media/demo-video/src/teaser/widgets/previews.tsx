import { AbsoluteFill } from "remotion";
import { WidgetCard } from "./WidgetCard";
import { DBHDistribution } from "./DBHDistribution";
import { SubstrateDonut } from "./SubstrateDonut";
import { OccurrencesBarChart } from "./OccurrencesBarChart";
import { PhenologyCalendar } from "./PhenologyCalendar";
import { TaxonomicNav } from "./TaxonomicNav";
import { BubbleMapNC } from "./BubbleMapNC";
import { teaserTheme } from "../theme";

/**
 * Wrappers de preview isolés pour Remotion Studio.
 * Chaque composant est rendu dans un frame 1920×1080 centré avec card ombrée.
 */

const PreviewFrame: React.FC<{ children: React.ReactNode; width?: number; height?: number }> = ({ children, width = 900, height = 560 }) => (
  <AbsoluteFill style={{ background: teaserTheme.pageBg, alignItems: "center", justifyContent: "center" }}>
    <div style={{ width, height }}>{children}</div>
  </AbsoluteFill>
);

export const PreviewDBHDistribution: React.FC = () => (
  <PreviewFrame>
    <WidgetCard title="Distribution DBH" style={{ height: "100%" }} bodyStyle={{ height: "100%" }}>
      <DBHDistribution startFrame={15} />
    </WidgetCard>
  </PreviewFrame>
);

export const PreviewSubstrateDonut: React.FC = () => (
  <PreviewFrame width={560} height={560}>
    <WidgetCard title="Distribution substrat" style={{ height: "100%" }} bodyStyle={{ height: "100%" }}>
      <SubstrateDonut startFrame={15} />
    </WidgetCard>
  </PreviewFrame>
);

export const PreviewOccurrencesBarChart: React.FC = () => (
  <PreviewFrame>
    <WidgetCard title="Sous-taxons principaux" style={{ height: "100%" }} bodyStyle={{ height: "100%" }}>
      <OccurrencesBarChart startFrame={15} />
    </WidgetCard>
  </PreviewFrame>
);

export const PreviewPhenologyCalendar: React.FC = () => (
  <PreviewFrame>
    <WidgetCard title="Phénologie" style={{ height: "100%" }} bodyStyle={{ height: "100%" }}>
      <PhenologyCalendar startFrame={15} />
    </WidgetCard>
  </PreviewFrame>
);

export const PreviewTaxonomicNav: React.FC = () => (
  <AbsoluteFill style={{ background: teaserTheme.pageBg, padding: 80, display: "flex", justifyContent: "flex-start", alignItems: "flex-start" }}>
    <TaxonomicNav startFrame={15} />
  </AbsoluteFill>
);

export const PreviewBubbleMapNC: React.FC = () => (
  <PreviewFrame width={1200} height={700}>
    <WidgetCard title="Distribution géographique" style={{ height: "100%" }} bodyStyle={{ height: "100%", padding: 0 }}>
      <BubbleMapNC startFrame={15} />
    </WidgetCard>
  </PreviewFrame>
);
