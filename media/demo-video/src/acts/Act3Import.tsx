import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { fontDisplay, fontMono } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";

type ImportFile = {
  name: string;
  size: string;
  color: string;
  category: string;
  note?: string;
  status?: "pending" | "running" | "detected";
};

const importGroups: Array<{ label: string; files: ImportFile[] }> = [
  {
    label: "GEOPACKAGE/GEOJSON",
    files: [
      {
        name: "substrate.gpkg",
        size: "1.61 MB",
        color: "#22C55E",
        category: "spatial",
        status: "detected",
        note: "Detected spatial layer in substrate.gpkg",
      },
      {
        name: "provinces.gpkg",
        size: "23.24 MB",
        color: "#22C55E",
        category: "spatial",
        status: "detected",
        note: "Detected spatial layer in provinces.gpkg",
      },
      {
        name: "protected_areas.gpkg",
        size: "320.0 KB",
        color: "#22C55E",
        category: "spatial",
        status: "pending",
        note: "En attente d’analyse",
      },
    ],
  },
  {
    label: "FICHIERS CSV",
    files: [
      {
        name: "occurrences.csv",
        size: "38.99 MB",
        color: "#3B82F6",
        category: "csv",
        status: "detected",
        note: "Loaded 29 columns from occurrences.csv",
      },
      {
        name: "plot_stats.csv",
        size: "23.9 KB",
        color: "#3B82F6",
        category: "csv",
        status: "running",
        note: "Analyzing plot_stats.csv",
      },
      {
        name: "shape_stats.csv",
        size: "1.99 MB",
        color: "#3B82F6",
        category: "csv",
        status: "detected",
        note: "Detected hierarchy candidates in shape_stats.csv",
      },
    ],
  },
  {
    label: "FICHIERS TIF",
    files: [
      {
        name: "rainfall_epsg3163.tif",
        size: "310.6 KB",
        color: "#A855F7",
        category: "raster",
        status: "pending",
        note: "En attente d’analyse",
      },
      {
        name: "mnt100_epsg3163.tif",
        size: "17.15 MB",
        color: "#A855F7",
        category: "raster",
        status: "pending",
        note: "En attente d’analyse",
      },
    ],
  },
];

const summaryReferences = [
  { name: "plots", meta: "Générique • 22 lignes · 30 champs", badge: "Importé" },
  { name: "taxons", meta: "Hiérarchique • 1667 lignes · 11 champs", badge: "Enrichissement disponible" },
  { name: "shapes", meta: "Spatial • 96 lignes · 13 champs", badge: "Importé" },
];

const importCandidates = [
  { name: "plots", badgeA: "Référence", badgeB: "À noter", meta: "3 datasets • 1 sources auxiliaires" },
  { name: "shapes", badgeA: "Spatial", meta: "Spatial • 7 sources • 1 sources auxiliaires" },
  { name: "taxons", badgeA: "Hiérarchique", meta: "Hiérarchique • dérivé de occurrences" },
];

const supportSources = [
  { name: "occurrences", tag: "Dataset", meta: "CSV • 29 champs • 3 agrégations", color: "#3B82F6" },
  { name: "plot_stats", tag: "Auxiliaire", meta: "rattaché à plots • plot_id → id_plot", color: "#8B5CF6" },
  { name: "shape_stats", tag: "Auxiliaire", meta: "rattaché à shapes • label → name", color: "#8B5CF6" },
];

