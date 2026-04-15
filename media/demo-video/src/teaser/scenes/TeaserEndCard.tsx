import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";

/**
 * EndCard — logo + tagline + CTA (décision #1 : inversion R15).
 * Durée : 5s (150 frames à 30fps).
 *
 * Narration (one-shot avec hold final — décision #5) :
 *  - 0-20f   : Logo + "NIAMOTO" apparaissent (spring damping 14)
 *  - 20-32f  : Tagline "Import. Structure. Publish." fade-in sous le logo
 *  - 32-48f  : Accroche "Open source. Auto-hébergeable." fade-in
 *  - 48-62f  : Bouton CTA "niamoto.org" apparaît
 *  - 62-150f : Hold statique (~3s) — lisibilité clic autoplay loop hard
 */

export const TeaserEndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoSpring = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 160 },
    durationInFrames: 20,
  });
  const logoProgress = interpolate(logoSpring, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const taglineOpacity = interpolate(frame, [20, 32], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const taglineTranslateY = interpolate(frame, [20, 32], [8, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const pitchOpacity = interpolate(frame, [32, 48], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pitchTranslateY = interpolate(frame, [32, 48], [8, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const ctaSpring = spring({
    frame: frame - 48,
    fps,
    config: { damping: 12, stiffness: 180 },
    durationInFrames: 14,
  });
  const ctaProgress = interpolate(ctaSpring, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${teaserTheme.cardWhite} 0%, ${teaserTheme.pageBg} 100%)`,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
        }}
      >
        {/* Logo + wordmark */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 18,
            opacity: logoProgress,
            transform: `translateY(${interpolate(logoProgress, [0, 1], [16, 0])}px) scale(${interpolate(logoProgress, [0, 1], [0.96, 1])})`,
          }}
        >
          <LeafLogo size={78} color={teaserTheme.primary} />
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: 72,
              fontWeight: 700,
              color: teaserTheme.primary,
              letterSpacing: 2.5,
            }}
          >
            NIAMOTO
          </div>
        </div>

        {/* Tagline marque (décision #2 hybride hook) */}
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 22,
            fontWeight: 500,
            color: teaserTheme.textPrimary,
            opacity: taglineOpacity,
            transform: `translateY(${taglineTranslateY}px)`,
            letterSpacing: 0.4,
          }}
        >
          Import. Structure. Publish.
        </div>

        {/* Accroche */}
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 16,
            fontWeight: 400,
            color: teaserTheme.textSecondary,
            opacity: pitchOpacity,
            transform: `translateY(${pitchTranslateY}px)`,
            marginTop: 4,
          }}
        >
          Open source. Auto-hébergeable.
        </div>

        {/* CTA bouton (décision #1 — inversion R15) */}
        <div
          style={{
            marginTop: 20,
            opacity: ctaProgress,
            transform: `scale(${interpolate(ctaProgress, [0, 1], [0.92, 1])})`,
          }}
        >
          <div
            style={{
              padding: "16px 40px",
              borderRadius: 12,
              background: teaserTheme.primary,
              color: teaserTheme.cardWhite,
              fontFamily: fontDisplay,
              fontSize: 17,
              fontWeight: 700,
              letterSpacing: 0.3,
              boxShadow: "0 8px 24px rgba(34, 139, 34, 0.32)",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            niamoto.org
            <ArrowIcon />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* -------------------------- helpers -------------------------- */

const LeafLogo: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
    <path
      d="M8 30 Q 8 14 20 8 Q 32 14 32 30 Q 20 36 8 30 Z"
      fill={color}
      stroke={color}
      strokeWidth="1.5"
    />
    <path d="M20 10 L 20 32" stroke="#ffffff" strokeWidth="2" />
    <path d="M20 18 Q 15 19 13 24" stroke="#ffffff" strokeWidth="1.5" fill="none" />
    <path d="M20 22 Q 25 23 27 28" stroke="#ffffff" strokeWidth="1.5" fill="none" />
  </svg>
);

const ArrowIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <line x1="5" y1="12" x2="19" y2="12" />
    <polyline points="12 5 19 12 12 19" />
  </svg>
);
