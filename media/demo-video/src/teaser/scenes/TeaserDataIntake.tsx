import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { teaserCopy } from "../copy";
import { EditorialOverlay } from "../components/EditorialOverlay";
import { fontDisplay } from "../../shared/fonts";
import { theme } from "../../shared/theme";
import { AppWindow } from "../../ui/AppWindow";

const importFiles = [
  { label: "occurrences.csv", color: "#5B86B0", fromX: 160, fromY: 330, toX: 436, toY: 284 },
  { label: "plots.csv", color: "#86EFAC", fromX: 244, fromY: 420, toX: 640, toY: 284 },
  { label: "traits.csv", color: "#F9D47A", fromX: 292, fromY: 520, toX: 798, toY: 284 },
  { label: "regions.gpkg", color: "#A78BFA", fromX: 1580, fromY: 374, toX: 964, toY: 284 },
] as const;

const groupCards = [
  {
    title: "Tables",
    description: "Occurrences, plots, traits",
    rows: ["3 data files", "29 columns detected", "ready for import"],
  },
  {
    title: "Spatial",
    description: "Administrative layers, regions",
    rows: ["2 layers grouped", "geometry detected", "reference ready"],
  },
  {
    title: "References",
    description: "Controlled vocabularies",
    rows: ["1 vocabulary file", "cross-file match", "schema inferred"],
  },
] as const;

const MovingFileCard: React.FC<{
  label: string;
  color: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  startFrame: number;
}> = ({ label, color, fromX, fromY, toX, toY, startFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 16, stiffness: 120 },
  });

  return (
    <div
      style={{
        position: "absolute",
        left: interpolate(progress, [0, 1], [fromX, toX], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        top: interpolate(progress, [0, 1], [fromY, toY], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        height: 34,
        padding: "0 14px",
        borderRadius: 999,
        border: `1px solid ${theme.border}`,
        background: "#FFFFFF",
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontFamily: fontDisplay,
        fontSize: 12,
        fontWeight: 600,
        color: "#344054",
        boxShadow: "0 8px 20px rgba(15, 23, 42, 0.08)",
      }}
    >
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
      {label}
    </div>
  );
};

export const TeaserDataIntake: React.FC = () => {
  const frame = useCurrentFrame();
  const groupedOpacity = interpolate(frame, [72, 132], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const analysisOpacity = interpolate(frame, [158, 198], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const overlayOpacity = interpolate(frame, [0, 20, 222, 254], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #F7F8FA 0%, #EEF3F6 100%)",
      }}
    >
      <AppWindow activeSidebarItem="data">
        <div style={{ height: "100%", padding: "34px 36px 30px", boxSizing: "border-box", background: "#F9FBFC" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 24 }}>
            <div>
              <div style={{ fontFamily: fontDisplay, fontSize: 12, color: "#98A2B3" }}>Data / Import</div>
              <div style={{ marginTop: 10, fontFamily: fontDisplay, fontSize: 34, fontWeight: 700, color: "#111827" }}>
                Import data
              </div>
              <div style={{ marginTop: 12, fontFamily: fontDisplay, fontSize: 15, color: "#667085", maxWidth: 640 }}>
                Bring source files together before they become collections, pages, and published content.
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {["16 files prepared", "3 target collections", "schema inferred"].map((label, index) => (
                <div
                  key={label}
                  style={{
                    height: 30,
                    padding: "0 12px",
                    borderRadius: 999,
                    background: index === 2 ? "#EEF9F0" : "#FFFFFF",
                    border: `1px solid ${index === 2 ? "#CDEBD5" : theme.border}`,
                    color: index === 2 ? "#15803D" : "#344054",
                    display: "flex",
                    alignItems: "center",
                    fontFamily: fontDisplay,
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  {label}
                </div>
              ))}
            </div>
          </div>

          <div
            style={{
              marginTop: 24,
              borderRadius: 22,
              border: `1px dashed ${theme.borderStrong}`,
              background: "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,248,251,0.96))",
              height: 226,
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 14,
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
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#5B86B0" strokeWidth="1.8">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div style={{ fontFamily: fontDisplay, fontSize: 26, fontWeight: 700, color: "#111827" }}>
                Upload ecological sources
              </div>
              <div style={{ fontFamily: fontDisplay, fontSize: 14, color: "#667085" }}>
                CSV, GeoPackage, GeoJSON, reference files
              </div>
            </div>

            {importFiles.map((file, index) => (
              <MovingFileCard key={file.label} startFrame={18 + index * 10} {...file} />
            ))}
          </div>

          <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
            {groupCards.map((group) => (
              <div
                key={group.title}
                style={{
                  borderRadius: 16,
                  border: `1px solid ${theme.border}`,
                  background: "#FFFFFF",
                  padding: "18px 18px 16px",
                  opacity: groupedOpacity,
                  transform: `translateY(${interpolate(groupedOpacity, [0, 1], [18, 0])}px)`,
                }}
              >
                <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#111827" }}>
                  {group.title}
                </div>
                <div style={{ marginTop: 8, fontFamily: fontDisplay, fontSize: 13, color: "#667085" }}>
                  {group.description}
                </div>
                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
                  {group.rows.map((row) => (
                    <div key={row} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: "#22C55E",
                          flexShrink: 0,
                        }}
                      />
                      <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#475467" }}>{row}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              marginTop: 18,
              borderRadius: 16,
              border: `1px solid ${theme.border}`,
              background: "#FFFFFF",
              padding: "16px 18px 18px",
              opacity: analysisOpacity,
              transform: `translateY(${interpolate(analysisOpacity, [0, 1], [16, 0])}px)`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#111827" }}>
                Automatic preparation
              </div>
              <div style={{ fontFamily: fontDisplay, fontSize: 12, fontWeight: 600, color: "#15803D" }}>
                Analysis running
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14, marginTop: 16 }}>
              {[
                ["Collections", "3"],
                ["Matched layers", "2"],
                ["Reference links", "4"],
                ["Ready pages", "taxa / plots"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  style={{
                    borderRadius: 14,
                    background: "#F8FAFC",
                    border: `1px solid ${theme.border}`,
                    padding: "14px 14px 16px",
                  }}
                >
                  <div style={{ fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>{label}</div>
                  <div style={{ marginTop: 8, fontFamily: fontDisplay, fontSize: 24, fontWeight: 700, color: "#111827" }}>
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </AppWindow>

      <EditorialOverlay
        eyebrow={teaserCopy.intake.eyebrow}
        title={teaserCopy.intake.title}
        description={teaserCopy.intake.description}
        align="top-right"
        width={390}
        opacity={overlayOpacity}
        offsetY={interpolate(overlayOpacity, [0, 1], [16, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
      />
    </AbsoluteFill>
  );
};
