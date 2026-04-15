import { memo, useEffect, useMemo, useState } from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate, delayRender, continueRender, staticFile, cancelRender } from "remotion";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import { teaserTheme } from "../theme";
import taxonData from "../data/taxon-vedette.json";

interface BubbleMapNCProps {
  startFrame?: number;
  /** Frames pour révéler le contour de la NC. Default 18. */
  landRevealFrames?: number;
  /** Frames entre chaque bubble. Default 2. */
  bubbleStaggerFrames?: number;
}

const NC_TOPO_URL = staticFile("maps/nc.topojson");
const NC_PROJECTION_CONFIG = {
  scale: 4800,
  center: [165.7, -21.3] as [number, number],
  rotate: [0, 0, 0] as [number, number, number],
};

/**
 * Carte Nouvelle-Calédonie + bubbles d'occurrences Araucariaceae.
 * Money shot #1 du teaser (référence : `/fr/taxons/948049381.html` widget « Distribution géographique » zoom).
 *
 * Data :
 * - contour NC depuis `public/maps/nc.topojson` (provinces du projet nouvelle-caledonie, WGS84)
 * - bubbles depuis `taxon-vedette.json` (hot spots + diffus)
 *
 * Pattern Remotion :
 * - `delayRender` pendant le fetch du topojson
 * - spring() sur chaque bubble avec stagger `bubbleStaggerFrames`
 * - opacité contour NC animée de 0 → 1 au début
 */
export const BubbleMapNC = memo<BubbleMapNCProps>(({ startFrame = 0, landRevealFrames = 18, bubbleStaggerFrames = 2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [topoReady, setTopoReady] = useState(false);
  const [handle] = useState(() => delayRender("Loading NC topojson"));

  useEffect(() => {
    fetch(NC_TOPO_URL)
      .then((r) => r.json())
      .then(() => {
        setTopoReady(true);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, [handle]);

  const localFrame = Math.max(0, frame - startFrame);

  const landOpacity = interpolate(localFrame, [0, landRevealFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const allBubbles = useMemo(() => {
    const out: Array<{ lon: number; lat: number; count: number; hot: boolean }> = [];
    taxonData.mapSampling.hotSpots.forEach((s) => out.push({ lon: s.lon, lat: s.lat, count: s.count, hot: true }));
    taxonData.mapSampling.diffusePoints.forEach((p) => out.push({ lon: p.lon, lat: p.lat, count: p.count, hot: false }));
    return out;
  }, []);

  const maxCount = Math.max(...allBubbles.map((b) => b.count));

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", background: teaserTheme.pageBg }}>
      {topoReady && (
        <ComposableMap projection="geoMercator" projectionConfig={NC_PROJECTION_CONFIG} width={800} height={500} style={{ width: "100%", height: "100%" }}>
          {/* Contour NC */}
          <g style={{ opacity: landOpacity }}>
            <Geographies geography={NC_TOPO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#f4ead5"
                    stroke="#d9c7a1"
                    strokeWidth={0.6}
                    style={{
                      default: { outline: "none" },
                      hover: { outline: "none" },
                      pressed: { outline: "none" },
                    }}
                  />
                ))
              }
            </Geographies>
          </g>

          {/* Bubbles d'occurrences */}
          {allBubbles.map((b, idx) => {
            const delay = landRevealFrames + idx * bubbleStaggerFrames;
            const bubbleFrame = Math.max(0, localFrame - delay);
            const scale = spring({
              frame: bubbleFrame,
              fps,
              config: { damping: 12, stiffness: 160 },
            });
            const clampedScale = interpolate(scale, [0, 1], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });

            const radius = mapCountToRadius(b.count, maxCount, b.hot);
            const color = mapCountToColor(b.count, maxCount);

            return (
              <Marker key={idx} coordinates={[b.lon, b.lat]}>
                <circle
                  r={radius * clampedScale}
                  fill={color}
                  fillOpacity={0.72}
                  stroke={b.hot ? teaserTheme.cardWhite : "transparent"}
                  strokeWidth={b.hot ? 1 : 0}
                />
              </Marker>
            );
          })}
        </ComposableMap>
      )}

      {/* Légende count */}
      <div
        style={{
          position: "absolute",
          right: 12,
          top: 18,
          bottom: 18,
          width: 14,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: landOpacity,
        }}
      >
        <div style={{ fontFamily: "inherit", fontSize: 10, color: teaserTheme.textSecondary, marginBottom: 4 }}>count</div>
        <div
          style={{
            flex: 1,
            width: 8,
            borderRadius: 2,
            background: `linear-gradient(to bottom, ${teaserTheme.mapGradient.slice().reverse().join(", ")})`,
          }}
        />
        <div style={{ fontFamily: "inherit", fontSize: 10, color: teaserTheme.textSecondary, marginTop: 4 }}>1</div>
      </div>
    </div>
  );
});

BubbleMapNC.displayName = "BubbleMapNC";

function mapCountToRadius(count: number, maxCount: number, hot: boolean): number {
  const ratio = Math.sqrt(count / maxCount);
  const minR = hot ? 7 : 3;
  const maxR = hot ? 22 : 10;
  return minR + ratio * (maxR - minR);
}

function mapCountToColor(count: number, maxCount: number): string {
  const ratio = count / maxCount;
  const gradient = teaserTheme.mapGradient;
  const idx = Math.min(gradient.length - 1, Math.floor(ratio * gradient.length));
  return gradient[idx];
}
