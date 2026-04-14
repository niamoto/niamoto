import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { CursorWaypoint } from "../animations/CursorFlow";

const transitionFrames = 14;
const listEnd = 126;
const templateStart = listEnd - transitionFrames;
const templateEnd = 236;
const editorStart = templateEnd - transitionFrames;

const siteActWaypoints: CursorWaypoint[] = [
  { x: 1610, y: 214, hold: 40 },
  { x: 1768, y: 262, hold: 16, click: true },
  { x: 1218, y: 518, hold: 70 },
  { x: 1218, y: 518, hold: 16, click: true },
  { x: 1146, y: 624, hold: 140 },
];

const screenOpacity = (frame: number, start: number, end?: number) => {
  const fadeInStart = Math.max(0, start - transitionFrames);
  const fadeOutEnd = end ?? Number.POSITIVE_INFINITY;

  if (frame < fadeInStart) return 0;
  if (frame < start) {
    return interpolate(frame, [fadeInStart, start], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  if (Number.isFinite(fadeOutEnd) && frame > fadeOutEnd - transitionFrames) {
    return interpolate(frame, [fadeOutEnd - transitionFrames, fadeOutEnd], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  return 1;
};

const screenShift = (frame: number, start: number) =>
  interpolate(frame, [start - transitionFrames, start + 18], [18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const cardStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: `1px solid ${theme.border}`,
  borderRadius: 12,
  boxShadow: "0 2px 8px rgba(15, 23, 42, 0.04)",
};

const sectionLabelStyle: React.CSSProperties = {
  fontFamily: fontDisplay,
  fontSize: 12,
  fontWeight: 600,
  color: "#667085",
  letterSpacing: 0.12,
  textTransform: "uppercase",
};

const fieldLabelStyle: React.CSSProperties = {
  fontFamily: fontDisplay,
  fontSize: 13,
  fontWeight: 500,
  color: "#181D27",
};

const fieldHelpStyle: React.CSSProperties = {
  fontFamily: fontDisplay,
  fontSize: 11,
  color: "#98A2B3",
};

const textFieldStyle: React.CSSProperties = {
  height: 34,
  borderRadius: 8,
  border: `1px solid ${theme.border}`,
  background: "#FFFFFF",
  display: "flex",
  alignItems: "center",
  padding: "0 12px",
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 12,
  color: "#344054",
};

const pageCards = [
  { title: "home", file: "index.html", body: "Contenu MD", chip: "index", icon: "home", status: "green" },
  { title: "methodology", file: "methodology.html", body: "Contenu MD", chip: "page", icon: "doc", status: "green" },
  { title: "resources", file: "resources.html", body: "Vide", chip: "page", icon: "doc", status: "gray" },
  { title: "team", file: "team.html", body: "Vide", chip: "team", icon: "users", status: "gray" },
  { title: "bibliography", file: "bibliography.html", body: "Vide", chip: "bibliography", icon: "book", status: "gray" },
  { title: "plots", file: "plots.html", body: "Contenu MD", chip: "page", icon: "doc", status: "green" },
  { title: "trees", file: "trees.html", body: "Contenu MD", chip: "page", icon: "doc", status: "green" },
  { title: "forests", file: "forests.html", body: "Contenu MD", chip: "page", icon: "doc", status: "green" },
] as const;

const collectionCards = [
  { title: "taxons/", file: "taxons/{id}.html", widgets: "18 widgets", index: "Index" },
  { title: "plots/", file: "plots/{id}.html", widgets: "18 widgets", index: "Index" },
  { title: "shapes/", file: "shapes/{id}.html", widgets: "12 widgets", index: "Index" },
] as const;

const templateSections = [
  {
    label: "Contenu",
    items: [
      { title: "article", subtitle: "Article avec auteur, date et contenu enrichi", kind: "text" },
      { title: "documentation", subtitle: "Documentation technique avec sommaire et sections", kind: "text" },
      { title: "page", subtitle: "Page de contenu simple avec titre et texte markdown", kind: "text", selected: true },
    ],
  },
  {
    label: "Projet",
    items: [
      { title: "contact", subtitle: "Page de contact avec email, adresse et réseaux sociaux", kind: "project" },
      { title: "team", subtitle: "Équipe, partenaires et financeurs avec photos et logos", kind: "grid" },
    ],
  },
  {
    label: "Référence",
    items: [
      { title: "glossary", subtitle: "Glossaire de termes avec définitions et catégories", kind: "text" },
      { title: "resources", subtitle: "Liste de ressources téléchargeables avec fichiers et liens", kind: "grid" },
      { title: "bibliography", subtitle: "Liste de références bibliographiques formatées", kind: "text" },
    ],
  },
] as const;

type BuilderTreeEntry = {
  label: string;
  icon: "home" | "doc" | "users" | "book" | "folder" | "collection";
  badge?: string;
  active?: boolean;
};

const builderTree: BuilderTreeEntry[] = [
  { label: "Accueil", icon: "home" },
  { label: "Méthodologie", icon: "doc", active: true, badge: "page" },
  { label: "Resources", icon: "doc", badge: "page" },
  { label: "Équipe & Partenaires", icon: "users", badge: "team" },
  { label: "Bibliographie", icon: "book", badge: "bibliography" },
  { label: "Peuplements", icon: "doc", badge: "page" },
  { label: "Explorer les données/", icon: "collection" },
  { label: "Arbres", icon: "doc", badge: "page" },
  { label: "Explorer les données/", icon: "collection" },
  { label: "Forêt", icon: "doc", badge: "page" },
  { label: "Explorer les données/", icon: "collection" },
  { label: "article", icon: "doc", badge: "article" },
] as const;

const MarkdownParagraph = ({ children, size = 15, weight = 400, color = "#1F2937" }: { children: React.ReactNode; size?: number; weight?: number; color?: string }) => (
  <p
    style={{
      margin: 0,
      fontFamily: fontDisplay,
      fontSize: size,
      lineHeight: 1.55,
      fontWeight: weight,
      color,
    }}
  >
    {children}
  </p>
);

const StatusDot: React.FC<{ color: string }> = ({ color }) => (
  <span
    style={{
      width: 7,
      height: 7,
      borderRadius: "50%",
      display: "inline-block",
      background: color,
    }}
  />
);

const Chip: React.FC<{ label: string; tone?: "default" | "active" | "soft" }> = ({ label, tone = "default" }) => {
  const palette =
    tone === "active"
      ? { bg: "#E7F0FF", color: "#2867F0", border: "#BBD0FF" }
      : tone === "soft"
        ? { bg: "#F7F8FA", color: "#667085", border: "#E4E7EC" }
        : { bg: "#FFFFFF", color: "#475467", border: "#D0D5DD" };

  return (
    <span
      style={{
        height: 28,
        padding: "0 11px",
        borderRadius: 8,
        border: `1px solid ${palette.border}`,
        background: palette.bg,
        display: "inline-flex",
        alignItems: "center",
        fontFamily: fontDisplay,
        fontSize: 12,
        color: palette.color,
        fontWeight: 500,
      }}
    >
      {label}
    </span>
  );
};

const PrimaryButton: React.FC<{ label: string; icon?: string }> = ({ label, icon }) => (
  <div
    style={{
      height: 32,
      padding: "0 14px",
      borderRadius: 6,
      background: "#14803C",
      display: "inline-flex",
      alignItems: "center",
      gap: 9,
      fontFamily: fontDisplay,
      fontSize: 13,
      fontWeight: 500,
      color: "#FFFFFF",
      boxShadow: "inset 0 -1px 0 rgba(0,0,0,0.08)",
    }}
  >
    {icon && <span style={{ fontSize: 18, lineHeight: 1 }}>{icon}</span>}
    <span>{label}</span>
  </div>
);

const SecondaryButton: React.FC<{ label: string; icon?: React.ReactNode; subtle?: boolean }> = ({ label, icon, subtle = false }) => (
  <div
    style={{
      height: 32,
      padding: "0 13px",
      borderRadius: 6,
      border: `1px solid ${theme.border}`,
      background: subtle ? "#F8FAFC" : "#FFFFFF",
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      fontFamily: fontDisplay,
      fontSize: 13,
      fontWeight: 500,
      color: "#344054",
    }}
  >
    {icon}
    <span>{label}</span>
  </div>
);

const TinyIcon: React.FC<{ type: BuilderTreeEntry["icon"]; color?: string }> = ({ type, color = "#475467" }) => {
  const common = { width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: color, strokeWidth: 1.8 } as const;

  switch (type) {
    case "home":
      return (
        <svg {...common}>
          <path d="M3 10 12 3l9 7" />
          <path d="M5 10v10h14V10" />
        </svg>
      );
    case "users":
      return (
        <svg {...common}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="3" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 4.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "book":
      return (
        <svg {...common}>
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
        </svg>
      );
    case "collection":
      return (
        <svg {...common}>
          <path d="M3 8h18" />
          <path d="M3 12h18" />
          <path d="M3 16h18" />
        </svg>
      );
    case "folder":
      return (
        <svg {...common}>
          <path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H3z" />
        </svg>
      );
    case "doc":
    default:
      return (
        <svg {...common}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16h16V8z" />
          <path d="M14 2v6h6" />
        </svg>
      );
  }
};

const BuilderShell: React.FC<{
  contentHeader: React.ReactNode;
  main: React.ReactNode;
  selectedTreeLabel?: string;
}> = ({ contentHeader, main, selectedTreeLabel }) => (
  <AppWindow showSidebar activeSidebarItem="site">
    <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "#FCFDFE" }}>
      <div
        style={{
          height: 44,
          borderBottom: `1px solid ${theme.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: fontDisplay, fontSize: 12, color: "#667085" }}>
          <span>⌂</span>
          <span>Site</span>
          <span>›</span>
          <span>Pages</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: fontDisplay, fontSize: 12, color: "#16A34A", fontWeight: 500 }}>
          <StatusDot color="#22C55E" />
          <span>Site configuré</span>
        </div>
      </div>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "292px 1fr", minHeight: 0 }}>
        <div
          style={{
            borderRight: `1px solid ${theme.border}`,
            background: "#F8FAFC",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <div style={{ padding: "14px 16px 12px" }}>
            <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>Niamoto</div>
            <div style={{ fontFamily: fontDisplay, fontSize: 12, color: "#98A2B3", marginTop: 2 }}>Constructeur de site</div>
          </div>

          <div style={{ padding: "0 8px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
            {["Général", "Apparence", "Menu footer"].map((item) => (
              <div
                key={item}
                style={{
                  height: 36,
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "0 12px",
                  borderRadius: 8,
                  fontFamily: fontDisplay,
                  fontSize: 14,
                  color: "#344054",
                }}
              >
                <span style={{ width: 16, color: "#475467" }}>{item === "Général" ? "⚙" : item === "Apparence" ? "◔" : "▤"}</span>
                <span>{item}</span>
              </div>
            ))}
          </div>

          <div style={{ borderTop: `1px solid ${theme.border}`, padding: "10px 8px 0", overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 2, overflow: "hidden" }}>
              {builderTree.map((item) => {
                const selected = selectedTreeLabel === item.label;
                const isCollection = item.icon === "collection";

                return (
                  <div
                    key={item.label}
                    style={{
                      height: 30,
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "0 10px 0 12px",
                      borderRadius: 8,
                      background: selected ? "#E7F4EE" : "transparent",
                      color: selected ? "#15803D" : "#344054",
                      fontFamily: fontDisplay,
                      fontSize: 14,
                    }}
                  >
                    <span style={{ width: 10, color: "#D0D5DD" }}>⋮</span>
                    <TinyIcon type={item.icon} color={selected ? "#15803D" : isCollection ? "#D97706" : "#475467"} />
                    <span style={{ flex: 1 }}>{item.label}</span>
                    {item.badge && (
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: 999,
                          border: `1px solid ${theme.border}`,
                          background: "#FFFFFF",
                          fontSize: 10,
                          color: "#667085",
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                    <span style={{ color: "#98A2B3" }}>◉</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: "auto", padding: "14px 14px 14px", display: "flex", justifyContent: "space-between", fontFamily: fontDisplay, fontSize: 13, color: "#667085" }}>
            <span>＋ Page</span>
            <span>↗ Link</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          {contentHeader}
          <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>{main}</div>
        </div>
      </div>
    </div>
  </AppWindow>
);

const PageCard: React.FC<(typeof pageCards)[number]> = ({ title, file, body, chip, icon, status }) => (
  <div
    style={{
      ...cardStyle,
      minHeight: 120,
      padding: "14px 16px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <TinyIcon type={icon} color="#1F2937" />
      <span style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#181D27" }}>{title}</span>
    </div>
    <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "#667085" }}>{file} ↪</div>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 7, fontFamily: fontDisplay, fontSize: 13, color: "#667085" }}>
        <StatusDot color={status === "green" ? "#22C55E" : "#D0D5DD"} />
        <span>{body}</span>
      </div>
      <span
        style={{
          padding: "3px 8px",
          borderRadius: 8,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          fontFamily: fontDisplay,
          fontSize: 11,
          color: "#667085",
        }}
      >
        {chip}
      </span>
    </div>
  </div>
);

const CollectionCard: React.FC<(typeof collectionCards)[number]> = ({ title, file, widgets, index }) => (
  <div
    style={{
      ...cardStyle,
      minHeight: 126,
      padding: "14px 16px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
    }}
  >
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <TinyIcon type="folder" color="#F97316" />
      <span style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#181D27" }}>{title}</span>
    </div>
    <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "#667085" }}>{file}</div>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontFamily: fontDisplay, fontSize: 13, color: "#344054" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Chip label={widgets} tone="soft" />
        <div style={{ display: "flex", alignItems: "center", gap: 5, color: "#16A34A" }}>
          <StatusDot color="#22C55E" />
          <span>{index}</span>
        </div>
      </div>
      <span>Voir</span>
    </div>
  </div>
);

const ListScreen: React.FC = () => (
  <BuilderShell
    contentHeader={
      <div
        style={{
          height: 86,
          borderBottom: `1px solid ${theme.border}`,
          padding: "16px 18px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>Pages</div>
          <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#667085", marginTop: 6 }}>
            Gérez les pages statiques et visualisez les collections
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <SecondaryButton label="Reconfigurer" icon={<span style={{ fontSize: 15 }}>↻</span>} />
            <PrimaryButton label="Enregistrer" icon="💾" />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SecondaryButton label="Aperçu" icon={<span style={{ fontSize: 14 }}>◉</span>} />
            <PrimaryButton label="Nouvelle page" icon="＋" />
          </div>
        </div>
      </div>
    }
    main={
      <div style={{ padding: "18px", display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <TinyIcon type="doc" color="#667085" />
            <span style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>Pages statiques</span>
            <Chip label="8" tone="soft" />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
            {pageCards.map((card) => (
              <PageCard key={card.title} {...card} />
            ))}
          </div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <TinyIcon type="folder" color="#F97316" />
            <span style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>Collections</span>
            <Chip label="3" tone="soft" />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
            {collectionCards.map((card) => (
              <CollectionCard key={card.title} {...card} />
            ))}
          </div>
        </div>
      </div>
    }
  />
);

const TemplateTile: React.FC<{
  title: string;
  subtitle: string;
  kind: "text" | "project" | "grid";
  selected?: boolean;
}> = ({ title, subtitle, kind, selected }) => (
  <div
    style={{
      height: 52,
      padding: "0 12px",
      borderRadius: 10,
      background: selected ? "#EEF2F6" : "transparent",
      display: "flex",
      alignItems: "center",
      gap: 12,
    }}
  >
    <div
      style={{
        width: 44,
        height: 30,
        borderRadius: 6,
        border: `1px solid ${theme.border}`,
        background: "#FFFFFF",
        padding: 5,
        boxSizing: "border-box",
      }}
    >
      <div style={{ height: 3, width: 18, background: "#6366F1", borderRadius: 2, marginBottom: 4 }} />
      {kind === "text" && (
        <>
          <div style={{ height: 2, width: 28, background: "#CBD5E1", borderRadius: 2, marginBottom: 3 }} />
          <div style={{ height: 2, width: 24, background: "#CBD5E1", borderRadius: 2, marginBottom: 3 }} />
          <div style={{ height: 2, width: 26, background: "#CBD5E1", borderRadius: 2 }} />
        </>
      )}
      {kind === "project" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 3 }}>
          <div style={{ height: 8, borderRadius: 2, background: "#E2E8F0" }} />
          <div style={{ height: 8, borderRadius: 2, background: "#E2E8F0" }} />
          <div style={{ height: 8, borderRadius: 2, background: "#E2E8F0" }} />
          <div style={{ height: 8, borderRadius: 2, background: "#E2E8F0" }} />
        </div>
      )}
      {kind === "grid" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2 }}>
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} style={{ height: 5, borderRadius: 1.5, background: "#E2E8F0" }} />
          ))}
        </div>
      )}
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <span style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 500, color: "#181D27" }}>{title}</span>
      <span style={{ fontFamily: fontDisplay, fontSize: 12, color: "#667085" }}>{subtitle}</span>
    </div>
  </div>
);

const TemplateScreen: React.FC = () => (
  <BuilderShell
    contentHeader={
      <div
        style={{
          height: 86,
          borderBottom: `1px solid ${theme.border}`,
          padding: "16px 18px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div />
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <SecondaryButton label="Reconfigurer" icon={<span style={{ fontSize: 15 }}>↻</span>} />
          <PrimaryButton label="Enregistrer" icon="💾" />
        </div>
      </div>
    }
    main={
      <div style={{ padding: "16px 22px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 18, color: "#344054" }}>←</span>
          <div>
            <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>Nouvelle page</div>
            <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#667085", marginTop: 4 }}>
              Choisissez un template pour commencer
            </div>
          </div>
        </div>

        {templateSections.map((section) => (
          <div key={section.label}>
            <div style={{ ...sectionLabelStyle, marginBottom: 8 }}>{section.label}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {section.items.map((item) => (
                <TemplateTile key={item.title} {...item} />
              ))}
            </div>
          </div>
        ))}
      </div>
    }
  />
);

const EditorScreen: React.FC = () => (
  <BuilderShell
    selectedTreeLabel="Méthodologie"
    contentHeader={
      <div
        style={{
          height: 86,
          borderBottom: `1px solid ${theme.border}`,
          padding: "16px 18px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 18, color: "#344054" }}>←</span>
          <div>
            <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>methodology</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "#667085", marginTop: 4 }}>
              methodology.html
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <SecondaryButton label="Reconfigurer" icon={<span style={{ fontSize: 15 }}>↻</span>} />
          <SecondaryButton label="Aperçu" icon={<span style={{ fontSize: 14 }}>◉</span>} />
          <PrimaryButton label="Enregistrer" icon="💾" />
          <SecondaryButton label="Supprimer" icon={<span style={{ fontSize: 15, color: "#DC2626" }}>🗑</span>} />
        </div>
      </div>
    }
    main={
      <div style={{ padding: "18px", overflow: "hidden", display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ ...cardStyle, padding: "16px 16px 18px" }}>
          <div style={{ fontFamily: fontDisplay, fontSize: 17, fontWeight: 700, color: "#181D27" }}>Contenu</div>
          <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#667085", marginTop: 6, marginBottom: 18 }}>
            Contenu markdown de la page
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 7, fontFamily: fontDisplay, fontSize: 13, color: "#181D27" }}>
                <span style={{ color: "#16A34A", fontSize: 16 }}>◉</span>
                <span>Fichier unique</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 7, fontFamily: fontDisplay, fontSize: 13, color: "#181D27" }}>
                <span style={{ color: "#16A34A", fontSize: 16 }}>◯</span>
                <span>Fichiers multilingues</span>
              </div>
            </div>
          </div>

          <div style={{ ...fieldLabelStyle, marginBottom: 8 }}>Fichier source</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 36px 24px", gap: 8, alignItems: "center" }}>
            <div style={{ ...textFieldStyle, justifyContent: "space-between" }}>
              <span>methodology.md</span>
              <span style={{ color: "#98A2B3" }}>⌄</span>
            </div>
            <div style={{ width: 36, height: 34, borderRadius: 8, border: `1px solid ${theme.border}`, display: "flex", alignItems: "center", justifyContent: "center", color: "#475467" }}>
              ⤴
            </div>
            <div style={{ color: "#475467", fontSize: 22, textAlign: "center" }}>×</div>
          </div>
          <div style={{ ...fieldHelpStyle, marginTop: 8, marginBottom: 18 }}>Fichier markdown dans templates/content/</div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={fieldLabelStyle}>Contenu du fichier</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ color: "#344054", fontSize: 18 }}>‹›</span>
              <SecondaryButton label="Éditer" icon={<span style={{ fontSize: 16 }}>✎</span>} subtle />
            </div>
          </div>

          <div
            style={{
              position: "relative",
              borderRadius: 10,
              border: `1px solid ${theme.border}`,
              background: "#FFFFFF",
              padding: "20px 22px 22px",
              minHeight: 406,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                right: 10,
                top: 12,
                width: 6,
                height: 28,
                borderRadius: 999,
                background: "#667085",
              }}
            />

            <div
              style={{
                position: "absolute",
                left: 20,
                top: 30,
                width: 280,
                borderRadius: 10,
                border: `1px solid ${theme.borderStrong}`,
                background: "#FFFFFF",
                boxShadow: "0 14px 28px rgba(15, 23, 42, 0.14)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: 38,
                  background: "#4F87BD",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "0 10px",
                  fontFamily: fontDisplay,
                  color: "#FFFFFF",
                }}
              >
                <div style={{ width: 28, height: 28, borderRadius: 8, background: "#F7F8FA", color: "#344054", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  ☰
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>Texte</span>
                  <span style={{ fontSize: 11, opacity: 0.75 }}>Texte simple</span>
                </div>
              </div>

              <div style={{ padding: "10px 10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  ["H1", "Titre 1", "Grand titre de section"],
                  ["H2", "Titre 2", "Titre de sous-section"],
                  ["H3", "Titre 3", "Petit titre"],
                  ["🖼", "Image", "Insérer une image"],
                  ["☰", "Liste", "Liste à puces"],
                  ["≣", "Liste numérotée", "Liste ordonnée"],
                ].map(([icon, title, subtitle]) => (
                  <div key={title} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        background: "#F8FAFC",
                        border: `1px solid ${theme.border}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: fontDisplay,
                        fontSize: 16,
                        color: "#181D27",
                      }}
                    >
                      {icon}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <span style={{ fontFamily: fontDisplay, fontSize: 13, fontWeight: 500, color: "#181D27" }}>{title}</span>
                      <span style={{ fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>{subtitle}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 18, paddingTop: 6 }}>
              <div style={{ marginLeft: 8, paddingLeft: 8 }}>
                <div style={{ fontFamily: fontDisplay, fontSize: 20, fontWeight: 700, color: "#181D27", marginBottom: 14 }}>Préambule</div>
                <MarkdownParagraph size={15} weight={700}>
                  La méthodologie se situe au cœur de notre métier de botanistes-écologues. Elle nous conduit à définir
                  les protocoles qui permettent d&apos;accumuler et d&apos;analyser des données pour répondre à une question qui
                  repose elle-même sur les résultats d&apos;une ou de plusieurs autres études.
                </MarkdownParagraph>
                <div style={{ height: 10 }} />
                <MarkdownParagraph color="#344054">
                  La méthode scientifique permet à chacun de reproduire une étude dans le même contexte technique. C&apos;est
                  un peu comme une recette de cuisine qui permet à chacun de reproduire le délicieux met. La première
                  phase de la méthode, peut être la plus importante, est de compiler les travaux issus du monde
                  scientifique au travers d&apos;une veille bibliographique continue.
                </MarkdownParagraph>
                <div style={{ height: 12 }} />
                <MarkdownParagraph color="#344054">
                  C&apos;est à partir de cette première pierre de la connaissance qu&apos;il est possible de construire une
                  méthode robuste pour évaluer un écosystème comme la forêt. Cependant il convient de prendre du recul et
                  maintenir un esprit critique méticuleux face aux conclusions qui sont le plus souvent construites à
                  partir d&apos;une partie infime de la réalité biologique et écologique.
                </MarkdownParagraph>
              </div>

              <div style={{ marginLeft: 8, paddingLeft: 8 }}>
                <div style={{ fontFamily: fontDisplay, fontSize: 18, fontWeight: 700, color: "#181D27", marginBottom: 12 }}>Nos méthodes</div>
                <MarkdownParagraph size={16} weight={600}>Taxonomie et identification</MarkdownParagraph>
                <div style={{ height: 10 }} />
                <MarkdownParagraph color="#344054">
                  La taxonomie est une classification du monde vivant basée sur des critères de similitude qui a pour
                  objet de décrire les organismes et de les regrouper. Initialement basée sur la comparaison
                  morphologique, elle s&apos;appuie désormais sur la biologie moléculaire et tous les outils issus de la
                  génétique.
                </MarkdownParagraph>
                <div style={{ height: 18 }} />
                <div
                  style={{
                    width: 132,
                    margin: "0 auto",
                    padding: "8px 0",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  {["Espèce", "Genre", "Famille", "Ordre", "Classe"].map((label, index) => (
                    <div key={label} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                      <div
                        style={{
                          padding: "4px 10px",
                          borderRadius: 4,
                          background: index % 2 === 0 ? "#FDE68A" : "#F9D28D",
                          border: "1px solid #D4A948",
                          fontFamily: fontDisplay,
                          fontSize: 10,
                          color: "#4B5563",
                        }}
                      >
                        {label}
                      </div>
                      {index < 4 && <div style={{ width: 2, height: 12, background: "#9CA3AF" }} />}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    }
  />
);

export const Act5SiteBuilder: React.FC = () => {
  const frame = useCurrentFrame();

  const listOpacity = screenOpacity(frame, 0, listEnd);
  const templateOpacity = screenOpacity(frame, templateStart, templateEnd);
  const editorOpacity = screenOpacity(frame, editorStart);

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at top, rgba(255,255,255,0.95), rgba(245,246,248,1) 55%, rgba(237,241,245,1) 100%)",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: listOpacity,
          transform: `translateX(${screenShift(frame, 0)}px)`,
        }}
      >
        <ListScreen />
      </div>

      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: templateOpacity,
          transform: `translateX(${screenShift(frame, templateStart)}px)`,
        }}
      >
        <TemplateScreen />
      </div>

      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: editorOpacity,
          transform: `translateX(${screenShift(frame, editorStart)}px)`,
        }}
      >
        <EditorScreen />
      </div>

      <CursorOverlay waypoints={siteActWaypoints} />
    </AbsoluteFill>
  );
};
