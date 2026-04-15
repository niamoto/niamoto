import { fontDisplay } from "../../shared/fonts";

type EditorialOverlayAlign = "top-left" | "top-right" | "bottom-left";

interface EditorialOverlayProps {
  eyebrow: string;
  title: string;
  description: string;
  align?: EditorialOverlayAlign;
  width?: number;
  opacity?: number;
  offsetY?: number;
}

const getPositionStyle = (align: EditorialOverlayAlign): React.CSSProperties => {
  switch (align) {
    case "top-right":
      return { top: 74, right: 74 };
    case "bottom-left":
      return { bottom: 74, left: 74 };
    case "top-left":
    default:
      return { top: 74, left: 74 };
  }
};

export const EditorialOverlay: React.FC<EditorialOverlayProps> = ({
  eyebrow,
  title,
  description,
  align = "top-left",
  width = 380,
  opacity = 1,
  offsetY = 0,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        width,
        padding: "18px 20px 18px",
        borderRadius: 18,
        background: "rgba(255,255,255,0.96)",
        border: "1px solid rgba(208, 213, 221, 0.6)",
        boxShadow: "0 2px 4px rgba(17,24,39,0.12), 0 16px 32px rgba(17,24,39,0.06), 0 32px 64px rgba(17,24,39,0.04)",
        opacity,
        transform: `translateY(${offsetY}px)`,
        ...getPositionStyle(align),
      }}
    >
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: 0.3,
          textTransform: "uppercase",
          color: "#5B86B0",
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          marginTop: 10,
          fontFamily: fontDisplay,
          fontSize: 28,
          lineHeight: 1.1,
          fontWeight: 700,
          color: "#111827",
        }}
      >
        {title}
      </div>
      <div
        style={{
          marginTop: 10,
          fontFamily: fontDisplay,
          fontSize: 15,
          lineHeight: 1.45,
          color: "#475467",
        }}
      >
        {description}
      </div>
    </div>
  );
};
