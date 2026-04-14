import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CursorWaypoint } from "../animations/CursorFlow";
import { CursorOverlay } from "../cursor/CursorOverlay";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";
import { AppWindow } from "../ui/AppWindow";

type PublishScene = "loading" | "generating" | "picker" | "config" | "logs" | "success";

const transitionFrames = 14;
const loadingEnd = 60;
const generatingStart = loadingEnd - transitionFrames;
const generatingEnd = 230;
const pickerStart = generatingEnd - transitionFrames;
const pickerEnd = 304;
const configStart = pickerEnd - transitionFrames;
const configEnd = 424;
const logsStart = configEnd - transitionFrames;
const logsEnd = 488;
const successStart = logsEnd - transitionFrames;

const act6Waypoints: CursorWaypoint[] = [
  { x: 1682, y: 206, hold: 20 },
  { x: 1778, y: 206, hold: 16, click: true },
  { x: 1184, y: 512, hold: 140 },
  { x: 1092, y: 488, hold: 18, click: true },
  { x: 980, y: 642, hold: 38 },
  { x: 1194, y: 934, hold: 18, click: true },
  { x: 1218, y: 624, hold: 120 },
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

const panelStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: `1px solid ${theme.border}`,
  borderRadius: 12,
  boxShadow: "0 2px 10px rgba(15, 23, 42, 0.05)",
};

const sectionTitleStyle: React.CSSProperties = {
  fontFamily: fontDisplay,
  fontSize: 16,
  fontWeight: 700,
  color: "#181D27",
};

const mutedStyle: React.CSSProperties = {
  fontFamily: fontDisplay,
  fontSize: 12,
  color: "#98A2B3",
};

const monoStyle: React.CSSProperties = {
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 11,
  color: "#667085",
};

const GithubIcon: React.FC<{ size?: number; color?: string; background?: string }> = ({
  size = 20,
  color = "#FFFFFF",
  background = "#111827",
}) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: Math.round(size * 0.28),
      background,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}
  >
    <svg viewBox="0 0 24 24" width={Math.round(size * 0.66)} height={Math.round(size * 0.66)} fill={color}>
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.44 9.8 8.2 11.39.6.11.82-.26.82-.57 0-.28-.01-1.04-.02-2.05-3.34.73-4.04-1.42-4.04-1.42-.55-1.38-1.33-1.75-1.33-1.75-1.09-.74.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.08 1.84 2.84 1.31 3.53 1 .11-.78.42-1.31.77-1.61-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.31-.54-1.55.11-3.23 0 0 1.01-.32 3.3 1.23a11.4 11.4 0 0 1 6 0c2.29-1.55 3.29-1.23 3.29-1.23.66 1.68.25 2.92.12 3.23.77.84 1.24 1.92 1.24 3.23 0 4.62-2.81 5.64-5.5 5.94.43.38.82 1.12.82 2.26 0 1.64-.02 2.95-.02 3.35 0 .31.21.68.83.57A12 12 0 0 0 24 12c0-6.63-5.37-12-12-12Z" />
    </svg>
  </div>
);

const MoreIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#98A2B3" strokeWidth="2">
    <circle cx="12" cy="5" r="1.4" fill="#98A2B3" stroke="none" />
    <circle cx="12" cy="12" r="1.4" fill="#98A2B3" stroke="none" />
    <circle cx="12" cy="19" r="1.4" fill="#98A2B3" stroke="none" />
  </svg>
);

const SendIcon = ({ color = "#FFFFFF" }: { color?: string }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
    <path d="m22 2-7 20-4-9-9-4z" />
    <path d="m22 2-11 11" />
  </svg>
);

const ExternalLinkIcon = ({ color = "#344054" }: { color?: string }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
    <path d="M14 3h7v7" />
    <path d="M10 14 21 3" />
    <path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
  </svg>
);

const Spinner: React.FC<{ size?: number; tone?: string }> = ({ size = 24, tone = "#667085" }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        border: `2px solid rgba(102,112,133,0.2)`,
        borderTopColor: tone,
        transform: `rotate(${frame * 8}deg)`,
      }}
    />
  );
};

const StatusDot: React.FC<{ color: string }> = ({ color }) => (
  <span
    style={{
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: color,
      display: "inline-block",
      flexShrink: 0,
    }}
  />
);

