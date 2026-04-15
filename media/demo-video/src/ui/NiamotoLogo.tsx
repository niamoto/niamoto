import { Img, staticFile } from "remotion";

interface NiamotoLogoProps {
  width: number;
  opacity?: number;
}

export const NiamotoLogo: React.FC<NiamotoLogoProps> = ({ width, opacity = 1 }) => {
  return (
    <Img
      src={staticFile("logo/niamoto_logo.png")}
      style={{
        width,
        height: "auto",
        objectFit: "contain",
        opacity,
      }}
    />
  );
};