const DashboardStart: React.FC<{ clickFrame: number }> = ({ clickFrame }) => {
  const frame = useCurrentFrame();

  const buttonScale = interpolate(frame, [clickFrame, clickFrame + 6, clickFrame + 16], [1, 0.96, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        padding: "30px 36px 36px",
        height: "100%",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 24,
          fontWeight: 700,
          color: "#181D27",
          textAlign: "center",
          marginTop: 6,
        }}
      >
        Commencer votre projet
      </div>

      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 15,
          color: "#667085",
          textAlign: "center",
          marginTop: 10,
          lineHeight: 1.45,
        }}
      >
        Commencez par importer vos données. Vous pourrez ensuite configurer les collections et publier votre portail.
      </div>

      <div
        style={{
          width: 1040,
          margin: "28px auto 0",
          borderRadius: 10,
          border: "1px solid rgba(187, 247, 208, 0.98)",
          background: "linear-gradient(180deg, rgba(247, 254, 249, 0.98), rgba(255,255,255,0.99))",
          boxShadow: "0 6px 16px rgba(15, 23, 42, 0.03)",
          padding: "28px 22px 26px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 24,
        }}
      >
        <div style={{ maxWidth: 625 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              height: 22,
              padding: "0 8px",
              borderRadius: 999,
              background: "#DCFCE7",
              color: "#15803D",
              fontFamily: fontDisplay,
              fontSize: 11,
              fontWeight: 500,
            }}
          >
            Étape requise
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginTop: 16,
            }}
          >
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 17,
                background: theme.forestGreen,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 8px 18px rgba(46, 125, 50, 0.18)",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>

            <div
              style={{
                fontFamily: fontDisplay,
                fontSize: 18,
                fontWeight: 600,
                color: "#181D27",
              }}
            >
              Importer vos données
            </div>
          </div>

          <div
            style={{
              marginTop: 16,
              fontFamily: fontDisplay,
              fontSize: 14,
              lineHeight: 1.55,
              color: "#667085",
              maxWidth: 620,
            }}
          >
            Ajoutez vos fichiers sources pour initialiser le projet : CSV, taxonomies, couches géographiques et autres tables de référence.
          </div>
        </div>

        <div
          style={{
            flexShrink: 0,
            height: 38,
            minWidth: 176,
            padding: "0 16px",
            borderRadius: 6,
            background: theme.forestGreen,
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            fontFamily: fontDisplay,
            fontSize: 14,
            fontWeight: 500,
            marginTop: 4,
            transform: `scale(${buttonScale})`,
            boxShadow: "0 10px 22px rgba(46, 125, 50, 0.16)",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>Ouvrir l’import</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2">
            <path d="M5 12h14" />
            <path d="m13 5 7 7-7 7" />
          </svg>
        </div>
      </div>

      <div
        style={{
          width: 1040,
          margin: "16px auto 0",
          borderRadius: 10,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          boxShadow: "0 6px 16px rgba(15, 23, 42, 0.03)",
          padding: "24px 18px 22px",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 11,
              background: "#E6EEFB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              marginTop: 1,
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={theme.steelBlue} strokeWidth="1.9">
              <circle cx="12" cy="12" r="9" />
              <path d="M2.5 12h19" />
              <path d="M12 3a15 15 0 0 1 0 18" />
              <path d="M12 3a15 15 0 0 0 0 18" />
            </svg>
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 18,
                  fontWeight: 600,
                  color: "#181D27",
                }}
              >
                Préparer le site
              </div>
              <div
                style={{
                  height: 26,
                  padding: "0 10px",
                  borderRadius: 999,
                  border: `1px solid ${theme.borderStrong}`,
                  display: "inline-flex",
                  alignItems: "center",
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  color: "#111827",
                }}
              >
                Optionnel
              </div>
            </div>

            <div
              style={{
                marginTop: 10,
                fontFamily: fontDisplay,
                fontSize: 14,
                lineHeight: 1.5,
                color: "#667085",
              }}
            >
              Vous pouvez déjà préparer les pages, la navigation et la structure du portail pendant que les données arrivent.
            </div>

            <div
              style={{
                marginTop: 18,
                display: "inline-flex",
                alignItems: "center",
                gap: 12,
                height: 34,
                padding: "0 14px",
                borderRadius: 6,
                border: `1px solid ${theme.borderStrong}`,
                background: "#FFFFFF",
                fontFamily: fontDisplay,
                fontSize: 13,
                color: "#111827",
              }}
            >
              <span>Ouvrir le site builder</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#111827" strokeWidth="2">
                <path d="M5 12h14" />
                <path d="m13 5 7 7-7 7" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          width: 1040,
          margin: "16px auto 0",
          borderRadius: 10,
          border: "1px dashed rgba(208, 213, 221, 0.95)",
          background: "#FFFFFF",
          padding: "26px 16px",
          boxSizing: "border-box",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#98A2B3" strokeWidth="2" style={{ marginTop: 2 }}>
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <circle cx="12" cy="16" r="0.8" fill="#98A2B3" />
          </svg>

          <div>
            <div
              style={{
                fontFamily: fontDisplay,
                fontSize: 14,
                fontWeight: 600,
                color: "#344054",
              }}
            >
              Ce qui viendra ensuite
            </div>

            <div
              style={{
                marginTop: 10,
                fontFamily: fontDisplay,
                fontSize: 14,
                lineHeight: 1.5,
                color: "#98A2B3",
              }}
            >
              Les collections et la publication seront disponibles après l’import des premières données.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const ModuleSidebar: React.FC<{
  activeSection: "overview" | "import";
  datasetsCount: number;
  referencesCount: number;
}> = ({ activeSection, datasetsCount, referencesCount }) => {
  const navItemStyle = (active: boolean): React.CSSProperties => ({
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "11px 14px",
    borderRadius: 10,
    background: active ? "#E7F3EC" : "transparent",
    color: active ? "#0A8A65" : "#6B7280",
    fontFamily: fontDisplay,
    fontSize: 14,
    fontWeight: active ? 600 : 500,
  });

  return (
    <div
      style={{
        width: 240,
        height: "100%",
        borderRight: `1px solid ${theme.border}`,
        background: "#FBFCFE",
        display: "flex",
        flexDirection: "column",
        padding: "14px 10px 16px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={navItemStyle(activeSection === "overview")}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <rect x="4" y="4" width="7" height="7" rx="1.5" />
            <rect x="13" y="4" width="7" height="7" rx="1.5" />
            <rect x="4" y="13" width="7" height="7" rx="1.5" />
            <rect x="13" y="13" width="7" height="7" rx="1.5" />
          </svg>
          <span>Vue d’ensemble</span>
        </div>

        <div style={navItemStyle(activeSection === "import")}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>Importer des données</span>
        </div>

        <div style={navItemStyle(false)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v8" />
            <path d="M8 12h8" />
          </svg>
          <span>Outils de vérification</span>
        </div>

        <div style={navItemStyle(false)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="m12 2 2.1 6.3L20 10.5l-5.9 2.2L12 19l-2.1-6.3L4 10.5l5.9-2.2z" />
          </svg>
          <span>Enrichissement API</span>
        </div>
      </div>

      <div style={{ height: 1, background: theme.border, margin: "16px 8px" }} />

      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontFamily: fontDisplay,
              fontSize: 14,
              fontWeight: 600,
              color: "#181D27",
            }}
          >
            <span>Jeux de données</span>
            <span
              style={{
                minWidth: 22,
                height: 22,
                borderRadius: 11,
                background: "#EFF3F7",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                color: "#475467",
              }}
            >
              {datasetsCount}
            </span>
          </div>
          <div
            style={{
              marginTop: 10,
              fontFamily: fontDisplay,
              fontSize: 12,
              color: "#98A2B3",
              lineHeight: 1.4,
            }}
          >
            {datasetsCount === 0 ? "Aucun jeu de données importé" : "occurrences"}
          </div>
        </div>

        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontFamily: fontDisplay,
              fontSize: 14,
              fontWeight: 600,
              color: "#181D27",
            }}
          >
            <span>Références</span>
            <span
              style={{
                minWidth: 22,
                height: 22,
                borderRadius: 11,
                background: "#EFF3F7",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                color: "#475467",
              }}
            >
              {referencesCount}
            </span>
          </div>
          <div
            style={{
              marginTop: 10,
              fontFamily: fontDisplay,
              fontSize: 12,
              color: "#98A2B3",
              lineHeight: 1.4,
            }}
          >
            {referencesCount === 0 ? "Aucune référence importée" : "plots · taxons · shapes"}
          </div>
        </div>
      </div>
    </div>
  );
};

const ImportFileRow: React.FC<{
  file: ImportFile;
  mode: "review" | "analysis";
  enterAt: number;
}> = ({ file, mode, enterAt }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [enterAt, enterAt + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const isAnalysis = mode === "analysis";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: isAnalysis ? 12 : 16,
        border: `1px solid ${theme.border}`,
        borderRadius: 10,
        background: "#FFFFFF",
        padding: isAnalysis ? "9px 12px" : "12px 14px",
        opacity: progress,
        transform: `translateY(${(1 - progress) * 10}px)`,
      }}
    >
      <div style={{ display: "flex", gap: isAnalysis ? 10 : 12, minWidth: 0 }}>
        <div
          style={{
            width: isAnalysis ? 16 : 18,
            height: isAnalysis ? 16 : 18,
            borderRadius: isAnalysis ? 8 : 9,
            background: `${file.color}1A`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: isAnalysis ? 1 : 2,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: isAnalysis ? 8 : 9,
              height: isAnalysis ? 8 : 9,
              borderRadius: isAnalysis ? 4 : 4.5,
              background: file.color,
            }}
          />
        </div>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: isAnalysis ? 13 : 14,
              color: "#181D27",
              fontWeight: 500,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: 520,
            }}
          >
            {file.name}
          </div>

          {mode === "analysis" && file.note && (
            <div
              style={{
                marginTop: 2,
                fontFamily: fontDisplay,
                fontSize: 11,
                color: file.status === "detected" ? "#2563EB" : file.status === "running" ? "#15803D" : "#98A2B3",
              }}
            >
              {file.note}
            </div>
          )}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: isAnalysis ? 10 : 14,
          color: "#98A2B3",
          fontFamily: fontDisplay,
          fontSize: isAnalysis ? 12 : 13,
          flexShrink: 0,
        }}
      >
        <span>{file.size}</span>
        {mode === "review" ? <span style={{ fontSize: 18, lineHeight: 1 }}>×</span> : null}
      </div>
    </div>
  );
};