const HeaderBadge: React.FC<{ label: string; tone?: "neutral" | "success" | "active" }> = ({
  label,
  tone = "neutral",
}) => {
  const palette =
    tone === "success"
      ? { bg: "#EEF9F0", color: "#15803D", border: "#CDEBD5" }
      : tone === "active"
        ? { bg: "#EFF6FF", color: "#2563EB", border: "#DBEAFE" }
        : { bg: "#FFFFFF", color: "#344054", border: theme.borderStrong };

  return (
    <div
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
        fontWeight: 600,
        color: palette.color,
      }}
    >
      {label}
    </div>
  );
};

const PrimaryButton: React.FC<{
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  compact?: boolean;
}> = ({ label, icon, disabled = false, compact = false }) => (
  <div
    style={{
      height: compact ? 30 : 32,
      padding: compact ? "0 12px" : "0 14px",
      borderRadius: 6,
      background: disabled ? "#D0D5DD" : "#2F855A",
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      color: "#FFFFFF",
      fontFamily: fontDisplay,
      fontSize: compact ? 12 : 13,
      fontWeight: 600,
      opacity: disabled ? 0.75 : 1,
      boxShadow: "inset 0 -1px 0 rgba(0,0,0,0.08)",
    }}
  >
    {icon}
    <span>{label}</span>
  </div>
);

const SecondaryButton: React.FC<{
  label: string;
  icon?: React.ReactNode;
  subtle?: boolean;
  danger?: boolean;
}> = ({ label, icon, subtle = false, danger = false }) => (
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
      color: danger ? "#DC2626" : "#344054",
    }}
  >
    {icon}
    <span>{label}</span>
  </div>
);

const MetricCell: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
    <div
      style={{
        fontFamily: fontDisplay,
        fontSize: 11,
        fontWeight: 600,
        color: "#98A2B3",
        letterSpacing: 0.1,
        textTransform: "uppercase",
      }}
    >
      {label}
    </div>
    <div style={{ fontFamily: fontDisplay, fontSize: 14, fontWeight: 600, color: "#181D27" }}>{value}</div>
  </div>
);

const ToggleSwitch = ({ enabled = false }: { enabled?: boolean }) => (
  <div
    style={{
      width: 42,
      height: 24,
      borderRadius: 999,
      background: enabled ? "#2F855A" : "#E5E7EB",
      display: "flex",
      alignItems: "center",
      padding: 3,
      justifyContent: enabled ? "flex-end" : "flex-start",
    }}
  >
    <div
      style={{
        width: 18,
        height: 18,
        borderRadius: "50%",
        background: "#FFFFFF",
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.18)",
      }}
    />
  </div>
);

const ProgressTrack: React.FC<{
  percent: number;
  color?: string;
  slim?: boolean;
  label?: string;
  rightLabel?: string;
}> = ({ percent, color = "#3F8D55", slim = false, label, rightLabel }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
    {(label || rightLabel) && (
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
          fontFamily: fontDisplay,
          fontSize: 12,
          color: "#344054",
        }}
      >
        <span>{label}</span>
        {rightLabel && <span>{rightLabel}</span>}
      </div>
    )}
    <div
      style={{
        height: slim ? 12 : 10,
        borderRadius: 999,
        background: "#E5E7EB",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: `${Math.max(0, Math.min(100, percent))}%`,
          height: "100%",
          borderRadius: 999,
          background: color,
        }}
      />
    </div>
  </div>
);

