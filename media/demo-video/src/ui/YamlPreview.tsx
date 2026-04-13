import { useCurrentFrame, interpolate } from "remotion";
import { fontMono } from "../shared/fonts";
import { theme } from "../shared/theme";

interface YamlPreviewProps {
  yaml: string;
  enterAtFrame?: number;
}

/**
 * YAML code block with simplified syntax highlighting.
 * Slides up on entry.
 */
export const YamlPreview: React.FC<YamlPreviewProps> = ({
  yaml,
  enterAtFrame = 0,
}) => {
  const frame = useCurrentFrame();

  const progress = interpolate(frame, [enterAtFrame, enterAtFrame + 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(progress, [0, 1], [30, 0]);
  const opacity = progress;

  // Simple YAML syntax highlighting
  const highlightLine = (line: string) => {
    // Key: value pattern
    const keyMatch = line.match(/^(\s*)([\w_]+)(:)(.*)/);
    if (keyMatch) {
      const [, indent, key, colon, value] = keyMatch;
      return (
        <>
          <span>{indent}</span>
          <span style={{ color: theme.lightGreen }}>{key}</span>
          <span style={{ color: theme.textMuted }}>{colon}</span>
          <span style={{ color: value.trim() ? theme.steelBlue : theme.textWhite }}>
            {value}
          </span>
        </>
      );
    }
    return <span style={{ color: theme.textWhite }}>{line}</span>;
  };

  const lines = yaml.split("\n");

  return (
    <div
      style={{
        background: "#16161A",
        borderRadius: 10,
        padding: "16px 20px",
        fontFamily: fontMono,
        fontSize: 13,
        lineHeight: 1.7,
        transform: `translateY(${translateY}px)`,
        opacity,
        border: "1px solid rgba(255,255,255,0.06)",
        overflow: "hidden",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 12,
          paddingBottom: 10,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <span style={{ fontSize: 11, color: theme.textMuted }}>import.yml</span>
      </div>
      {/* Code lines */}
      {lines.map((line, i) => (
        <div key={i} style={{ whiteSpace: "pre" }}>
          {highlightLine(line)}
        </div>
      ))}
    </div>
  );
};
