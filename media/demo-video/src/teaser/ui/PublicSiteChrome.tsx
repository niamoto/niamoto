import { memo, type ReactNode } from "react";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";

interface PublicSiteChromeProps {
  /** URL dans la barre d'adresse (optionnelle). */
  url?: string;
  children: ReactNode;
}

/**
 * Chrome du site publié Niamoto — header vert plein largeur + nav + zone URL.
 * Référence visuelle : `http://localhost:5173/api/site/preview-exported/fr/index.html`
 * (header #228b22 plein largeur, logo blanc Niamoto, nav droite, FR toggle).
 */
export const PublicSiteChrome = memo<PublicSiteChromeProps>(({ url = "niamoto.example/fr", children }) => {
  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        background: teaserTheme.pageBg,
        display: "flex",
        flexDirection: "column",
        borderRadius: 14,
        overflow: "hidden",
        boxShadow: teaserTheme.shadowWindow,
      }}
    >
      {/* Browser URL bar (mac-style traffic lights + URL) */}
      <div
        style={{
          height: 36,
          background: "#f2f3f5",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          gap: 8,
          flexShrink: 0,
        }}
      >
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#FEBC2E" }} />
        <span style={{ width: 12, height: 12, borderRadius: "50%", background: "#28C840" }} />
        <div
          style={{
            flex: 1,
            marginLeft: 14,
            height: 22,
            borderRadius: 6,
            background: teaserTheme.cardWhite,
            border: `1px solid ${teaserTheme.border}`,
            padding: "0 10px",
            display: "flex",
            alignItems: "center",
            fontFamily: fontDisplay,
            fontSize: 11,
            color: teaserTheme.textSecondary,
            maxWidth: 520,
          }}
        >
          <LockIcon />
          <span style={{ marginLeft: 6 }}>{url}</span>
        </div>
      </div>

      {/* Header vert Niamoto */}
      <div
        style={{
          height: 56,
          background: teaserTheme.primary,
          display: "flex",
          alignItems: "center",
          padding: "0 24px",
          gap: 16,
          flexShrink: 0,
        }}
      >
        <NiamotoWordmark />
        <div style={{ flex: 1 }} />
        <NavLinks />
      </div>

      {/* Zone contenu */}
      <div style={{ flex: 1, overflow: "hidden", minHeight: 0 }}>{children}</div>
    </div>
  );
});

PublicSiteChrome.displayName = "PublicSiteChrome";

/* -------------------------- helpers -------------------------- */

const NiamotoWordmark: React.FC = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
    {/* Logo minimaliste (feuille stylisée) */}
    <svg width="26" height="26" viewBox="0 0 40 40" fill="none">
      <path
        d="M8 30 Q 8 14 20 8 Q 32 14 32 30 Q 20 36 8 30 Z"
        fill="#ffffff"
        stroke="#ffffff"
        strokeWidth="1.5"
      />
      <path d="M20 10 L 20 32" stroke={teaserTheme.primary} strokeWidth="1.5" />
    </svg>
    <span
      style={{
        fontFamily: fontDisplay,
        fontSize: 22,
        fontWeight: 700,
        color: teaserTheme.cardWhite,
        letterSpacing: 1.5,
      }}
    >
      NIAMOTO
    </span>
  </div>
);

const NAV_ITEMS = ["Accueil", "Méthodologie", "Ressources", "Arbres", "Peuplements", "Forêt"];

const NavLinks: React.FC = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
    {NAV_ITEMS.map((item) => (
      <span
        key={item}
        style={{
          fontFamily: fontDisplay,
          fontSize: 13,
          fontWeight: 500,
          color: teaserTheme.cardWhite,
          opacity: 0.95,
        }}
      >
        {item}
      </span>
    ))}
    <div
      style={{
        marginLeft: 12,
        fontFamily: fontDisplay,
        fontSize: 12,
        fontWeight: 600,
        color: teaserTheme.cardWhite,
        opacity: 0.95,
        display: "flex",
        alignItems: "center",
        gap: 4,
      }}
    >
      <GlobeIcon />
      FR
    </div>
  </div>
);

const LockIcon: React.FC = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const GlobeIcon: React.FC = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20" />
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);
