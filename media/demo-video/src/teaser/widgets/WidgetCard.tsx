import { memo, type CSSProperties, type ReactNode } from "react";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";

interface WidgetCardProps {
  title: string;
  /** Bandeau d'info à droite (ex: icône help). Optionnel. */
  actions?: ReactNode;
  /** Opacité du bandeau (pour révélations). Default 1. */
  headerOpacity?: number;
  style?: CSSProperties;
  bodyStyle?: CSSProperties;
  children: ReactNode;
}

/**
 * Card Niamoto signature : header gradient vert + body blanc + ombre triple-couche.
 * Référence visuelle : `docs/plans/caps/*.png` (bandeau vert en haut de chaque widget)
 * et `src/niamoto/publish/assets/css/niamoto.css:313`.
 */
export const WidgetCard = memo<WidgetCardProps>(({ title, actions, headerOpacity = 1, style, bodyStyle, children }) => {
  return (
    <div
      style={{
        background: teaserTheme.cardWhite,
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: teaserTheme.shadowCard,
        display: "flex",
        flexDirection: "column",
        ...style,
      }}
    >
      <div
        style={{
          background: teaserTheme.widgetHeaderGradient,
          padding: "12px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          opacity: headerOpacity,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontFamily: fontDisplay,
            fontSize: 15,
            fontWeight: 600,
            color: teaserTheme.textOnPrimary,
            letterSpacing: 0.1,
          }}
        >
          {title}
        </h3>
        {actions ? <div style={{ color: teaserTheme.textOnPrimary, opacity: 0.7 }}>{actions}</div> : <HelpIcon />}
      </div>

      <div style={{ flex: 1, padding: 20, ...bodyStyle }}>{children}</div>
    </div>
  );
});

WidgetCard.displayName = "WidgetCard";

const HelpIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ color: teaserTheme.textOnPrimary, opacity: 0.7 }}>
    <circle cx="12" cy="12" r="10" />
    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);
