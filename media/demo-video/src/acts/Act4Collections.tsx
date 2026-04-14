import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CURSOR_PATHS } from "../cursor/cursorPaths";

type CollectionCardData = {
  name: string;
  entityCount: string;
  type: string;
  sheets: string;
};

type CatalogWidget = {
  id: number;
  title: string;
  subtitle: string;
  source: string;
  kind: "nav" | "info" | "map" | "bar" | "donut" | "gauge" | "blank";
  selected?: boolean;
};

type CatalogGroup = {
  title: string;
  icon: "branch" | "map" | "gauge" | "rain" | "tag";
  count: number;
  tint: string;
  widgets: CatalogWidget[];
};

type WidgetListItem = {
  name: string;
  kind: string;
  accent: string;
  icon: "nav" | "map" | "info" | "bar" | "donut" | "gauge";
};

const collectionCards: CollectionCardData[] = [
  { name: "plots", entityCount: "22 entités", type: "Plot", sheets: "22" },
  { name: "taxons", entityCount: "1667 entités", type: "Hiérarchique", sheets: "1667" },
  { name: "shapes", entityCount: "96 entités", type: "Spatial", sheets: "96" },
];

const widgetCatalogGroups: CatalogGroup[] = [
  {
    title: "taxons",
    icon: "branch",
    count: 2,
    tint: "#E8F7EB",
    widgets: [
      {
        id: 3,
        title: "Navigation Taxons",
        subtitle: "hierarchical_nav_widget",
        source: "taxons",
        kind: "nav",
        selected: true,
      },
      {
        id: 1,
        title: "Informations générales",
        subtitle: "field_aggregator",
        source: "taxons",
        kind: "info",
        selected: true,
      },
    ],
  },
  {
    title: "Cartographie",
    icon: "map",
    count: 1,
    tint: "#E8F7EB",
    widgets: [
      {
        id: 2,
        title: "Geo Pt map",
        subtitle: "geospatial_extractor",
        source: "occurrences",
        kind: "map",
        selected: true,
      },
    ],
  },
  {
    title: "elevation",
    icon: "gauge",
    count: 3,
    tint: "#FFF6E5",
    widgets: [
      {
        id: 4,
        title: "Elevation distribution",
        subtitle: "binned_distribution",
        source: "occurrences",
        kind: "bar",
      },
      {
        id: 5,
        title: "Elevation distribution",
        subtitle: "binned_distribution",
        source: "occurrences",
        kind: "donut",
      },
      {
        id: 6,
        title: "Elevation statistics",
        subtitle: "statistical_summary",
        source: "occurrences",
        kind: "gauge",
      },
    ],
  },
  {
    title: "rainfall",
    icon: "rain",
    count: 3,
    tint: "#FFF6E5",
    widgets: [
      {
        id: 7,
        title: "Rainfall distribution",
        subtitle: "binned_distribution",
        source: "occurrences",
        kind: "bar",
      },
      {
        id: 8,
        title: "Rainfall distribution",
        subtitle: "binned_distribution",
        source: "occurrences",
        kind: "donut",
      },
      {
        id: 9,
        title: "Rainfall statistics",
        subtitle: "statistical_summary",
        source: "occurrences",
        kind: "gauge",
      },
    ],
  },
  {
    title: "rank_name",
    icon: "tag",
    count: 2,
    tint: "#F6F7FB",
    widgets: [
      {
        id: 10,
        title: "Rank Name breakdown",
        subtitle: "grouped_breakdown",
        source: "taxons",
        kind: "blank",
      },
      {
        id: 11,
        title: "Top Rank Name",
        subtitle: "top_rank_name",
        source: "taxons",
        kind: "bar",
      },
    ],
  },
];

const widgetList: WidgetListItem[] = [
  { name: "Navigation taxonomique", kind: "Navigation", accent: "#A78BFA", icon: "nav" },
  { name: "Distribution géographique", kind: "Interactive map", accent: "#86EFAC", icon: "map" },
  { name: "Informations générales", kind: "Info grid", accent: "#BFD8FF", icon: "info" },
  { name: "Sous-taxons principaux", kind: "Bar chart", accent: "#F9D47A", icon: "bar" },
  { name: "Distribution DBH", kind: "Bar chart", accent: "#F6C287", icon: "bar" },
  { name: "Phénologie", kind: "Bar chart", accent: "#F9D47A", icon: "bar" },
  { name: "Milieu de vie (Holdridge)", kind: "Bar chart", accent: "#F8CBAA", icon: "bar" },
  { name: "Distribution substrat", kind: "Donut chart", accent: "#FFB36B", icon: "donut" },
  { name: "Répartition pluviométrie", kind: "Bar chart", accent: "#FFD56A", icon: "bar" },
  { name: "Distribution altitudinale", kind: "Bar chart", accent: "#FFD56A", icon: "bar" },
  { name: "Stratification", kind: "Bar chart", accent: "#FFD56A", icon: "bar" },
  { name: "Hauteur maximale", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
  { name: "Diamètre maximal (DBH)", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
  { name: "Densité de bois", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
  { name: "Épaisseur d'écorce", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
  { name: "Surface foliaire spécifique (SLA)", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
  { name: "Surface foliaire", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
  { name: "Épaisseur des feuilles", kind: "Gauge", accent: "#9DE8D4", icon: "gauge" },
];

const breadcrumbStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  fontFamily: fontDisplay,
  fontSize: 12,
  color: "#98A2B3",
};

const chipStyle = (active = false): React.CSSProperties => ({
  height: 28,
  padding: "0 10px",
  borderRadius: 8,
  border: active ? "1px solid rgba(91, 134, 176, 0.35)" : `1px solid ${theme.border}`,
  background: active ? "#F2F7FB" : "#FFFFFF",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: fontDisplay,
  fontSize: 12,
  color: active ? "#365C80" : "#667085",
  fontWeight: active ? 600 : 500,
});

const fadeWindow = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, start + 12, end - 12, end], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const OverviewCard: React.FC<{
  card: CollectionCardData;
  emphasis?: boolean;
}> = ({ card, emphasis = false }) => (
  <div
    style={{
      borderRadius: 10,
      border: `1px solid ${theme.border}`,
      background: "#FFFFFF",
      padding: "14px 14px 12px",
      boxShadow: emphasis ? "0 16px 30px rgba(15, 23, 42, 0.08)" : "0 8px 20px rgba(15, 23, 42, 0.03)",
      transform: emphasis ? "scale(1.01)" : "scale(1)",
    }}
  >
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.8">
          <path d="M12 2 2 7l10 5 10-5-10-5z" />
          <path d="m2 17 10 5 10-5" />
          <path d="m2 12 10 5 10-5" />
        </svg>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 16,
            fontWeight: 700,
            color: "#181D27",
          }}
        >
          {card.name}
        </div>
      </div>

      <div
        style={{
          height: 22,
          padding: "0 10px",
          borderRadius: 999,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          fontFamily: fontDisplay,
          fontSize: 11,
          color: "#98A2B3",
          display: "inline-flex",
          alignItems: "center",
        }}
      >
        Aucune collection configurée
      </div>
    </div>

    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 18 }}>
      <div
        style={{
          height: 30,
          padding: "0 14px",
          borderRadius: 6,
          border: `1px solid ${theme.border}`,
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          fontFamily: fontDisplay,
          fontSize: 13,
          color: "#667085",
          background: "#FFFFFF",
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M8 5v14l11-7z" />
        </svg>
        <span>Calculer</span>
      </div>
    </div>

    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
      <div
        style={{
          height: 22,
          padding: "0 8px",
          borderRadius: 7,
          background: "#F3F4F6",
          fontFamily: fontDisplay,
          fontSize: 11,
          color: "#667085",
          display: "inline-flex",
          alignItems: "center",
        }}
      >
        {card.type}
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 13,
          color: "#667085",
        }}
      >
        {card.entityCount}
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginTop: 16 }}>
      {[
        { value: "0", label: "BLOCS" },
        { value: card.sheets, label: "FICHES" },
        { value: "0", label: "EXPORTS" },
      ].map((stat) => (
        <div
          key={stat.label}
          style={{
            borderRadius: 8,
            background: "#F6F8FB",
            padding: "12px 8px 10px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 24,
              fontWeight: 700,
              color: "#181D27",
              lineHeight: 1,
            }}
          >
            {stat.value}
          </div>
          <div
            style={{
              marginTop: 8,
              fontFamily: fontDisplay,
              fontSize: 10,
              color: "#98A2B3",
              letterSpacing: 0.4,
            }}
          >
            {stat.label}
          </div>
        </div>
      ))}
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginTop: 12 }}>
      {["Blocs", "Liste", "Export"].map((tab, index) => (
        <div
          key={tab}
          style={{
            height: 30,
            borderRadius: 6,
            background: index === 0 ? "#3E8A43" : "#FFFFFF",
            border: index === 0 ? "none" : `1px solid ${theme.border}`,
            color: index === 0 ? "#FFFFFF" : "#111827",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: fontDisplay,
            fontSize: 12,
            fontWeight: 500,
          }}
        >
          {tab}
        </div>
      ))}
    </div>
  </div>
);