const ImportPanel: React.FC<{
  title: string;
  subtitle: string;
  children: React.ReactNode;
}> = ({ title, subtitle, children }) => (
  <div
    style={{
      border: `1px solid ${theme.border}`,
      borderRadius: 12,
      background: "#FFFFFF",
      boxShadow: "0 8px 24px rgba(15, 23, 42, 0.04)",
      padding: "18px 18px 16px",
      boxSizing: "border-box",
    }}
  >
    <div
      style={{
        fontFamily: fontDisplay,
        fontSize: 16,
        fontWeight: 600,
        color: "#181D27",
      }}
    >
      {title}
    </div>
    <div
      style={{
        marginTop: 6,
        fontFamily: fontDisplay,
        fontSize: 13,
        color: "#667085",
      }}
    >
      {subtitle}
    </div>
    <div style={{ marginTop: 16 }}>{children}</div>
  </div>
);

const EmptyDropzone: React.FC = () => (
  <div
    style={{
      minHeight: 208,
      borderRadius: 12,
      border: "2px dashed rgba(148, 163, 184, 0.45)",
      background: "#FFFFFF",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
    }}
  >
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.8">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
    <div
      style={{
        fontFamily: fontDisplay,
        fontSize: 14,
        fontWeight: 500,
        color: "#344054",
      }}
    >
      Glissez-déposez vos fichiers
    </div>
    <div
      style={{
        fontFamily: fontDisplay,
        fontSize: 12,
        color: "#98A2B3",
      }}
    >
      CSV, GeoPackage, GeoJSON, TIFF
    </div>
  </div>
);