const ProviderTile: React.FC<{
  name: string;
  description: string;
  accent: string;
  icon: React.ReactNode;
}> = ({ name, description, accent, icon }) => (
  <div
    style={{
      ...panelStyle,
      height: 58,
      padding: "0 12px",
      display: "flex",
      alignItems: "center",
      gap: 10,
      boxShadow: "none",
    }}
  >
    <div
      style={{
        width: 26,
        height: 26,
        borderRadius: 6,
        background: accent,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#FFFFFF",
        flexShrink: 0,
      }}
    >
      {icon}
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontFamily: fontDisplay, fontSize: 13, fontWeight: 600, color: "#181D27" }}>{name}</span>
      <span style={{ fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>{description}</span>
    </div>
  </div>
);

const SitePreviewMock: React.FC<{ scene: PublishScene }> = ({ scene }) => {
  if (scene === "loading") {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 16,
          color: "#667085",
        }}
      >
        <Spinner size={30} />
        <div style={{ fontFamily: fontDisplay, fontSize: 16, color: "#667085" }}>Génération de l’aperçu...</div>
      </div>
    );
  }

  return (
    <div
      style={{
        margin: "18px 18px 20px",
        height: 420,
        borderRadius: 10,
        overflow: "hidden",
        border: `1px solid ${theme.border}`,
        background: "#FFFFFF",
      }}
    >
      <div
        style={{
          height: 24,
          background: "#3F8D2B",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 14px",
          color: "#FFFFFF",
          fontFamily: fontDisplay,
          fontSize: 8,
          letterSpacing: 0.06,
          textTransform: "uppercase",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontWeight: 800, fontSize: 10 }}>NIAMOTO</span>
          <span>Accueil</span>
          <span>Méthodologie</span>
          <span>Ressources</span>
          <span>Peuplements</span>
        </div>
        <span>FR ▼</span>
      </div>

      <div
        style={{
          position: "relative",
          height: 396,
          overflow: "hidden",
          background:
            "radial-gradient(circle at 18% 28%, rgba(61,91,34,0.82), transparent 28%), radial-gradient(circle at 70% 20%, rgba(31,78,45,0.85), transparent 32%), radial-gradient(circle at 45% 64%, rgba(19,58,31,0.92), transparent 36%), linear-gradient(180deg, #3D5B22 0%, #29411E 32%, #162916 100%)",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(125deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.02) 34%, transparent 35%), linear-gradient(55deg, rgba(255,255,255,0.12) 0%, transparent 18%)",
            mixBlendMode: "screen",
          }}
        />
        {Array.from({ length: 14 }).map((_, index) => (
          <div
            key={index}
            style={{
              position: "absolute",
              left: 22 + index * 38 + (index % 3) * 8,
              top: 28 + (index % 4) * 32,
              width: 26 + (index % 3) * 12,
              height: 190 + (index % 5) * 32,
              borderRadius: "55% 45% 50% 50%",
              background: `linear-gradient(180deg, rgba(35,92,44,${0.45 + (index % 2) * 0.08}) 0%, rgba(17,48,25,0.0) 100%)`,
              transform: `rotate(${index % 2 === 0 ? -16 : 14}deg)`,
              opacity: 0.66,
            }}
          />
        ))}

        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            color: "#FFFFFF",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 48,
              fontWeight: 800,
              letterSpacing: 0.5,
              textShadow: "0 4px 18px rgba(0,0,0,0.35)",
            }}
          >
            NIAMOTO
          </div>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 16,
              marginTop: 8,
              color: "rgba(255,255,255,0.82)",
              textShadow: "0 4px 18px rgba(0,0,0,0.35)",
            }}
          >
            Portail de la flore de Nouvelle-Calédonie
          </div>
        </div>
      </div>
    </div>
  );
};

