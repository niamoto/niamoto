# Design System — Niamoto Demo Video

**Project** : `media/demo-video/` (Remotion 4.0.448, React 19, 1920×1080, 30fps)
**Total duration** : ~92.5s (2775 frames) — 8 sequences with 7 transitions (15f each)

---

## 1. Visual Theme & Atmosphere

Light, airy, **data-forward** aesthetic inspired by the Niamoto frond theme — a scientific workspace that feels trustworthy without being sterile. The overall mood is **calm and precise** : neutral whites and soft greys provide breathing room, while the forest-green brand accent anchors the eye on what matters (primary actions, active states, validated outcomes). No decorative flourishes — every visual element serves to orient or reassure the viewer.

The motion language is **confident but gentle** : spring-driven entrances land softly (damping 14-15), cursor trajectories follow cubic Bézier curves, and transitions between acts use 15-frame fades to avoid visual whiplash.

---

## 2. Color Palette & Roles

### Brand

| Name | Hex | Role |
|------|-----|------|
| **Deep Forest Green** | `#2E7D32` | Primary CTA fill, active focus rings, success gradient start |
| **Vibrant Leaf Green** | `#4BAF50` | Success badges, progress-bar fill, active tree-item highlight |
| **Muted Steel Blue** | `#5B86B0` | Sidebar active chip background, preview header gradient end, accent |
| **Charcoal** | `#1E1E22` | Reserved for dark accents (traffic-light titlebar aside, logo fallback) |

### Surfaces (light frond)

| Name | Hex | Role |
|------|-----|------|
| **Cloud Canvas** | `#F5F6F8` | Page/video background — the base canvas |
| **Pearl Light** | `#FBFCFD` | Window interior fallback |
| **Window Interior** | `#FCFDFE` | AppWindow body + TopBar background |
| **Titlebar Mist** | `#F7F8FA` | macOS titlebar stripe |
| **Sidebar Fog** | `#F2F4F7` | Sidebar column |
| **Sidebar Hover** | `#EAEEF3` | Inactive nav-item hover (unused in video but available) |
| **Card White** | `#FFFFFF` | Elevated cards, form panels |
| **Subtle Surface** | `#F6F7F9` | Recessed mock widgets in Site Builder editor |
| **Muted Surface** | `#EEF2F5` | Canvas gradient end, secondary fill |

### Text

| Name | Hex | Role |
|------|-----|------|
| **Ink Slate** | `#111827` | Body text, labels, input values |
| **Ink Graphite** | `#1E293B` | Legacy "textWhite" token — used where a slightly softer ink reads better |
| **Stone Grey** | `#667085` | Secondary text, muted labels, inactive nav labels |
| **Pebble Grey** | `#98A2B3` | Placeholder text, tertiary copy |
| **Snow** | `#FFFFFF` | Text on primary CTA (`textOnPrimary`) |

### Borders & Semantic

| Name | Value | Role |
|------|-------|------|
| **Border Default** | `rgba(208, 213, 221, 0.78)` | Standard 1px dividers |
| **Border Strong** | `rgba(208, 213, 221, 1)` | Input rings, card outlines |
| **Window Shadow** | `0 16px 44px rgba(15, 23, 42, 0.12)` | AppWindow elevation |
| **Success** | `#4BAF50` | Published badge, step-complete dots |
| **Warning** | `#F2B94B` | "Stale" status badges |
| **Danger** | `#E85D5D` | Error states |

### FileTypeChip palette (Act 3)

| Type | Hex | Extensions |
|------|-----|------------|
| **Tabular data** | `#3FA9F5` (legacy steel blue) | `.csv` |
| **Spatial data** | `#4BAF50` | `.gpkg`, `.geojson` |
| **Raster data** | `#9333EA` (amethyst) | `.tif` |

### macOS Traffic Lights

`#FF5F57` (red) · `#FEBC2E` (yellow) · `#28C840` (green) — 12px circles, 8px gap.

---

## 3. Typography Rules

Two families — one for UI, one for code.