const ReviewFileList: React.FC<{ mode: "review" | "analysis" }> = ({ mode }) => {
  let rowIndex = 0;
  const isAnalysis = mode === "analysis";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: isAnalysis ? 8 : 12 }}>
      {importGroups.map((group) => (
        <div key={group.label}>
          <div
            style={{
              marginBottom: isAnalysis ? 6 : 8,
              fontFamily: fontDisplay,
              fontSize: isAnalysis ? 11 : 12,
              color: "#667085",
              fontWeight: 500,
            }}
          >
            {group.label}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: isAnalysis ? 6 : 8 }}>
            {group.files.map((file) => {
              const currentIndex = rowIndex;
              rowIndex += 1;
              return (
                <ImportFileRow
                  key={file.name}
                  file={file}
                  mode={mode}
                  enterAt={12 + currentIndex * 5}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

const AnalysisHero: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = 1 + 0.08 * Math.sin(frame / 6);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        paddingBottom: 12,
      }}
    >
      <div
        style={{
          width: 42,
          height: 42,
          borderRadius: 21,
          background: "#EEF7F0",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${scale})`,
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#65A879" strokeWidth="2">
          <path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7z" />
        </svg>
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 16,
          fontWeight: 700,
          color: "#181D27",
        }}
      >
        Analyse en cours...
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 12,
          color: "#667085",
        }}
      >
        Préparation de l’analyse pour 16 fichier(s)
      </div>
    </div>
  );
};

const DetectedConfigPanel: React.FC<{ clickFrame: number }> = ({ clickFrame }) => {
  const frame = useCurrentFrame();
  const buttonScale = interpolate(frame, [clickFrame, clickFrame + 6, clickFrame + 14], [1, 0.96, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <ImportPanel
      title="Configuration détectée"
      subtitle="Les entités, agrégations et sources de support ont été déduites automatiquement."
    >
      <div
        style={{
          display: "flex",
          gap: 10,
          padding: 4,
          borderRadius: 10,
          background: "#EEF2F6",
        }}
      >
        <div
          style={{
            flex: 1,
            height: 34,
            borderRadius: 8,
            background: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: fontDisplay,
            fontSize: 14,
            color: "#181D27",
          }}
        >
          Configuration
        </div>
        <div
          style={{
            flex: 1,
            height: 34,
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: fontDisplay,
            fontSize: 14,
            color: "#667085",
          }}
        >
          YAML
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
        {["Agrégations candidates (3)", "Datasets: 1", "Références: 3", "Sources auxiliaires (2)"].map((label) => (
          <div
            key={label}
            style={{
              padding: "5px 9px",
              borderRadius: 8,
              border: `1px solid ${theme.border}`,
              background: "#FFFFFF",
              fontFamily: fontDisplay,
              fontSize: 12,
              color: "#344054",
            }}
          >
            {label}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        {importCandidates.map((candidate) => (
          <div
            key={candidate.name}
            style={{
              borderRadius: 10,
              border: "1px solid rgba(167, 243, 208, 0.9)",
              background: "#FCFFFD",
              padding: "10px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <div
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 14,
                    fontWeight: 600,
                    color: "#181D27",
                  }}
                >
                  {candidate.name}
                </div>
                <div
                  style={{
                    padding: "4px 8px",
                    borderRadius: 8,
                    border: `1px solid ${theme.border}`,
                    fontFamily: fontDisplay,
                    fontSize: 10,
                    color: "#475467",
                  }}
                >
                  {candidate.badgeA}
                </div>
                {candidate.badgeB ? (
                  <div
                    style={{
                      padding: "4px 8px",
                      borderRadius: 8,
                      background: "#EEF2F6",
                      fontFamily: fontDisplay,
                      fontSize: 10,
                      color: "#475467",
                    }}
                  >
                    {candidate.badgeB}
                  </div>
                ) : null}
              </div>
              <div
                style={{
                  marginTop: 8,
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  color: "#667085",
                }}
              >
                {candidate.meta}
              </div>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                color: "#181D27",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="m16 3 5 5-11 11H5v-5z" />
              </svg>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 12,
          fontFamily: fontDisplay,
          fontSize: 15,
          fontWeight: 600,
          color: "#181D27",
        }}
      >
        Sources de support (3)
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
        {supportSources.map((source) => (
          <div
            key={source.name}
            style={{
              borderRadius: 10,
              border: `1px solid ${theme.border}`,
              background: "#FFFFFF",
              padding: "10px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 5,
                    background: source.color,
                  }}
                />
                <div
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 14,
                    fontWeight: 600,
                    color: "#181D27",
                  }}
                >
                  {source.name}
                </div>
                <div
                  style={{
                    padding: "4px 8px",
                    borderRadius: 8,
                    border: `1px solid ${theme.border}`,
                    fontFamily: fontDisplay,
                    fontSize: 10,
                    color: "#475467",
                  }}
                >
                  {source.tag}
                </div>
              </div>
              <div
                style={{
                  marginTop: 8,
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  color: "#667085",
                }}
              >
                {source.meta}
              </div>
            </div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#181D27" strokeWidth="1.8">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14 }}>
        <div
          style={{
            height: 40,
            padding: "0 14px",
            borderRadius: 6,
            border: `1px solid ${theme.borderStrong}`,
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            fontFamily: fontDisplay,
            fontSize: 14,
            color: "#111827",
            background: "#FFFFFF",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#111827" strokeWidth="2">
            <path d="m15 18-6-6 6-6" />
          </svg>
          <span>Annuler</span>
        </div>

        <div
          style={{
            height: 42,
            padding: "0 18px",
            borderRadius: 6,
            background: theme.forestGreen,
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            fontFamily: fontDisplay,
            fontSize: 14,
            fontWeight: 500,
            color: "#FFFFFF",
            boxShadow: "0 10px 22px rgba(46, 125, 50, 0.16)",
            transform: `scale(${buttonScale})`,
          }}
        >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2">
              <path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7z" />
            </svg>
            <span>Lancer l’import</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2">
              <path d="M5 12h14" />
              <path d="m13 5 7 7-7 7" />
            </svg>
        </div>
      </div>
    </ImportPanel>
  );
};

const DataSummaryPanel: React.FC = () => (
  <div style={{ padding: "26px 28px 28px", height: "100%", boxSizing: "border-box" }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 16,
            color: "#667085",
            marginBottom: 8,
          }}
        >
          Données
        </div>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 24,
            fontWeight: 700,
            color: "#181D27",
          }}
        >
          Données importées
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 14,
            color: "#16A34A",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ width: 7, height: 7, borderRadius: 3.5, background: "#22C55E", display: "inline-block" }} />
          <span>Données importées</span>
        </div>

        {["Rafraîchir", "Réimporter"].map((label) => (
          <div
            key={label}
            style={{
              height: 40,
              padding: "0 14px",
              borderRadius: 6,
              border: `1px solid ${theme.borderStrong}`,
              display: "inline-flex",
              alignItems: "center",
              fontFamily: fontDisplay,
              fontSize: 14,
              color: "#111827",
              background: "#FFFFFF",
            }}
          >
            {label}
          </div>
        ))}
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginTop: 18 }}>
      {[
        { value: "205 654", label: "LIGNES IMPORTÉES", meta: "Réparties sur 4 sources" },
        { value: "0", label: "ALERTES CONNUES", meta: "Aucune détectée" },
        { value: "1", label: "ENRICHISSEMENT", meta: "1 disponible(s)", highlight: true },
      ].map((card) => (
        <div
          key={card.label}
          style={{
            borderRadius: 12,
            border: card.highlight ? "1px solid rgba(167, 243, 208, 0.9)" : `1px solid ${theme.border}`,
            background: card.highlight ? "linear-gradient(180deg, rgba(240,253,249,0.95), #FFFFFF)" : "#FFFFFF",
            padding: "24px 18px",
            boxShadow: "0 8px 24px rgba(15, 23, 42, 0.04)",
          }}
        >
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 28,
              fontWeight: 700,
              color: "#181D27",
            }}
          >
            {card.value}
          </div>
          <div
            style={{
              marginTop: 4,
              fontFamily: fontDisplay,
              fontSize: 12,
              letterSpacing: 0.5,
              color: "#667085",
            }}
          >
            {card.label}
          </div>
          <div
            style={{
              marginTop: 8,
              fontFamily: fontDisplay,
              fontSize: 14,
              color: card.highlight ? "#15803D" : "#667085",
            }}
          >
            {card.meta}
          </div>
        </div>
      ))}
    </div>

    <div
      style={{
        marginTop: 16,
        borderRadius: 12,
        border: `1px solid ${theme.border}`,
        background: "#FFFFFF",
        padding: "16px 18px",
        fontFamily: fontDisplay,
        fontSize: 14,
        color: "#667085",
      }}
    >
      Configurez l’enrichissement là où il apporte vraiment quelque chose, ou poursuivez directement vers les collections.
    </div>

    <div style={{ marginTop: 18 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontFamily: fontDisplay,
          fontSize: 15,
          fontWeight: 700,
          color: "#344054",
        }}
      >
        <span style={{ width: 3, height: 16, borderRadius: 2, background: "#16A34A", display: "inline-block" }} />
        <span>RÉFÉRENCES</span>
        <span
          style={{
            minWidth: 22,
            height: 22,
            borderRadius: 11,
            background: "#EFF3F7",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
          }}
        >
          3
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
        {summaryReferences.map((reference) => (
          <div
            key={reference.name}
            style={{
              borderRadius: 10,
              border: `1px solid ${theme.border}`,
              background: "#FFFFFF",
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 15,
                  fontWeight: 600,
                  color: "#181D27",
                }}
              >
                {reference.name}
              </div>
              <div
                style={{
                  marginTop: 4,
                  fontFamily: fontDisplay,
                  fontSize: 13,
                  color: "#667085",
                }}
              >
                {reference.meta}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  padding: "4px 10px",
                  borderRadius: 999,
                  background: reference.badge === "Enrichissement disponible" ? "#F5F7FA" : "#FFFFFF",
                  border: `1px solid ${theme.border}`,
                  fontFamily: fontDisplay,
                  fontSize: 12,
                  color: "#344054",
                }}
              >
                {reference.badge}
              </div>
              <span
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 14,
                  color: "#667085",
                }}
              >
                Détails
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>

    <div style={{ marginTop: 18 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontFamily: fontDisplay,
          fontSize: 15,
          fontWeight: 700,
          color: "#344054",
        }}
      >
        <span style={{ width: 3, height: 16, borderRadius: 2, background: "#60A5FA", display: "inline-block" }} />
        <span>JEUX DE DONNÉES</span>
        <span
          style={{
            minWidth: 22,
            height: 22,
            borderRadius: 11,
            background: "#EFF3F7",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
          }}
        >
          1
        </span>
      </div>

      <div
        style={{
          borderRadius: 10,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          padding: "14px 16px",
          marginTop: 12,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 15,
              fontWeight: 600,
              color: "#181D27",
            }}
          >
            occurrences
          </div>
          <div
            style={{
              marginTop: 4,
              fontFamily: fontDisplay,
              fontSize: 13,
              color: "#667085",
            }}
          >
            Dataset • 203 865 lignes • 31 champs
          </div>
        </div>
        <div
          style={{
            display: "flex",
            gap: 18,
            fontFamily: fontDisplay,
            fontSize: 14,
            color: "#344054",
          }}
        >
          <span>Modifier la config</span>
          <span>Mettre à jour le fichier</span>
        </div>
      </div>
    </div>
  </div>
);

const ImportFlow: React.FC = () => {
  const frame = useCurrentFrame();

  const emptyStart = 0;
  const emptyEnd = 54;
  const reviewStart = 38;
  const reviewEnd = 148;
  const analysisStart = 136;
  const analysisEnd = 270;
  const configStart = 258;
  const configEnd = 370;
  const summaryStart = 360;

  const showEmpty = frame < emptyEnd;
  const showReview = frame >= reviewStart && frame < reviewEnd;
  const showAnalysis = frame >= analysisStart && frame < analysisEnd;
  const showConfig = frame >= configStart && frame < configEnd;
  const showSummary = frame >= summaryStart;

  const panelOpacity = (start: number, end: number) =>
    interpolate(frame, [start, start + 10, end - 10, end], [0, 1, 1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <ModuleSidebar
        activeSection={showSummary ? "overview" : "import"}
        datasetsCount={showSummary ? 1 : 0}
        referencesCount={showSummary ? 3 : 0}
      />

      <div style={{ flex: 1, minWidth: 0, height: "100%", overflow: "hidden" }}>
        {!showSummary && (
          <div style={{ padding: "10px 16px 0", fontFamily: fontDisplay, fontSize: 13, color: "#667085" }}>
            Données &gt; Import
          </div>
        )}

        <div style={{ padding: showSummary ? 0 : "8px 16px 22px", height: "100%", boxSizing: "border-box" }}>
          {!showSummary && (
            <>
              <div
                style={{
                  fontFamily: fontDisplay,
                  fontSize: 24,
                  fontWeight: 700,
                  color: "#181D27",
                }}
              >
                Import de données
              </div>
              <div
                style={{
                  marginTop: 6,
                  fontFamily: fontDisplay,
                  fontSize: 14,
                  color: "#667085",
                }}
              >
                Importez vos fichiers de données et configurez les entités.
              </div>
            </>
          )}

          {!showSummary && (
            <div style={{ position: "relative", marginTop: 18, height: 820 }}>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: showEmpty ? panelOpacity(emptyStart, emptyEnd) : 0,
                }}
              >
                <ImportPanel
                  title="Ajouter des données"
                  subtitle="Glissez-déposez vos fichiers pour commencer l’import."
                >
                  <EmptyDropzone />
                </ImportPanel>
              </div>

              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: showReview ? panelOpacity(reviewStart, reviewEnd) : 0,
                }}
              >
                <ImportPanel
                  title="Ajouter des données"
                  subtitle="Les fichiers sont classés automatiquement avant l’analyse."
                >
                  <ReviewFileList mode="review" />

                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
                    <div
                      style={{
                        height: 42,
                        padding: "0 14px",
                        borderRadius: 6,
                        border: `1px solid ${theme.borderStrong}`,
                        background: "#FFFFFF",
                        display: "inline-flex",
                        alignItems: "center",
                        fontFamily: fontDisplay,
                        fontSize: 14,
                        color: "#111827",
                      }}
                    >
                      Annuler
                    </div>
                    <div
                      style={{
                        height: 42,
                        padding: "0 16px",
                        borderRadius: 6,
                        background: "#0D9F83",
                        color: "#FFFFFF",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 10,
                        fontFamily: fontDisplay,
                        fontSize: 14,
                        fontWeight: 500,
                      }}
                    >
                      <span>Télécharger 16 fichiers</span>
                    </div>
                  </div>
                </ImportPanel>
              </div>

              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: showAnalysis ? panelOpacity(analysisStart, analysisEnd) : 0,
                }}
              >
                <ImportPanel
                  title="Import de données"
                  subtitle="Importez vos fichiers de données et configurez les entités."
                >
                  <AnalysisHero />
                  <ReviewFileList mode="analysis" />
                </ImportPanel>
              </div>

              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  opacity: showConfig ? panelOpacity(configStart, configEnd) : 0,
                }}
              >
                <DetectedConfigPanel clickFrame={282} />
              </div>
            </div>
          )}

          {showSummary && <DataSummaryPanel />}
        </div>
      </div>
    </div>
  );
};

export const Act3Import: React.FC = () => {
  const frame = useCurrentFrame();
  const dashboardEnd = 138;
  const dashboardClickFrame = 92;
  const dashboardOpacity = interpolate(frame, [dashboardEnd - 10, dashboardEnd], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const activeItem = frame < dashboardClickFrame + 12 ? "home" : "data";

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${theme.canvasGradientStart}, ${theme.canvasGradientEnd})`,
      }}
    >
      <AppWindow showSidebar activeSidebarItem={activeItem}>
        <div style={{ position: "relative", height: "100%" }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: dashboardOpacity,
              pointerEvents: "none",
            }}
          >
            <DashboardStart clickFrame={dashboardClickFrame} />
          </div>

          <Sequence from={dashboardEnd}>
            <div style={{ position: "absolute", inset: 0 }}>
              <ImportFlow />
            </div>
          </Sequence>
        </div>
      </AppWindow>

      <CursorOverlay waypoints={CURSOR_PATHS.act3} startFrame={40} />
    </AbsoluteFill>
  );
};
