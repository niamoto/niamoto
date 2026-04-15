import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { teaserCopy } from "../copy";
import { fontDisplay } from "../../shared/fonts";
import { theme } from "../../shared/theme";
import { AppWindow } from "../../ui/AppWindow";

const FilePill: React.FC<{
  label: string;
  color: string;
  x: number;
  y: number;
  frameStart: number;
}> = ({ label, color, x, y, frameStart }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    frame: frame - frameStart,
    fps,
    config: { damping: 18, stiffness: 110 },
  });

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        height: 34,
        padding: "0 14px",
        borderRadius: 999,
        border: `1px solid ${theme.border}`,
        background: "rgba(255,255,255,0.92)",
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontFamily: fontDisplay,
        fontSize: 12,
        color: "#344054",
        opacity: progress,
        transform: `translateY(${interpolate(progress, [0, 1], [18, 0])}px)`,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
        }}
      />
      {label}
    </div>
  );
};

const OpenerWindowPreview: React.FC = () => (
  <div style={{ height: "100%", padding: "34px 40px 40px", boxSizing: "border-box", background: "#F9FBFC" }}>
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div>
        <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#98A2B3" }}>Data / Import</div>
        <div style={{ marginTop: 8, fontFamily: fontDisplay, fontSize: 34, fontWeight: 700, color: "#111827" }}>
          Import data
        </div>
      </div>
      <div
        style={{
          height: 34,
          padding: "0 16px",
          borderRadius: 8,
          background: "#15803D",
          display: "flex",
          alignItems: "center",
          color: "#FFFFFF",
          fontFamily: fontDisplay,
          fontSize: 14,
          fontWeight: 700,
        }}
      >
        Upload files
      </div>
    </div>

    <div
      style={{
        marginTop: 24,
        borderRadius: 20,
        border: `1px dashed ${theme.borderStrong}`,
        background: "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,248,251,0.96))",
        height: 290,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: "50%",
          background: "#EEF6FB",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#5B86B0" strokeWidth="1.8">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </div>
      <div style={{ fontFamily: fontDisplay, fontSize: 24, fontWeight: 700, color: "#111827" }}>
        Bring files into one import flow
      </div>
      <div style={{ fontFamily: fontDisplay, fontSize: 15, color: "#667085", textAlign: "center", maxWidth: 580 }}>
        CSV tables, spatial layers, and reference files are grouped before they become structured pages.
      </div>
    </div>
  </div>
);

export const TeaserOpener: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const heroProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 110 },
  });
  const heroOpacity = interpolate(frame, [0, 18, 110, 138], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const windowProgress = spring({
    frame: frame - 42,
    fps,
    config: { damping: 20, stiffness: 120 },
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #F7F8FA 0%, #EEF3F6 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 22% 18%, rgba(91,134,176,0.12), transparent 28%), radial-gradient(circle at 76% 16%, rgba(75,175,80,0.10), transparent 24%), radial-gradient(circle at 50% 84%, rgba(91,134,176,0.08), transparent 30%)",
        }}
      />

      <div
        style={{
          opacity: windowProgress,
          transform: `translateY(${interpolate(windowProgress, [0, 1], [88, 0])}px) scale(${interpolate(
            windowProgress,
            [0, 1],
            [0.96, 1],
          )})`,
        }}
      >
        <AppWindow activeSidebarItem="data">
          <OpenerWindowPreview />
        </AppWindow>
      </div>

      <FilePill label="occurrences.csv" color="#5B86B0" x={210} y={760} frameStart={58} />
      <FilePill label="plots.csv" color="#86EFAC" x={372} y={796} frameStart={68} />
      <FilePill label="reference.gpkg" color="#A78BFA" x={1370} y={212} frameStart={76} />
      <FilePill label="traits.csv" color="#F9D47A" x={1510} y={254} frameStart={86} />

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 92,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          opacity: heroOpacity,
          transform: `translateY(${interpolate(heroProgress, [0, 1], [18, 0])}px)`,
          zIndex: 20,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: 0.4,
            textTransform: "uppercase",
            color: "#5B86B0",
          }}
        >
          {teaserCopy.opener.eyebrow}
        </div>
        <div
          style={{
            marginTop: 18,
            fontFamily: fontDisplay,
            fontSize: 64,
            lineHeight: 1,
            fontWeight: 700,
            color: "#111827",
          }}
        >
          {teaserCopy.opener.title}
        </div>
        <div
          style={{
            marginTop: 18,
            maxWidth: 860,
            fontFamily: fontDisplay,
            fontSize: 19,
            lineHeight: 1.45,
            color: "#475467",
          }}
        >
          {teaserCopy.opener.description}
        </div>
      </div>
    </AbsoluteFill>
  );
};