- **Plus Jakarta Sans** (display) — weights 400, 500, 600, 700. Friendly geometric sans with generous counters. Used for every label, headline, button, and nav item. Loaded via `@remotion/fonts` from `public/fonts/plus-jakarta-sans/*.woff2`.
- **JetBrains Mono** (code) — weights 400, 500. Used exclusively for paths (`~/projects/my-ecology-project`), YAML content, and domain names displayed as URLs.

### Scale (observed from the codebase)

| Size | Usage |
|------|-------|
| 56 / 700 | Act 1 hero logotype ("Niamoto") |
| 42 / 700 | Legacy gradient hero (unused in final composition) |
| 32 / 700 | Act 2 wizard title "Créer un nouveau projet" |
| 28 / 700 | MockCard count numbers |
| 24 / 500 | TransitionLabel pill text |
| 22 / 700 | Act headers ("Import Data", "Collections", "Publish Site") |
| 20 / 600 | ShimmerText "Auto-configuration…" |
| 18 / 700 | Site Builder editor section title |
| 17 / 500-600 | Wizard field labels, MockCard name |
| 16 / 400-500 | Buttons, tagline, editor body |
| 15 / 500-600 | Input values, mock widget labels |
| 14 / 400-500 | Sidebar labels, card subtitle, descriptions |
| 13 / 400-500 | TopBar search, YAML code, editor fields |
| 12 / 500-600 | Section headers ("PAGES", "PREVIEW"), status badges |
| 11 / 500 | Stat labels, keyboard hints (⌘K) |
| 9 / 400 | Browser chrome URL, "Powered by Niamoto" footer |

Letter-spacing stays at `0` everywhere **except** for two cases : hero logotype (`-1.5`), wizard title (`-0.8`) — subtle negative tracking to tighten display type.

---

## 4. Component Stylings

### AppWindow

macOS-style container with gently rounded corners (`borderRadius: 12`), a 1px `borderStrong` outline and the **Window Shadow** elevation. Body is **Window Interior** (`#FCFDFE`). Titlebar is a 32px **Titlebar Mist** stripe with traffic lights left-aligned (56,46) and an optional centered title in **Stone Grey**. Props: `showSidebar`, `showTopBar`, `activeSidebarItem`, `title`, `sidebarSlideInDuration` (default 20 frames). The sidebar width interpolates from 0 to `LAYOUT.sidebar.width` (200px) over the slide-in window.

### Sidebar

200px column on **Sidebar Fog** (`#F2F4F7`). Header is a white "project picker" pill (truncated project name + chevron) on a 0.68 white with **Border Default**. Five nav items (Home/Data/Collections/Site/Publish), each with an 18px SVG icon. Active item : **Sidebar Active** chip (`#5B86B0`) with white text and weight 600. Inactive items stay on **Stone Grey** (`#667085`). Footer holds the `⌘K` hint and a "Paramètres" row with a soft `+` chip. All rows use `borderRadius: 9`.

### TopBar

48px bar on **Window Interior**. Left: a subtle sidebar-toggle icon (stylized column). Right-aligned: search field (`rgba(255,255,255,0.94)`, `borderRadius: 10`, width 330, **Border Default**) with magnifier glyph, "Search…" placeholder in **Stone Grey**, and a `⌘K` keycap chip. Far right: a bell and a help icon (16px, Stone Grey / Ink Slate).

### MockButton

Three variants, all `borderRadius: 8`, padding `12px 28px`, 15/600:

- **Gradient** (primary): `linear-gradient(180deg, lightGreen → forestGreen)`, white text, soft green-tinted shadow (`0 10px 24px rgba(46, 125, 50, 0.18)`).
- **Outline**: near-white (`rgba(255,255,255,0.96)`) surface, ink text, 1px **Border Strong**.
- **Default**: `cardDark` (now white) with soft **Border Default**.

Click springs (`damping 12, stiffness 200, mass 0.5`) scale from 0.92 → 1 when `clickAtFrame` is reached.

### MockInput

Vertical stack (6px gap) with a **Stone Grey** 13/500 label. Field: `rgba(255,255,255,0.96)` on 1px **Border Strong**, `borderRadius: 8`, 10/14 padding. Value in Ink Slate (mono when `mono` prop is set). Typing reveal via `text.substring(0, revealedCount)` — blinking 2px cursor in **accent** colour (now steelBlue) every 15 frames once typing is done.

