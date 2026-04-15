# Niamoto Demo Video

Remotion project for Niamoto marketing video — animated motion graphics reproducing the UI.

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

Outputs `out/marketing-landscape.mp4` (1920x1080, 30fps, ~92s).

```bash
pnpm run build:teaser
```

Outputs `out/landing-teaser.mp4` (1920x1080, 30fps, ~45s).

## Type Check

```bash
pnpm exec tsc --noEmit
```

## Structure

```
src/
  Root.tsx                       # Remotion entry — all compositions
  index.ts                       # registerRoot
  compositions/
    MarketingLandscape.tsx       # Main 16:9 marketing video (TransitionSeries)
    LandingTeaser.tsx            # ~45s landing teaser composition
  teaser/                        # Dedicated teaser modules and scenes
    config.ts                    # Teaser timings and composition metadata
    copy.ts                      # Short editorial copy
    theme.ts                     # Teaser palette mirroring the real Niamoto product
    PIXEL_REFERENCES.md          # Component <-> screenshot reference table + locked decisions
    data/
      taxon-vedette.json         # Araucariaceae dataset used by widgets (3539 occurrences)
    widgets/                     # Niamoto-specific widgets rendered with recharts/react-simple-maps
    ui/                          # Simulated cursor + public site chrome
    components/                  # Shared teaser primitives (editorial overlay)
    scenes/                      # Opener, intake, structure, publish, end-card
  acts/                          # 6 acts of the user journey
    Act1Welcome.tsx              # Welcome screen + "Create New Project"
    Act2ProjectWizard.tsx        # Project creation wizard
    Act3Import.tsx               # File import + auto-configuration
    Act4Collections.tsx          # Collection cards grid
    Act5SiteBuilder.tsx          # 3-panel site builder
    Act6Publish.tsx              # Build + deploy progress
  scenes/                        # Intro, transition labels, outro
    IntroScene.tsx               # Logo + tagline
    TransitionLabel.tsx          # Contextual label between acts
    OutroScene.tsx               # Logo + URLs
  ui/                            # Mock UI components (Niamoto look)
    AppWindow.tsx                # macOS window frame + sidebar
    Sidebar.tsx                  # Navigation sidebar
    TopBar.tsx                   # Top bar with search
    MockButton.tsx               # Gradient/outline button
    MockInput.tsx                # Input with typing animation
    MockCard.tsx                 # Collection card
    MockTree.tsx                 # Page tree (site builder)
    MockPreviewPanel.tsx         # Site preview mini-layout
    FileUploadZone.tsx           # Upload drop zone
    FileTypeChip.tsx             # File type chip (CSV/vector/raster)
    ProgressBar.tsx              # Animated progress bar
    YamlPreview.tsx              # YAML code block
  animations/                    # Vendored animation primitives
    CursorFlow.tsx               # Bézier cursor with waypoints
    SpringPopIn.tsx              # Spring scale entrance
    ShimmerText.tsx              # Gradient shimmer on text
  cursor/                        # Cursor overlay system
    CursorOverlay.tsx            # Positions cursor above all content
    cursorPaths.ts               # Waypoints per act
  shared/
    theme.ts                     # Frond brand colors (hex)
    fonts.ts                     # Local font loading
    config.ts                    # Composition dimensions, durations, fps
    layout.ts                    # AppWindow, sidebar, topbar constants
    mockData.ts                  # Fake data for acts
    DESIGN_SYSTEM.md             # Visual reference for AI
public/
  logo/                          # Niamoto logo PNG
  fonts/                         # Local WOFF2 fonts
```

## Compositions

- `MarketingLandscape`: full walkthrough video for product demonstrations
- `LandingTeaser`: shorter editorial asset for landing usage

## Theme

Based on the `frond` preset (Niamoto brand):
- Charcoal #1E1E22
- Forest Green #2E7D32
- Light Green #4BAF50
- Steel Blue #3FA9F5