const CollectionsOverview: React.FC = () => (
  <div style={{ padding: "18px 18px 24px", height: "100%", boxSizing: "border-box" }}>
    <div style={breadcrumbStyle}>
      <span>Collections</span>
    </div>

    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginTop: 8 }}>
      <div>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 26,
            fontWeight: 700,
            color: "#181D27",
          }}
        >
          Collections
        </div>
        <div
          style={{
            marginTop: 6,
            fontFamily: fontDisplay,
            fontSize: 14,
            color: "#667085",
          }}
        >
          Configurez les widgets et transformations pour chaque collection de référence.
        </div>
      </div>

      <div
        style={{
          height: 32,
          padding: "0 14px",
          borderRadius: 6,
          background: "#95C492",
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          fontFamily: fontDisplay,
          fontSize: 12,
          color: "#FFFFFF",
          fontWeight: 500,
        }}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M8 5v14l11-7z" />
        </svg>
        <span>Recalculer les collections</span>
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 18 }}>
      {collectionCards.map((card) => (
        <OverviewCard key={card.name} card={card} emphasis={card.name === "taxons"} />
      ))}
    </div>
  </div>
);

const EmptyWidgetState: React.FC = () => (
  <>
    <div
      style={{
        marginTop: 28,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
        color: "#98A2B3",
        textAlign: "center",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 24,
          background: "#F2F4F7",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#98A2B3" strokeWidth="1.8">
          <path d="M12 3v6" />
          <path d="M12 15v6" />
          <path d="M5 9h14" />
          <path d="M5 15h14" />
          <circle cx="12" cy="9" r="2" />
          <circle cx="12" cy="15" r="2" />
        </svg>
      </div>

      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 18,
          fontWeight: 700,
          color: "#344054",
        }}
      >
        Aucun widget
      </div>

      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 13,
          lineHeight: 1.45,
          maxWidth: 160,
        }}
      >
        Cliquez sur “Ajouter un widget” pour commencer.
      </div>
    </div>
  </>
);

const WidgetSidebarIcon: React.FC<{ item: WidgetListItem }> = ({ item }) => {
  const common = { width: 12, height: 12, viewBox: "0 0 24 24", fill: "none", stroke: item.accent, strokeWidth: 1.8 };

  if (item.icon === "nav") {
    return (
      <svg {...common}>
        <circle cx="6" cy="6" r="2.2" />
        <circle cx="6" cy="18" r="2.2" />
        <circle cx="18" cy="12" r="2.2" />
        <path d="M8.2 6h3.5a4 4 0 0 1 4 4" />
        <path d="M8.2 18h3.5a4 4 0 0 0 4-4" />
      </svg>
    );
  }

  if (item.icon === "map") {
    return (
      <svg {...common}>
        <path d="M9 18 3 20V6l6-2 6 2 6-2v14l-6 2-6-2z" />
        <path d="M9 4v14" />
        <path d="M15 6v14" />
      </svg>
    );
  }

  if (item.icon === "info") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 10v5" />
        <circle cx="12" cy="7" r="0.8" fill={item.accent} />
      </svg>
    );
  }

  if (item.icon === "donut") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="7" />
        <path d="M12 5a7 7 0 0 1 6 3" />
      </svg>
    );
  }

  if (item.icon === "gauge") {
    return (
      <svg {...common}>
        <path d="M5 15a7 7 0 1 1 14 0" />
        <path d="m12 12 3-3" />
      </svg>
    );
  }

  return (
    <svg {...common}>
      <path d="M4 20V8" />
      <path d="M10 20V4" />
      <path d="M16 20v-9" />
      <path d="M22 20V12" />
    </svg>
  );
};