const PublishMainPage: React.FC<{ scene: PublishScene; frame: number }> = ({ scene, frame }) => {
  const generationProgress = interpolate(frame, [generatingStart, generatingEnd], [28, 77], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const lateBuildProgress = interpolate(frame, [successStart, successStart + 32], [38, 49], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const topBadge =
    scene === "loading"
      ? { label: "Jamais généré", tone: "neutral" as const }
      : scene === "generating"
        ? { label: "Génération en cours...", tone: "neutral" as const }
        : { label: "Site configuré", tone: "success" as const };

  const filesGenerated = scene === "loading" ? "—" : "3 595";
  const leftBuildProgress =
    scene === "generating" ? generationProgress : scene === "success" ? lateBuildProgress : scene === "loading" ? 0 : 100;

  return (
    <AppWindow showSidebar activeSidebarItem="publish">
      <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "#FCFDFE" }}>
        <div
          style={{
            height: 40,
            borderBottom: `1px solid ${theme.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontFamily: fontDisplay,
              fontSize: 12,
              color: "#667085",
            }}
          >
            <span>⌂</span>
            <span>Publication</span>
          </div>
        </div>

        <div
          style={{
            height: 52,
            padding: "0 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: `1px solid ${theme.border}`,
          }}
        >
          <div>
            <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>Niamoto</div>
            <div style={{ fontFamily: fontDisplay, fontSize: 12, color: "#98A2B3", marginTop: 2 }}>Publication</div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <HeaderBadge label={topBadge.label} tone={topBadge.tone} />
            <PrimaryButton
              label={scene === "generating" ? "Génération en cours..." : "Générer le site"}
              icon={scene === "generating" ? <Spinner size={14} tone="#FFFFFF" /> : <SendIcon />}
              disabled={scene === "generating"}
              compact
            />
          </div>
        </div>

        <div
          style={{
            height: 70,
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
            gap: 24,
            padding: "12px 16px 10px",
            borderBottom: `1px solid ${theme.border}`,
          }}
        >
          <MetricCell label="Fichiers générés" value={filesGenerated} />
          <MetricCell label="Temps de génération" value="—" />
          <MetricCell label="Dernière génération" value="—" />
          <MetricCell label="Répertoire" value="./exports" />
        </div>

        <div
          style={{
            flex: 1,
            minHeight: 0,
            display: "grid",
            gridTemplateColumns: "520px 1fr",
            gap: 16,
            padding: "12px 16px 16px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
            <div style={{ ...panelStyle, padding: "14px 14px 16px" }}>
              <div style={sectionTitleStyle}>Génération settings</div>
              <div style={{ ...mutedStyle, marginTop: 4, marginBottom: 18 }}>Création du site web statique complet</div>

              {scene === "loading" ? (
                <div
                  style={{
                    border: `1px solid ${theme.border}`,
                    borderRadius: 10,
                    padding: "14px 14px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 16,
                  }}
                >
                  <div
                    style={{
                      fontFamily: fontDisplay,
                      fontSize: 13,
                      fontWeight: 600,
                      color: "#344054",
                      maxWidth: 210,
                      lineHeight: 1.35,
                    }}
                  >
                    Recalculer les statistiques avant la génération
                  </div>
                  <ToggleSwitch />
                </div>
              ) : (
                <div
                  style={{
                    border: `1px solid ${theme.border}`,
                    borderRadius: 10,
                    padding: "14px 14px 12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  <div
                    style={{
                      fontFamily: fontDisplay,
                      fontSize: 12,
                      color: "#344054",
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                    }}
                  >
                    <span>
                      {scene === "success"
                        ? "Génération du site - Génération en cours..."
                        : "Génération du site - Génération en cours..."}
                    </span>
                    <span>({Math.round(leftBuildProgress)}%)</span>
                  </div>
                  <ProgressTrack percent={leftBuildProgress} color="#3F8D55" />
                </div>
              )}
            </div>

            <div style={{ ...panelStyle, padding: "14px 14px 16px" }}>
              <div style={sectionTitleStyle}>Déployer</div>
              <div style={{ ...mutedStyle, marginTop: 4, marginBottom: 16 }}>Publiez votre site en ligne</div>

              {scene === "logs" || scene === "success" ? (
                <div
                  style={{
                    border: `1px solid ${theme.border}`,
                    borderRadius: 10,
                    padding: "12px 12px 10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <GithubIcon />
                    <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
                      <div style={{ fontFamily: fontDisplay, fontSize: 13, fontWeight: 700, color: "#181D27" }}>
                        GitHub Pages
                      </div>
                      <div style={{ ...mutedStyle, fontSize: 11 }}>arsis-dev/niamoto-test</div>
                    </div>
                    <HeaderBadge
                      label={scene === "success" ? "Terminé" : "Déploiement en cours..."}
                      tone={scene === "success" ? "success" : "neutral"}
                    />
                  </div>
                  <div style={{ ...mutedStyle, fontSize: 11 }}>
                    {scene === "success" ? "Dernier déploiement: il y a 9 min" : "Déploiement en cours..."}
                  </div>
                  {scene === "success" && (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: fontDisplay, fontSize: 12, color: "#15803D" }}>
                      <StatusDot color="#22C55E" />
                      <span>https://arsis-dev.github.io/niamoto-test</span>
                    </div>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <PrimaryButton
                      label={scene === "success" ? "Déployer" : "Déploiement en cours..."}
                      icon={<SendIcon />}
                      compact
                      disabled={scene !== "success"}
                    />
                    <SecondaryButton label="Voir" icon={<ExternalLinkIcon />} />
                  </div>
                  <SecondaryButton label="Gérer les destinations" icon={<span style={{ fontSize: 14 }}>⚙</span>} subtle />
                </div>
              ) : (
                <>
                  <div
                    style={{
                      border: `1px solid ${theme.border}`,
                      borderRadius: 10,
                      padding: "14px 14px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 16,
                      marginBottom: 12,
                    }}
                  >
                    <div style={{ display: "flex", gap: 10 }}>
                      <span style={{ color: "#98A2B3", fontSize: 16 }}>◌</span>
                      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                        <div style={{ fontFamily: fontDisplay, fontSize: 12, color: "#667085", maxWidth: 162, lineHeight: 1.35 }}>
                          Vous devez d’abord générer le site avant de pouvoir le déployer.
                        </div>
                      </div>
                    </div>
                    <PrimaryButton label="Générer le site" icon={<SendIcon />} compact disabled />
                  </div>

                  <div
                    style={{
                      border: `1px dashed ${theme.borderStrong}`,
                      borderRadius: 10,
                      padding: "16px 14px",
                      display: "flex",
                      flexDirection: "column",
                      gap: 10,
                    }}
                  >
                    <div style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#181D27" }}>
                      Aucun déploiement configuré
                    </div>
                    <div style={{ ...mutedStyle, lineHeight: 1.4 }}>
                      Configurez une plateforme pour publier votre site en ligne
                    </div>
                    <PrimaryButton label="Ajouter un déploiement" icon={<span style={{ fontSize: 16 }}>＋</span>} compact />
                  </div>
                </>
              )}
            </div>

            <div style={{ ...panelStyle, padding: "14px 14px 12px", marginTop: "auto" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={sectionTitleStyle}>Activité récente</div>
                  <div style={{ ...mutedStyle, marginTop: 4 }}>Consultez l’historique des builds et déploiements</div>
                </div>
                <SecondaryButton label="Historique" icon={<span style={{ fontSize: 15 }}>◷</span>} />
              </div>

              {scene === "logs" || scene === "success" ? (
                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
                  {[
                    "Déploiement · github",
                    "Déploiement · github",
                    "Déploiement · github",
                  ].map((entry, index) => (
                    <div key={entry + index} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 15, color: "#667085" }}>✈</span>
                      <div>
                        <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#344054" }}>{entry}</div>
                        <div style={{ ...mutedStyle, fontSize: 11 }}>{index === 0 ? "Il y a 9 minutes" : "Il y a environ 1 heure"}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ ...mutedStyle, marginTop: 16 }}>Aucune activité récente pour le moment</div>
              )}
            </div>
          </div>

          <div style={{ ...panelStyle, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
            <div style={{ padding: "14px 16px 10px", borderBottom: `1px solid ${theme.border}` }}>
              <div style={sectionTitleStyle}>Aperçu du site</div>
              <div style={{ ...mutedStyle, marginTop: 4 }}>Preview the current site structure before generation</div>
            </div>

            <div
              style={{
                height: 40,
                borderBottom: `1px solid ${theme.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 12px 0 16px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontFamily: fontDisplay, fontSize: 13, color: "#181D27" }}>Dynamic preview</span>
                <span style={{ fontFamily: fontDisplay, fontSize: 11, color: "#98A2B3" }}>1440x900 (60%)</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#667085" }}>
                <span>📱</span>
                <span>📟</span>
                <span
                  style={{
                    width: 26,
                    height: 22,
                    borderRadius: 6,
                    background: "#5B86B0",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#FFFFFF",
                  }}
                >
                  🖥
                </span>
                <span style={{ fontSize: 15 }}>↻</span>
              </div>
            </div>

            <SitePreviewMock scene={scene} />
          </div>
        </div>
      </div>
    </AppWindow>
  );
};

const DestinationPanel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <>
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(15, 23, 42, 0.48)",
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 568,
        top: 86,
        width: 1230,
        height: 890,
        borderRadius: 14,
        background: "#FFFFFF",
        boxShadow: "0 24px 60px rgba(15, 23, 42, 0.22)",
        overflow: "hidden",
        border: `1px solid ${theme.border}`,
      }}
    >
      <div
        style={{
          height: 74,
          borderBottom: `1px solid ${theme.border}`,
          padding: "18px 20px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>
            Gérer les destinations
          </div>
          <div style={{ ...mutedStyle, marginTop: 4, fontSize: 13 }}>Publiez votre site en ligne</div>
        </div>
        <span style={{ fontSize: 18, color: "#98A2B3" }}>×</span>
      </div>
      {children}
    </div>
  </>
);

const ProviderPickerOverlay: React.FC = () => (
  <DestinationPanel>
    <div style={{ position: "relative", height: "calc(100% - 74px)" }}>
      <div style={{ position: "absolute", right: 18, top: 16 }}>
        <PrimaryButton label="Ajouter un déploiement" icon={<span style={{ fontSize: 16 }}>＋</span>} compact />
      </div>

      <div
        style={{
          position: "absolute",
          inset: 22,
          borderRadius: 12,
          border: `1px solid ${theme.border}`,
          background: "#F8FAFC",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <span style={{ fontSize: 34, color: "#98A2B3" }}>✈</span>
        <div style={{ fontFamily: fontDisplay, fontSize: 28, fontWeight: 700, color: "#181D27" }}>
          Aucun déploiement configuré
        </div>
        <div style={{ fontFamily: fontDisplay, fontSize: 15, color: "#98A2B3" }}>
          Configurez une plateforme pour publier votre site
        </div>
        <PrimaryButton label="Ajouter un déploiement" icon={<span style={{ fontSize: 16 }}>＋</span>} />
      </div>

      <div
        style={{
          position: "absolute",
          left: 226,
          top: 220,
          width: 402,
          borderRadius: 12,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          boxShadow: "0 20px 50px rgba(15, 23, 42, 0.18)",
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "14px 14px 10px", borderBottom: `1px solid ${theme.border}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>
                Ajouter un déploiement
              </div>
              <div style={{ ...mutedStyle, marginTop: 4 }}>Choisir une plateforme</div>
            </div>
            <span style={{ fontSize: 18, color: "#98A2B3" }}>×</span>
          </div>
        </div>

        <div
          style={{
            padding: "14px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
          }}
        >
          <ProviderTile
            name="Cloudflare Workers"
            description="Edge network, HTTPS auto"
            accent="#F38020"
            icon={<span style={{ fontWeight: 700 }}>C</span>}
          />
          <ProviderTile name="GitHub Pages" description="Free, unlimited hosting" accent="#111827" icon={<GithubIcon size={16} background="transparent" />} />
          <ProviderTile
            name="Netlify"
            description="CDN mondial, HTTPS auto"
            accent="#00C7B7"
            icon={<span style={{ fontWeight: 700 }}>N</span>}
          />
          <ProviderTile
            name="Vercel"
            description="Edge network, previews auto"
            accent="#111827"
            icon={
              <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                <path d="M12 4 21 20H3z" />
              </svg>
            }
          />
          <ProviderTile
            name="Render"
            description="Free static sites"
            accent="#46E3B7"
            icon={<span style={{ fontWeight: 700, color: "#14532D" }}>R</span>}
          />
          <ProviderTile
            name="SSH / rsync"
            description="Personal server, full control"
            accent="#334155"
            icon={<span style={{ fontWeight: 700 }}>S</span>}
          />
        </div>
      </div>
    </div>
  </DestinationPanel>
);

const GitHubConfigOverlay: React.FC = () => (
  <DestinationPanel>
    <div style={{ position: "relative", height: "calc(100% - 74px)" }}>
      <div style={{ position: "absolute", right: 18, top: 16 }}>
        <PrimaryButton label="Ajouter un déploiement" icon={<span style={{ fontSize: 16 }}>＋</span>} compact />
      </div>

      <div
        style={{
          position: "absolute",
          inset: 22,
          borderRadius: 12,
          border: `1px solid ${theme.border}`,
          background: "#F8FAFC",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <span style={{ fontSize: 34, color: "#98A2B3" }}>✈</span>
        <div style={{ fontFamily: fontDisplay, fontSize: 28, fontWeight: 700, color: "#181D27" }}>
          Aucun déploiement configuré
        </div>
        <div style={{ fontFamily: fontDisplay, fontSize: 15, color: "#98A2B3" }}>
          Configurez une plateforme pour publier votre site
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 226,
          top: 128,
          width: 520,
          borderRadius: 12,
          border: `1px solid ${theme.border}`,
          background: "#FFFFFF",
          boxShadow: "0 20px 50px rgba(15, 23, 42, 0.18)",
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "14px 14px 10px", borderBottom: `1px solid ${theme.border}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>
                Ajouter un déploiement
              </div>
              <div style={{ ...mutedStyle, marginTop: 4 }}>Choisir une plateforme</div>
            </div>
            <span style={{ fontSize: 18, color: "#98A2B3" }}>×</span>
          </div>
        </div>

        <div style={{ padding: "16px 16px 14px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            <GithubIcon size={26} />
            <div>
              <div style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#181D27" }}>
                GitHub Pages
              </div>
              <div style={{ fontFamily: fontDisplay, fontSize: 12, color: "#667085", lineHeight: 1.45, marginTop: 3 }}>
                Hébergement gratuit et illimité pour sites statiques. Les fichiers sont poussés
                sur une branche dédiée (gh-pages) de votre dépôt.
              </div>
              <div style={{ ...mutedStyle, marginTop: 8, lineHeight: 1.45 }}>
                ○ Créez un dépôt sur GitHub. Générez un Fine-Grained Token avec les permissions
                Contents: Read and Write sur ce dépôt.
              </div>
            </div>
          </div>

          <div style={{ ...panelStyle, boxShadow: "none", padding: "12px 12px 14px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ fontFamily: fontDisplay, fontSize: 13, fontWeight: 700, color: "#344054" }}>Identifiants</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <SecondaryButton label="Vérifier" subtle />
                <SecondaryButton label="Créer un token" subtle />
              </div>
            </div>
            <div style={{ ...mutedStyle, marginTop: 8, lineHeight: 1.45 }}>
              Allez dans Settings &gt; Developer settings &gt; Fine-grained tokens. Sélectionnez le dépôt cible et accordez Contents: Read and write.
            </div>
          </div>

          {[
            {
              label: "Personal Access Token",
              placeholder: "github_pat_...",
              help: "Allez dans Settings > Developer settings > Fine-grained tokens. Sélectionnez le dépôt cible et accordez Contents: Read and write.",
            },
            {
              label: "Repository (owner/repo)",
              placeholder: "user/my-site",
              help: "Format owner/repo. Ex: mon-org/mon-site. Le dépôt doit exister sur GitHub.",
            },
            {
              label: "Branch (optionnel)",
              placeholder: "gh-pages",
              help: "Par défaut : gh-pages. Après le premier déploiement, activez GitHub Pages dans Settings > Pages du dépôt.",
            },
          ].map((field) => (
            <div key={field.label}>
              <div style={{ fontFamily: fontDisplay, fontSize: 12, fontWeight: 600, color: "#344054", marginBottom: 6 }}>
                {field.label}
              </div>
              <div
                style={{
                  height: 34,
                  borderRadius: 8,
                  border: `1px solid ${theme.border}`,
                  background: "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  padding: "0 12px",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 12,
                  color: "#98A2B3",
                }}
              >
                {field.placeholder}
              </div>
              <div style={{ ...mutedStyle, marginTop: 6, lineHeight: 1.45 }}>{field.help}</div>
            </div>
          ))}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
            <SecondaryButton label="Annuler" />
            <SecondaryButton label="Enregistrer" subtle />
            <PrimaryButton label="Enregistrer et déployer" icon={<SendIcon />} />
          </div>
        </div>
      </div>
    </div>
  </DestinationPanel>
);

const DeploymentLogsOverlay: React.FC<{ frame: number }> = ({ frame }) => {
  const deployPercent = interpolate(frame, [logsStart, logsEnd], [22, 84], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const logSteps = [20, 40, 60, 80, 100, 120, 140, 160].map((value) =>
    Math.round(interpolate(frame, [logsStart, logsEnd], [Math.max(12, value - 18), value], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })),
  );

  return (
    <DestinationPanel>
      <div style={{ height: "calc(100% - 74px)", padding: "18px 18px 20px", background: "#FFFFFF" }}>
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
          <PrimaryButton label="Ajouter un déploiement" icon={<span style={{ fontSize: 16 }}>＋</span>} compact />
        </div>

        <div style={{ ...panelStyle, width: 430, padding: "14px 16px 12px", marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            <GithubIcon size={28} />
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>
                  GitHub Pages
                </span>
                <HeaderBadge label="Configuré" tone="neutral" />
              </div>
              <div style={{ ...mutedStyle, marginTop: 4, fontSize: 12 }}>arsis-dev/niamoto-test</div>
            </div>
            <MoreIcon />
          </div>

          <div style={{ ...mutedStyle, marginTop: 14, marginBottom: 10 }}>Jamais déployé</div>
          <ProgressTrack percent={deployPercent} color="#9CC59F" slim label="Déploiement en cours..." />
        </div>

        <div style={{ ...panelStyle, padding: "0", overflow: "hidden" }}>
          <div
            style={{
              height: 46,
              padding: "0 16px",
              borderBottom: `1px solid ${theme.border}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ fontFamily: fontDisplay, fontSize: 15, fontWeight: 700, color: "#181D27" }}>
              Logs de déploiement
            </div>
            <HeaderBadge label="Déploiement en cours..." tone="success" />
          </div>
          <div style={{ padding: "12px 16px 16px" }}>
            <div
              style={{
                borderRadius: 8,
                background: "#0F172A",
                minHeight: 154,
                padding: "14px 16px",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 12,
                lineHeight: 1.55,
                color: "#6EE7B7",
              }}
            >
              <div>Deploying to arsis-dev/niamoto-test (branch: gh-pages)</div>
              <div>Branch 'gh-pages' ready (tip: 92ea983)</div>
              <div>Found 3727 files to upload</div>
              {logSteps.map((count, index) => (
                <div key={index}>Uploading files: {count}/3727</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </DestinationPanel>
  );
};

const DeploymentSuccessOverlay: React.FC = () => (
  <DestinationPanel>
    <div style={{ height: "calc(100% - 74px)", padding: "18px 18px 20px", background: "#FFFFFF" }}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        <PrimaryButton label="Ajouter un déploiement" icon={<span style={{ fontSize: 16 }}>＋</span>} compact />
      </div>

      <div style={{ ...panelStyle, width: 460, padding: "16px 16px 14px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <GithubIcon size={28} />
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontFamily: fontDisplay, fontSize: 16, fontWeight: 700, color: "#181D27" }}>
                GitHub Pages
              </span>
              <HeaderBadge label="Déployé" tone="success" />
              <StatusDot color="#22C55E" />
            </div>
            <div style={{ ...mutedStyle, marginTop: 4, fontSize: 12 }}>arsis-dev/niamoto-test</div>
          </div>
          <MoreIcon />
        </div>

        <div style={{ fontFamily: fontDisplay, fontSize: 13, color: "#667085", marginTop: 18 }}>
          Dernier déploiement: 13/04/2026 16:04:27 —{" "}
          <span style={{ color: "#22C55E", fontWeight: 600 }}>✓ Déploiement réussi !</span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 14,
            fontFamily: fontDisplay,
            fontSize: 13,
            color: "#344054",
          }}
        >
          <StatusDot color="#22C55E" />
          <span>https://arsis-dev.github.io/niamoto-test</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 16 }}>
          <PrimaryButton label="Redéployer" icon={<SendIcon />} />
          <SecondaryButton label="Voir le site" icon={<ExternalLinkIcon />} />
        </div>
      </div>
    </div>
  </DestinationPanel>
);

const PublishSceneScreen: React.FC<{ scene: PublishScene; frame: number }> = ({ scene, frame }) => (
  <AbsoluteFill
    style={{
      opacity: 1,
      transform: "translateY(0px)",
    }}
  >
    <PublishMainPage scene={scene} frame={frame} />
    {scene === "picker" && <ProviderPickerOverlay />}
    {scene === "config" && <GitHubConfigOverlay />}
    {scene === "logs" && <DeploymentLogsOverlay frame={frame} />}
    {scene === "success" && <DeploymentSuccessOverlay />}
  </AbsoluteFill>
);

/**
 * Act 6 — Publication.
 * Rebuilt from the real publish/deploy UI flow:
 * preview loading -> generation preview -> provider picker -> GitHub Pages config -> deploy logs -> success
 */
export const Act6Publish: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ background: theme.bgDark }}>
      <AbsoluteFill
        style={{
          opacity: screenOpacity(frame, 0, loadingEnd),
          transform: `translateY(${screenShift(frame, 0)}px)`,
        }}
      >
        <PublishSceneScreen scene="loading" frame={frame} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          opacity: screenOpacity(frame, generatingStart, generatingEnd),
          transform: `translateY(${screenShift(frame, generatingStart)}px)`,
        }}
      >
        <PublishSceneScreen scene="generating" frame={frame} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          opacity: screenOpacity(frame, pickerStart, pickerEnd),
          transform: `translateY(${screenShift(frame, pickerStart)}px)`,
        }}
      >
        <PublishSceneScreen scene="picker" frame={frame} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          opacity: screenOpacity(frame, configStart, configEnd),
          transform: `translateY(${screenShift(frame, configStart)}px)`,
        }}
      >
        <PublishSceneScreen scene="config" frame={frame} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          opacity: screenOpacity(frame, logsStart, logsEnd),
          transform: `translateY(${screenShift(frame, logsStart)}px)`,
        }}
      >
        <PublishSceneScreen scene="logs" frame={frame} />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          opacity: screenOpacity(frame, successStart),
          transform: `translateY(${screenShift(frame, successStart)}px)`,
        }}
      >
        <PublishSceneScreen scene="success" frame={frame} />
      </AbsoluteFill>

      <CursorOverlay waypoints={act6Waypoints} />
    </AbsoluteFill>
  );
};