### MockCard

Elevated rectangle on **Card White** with 1px subtle border and `borderRadius: 7`. 20px padding, 14px gap between rows. Rows: (1) name + status chip, (2) large 28/700 count + "records" suffix, (3) divider + two stats. Status chips are pill-shaped (padding 3/10, 11/500), tinted at 9% of the status colour (Leaf Green / Amber / Danger). Entrance is wrapped in `SpringPopIn` staggered 0.3s apart.

### FileTypeChip

Pill-shaped (`borderRadius: 20`), padding `6px 14px`, 8px gap. Background uses the type colour at `~10%` opacity (`${color}18`), border at `~25%` (`${color}40`). Left: 8px circular dot in the type colour. Label is 13/500 in the type colour; extensions list is 11/400 in the same colour at `~60%` opacity. Slides in from the left (-30px → 0) with a 15-frame opacity fade.

### FileUploadZone

Dashed outline (`2px dashed rgba(255,255,255,0.15)`) with `borderRadius: 12`, centered Upload glyph, empty-state text in **Stone Grey**. When the `filesEnterFrame` milestone is crossed, padding collapses and the zone accepts child content (the FileTypeChips list). Background shifts from `rgba(255,255,255,0.03)` to `0.02` to signal "filled". *Note : the zone was designed against the original dark theme — on the current light theme its dashed ring reads subtly; could be retuned.*

### YamlPreview