const WidgetSidebar: React.FC<{ configured: boolean }> = ({ configured }) => (
  <div
    style={{
      width: 320,
      borderRight: `1px solid ${theme.border}`,
      display: "flex",
      flexDirection: "column",
      background: "#FAFBFD",
    }}
  >
    <div style={{ padding: "10px 8px 0", display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          height: 28,
          minWidth: 152,
          padding: "0 12px",
          borderRadius: 4,
          background: "#3E8A43",
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          fontFamily: fontDisplay,
          fontSize: 12.5,
          color: "#FFFFFF",
          fontWeight: 500,
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 15, lineHeight: 1 }}>+</span>
        <span>Ajouter un widget</span>
      </div>
      <div
        style={{
          marginLeft: "auto",
          width: 24,
          height: 24,
          borderRadius: 4,
          border: `1px solid ${theme.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#667085",
        }}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="4" y="5" width="16" height="14" rx="2" />
          <path d="M10 5v14" />
        </svg>
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 12,
          color: "#667085",
          minWidth: 110,
        }}
      >
        18 widgets configurés
      </div>
    </div>

    <div
      style={{
        margin: "8px 8px 0",
        height: 28,
        borderRadius: 4,
        border: `1px solid ${theme.border}`,
        background: "#FFFFFF",
        display: "flex",
        alignItems: "center",
        padding: "0 10px",
        fontFamily: fontDisplay,
        fontSize: 12,
        color: "#98A2B3",
      }}
    >
      Rechercher
    </div>

    {!configured ? (
      <div style={{ flex: 1, padding: "0 8px" }}>
        <EmptyWidgetState />
      </div>
    ) : (
      <>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8, padding: "0 8px", overflow: "hidden" }}>
          {widgetList.map((widget, index) => (
            <div
              key={widget.name}
              style={{
                borderRadius: 6,
                border: `1px solid ${theme.border}`,
                background: "#FFFFFF",
                padding: "6px 7px",
                display: "grid",
                gridTemplateColumns: "12px 18px 1fr 14px",
                alignItems: "center",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 2, color: "#98A2B3" }}>
                <span style={{ width: 3, height: 3, borderRadius: 2, background: "currentColor" }} />
                <span style={{ width: 3, height: 3, borderRadius: 2, background: "currentColor" }} />
                <span style={{ width: 3, height: 3, borderRadius: 2, background: "currentColor" }} />
              </div>

              <div
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 4,
                  background: `${widget.accent}1F`,
                  border: `1px solid ${widget.accent}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <WidgetSidebarIcon item={widget} />
              </div>

              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontFamily: fontDisplay,
                    fontSize: 11.5,
                    fontWeight: 500,
                    color: "#344054",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {widget.name}
                </div>
                <div
                  style={{
                    marginTop: 1,
                    fontFamily: fontDisplay,
                    fontSize: 9.5,
                    color: "#98A2B3",
                  }}
                >
                  {widget.kind}
                </div>
              </div>

              <div style={{ color: "#98A2B3", display: "flex", justifyContent: "center" }}>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="7" y="7" width="11" height="11" rx="1.6" />
                  <path d="M4 15V6a2 2 0 0 1 2-2h9" />
                </svg>
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            marginTop: "auto",
            height: 28,
            borderTop: `1px solid ${theme.border}`,
            padding: "0 8px",
            display: "flex",
            alignItems: "center",
            gap: 12,
            fontFamily: fontDisplay,
            fontSize: 11,
            color: "#98A2B3",
          }}
        >
          <span>18 widgets configurés</span>
        </div>
      </>
    )}
  </div>
);

const NavigationTreePanel: React.FC = () => (
  <div
    style={{
      width: 196,
      borderRight: `1px solid ${theme.border}`,
      display: "flex",
      flexDirection: "column",
      background: "#FFFFFF",
    }}
  >
    <div
      style={{
        height: 34,
        borderBottom: `1px solid ${theme.border}`,
        padding: "0 12px",
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontFamily: fontDisplay,
        fontSize: 12,
        color: "#475467",
      }}
    >
      <span style={{ fontWeight: 600, color: "#344054" }}>N.</span>
      <div
        style={{
          height: 22,
          padding: "0 8px",
          borderRadius: 6,
          background: "#F2F4F7",
          display: "inline-flex",
          alignItems: "center",
          color: "#344054",
        }}
      >
        Hiérarchique
      </div>
      <span style={{ marginLeft: "auto", fontSize: 14 }}>⟳</span>
    </div>

    <div style={{ padding: "10px 12px 0" }}>
      <div
        style={{
          height: 32,
          borderRadius: 6,
          border: `1px solid ${theme.border}`,
          display: "flex",
          alignItems: "center",
          padding: "0 10px",
          fontFamily: fontDisplay,
          fontSize: 12,
          color: "#98A2B3",
        }}
      >
        Search...
      </div>
    </div>

    <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: 12 }}>
      {["Acanthaceae", "Amborellaceae", "Anacardiaceae", "Annonaceae", "Apiaceae", "Apocynaceae"].map((label) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: fontDisplay, fontSize: 12.5, color: "#475467" }}>
          <span style={{ color: "#98A2B3", fontSize: 16, lineHeight: 1 }}>›</span>
          <span>{label}</span>
        </div>
      ))}
    </div>

    <div
      style={{
        marginTop: "auto",
        height: 28,
        borderTop: `1px solid ${theme.border}`,
        padding: "0 12px",
        display: "flex",
        alignItems: "center",
        fontFamily: fontDisplay,
        fontSize: 11,
        color: "#98A2B3",
      }}
    >
      Référence: taxons
    </div>
  </div>
);

const FakeMap: React.FC = () => (
  <Img
    src={staticFile("reference/collections-nc-map-card.png")}
    style={{
      width: "100%",
      display: "block",
      borderRadius: 10,
      border: `1px solid ${theme.border}`,
      background: "#FFFFFF",
    }}
  />
);

