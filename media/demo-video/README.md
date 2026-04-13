# Niamoto Demo Video

Remotion project for Niamoto marketing and demo videos.

## Quick Start

```bash
cd media/demo-video
pnpm install
pnpm run dev
```

Opens the Remotion Studio at `http://localhost:3000`.

## Render

```bash
pnpm run build
```

Outputs `out/marketing-landscape.mp4` (1920x1080, 30fps).

## Structure

```
src/
  Root.tsx                       # Remotion entry — all compositions
  index.ts                       # registerRoot
  compositions/
    MarketingLandscape.tsx       # Main 16:9 marketing video
  scenes/
    IntroLogo.tsx                # Logo + tagline (3s)
    PipelineAnimated.tsx         # Problem text + Import/Transform/Export diagram
    ScreencastBlock.tsx          # Screencast wrapper with label overlay
    StatsOrMap.tsx               # Key stats animation
    OutroCTA.tsx                 # Logo + arsis.dev + GitHub
  shared/
    theme.ts                     # Frond brand colors (hex)
    fonts.ts                     # Local font loading (Plus Jakarta Sans, JetBrains Mono)
    config.ts                    # Composition dimensions, durations, fps
public/
  screencasts/                   # Screencast MP4 files (manual capture)
  music/                         # Background music track
  logo/                          # Niamoto logo PNG
  fonts/                         # Local WOFF2 fonts
```

## Adding Screencasts

Capture with ffmpeg or QuickTime, place in `public/screencasts/`:
- `01-import-flow.mp4`
- `02-transform-preview.mp4`
- `03-publish-or-site-preview.mp4`

## Theme

Based on the `frond` preset (Niamoto brand):
- Charcoal #1E1E22
- Forest Green #2E7D32
- Light Green #4BAF50
- Steel Blue #3FA9F5