Dark scientific-notebook plate (`#16161A`) with `borderRadius: 10` and a soft top divider. Header bar shows `import.yml` in 11px **Stone Grey**. Code uses JetBrains Mono 13 at line-height 1.7. Simple syntax highlighting: **keys → Vibrant Leaf Green**, **values → Muted Steel Blue (legacy #3FA9F5)**, **colons → Stone Grey**. Enters with a 30px upward slide + opacity fade over 20 frames.

### ProgressBar

Two parts: (1) a 6px-tall track (**Card White**-on-dark `cardDark` — visually white now) with rounded ends; fill is `linear-gradient(90deg, forestGreen → lightGreen)` driven by `Easing.out(Easing.cubic)`. (2) Optional step list (8px row gap) with 16px circular indicators: complete → green filled check, active → green outline ring, pending → grey dot.

### MockTree

Compact hierarchical list, 1px row gap. Per-item padding `5px 8px`, indented 18px per depth level. Each row: chevron (collections only) + type icon + 13/400 label. Active item gets a subtle `rgba(75, 175, 80, 0.1)` background and label switches to **Leaf Green / 600**. Items fade in staggered (4 frames per item) once `expandAtFrame` is reached.

### MockPreviewPanel

A "mini-browser" simulation of a published Niamoto site. Top: 28px chrome bar in `#E8E8EC` with three grey dots and a white URL pill showing `my-ecology-project.niamoto.io`. Body: header band with `linear-gradient(135deg, forestGreen → #26A69A)` + 14/700 title in white, a 2×2 grid of white placeholder cards (boxShadow `0 1px 3px rgba(0,0,0,0.08)`), footer divider + "Powered by Niamoto" 9px caption. Supports an array of `transitions: [{atFrame, title}]` — each transition cross-fades between the outgoing and incoming layout over 15 frames.

### TransitionLabel

Pill-shaped contextual label appearing in the **first 30 frames** of Acts 3, 5 and 6. Centered near the top (72px from the top), padded `10px 18px`, `borderRadius: 999`. Background `rgba(30, 30, 34, 0.84)` with a thin light-alpha border and a soft drop shadow. Text is 24/500 in **Stone Grey** with `letterSpacing: 0.5`. Fade-in 10f → hold → fade-out 10f.

### NiamotoLogo

Vector-built logotype (see `ui/NiamotoLogo.tsx`). Used at 112px in Act 1 hero and 96px in the Act 2 wizard card. Renders crisply at any scale — no raster asset needed.

---

## 5. Layout Principles

- **Canvas** : fixed at **1920×1080**. All coordinates assume that frame.
- **AppWindow frame** : inset 40px left/right, 30px top, 30px bottom (1840×1020). `borderRadius: 12`, shadow as specified.
- **Titlebar** : 32px. Traffic lights at `(x=56, y=46)` — relative to canvas.
- **Sidebar** : 200px wide when visible. Animated slide-in (width 0 → 200) over 20 frames when `showSidebar` becomes true.
- **TopBar** : 48px tall when visible.
- **Content region** : the remaining area inside the AppWindow body, minus sidebar and topbar. Padding is 28px horizontal / 28px top by default.
- **Vertical rhythm** : 8px base unit. Common gaps: 6/8/10/12/16/20/24/28 px.
- **Site Builder panels** : 20% / 50% / 30% split, each separated by a 1px **Border Default** divider.
- **Cursor coordinates** : defined **in canvas space** (not window-relative). See `cursor/cursorPaths.ts`.

---

## 6. Depth & Elevation

Layering is flat but deliberate. Shadows are *whisper-soft* — never dominant — and used only to lift elevated surfaces from the canvas.

| z-index | Layer |
|---------|-------|
| `0` | Canvas (page background gradient) |
| `1` | AppWindow body content |
| `2` | Sidebar (stays at natural stacking inside the window) |
| `3` | TopBar (natural stacking) |
| `4` | Modal cards (e.g. Act 2 wizard — uses scale + opacity instead of a z-index shift) |
| `50` | TransitionLabel pill |
| `100` | CursorOverlay (always on top) |

Shadows in use:

- **AppWindow** : `0 16px 44px rgba(15, 23, 42, 0.12)` — primary elevation
- **Wizard card (Act 2)** : `0 12px 28px rgba(15, 23, 42, 0.06)` — secondary elevation
- **Welcome action card (primary)** : `0 14px 34px rgba(46, 125, 50, 0.18)` — green-tinted halo
- **Welcome action card (secondary)** : `0 8px 24px rgba(15, 23, 42, 0.06)`
- **Preview panel inner cards** : `0 1px 3px rgba(0,0,0,0.08)` — hairline elevation
- **Gradient buttons** : `0 10px 24px rgba(46, 125, 50, 0.18)` — matches the primary CTA halo
- **Input fields** : `0 1px 2px rgba(15, 23, 42, 0.03)` — barely perceptible lift
- **TransitionLabel** : `0 10px 30px rgba(0,0,0,0.22)` — the only darker shadow, because the label floats on top of variable content

---

## 7. Do's and Don'ts

### Do

- ✅ Use `spring()` for discrete entrances (cards, buttons, logos appearing).
- ✅ Use `interpolate()` for progressions (typing, progress bars, opacity fades, cross-fades).
- ✅ Always pass `extrapolateLeft: "clamp"` **and** `extrapolateRight: "clamp"` to `interpolate()`.
- ✅ Reveal text via `text.substring(0, revealedCount)` — never per-character opacity.
- ✅ Drive click feedback from frame, not from event handlers (`clickAtFrame` prop pattern).
- ✅ Use generic ecological mock data (`MOCK_COLLECTIONS`, `MOCK_YAML`) — no NC-specific place or species names.
- ✅ Wrap costly scenes in `<Sequence>` at the composition level for isolation.
- ✅ Block render on font load via `delayRender` / `continueRender` + `ensureFontsLoaded()`.

### Don't

- ❌ Never use CSS `@keyframes`, `transition`, or `animation`.
- ❌ Never adjacent-pair `TransitionSeries.Overlay` with a `TransitionSeries.Transition` — use a `<Sequence>` inside the act instead.
- ❌ Never use `pnpm build` as a typecheck — it triggers a render. Run `pnpm exec tsc --noEmit` instead.
- ❌ Never hardcode cursor coordinates inline in act components — add them to `cursor/cursorPaths.ts`.
- ❌ Never import from `src/niamoto/gui/ui` — the video must stay fully self-contained.
- ❌ Never introduce raster assets for UI chrome — everything is SVG or DOM primitives.

---

## 8. Scene Inventory

| # | Scene | Duration | AppWindow | Sidebar active | Key components | Primitives |
|---|-------|----------|-----------|----------------|----------------|------------|
| 0 | IntroLogo | 4s | — | — | NiamotoLogo (raster img), tagline | `spring`, `interpolate` |
| 1 | Act1Welcome | 8s | no chrome | — | `NiamotoLogo`, 2 × WelcomeActionCard, toggle row | `spring`, `interpolate`, `CursorOverlay` |
| 2 | Act2ProjectWizard | 12s | no chrome | — | `NiamotoLogo`, card with 2 × MockInput, 2 × WizardButton | `spring`, `interpolate`, `CursorOverlay` |
| 3 | Act3Import | 20s | with chrome | Data | `FileUploadZone`, `FileTypeChip × 3`, `ShimmerText`, `YamlPreview`, `TransitionLabel` | `spring`, `interpolate`, `Sequence` |
| 4 | Act4Collections | 14s | with chrome | Collections | `MockCard × 3` | `SpringPopIn`, `CursorOverlay` |
| 5 | Act5SiteBuilder | 20s | with chrome | Site | `MockTree`, editor fields, `MockPreviewPanel`, `TransitionLabel` | `interpolate`, `Sequence`, cross-fade |
| 6 | Act6Publish | 12s | with chrome | Publish | `MockButton`, 2 × `ProgressBar`, Published badge, `TransitionLabel` | `spring`, `interpolate`, `Sequence` |
| 7 | OutroCTA | 6s | — | — | Logo, arsis.dev, GitHub URL | `spring`, `interpolate` |

**Transitions** : 7 total, 15 frames each.
- Intro → Act1 → Act2 : `fade`
- **Act2 → Act3 : `slide({ direction: "from-right" })`** — unique moment, signals workspace reveal
- Act3 → Act4 → Act5 → Act6 → Outro : `fade`

**Cursor paths** live in `cursor/cursorPaths.ts`, keyed per act. Coordinates are in canvas space.

---

## 9. Agent Prompt Guide

When asking an AI agent to modify or regenerate a scene, follow this template :

```
Modify <Act N> in media/demo-video/src/acts/ActNName.tsx.

Constraints:
- Duration stays at <N>s — do not change DURATIONS in config.ts unless explicitly asked.
- Use only interpolate() and spring() — NEVER CSS @keyframes / transition / animation.
- Always pass extrapolateLeft + extrapolateRight: "clamp" to interpolate().
- Respect the design tokens in src/shared/theme.ts — do not introduce new hex values.
- Respect typography: Plus Jakarta Sans (display) + JetBrains Mono (code only).
- Respect the layout constants in src/shared/layout.ts — do not redefine window / sidebar sizes.
- If you need a new mock value, add it to src/shared/mockData.ts (generic ecological data only).
- Keep cursor waypoints in cursor/cursorPaths.ts — do not inline them.
- Validate with: cd media/demo-video && pnpm exec tsc --noEmit
- Preview in Studio: pnpm dev → open http://localhost:3000
```

### Recipes

- **Add a new UI primitive** → create `ui/<Name>.tsx` following the pattern of `MockCard` or `MockButton` : named `React.FC`, takes props, pure interpolate/spring, no side effects, no events.
- **Add a new animation primitive** → add to `animations/` with a 30-80 line component, export a clean interface, zero CSS animations, always read `useCurrentFrame()` and `useVideoConfig()`.
- **Adjust timing** → modify `DURATIONS` in `shared/config.ts`. The total frame count is recomputed automatically ; `TRANSITION_COUNT` in the same file assumes 7 transitions.
- **Adjust cursor path** → edit `cursor/cursorPaths.ts`. Coordinates are canvas-space. `hold` is in frames. `click: true` triggers the ripple + scale spring inside `CursorFlow`.
- **Render final MP4** → `npx remotion render MarketingLandscape --output=out/niamoto-demo.mp4` from `media/demo-video/`.

---

*Generated 2026-04-14 — reflects the state of `feat/demo-video` after Phase 4.*
