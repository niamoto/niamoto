import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

const loaded = Promise.all([
  // Plus Jakarta Sans — display font (frond theme)
  loadFont({
    family: "Plus Jakarta Sans",
    url: staticFile("fonts/plus-jakarta-sans/400-latin.woff2"),
    weight: "400",
  }),
  loadFont({
    family: "Plus Jakarta Sans",
    url: staticFile("fonts/plus-jakarta-sans/500-latin.woff2"),
    weight: "500",
  }),
  loadFont({
    family: "Plus Jakarta Sans",
    url: staticFile("fonts/plus-jakarta-sans/600-latin.woff2"),
    weight: "600",
  }),
  loadFont({
    family: "Plus Jakarta Sans",
    url: staticFile("fonts/plus-jakarta-sans/700-latin.woff2"),
    weight: "700",
  }),
  // JetBrains Mono — mono font
  loadFont({
    family: "JetBrains Mono",
    url: staticFile("fonts/jetbrains-mono/400-latin.woff2"),
    weight: "400",
  }),
  loadFont({
    family: "JetBrains Mono",
    url: staticFile("fonts/jetbrains-mono/500-latin.woff2"),
    weight: "500",
  }),
]);

export const fontDisplay = '"Plus Jakarta Sans", system-ui, sans-serif';
export const fontMono = '"JetBrains Mono", monospace';

export const ensureFontsLoaded = () => loaded;