const WorkspaceCard: React.FC<{
  title: string;
  mode: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ title, mode, children, style }) => (
  <div
    style={{
      borderRadius: 8,
      border: `1px solid ${theme.border}`,
      background: "#FFFFFF",
      overflow: "hidden",
      ...style,
    }}
  >
    <div
      style={{
        height: 40,
        borderBottom: `1px solid ${theme.border}`,
        padding: "0 14px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "#FCFCFD",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: fontDisplay, fontSize: 12.5, color: "#344054", fontWeight: 600 }}>
        <span style={{ color: "#98A2B3" }}>⋮</span>
        <span>{title}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div
          style={{
            height: 20,
            padding: "0 8px",
            borderRadius: 6,
            background: "#F2F4F7",
            display: "inline-flex",
            alignItems: "center",
            fontFamily: fontDisplay,
            fontSize: 10,
            color: "#475467",
          }}
        >
          {mode}
        </div>
        <span style={{ color: "#667085", fontSize: 13 }}>◻︎</span>
      </div>
    </div>
    {children}
  </div>
);

const PreviewWorkspace: React.FC<{ computing: boolean }> = ({ computing }) => (
  <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, background: "#FFFFFF" }}>
    {computing && (
      <>
        <div
          style={{
            height: 6,
            background: "#ECFDF3",
            position: "relative",
          }}
        >
          <div style={{ position: "absolute", inset: 0, width: "39%", background: "#3E8A43" }} />
        </div>
        <div
          style={{
            height: 34,
            borderBottom: `1px solid ${theme.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 12px",
            fontFamily: fontDisplay,
            fontSize: 12,
            color: "#667085",
          }}
        >
          <span>2 traitement en cours.</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span>Hiérarchique</span>
            <div
              style={{
                height: 20,
                padding: "0 8px",
                borderRadius: 6,
                background: "#8AB97D",
                color: "#FFFFFF",
                display: "inline-flex",
                alignItems: "center",
                fontWeight: 600,
              }}
            >
              33%
            </div>
          </div>
        </div>
      </>
    )}

    <div
      style={{
        height: 42,
        borderBottom: `1px solid ${theme.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 14px",
        fontFamily: fontDisplay,
        fontSize: 13,
        color: "#667085",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontWeight: 700, color: "#181D27", fontSize: 15 }}>taxons</span>
        <span style={{ color: "#98A2B3" }}>⌄</span>
        <span style={chipStyle()}>Sources</span>
        <span style={chipStyle(true)}>Blocs</span>
        <span style={chipStyle()}>Liste</span>
        <span style={chipStyle()}>Export</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span>1667 entités</span>
        <span style={chipStyle()}>Hiérarchique</span>
        <span style={{ color: "#16A34A", fontSize: 11 }}>◉ il y a 32 min</span>
        <div
          style={{
            height: 30,
            padding: "0 12px",
            borderRadius: 6,
            background: computing ? "#E8F4E7" : "#107D2F",
            color: computing ? "#107D2F" : "#FFFFFF",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 500,
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 5v14l11-7z" />
          </svg>
          <span>Lancer le calcul</span>
        </div>
      </div>
    </div>

    <div
      style={{
        height: 42,
        borderBottom: `1px solid ${theme.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 10px",
        background: "#FFFFFF",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            height: 28,
            padding: "0 10px",
            borderRadius: 4,
            background: "#3E8A43",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontFamily: fontDisplay,
            fontSize: 12,
            color: "#FFFFFF",
            fontWeight: 500,
          }}
        >
          <span>+</span>
          <span>Ajouter un widget</span>
        </div>
        <div style={{ color: "#667085", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ display: "inline-flex", width: 16, justifyContent: "center" }}>◫</span>
          <span style={{ fontFamily: fontDisplay, fontSize: 12, color: "#667085" }}>18 widgets configurés</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {[
          ["◉", "Miniatures", "⌄"],
          ["⟲", "[Family]Myrtac", "⌄"],
        ].map(([icon, label, arrow]) => (
          <div
            key={label}
            style={{
              height: 30,
              padding: "0 10px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              fontFamily: fontDisplay,
              fontSize: 12,
              color: "#475467",
            }}
          >
            <span>{icon}</span>
            <span>{label}</span>
            <span style={{ color: "#98A2B3" }}>{arrow}</span>
          </div>
        ))}
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#475467",
          }}
        >
          ⟳
        </div>
        <div
          style={{
            height: 30,
            padding: "0 12px",
            borderRadius: 4,
            background: "#9BC393",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            fontFamily: fontDisplay,
            fontSize: 12,
            color: "#FFFFFF",
            fontWeight: 500,
          }}
        >
          <span>💾</span>
          <span>Sauvegarder</span>
        </div>
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "320px 196px 1fr", flex: 1, minHeight: 0 }}>
      <WidgetSidebar configured />
      <NavigationTreePanel />

      <div style={{ padding: "10px 12px 10px", boxSizing: "border-box", display: "grid", gridTemplateColumns: "1fr 0.64fr", gap: 12, gridAutoRows: "min-content", alignContent: "start" }}>
        <div style={{ gridColumn: "1 / span 2" }}>
          <FakeMap />
        </div>

        <WorkspaceCard title="Informations générales" mode="Info grid">
          <div style={{ padding: "16px" }}>
            <div style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#111827", marginBottom: 16 }}>Informations générales</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {[
                ["Taxon", "Myrtaceae"],
                ["Rang", "Famille"],
                ["Nombre\nd'occurrences", "20 039"],
              ].map(([label, value], index) => (
                <div
                  key={label}
                  style={{
                    borderRadius: 8,
                    background: "#FFFFFF",
                    border: `1px solid ${theme.border}`,
                    padding: "12px 14px",
                    minHeight: index === 2 ? 64 : 58,
                  }}
                >
                  <div style={{ fontFamily: fontDisplay, fontSize: 10, color: "#98A2B3", whiteSpace: "pre-line" }}>{label}</div>
                  <div style={{ marginTop: 4, fontFamily: fontDisplay, fontSize: index === 2 ? 18 : 14, fontWeight: 700, color: "#1F2937" }}>{value}</div>
                </div>
              ))}
              <div style={{ borderRadius: 8, background: "#FFFFFF", border: `1px solid ${theme.border}`, minHeight: 64 }} />
            </div>
          </div>
        </WorkspaceCard>

        <WorkspaceCard title="Sous-taxons principaux" mode="Bar chart">
          <div style={{ padding: "12px 12px 10px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              {[
                ["Tristaniopsis calobuxus", 1160, "#6CA9DF"],
                ["Melaleuca quinquenervia", 899, "#C23C76"],
                ["Arillastrum gummiferum", 881, "#69CD58"],
                ["Tristaniopsis macphersonii", 841, "#5A46B2"],
                ["Syzygium macranthum", 697, "#E1A245"],
                ["Syzygium fructescens", 590, "#41B3AC"],
                ["Cloezia artensis", 530, "#C764C7"],
                ["Metrosideros laurifolia", 507, "#79BB1E"],
                ["Syzygium multipetalum", 481, "#5E88D7"],
                ["Syzygium neolaurifolium", 458, "#C56565"],
              ].map(([label, value, color]) => (
                <div key={String(label)} style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 8, alignItems: "center" }}>
                  <div style={{ fontFamily: fontDisplay, fontSize: 10.5, color: "#42526B", textAlign: "right", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {label}
                  </div>
                  <div style={{ position: "relative", height: 14, background: "#EDF2FA" }}>
                    <div style={{ width: `${(Number(value) / 1160) * 100}%`, height: "100%", background: String(color) }} />
                    <div style={{ position: "absolute", right: 4, top: 1, fontFamily: fontDisplay, fontSize: 8.5, color: "#FFFFFF", fontWeight: 700 }}>
                      {value}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 56, marginTop: 4, fontFamily: fontDisplay, fontSize: 10, color: "#667085" }}>
              <span>0</span>
              <span>500</span>
              <span>1000</span>
            </div>
            <div style={{ marginTop: 8, fontFamily: fontDisplay, fontSize: 10.5, color: "#98A2B3" }}>
              Principaux sous-taxons (espèce, sous-espèce)
            </div>
          </div>
        </WorkspaceCard>

        <WorkspaceCard title="Distribution DBH" mode="Bar chart">
          <div style={{ height: 164, padding: "8px 12px 12px", position: "relative" }}>
            <div style={{ position: "absolute", inset: "10px 12px 12px 12px", background: "#DFE8F4" }} />
            {[0, 1, 2, 3].map((index) => (
              <div key={index} style={{ position: "absolute", left: 12, right: 12, top: 24 + index * 28, height: 1, background: "rgba(255,255,255,0.75)" }} />
            ))}
            <div style={{ position: "absolute", left: 22, bottom: 18, display: "flex", alignItems: "flex-end", gap: 14 }}>
              {[0.96, 0.34, 0.28, 0.22, 0.16].map((bar, index) => (
                <div key={index} style={{ width: 20, height: `${bar * 110}px`, background: index === 0 ? "#DDBE9B" : "#D6E0F0" }} />
              ))}
            </div>
            <div style={{ position: "absolute", left: 8, top: 20, fontFamily: fontDisplay, fontSize: 10.5, color: "#42526B" }}>60</div>
            <div style={{ position: "absolute", left: 36, top: 30, transform: "rotate(90deg)", fontFamily: fontDisplay, fontSize: 10, color: "#667085" }}>57.8</div>
          </div>
        </WorkspaceCard>

        <WorkspaceCard title="Phénologie" mode="Bar chart">
          <div style={{ height: 164, padding: "8px 12px 12px", position: "relative" }}>
            <div style={{ position: "absolute", inset: "10px 12px 12px 12px", background: "#DFE8F4" }} />
            {[0, 1, 2].map((index) => (
              <div key={index} style={{ position: "absolute", left: 12, right: 12, top: 28 + index * 38, height: 1, background: "rgba(255,255,255,0.75)" }} />
            ))}
            <div style={{ position: "absolute", left: 22, bottom: 18, display: "flex", alignItems: "flex-end", gap: 10 }}>
              {[0.72, 0.86, 0.18, 0.06, 0.12, 0.14, 0.15, 0.06, 0.1, 0.14, 0.18, 0.72].map((bar, index) => (
                <div key={index} style={{ width: 8, height: `${bar * 96}px`, background: index >= 8 && index <= 10 ? "#95C47C" : "#FDB83B" }} />
              ))}
            </div>
            <div style={{ position: "absolute", left: 8, top: 18, fontFamily: fontDisplay, fontSize: 10.5, color: "#42526B" }}>50</div>
          </div>
        </WorkspaceCard>
      </div>
    </div>
  </div>
);

const EmptyCollectionPage: React.FC = () => (
  <div style={{ padding: "10px 12px 12px", boxSizing: "border-box", height: "100%" }}>
    <div style={breadcrumbStyle}>
      <span>Collections</span>
      <span>›</span>
      <span>taxons</span>
    </div>

    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 22,
            fontWeight: 700,
            color: "#181D27",
          }}
        >
          taxons
        </div>
        <span style={chipStyle()}>Sources</span>
        <span style={chipStyle(true)}>Blocs</span>
        <span style={chipStyle()}>Liste</span>
        <span style={chipStyle()}>Export</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: fontDisplay, fontSize: 12, color: "#667085" }}>
        <span>2007 entités</span>
        <span style={chipStyle()}>Hiérarchique</span>
        <div
          style={{
            height: 28,
            padding: "0 12px",
            borderRadius: 6,
            background: "#B9D8B3",
            color: "#FFFFFF",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 500,
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 5v14l11-7z" />
          </svg>
          <span>Lancer le calcul</span>
        </div>
      </div>
    </div>

    <div style={{ display: "flex", height: "calc(100% - 56px)", marginTop: 8 }}>
      <WidgetSidebar configured={false} />

      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#98A2B3",
          textAlign: "center",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 24,
              background: "#F2F4F7",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#98A2B3" strokeWidth="1.8">
              <path d="M12 3v6" />
              <path d="M12 15v6" />
              <path d="M5 9h14" />
              <path d="M5 15h14" />
              <circle cx="12" cy="9" r="2" />
              <circle cx="12" cy="15" r="2" />
            </svg>
          </div>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 26,
              fontWeight: 700,
              color: "#344054",
            }}
          >
            Aucun widget configuré
          </div>
          <div
            style={{
              maxWidth: 300,
              fontFamily: fontDisplay,
              fontSize: 14,
              lineHeight: 1.45,
            }}
          >
            Ajoutez des widgets en utilisant le bouton “Ajouter un widget” dans le panneau de gauche.
          </div>
        </div>
      </div>
    </div>
  </div>
);

const catalogTabStyle = (active = false): React.CSSProperties => ({
  height: 36,
  padding: "0 16px",
  borderRadius: 10,
  border: active ? "1px solid rgba(208, 213, 221, 0.9)" : "1px solid transparent",
  background: active ? "#FFFFFF" : "transparent",
  display: "inline-flex",
  alignItems: "center",
  gap: 10,
  fontFamily: fontDisplay,
  fontSize: 14,
  color: "#181D27",
  fontWeight: active ? 600 : 500,
});

const catalogChipStyle = (active = false): React.CSSProperties => ({
  height: 28,
  padding: "0 12px",
  borderRadius: 8,
  border: active ? "1px solid #15803D" : `1px solid ${theme.border}`,
  background: active ? "#15803D" : "#FFFFFF",
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  fontFamily: fontDisplay,
  fontSize: 13,
  color: active ? "#FFFFFF" : "#344054",
  fontWeight: active ? 600 : 500,
});

const sourceChipStyle = (active = false): React.CSSProperties => ({
  height: 22,
  padding: "0 10px",
  borderRadius: 7,
  border: "none",
  background: active ? "#F2F4F7" : "transparent",
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  fontFamily: fontDisplay,
  fontSize: 12,
  color: "#344054",
  fontWeight: active ? 600 : 500,
});

const CatalogIcon: React.FC<{
  kind:
    | CatalogGroup["icon"]
    | "sparkles"
    | "combine"
    | "custom"
    | "search"
    | "layers"
    | "chart"
    | "info"
    | "donut"
    | "database";
}> = ({ kind }) => {
  const stroke = "#344054";

  if (kind === "sparkles") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="m12 2 1.7 5.3L19 9l-5.3 1.7L12 16l-1.7-5.3L5 9l5.3-1.7z" />
        <path d="m5 14 .9 2.7L8.5 18l-2.6.9L5 21.5l-.9-2.6L1.5 18l2.6-.9z" />
      </svg>
    );
  }

  if (kind === "combine") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <rect x="4" y="5" width="6" height="6" rx="1.5" />
        <rect x="14" y="5" width="6" height="6" rx="1.5" />
        <rect x="9" y="13" width="6" height="6" rx="1.5" />
        <path d="M10 8h4" />
        <path d="M12 11v2" />
      </svg>
    );
  }

  if (kind === "custom") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="m4 20 4.5-1 9-9-3.5-3.5-9 9z" />
        <path d="m13.5 6.5 3.5 3.5" />
        <path d="m19 5 1.5-1.5" />
      </svg>
    );
  }

  if (kind === "search") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
    );
  }

  if (kind === "branch") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <circle cx="6" cy="6" r="2.2" />
        <circle cx="6" cy="18" r="2.2" />
        <circle cx="18" cy="12" r="2.2" />
        <path d="M8.2 6h3.5a4 4 0 0 1 4 4v0" />
        <path d="M8.2 18h3.5a4 4 0 0 0 4-4v0" />
      </svg>
    );
  }

  if (kind === "map") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="M9 18 3 20V6l6-2 6 2 6-2v14l-6 2-6-2z" />
        <path d="M9 4v14" />
        <path d="M15 6v14" />
      </svg>
    );
  }

  if (kind === "gauge") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="M4 15a8 8 0 1 1 16 0" />
        <path d="m12 12 4-4" />
      </svg>
    );
  }

  if (kind === "rain") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 8.5 3.5 3.5 0 1 1 17 18z" />
        <path d="m9 19-1 3" />
        <path d="m13 19-1 3" />
        <path d="m17 19-1 3" />
      </svg>
    );
  }

  if (kind === "tag") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="M20 13 11 22l-9-9V4h9z" />
        <circle cx="7" cy="9" r="1.4" />
      </svg>
    );
  }

  if (kind === "database") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <ellipse cx="12" cy="5" rx="7" ry="2.6" />
        <path d="M5 5v6c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V5" />
        <path d="M5 11v6c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6v-6" />
      </svg>
    );
  }

  if (kind === "layers") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <rect x="4" y="4" width="7" height="7" rx="1.5" />
        <rect x="13" y="4" width="7" height="7" rx="1.5" />
        <rect x="4" y="13" width="7" height="7" rx="1.5" />
        <rect x="13" y="13" width="7" height="7" rx="1.5" />
      </svg>
    );
  }

  if (kind === "chart") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <path d="M4 20V8" />
        <path d="M10 20V4" />
        <path d="M16 20v-9" />
        <path d="M22 20V12" />
      </svg>
    );
  }

  if (kind === "info") {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 10v6" />
        <circle cx="12" cy="7" r="0.8" fill={stroke} />
      </svg>
    );
  }

  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.8">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 4v8l5 3" />
    </svg>
  );
};

const WidgetThumb: React.FC<{ kind: CatalogWidget["kind"] }> = ({ kind }) => {
  if (kind === "nav") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF" }}>
        {[10, 22, 34, 46].map((top, index) => (
          <div key={top} style={{ position: "absolute", left: 10, right: 12, top, display: "flex", gap: 6, alignItems: "center" }}>
            <div style={{ width: index === 0 ? 16 : 6, height: 4, borderRadius: 2, background: index === 0 ? "#16A34A" : "#CBD5E1" }} />
            <div style={{ flex: 1, height: 4, borderRadius: 2, background: "#E2E8F0" }} />
          </div>
        ))}
      </div>
    );
  }

  if (kind === "info") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", padding: 6, boxSizing: "border-box", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
        {["Myrtaceae", "Famille", "1667", "Taxons"].map((label) => (
          <div key={label} style={{ borderRadius: 4, background: "#F8FAFC", padding: "4px 5px" }}>
            <div style={{ fontFamily: fontDisplay, fontSize: 6, color: "#94A3B8" }}>{label}</div>
            <div style={{ marginTop: 2, height: 6, borderRadius: 3, background: "#D0D5DD" }} />
          </div>
        ))}
      </div>
    );
  }

  if (kind === "map") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#D8E3EA" }}>
        <svg width="100%" height="100%" viewBox="0 0 104 64" preserveAspectRatio="none" style={{ position: "absolute", inset: 0 }}>
          <path d="M12 16 27 8l19 8 20 16 17 10-4 10-20 4-19-6-18-10-8-14Z" fill="#FFFEFC" stroke="#E4E4DC" strokeWidth="1.2" />
          {[
            [32, 24],
            [36, 26],
            [40, 28],
            [46, 31],
            [49, 33],
            [53, 35],
          ].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="1.5" fill="#6D28D9" />
          ))}
        </svg>
        <div style={{ position: "absolute", right: 8, top: 5, width: 10, height: 54, borderRadius: 5, background: "linear-gradient(180deg, #FDE047, #FB923C, #A21CAF)" }} />
      </div>
    );
  }

  if (kind === "bar") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", display: "flex", alignItems: "flex-end", gap: 3, padding: "7px 8px 6px", boxSizing: "border-box" }}>
        {[0.62, 0.82, 0.54, 0.9, 0.58, 0.42, 0.74].map((bar, index) => (
          <div key={index} style={{ width: 8, height: `${bar * 100}%`, borderRadius: "3px 3px 0 0", background: "#818CF8" }} />
        ))}
      </div>
    );
  }

  if (kind === "donut") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="52" height="52" viewBox="0 0 52 52">
          <circle cx="26" cy="26" r="17" stroke="#E5E7EB" strokeWidth="12" fill="none" />
          <circle cx="26" cy="26" r="17" stroke="#EF4444" strokeWidth="12" strokeDasharray="26 81" strokeLinecap="round" fill="none" transform="rotate(-90 26 26)" />
          <circle cx="26" cy="26" r="17" stroke="#F59E0B" strokeWidth="12" strokeDasharray="20 87" strokeDashoffset="-29" strokeLinecap="round" fill="none" transform="rotate(-90 26 26)" />
          <circle cx="26" cy="26" r="17" stroke="#8B5CF6" strokeWidth="12" strokeDasharray="14 93" strokeDashoffset="-52" strokeLinecap="round" fill="none" transform="rotate(-90 26 26)" />
          <circle cx="26" cy="26" r="17" stroke="#10B981" strokeWidth="12" strokeDasharray="10 97" strokeDashoffset="-68" strokeLinecap="round" fill="none" transform="rotate(-90 26 26)" />
        </svg>
      </div>
    );
  }

  if (kind === "gauge") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="84" height="52" viewBox="0 0 84 52">
          <path d="M12 42a30 30 0 0 1 60 0" fill="none" stroke="#E5E7EB" strokeWidth="8" />
          <path d="M12 42a30 30 0 0 1 36-28" fill="none" stroke="#60A5FA" strokeWidth="8" />
          <text x="42" y="35" textAnchor="middle" fontFamily="Plus Jakarta Sans" fontSize="8" fill="#344054">435m</text>
        </svg>
      </div>
    );
  }

  if (kind === "blank") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 42, height: 3, borderRadius: 2, background: "#E5E7EB" }} />
      </div>
    );
  }

  return null;
};

const GroupIcon: React.FC<{ icon: CatalogGroup["icon"] }> = ({ icon }) => {
  const color = icon === "map" ? "#16A34A" : icon === "gauge" || icon === "rain" ? "#D97706" : "#667085";
  return (
    <div style={{ color }}>
      <CatalogIcon kind={icon} />
    </div>
  );
};

const selectedWidgetCount = widgetCatalogGroups.reduce(
  (total, group) => total + group.widgets.filter((widget) => widget.selected).length,
  0,
);

const CatalogWidgetCard: React.FC<{ widget: CatalogWidget; selected: boolean }> = ({ widget, selected }) => {
  const isSelected = selected && widget.selected;

  return (
    <div
      style={{
        position: "relative",
        minHeight: 64,
        borderRadius: 10,
        border: isSelected ? "1px solid rgba(21, 128, 61, 0.55)" : `1px solid ${theme.border}`,
        background: isSelected ? "#F6FFF8" : "#FFFFFF",
        display: "grid",
        gridTemplateColumns: "98px 1fr 20px",
        gap: 10,
        padding: "7px 9px",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          height: 48,
          borderRadius: 8,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 6,
            top: 6,
            width: 20,
            height: 20,
            borderRadius: 10,
            background: "#15803D",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: fontDisplay,
            fontSize: 11,
            fontWeight: 700,
            zIndex: 1,
          }}
        >
          {widget.id}
        </div>
        <WidgetThumb kind={widget.kind} />
      </div>

      <div style={{ minWidth: 0, paddingTop: 5 }}>
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 12.5,
            fontWeight: 600,
            color: "#181D27",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {widget.title}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: 6, flexWrap: "wrap" }}>
          <div
            style={{
              height: 18,
              padding: "0 7px",
              borderRadius: 6,
              background: "#F2F4F7",
              display: "inline-flex",
              alignItems: "center",
              fontFamily: fontDisplay,
              fontSize: 9.5,
              color: "#344054",
            }}
          >
            {widget.subtitle}
          </div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 5, fontFamily: fontDisplay, fontSize: 10.5, color: "#344054" }}>
            <CatalogIcon kind={widget.source === "taxons" ? "branch" : "database"} />
            <span>{widget.source}</span>
          </div>
        </div>
      </div>

      <div
        style={{
          alignSelf: "center",
          width: 18,
          height: 18,
          borderRadius: 5,
          border: isSelected ? "1px solid #15803D" : `1px solid ${theme.borderStrong}`,
          background: isSelected ? "#15803D" : "#FFFFFF",
          color: "#FFFFFF",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          fontWeight: 700,
        }}
      >
        {isSelected ? "✓" : ""}
      </div>
    </div>
  );
};

const WidgetCatalogModal: React.FC<{ selected: boolean }> = ({ selected }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: "rgba(17, 24, 39, 0.56)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "18px 0 22px",
      boxSizing: "border-box",
    }}
  >
    <div
      style={{
        width: 1460,
        height: 888,
        borderRadius: 12,
        background: "#FFFFFF",
        boxShadow: "0 34px 68px rgba(15, 23, 42, 0.22)",
        overflow: "hidden",
        border: `1px solid ${theme.border}`,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          height: 58,
          borderBottom: `1px solid ${theme.border}`,
          padding: "0 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontFamily: fontDisplay,
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, color: "#181D27", fontSize: 18, fontWeight: 700 }}>
          <span style={{ fontSize: 28, fontWeight: 400 }}>+</span>
          <span>Ajouter un widget</span>
        </div>
        <div style={{ fontSize: 28, color: "#667085", lineHeight: 1 }}>×</div>
      </div>

      <div
        style={{
          height: 56,
          borderBottom: `1px solid ${theme.border}`,
          background: "#F8FAFC",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "0 16px",
          boxSizing: "border-box",
          flexShrink: 0,
        }}
      >
          <div style={catalogTabStyle(true)}>
          <CatalogIcon kind="sparkles" />
          <span>Suggestions</span>
          <div
            style={{
              minWidth: 28,
              height: 24,
              borderRadius: 8,
              background: "#F2F4F7",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: fontDisplay,
              fontSize: 12,
              color: "#475467",
              fontWeight: 600,
              padding: "0 6px",
            }}
          >
            66
          </div>
        </div>
        <div style={catalogTabStyle()}>
          <CatalogIcon kind="combine" />
          <span>Combines</span>
        </div>
        <div style={catalogTabStyle()}>
          <CatalogIcon kind="custom" />
          <span>Personnalise</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 408px", minHeight: 0, flex: 1 }}>
        <div style={{ minWidth: 0, borderRight: `1px solid ${theme.border}`, display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "16px 16px 12px", borderBottom: `1px solid ${theme.border}` }}>
            <div style={{ display: "flex", gap: 8 }}>
              <div
                style={{
                  flex: 1,
                  height: 36,
                  borderRadius: 8,
                  border: `1px solid ${theme.border}`,
                  background: "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "0 12px",
                  fontFamily: fontDisplay,
                  fontSize: 14,
                  color: "#98A2B3",
                }}
              >
                <CatalogIcon kind="search" />
                <span>Rechercher...</span>
              </div>
              <div
                style={{
                  width: 38,
                  height: 36,
                  borderRadius: 8,
                  border: `1px solid ${theme.border}`,
                  background: "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#667085",
                  fontSize: 15,
                }}
              >
                ⇅
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              {[
                ["Tout", "sparkles", true],
                ["Navigation", "branch", false],
                ["Carte", "map", false],
                ["Graphique", "chart", false],
                ["Info", "layers", false],
                ["Donut", "donut", false],
                ["Jauge", "gauge", false],
              ].map(([label, icon, active]) => (
                <div key={String(label)} style={catalogChipStyle(Boolean(active))}>
                  <CatalogIcon kind={icon as Parameters<typeof CatalogIcon>[0]["kind"]} />
                  <span>{label}</span>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10, fontFamily: fontDisplay, fontSize: 12, color: "#667085" }}>
              <span>Source:</span>
              <div style={sourceChipStyle(true)}>
                <span>Toutes</span>
              </div>
              <div style={sourceChipStyle()}>
                <CatalogIcon kind="branch" />
                <span>taxons</span>
              </div>
              <div style={sourceChipStyle()}>
                <CatalogIcon kind="database" />
                <span>occurrences</span>
              </div>
            </div>
          </div>

          <div
            style={{
              flex: 1,
              minHeight: 0,
              padding: "10px 14px 10px",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              overflow: "hidden",
              boxSizing: "border-box",
            }}
          >
            {widgetCatalogGroups.map((group) => (
              <div
                key={group.title}
                style={{
                  borderRadius: 10,
                  border: `1px solid ${theme.border}`,
                  background: "#FFFFFF",
                  overflow: "hidden",
                  boxShadow: "0 1px 2px rgba(16, 24, 40, 0.03)",
                }}
              >
                <div
                  style={{
                    height: 32,
                    background: group.tint,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0 11px",
                    boxSizing: "border-box",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 9, fontFamily: fontDisplay, fontSize: 14, fontWeight: 600, color: "#344054" }}>
                    <span style={{ color: "#98A2B3", fontSize: 12 }}>⌄</span>
                    <GroupIcon icon={group.icon} />
                    <span>{group.title}</span>
                  </div>
                  <div
                    style={{
                      minWidth: 24,
                      height: 22,
                      borderRadius: 8,
                      background: "#F2F4F7",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: fontDisplay,
                      fontSize: 11,
                      color: "#475467",
                      fontWeight: 600,
                      padding: "0 6px",
                    }}
                  >
                    {group.count}
                  </div>
                </div>

                <div
                  style={{
                    padding: "8px",
                    display: "grid",
                    gridTemplateColumns: group.widgets.length === 1 ? "1fr" : "1fr 1fr",
                    gap: 6,
                  }}
                >
                  {group.widgets.map((widget) => (
                    <CatalogWidgetCard key={`${group.title}-${widget.title}`} widget={widget} selected={selected} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ background: "#FFFFFF", display: "flex", flexDirection: "column", minWidth: 0 }}>
          <div style={{ padding: "16px 16px 0", display: "flex", alignItems: "center", justifyContent: "space-between", fontFamily: fontDisplay }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14.5, fontWeight: 600, color: "#344054" }}>
              <CatalogIcon kind="branch" />
              <span>Navigation Taxons</span>
            </div>

            <div
              style={{
                height: 30,
                padding: "0 12px",
                borderRadius: 8,
                border: `1px solid ${theme.border}`,
                background: "#FFFFFF",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                fontFamily: fontDisplay,
                fontSize: 12.5,
                color: "#344054",
                fontWeight: 600,
              }}
            >
              {selected ? (
                <>
                  <span style={{ color: "#15803D" }}>✓</span>
                  <span>Sélectionné</span>
                </>
              ) : (
                <span>Non sélectionné</span>
              )}
            </div>
          </div>

          <div style={{ padding: "12px 16px 0" }}>
            <div
              style={{
                height: 246,
                borderRadius: 8,
                background: "#FFFFFF",
                border: `1px solid ${theme.border}`,
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: 34,
                  borderBottom: `1px solid ${theme.border}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0 12px",
                  fontFamily: fontDisplay,
                  fontSize: 13,
                  color: "#98A2B3",
                }}
              >
                <span>Search...</span>
                <span style={{ fontSize: 16, color: "#667085" }}>⟳</span>
              </div>

              <div style={{ padding: "18px 18px 0", display: "flex", flexDirection: "column", gap: 14 }}>
                {["Acanthaceae", "Amborellaceae", "Anacardiaceae", "Annonaceae", "Apiaceae", "Apocynaceae"].map((label) => (
                  <div key={label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ color: "#667085", fontSize: 16, lineHeight: 1 }}>›</span>
                    <span style={{ fontFamily: fontDisplay, fontSize: 13, color: "#667085", fontWeight: 500 }}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{ padding: "12px 16px 0", fontFamily: fontDisplay, fontSize: 12.5, color: "#667085", lineHeight: 1.5 }}>
            Arborescence hiérarchique de navigation pour taxons
          </div>

          <div style={{ padding: "8px 16px 0", display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ height: 22, padding: "0 8px", borderRadius: 7, background: "#F2F4F7", display: "inline-flex", alignItems: "center", fontFamily: fontDisplay, fontSize: 11, color: "#344054" }}>
              hierarchical_nav_widget
            </div>
            <span style={{ fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>•</span>
            <div style={{ height: 22, padding: "0 8px", borderRadius: 7, background: "#F2F4F7", display: "inline-flex", alignItems: "center", fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>
              widget
            </div>
            <span style={{ fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>•</span>
            <div style={{ height: 22, padding: "0 8px", borderRadius: 7, background: "#F2F4F7", display: "inline-flex", alignItems: "center", fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>
              taxons
            </div>
          </div>

          <div style={{ marginTop: 12, borderTop: `1px solid ${theme.border}` }} />

          <div style={{ padding: "14px 16px 0", display: "flex", alignItems: "center", gap: 10, fontFamily: fontDisplay, fontSize: 14, fontWeight: 600, color: "#344054" }}>
            <CatalogIcon kind="custom" />
            <span>Personnalisation rapide</span>
          </div>

          <div style={{ padding: "12px 16px 0", fontFamily: fontDisplay, fontSize: 13, color: "#667085" }}>
            Titre
          </div>

          <div
            style={{
              height: 38,
              borderRadius: 8,
              border: `1px solid ${theme.border}`,
              background: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              padding: "0 12px",
              margin: "8px 16px 0",
              fontFamily: fontDisplay,
              fontSize: 14,
              color: "#344054",
            }}
          >
            Navigation Taxons
          </div>

          <div style={{ padding: "8px 16px 0", fontFamily: fontDisplay, fontSize: 11.5, color: "#98A2B3", fontStyle: "italic" }}>
            Utilisez l’édition avancée pour plus d’options
          </div>

          <div
            style={{
              height: 40,
              borderRadius: 8,
              border: `1px solid ${theme.borderStrong}`,
              background: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 14px",
              margin: "12px 16px 0",
              fontFamily: fontDisplay,
              fontSize: 14,
              color: "#344054",
              fontWeight: 500,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <CatalogIcon kind="custom" />
              <span>Édition avancée (YAML)</span>
            </div>
            <span style={{ fontSize: 18 }}>›</span>
          </div>
        </div>
      </div>

      <div
        style={{
          height: 58,
          borderTop: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          boxSizing: "border-box",
          flexShrink: 0,
          position: "relative",
          zIndex: 2,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontFamily: fontDisplay,
            fontSize: 13,
            color: selected ? "#667085" : "#98A2B3",
          }}
        >
          {selected ? <span style={{ color: "#16A34A" }}>✓</span> : null}
          <span>{selected ? `${selectedWidgetCount} champ(s) sélectionné(s)` : "Sélectionnez un widget"}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              height: 40,
              padding: "0 16px",
              borderRadius: 8,
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
              height: 40,
              padding: "0 16px",
              borderRadius: 8,
              background: selected ? "#15803D" : "#D1D5DB",
              color: "#FFFFFF",
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              fontFamily: fontDisplay,
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            <span style={{ fontSize: 18, lineHeight: 1 }}>+</span>
            <span>Ajouter {selectedWidgetCount} widget(s)</span>
          </div>
        </div>
      </div>
    </div>
  </div>
);

const CollectionConfiguredPage: React.FC<{ computing: boolean }> = ({ computing }) => (
  <div style={{ padding: "10px 12px 12px", boxSizing: "border-box", height: "100%" }}>
    <div style={breadcrumbStyle}>
      <span>Collections</span>
      <span>›</span>
      <span>Taxons</span>
    </div>

    <div style={{ marginTop: 8, height: "calc(100% - 20px)" }}>
      <PreviewWorkspace computing={computing} />
    </div>
  </div>
);

export const Act4Collections: React.FC = () => {
  const frame = useCurrentFrame();

  const overviewStart = 0;
  const overviewEnd = 110;
  const detailStart = 94;
  const detailEnd = 190;
  const modalStart = 174;
  const modalEnd = 322;
  const configuredStart = 306;
  const configuredEnd = 352;
  const computingStart = 352;
  const computingEnd = 420;

  const showOverview = frame < overviewEnd;
  const showDetail = frame >= detailStart && frame < detailEnd;
  const showModal = frame >= modalStart && frame < modalEnd;
  const showConfigured = frame >= configuredStart && frame < computingStart;
  const showComputing = frame >= computingStart;
  const modalSelected = frame >= 214;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${theme.canvasGradientStart}, ${theme.canvasGradientEnd})`,
      }}
    >
      <AppWindow showSidebar activeSidebarItem="collections">
        <div style={{ position: "relative", height: "100%" }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: showOverview ? fadeWindow(frame, overviewStart, overviewEnd) : 0,
            }}
          >
            <CollectionsOverview />
          </div>

          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: showDetail ? fadeWindow(frame, detailStart, detailEnd) : 0,
            }}
          >
            <EmptyCollectionPage />
          </div>

          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: showConfigured
                ? interpolate(frame, [configuredStart, configuredStart + 12], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })
                : 0,
            }}
          >
            <CollectionConfiguredPage computing={false} />
          </div>

          <div
            style={{
              position: "absolute",
              inset: 0,
              opacity: showComputing ? fadeWindow(frame, computingStart, computingEnd) : 0,
            }}
          >
            <CollectionConfiguredPage computing />
          </div>

          {showModal && <WidgetCatalogModal selected={modalSelected} />}
        </div>
      </AppWindow>

      <CursorOverlay waypoints={CURSOR_PATHS.act4} startFrame={20} />
    </AbsoluteFill>
  );
};
