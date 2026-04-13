import { useCurrentFrame, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

interface MockPreviewPanelProps {
  title?: string;
  changeAtFrame?: number;
  nextTitle?: string;
}

/**
 * Mini-layout HTML preview simulating a generated site.
 * Cross-fades between layouts when title changes.
 */
export const MockPreviewPanel: React.FC<MockPreviewPanelProps> = ({
  title = "Species",
  changeAtFrame,
  nextTitle,
}) => {
  const frame = useCurrentFrame();

  // Cross-fade between layouts
  const hasTransition = changeAtFrame !== undefined && nextTitle !== undefined;
  const transitionProgress = hasTransition
    ? interpolate(frame, [changeAtFrame!, changeAtFrame! + 15], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  const currentTitle = transitionProgress > 0.5 ? nextTitle! : title;
  const contentOpacity = hasTransition
    ? transitionProgress <= 0.5
      ? interpolate(transitionProgress, [0, 0.5], [1, 0])
      : interpolate(transitionProgress, [0.5, 1], [0, 1])
    : 1;

  return (
    <div
      style={{
        background: theme.bgLight,
        borderRadius: 6,
        overflow: "hidden",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderLeft: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Browser chrome */}
      <div
        style={{
          height: 28,
          background: "#E8E8EC",
          display: "flex",
          alignItems: "center",
          padding: "0 10px",
          gap: 6,
        }}
      >
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ccc" }} />
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ccc" }} />
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ccc" }} />
        <div
          style={{
            flex: 1,
            height: 18,
            background: "white",
            borderRadius: 4,
            marginLeft: 8,
            display: "flex",
            alignItems: "center",
            paddingLeft: 8,
          }}
        >
          <span style={{ fontFamily: fontDisplay, fontSize: 9, color: "#999" }}>
            my-ecology-project.niamoto.io
          </span>
        </div>
      </div>

      {/* Site content */}
      <div style={{ flex: 1, opacity: contentOpacity }}>
        {/* Header */}
        <div
          style={{
            background: `linear-gradient(135deg, ${theme.forestGreen}, #26A69A)`,
            padding: "14px 16px",
          }}
        >
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 14,
              fontWeight: 700,
              color: "white",
            }}
          >
            {currentTitle}
          </span>
        </div>

        {/* Content grid */}
        <div
          style={{
            padding: 12,
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
          }}
        >
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              style={{
                background: "white",
                borderRadius: 4,
                padding: 10,
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: 28,
                  background: "#E5E7EB",
                  borderRadius: 3,
                  marginBottom: 6,
                }}
              />
              <div style={{ width: "70%", height: 6, background: "#E5E7EB", borderRadius: 2, marginBottom: 4 }} />
              <div style={{ width: "50%", height: 6, background: "#E5E7EB", borderRadius: 2 }} />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div
          style={{
            marginTop: "auto",
            padding: "8px 16px",
            borderTop: "1px solid #E5E7EB",
          }}
        >
          <span style={{ fontFamily: fontDisplay, fontSize: 9, color: "#999" }}>
            Powered by Niamoto
          </span>
        </div>
      </div>
    </div>
  );
};
