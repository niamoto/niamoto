# GUI Desktop Polish — Brainstorm

**Date**: 2026-04-02
**Status**: Validated
**Mockups**: `.superpowers/brainstorm/65276-1775148142/`

## What We're Building

A visual refinement of the Niamoto desktop GUI to move from a generic shadcn/Radix look to a polished, distinctive desktop application — at the level of Linear, Raycast, or Notion.

**Scope**: Visual polish only. No layout changes, no new features, no restructuring.

## Why

- The current GUI uses shadcn defaults without a strong identity — it looks like "any React dashboard"
- The existing themes don't differentiate enough from each other
- The application needs to feel like a desktop app, not a web page in a wrapper
- For an ecological data platform, the visual identity should reflect the domain

## Current State (post-cleanup)

- **Deleted**: Neutral, Herbarium, Field themes (presets + imports + registrations)
- **Kept**: Laboratory, Forest (will coexist with new themes)
- **Default theme**: `forest`

## Key Decisions

### Approach: Polish Progressif

Iterative refinement in 4 layers:

1. **Framer Motion** — Page transitions, card entrance animations, spring physics on interactions
2. **CSS tokens refactoring** — Tinted shadows, near-invisible borders, micro-gradients, refined surfaces
3. **Theme system overhaul** — Add 8 new distinctive themes alongside Laboratory and Forest (10 total)
4. **magicui components** — Selective use for shimmer loading, spotlight hover, etc.

### New Theme System

Add 8 new themes alongside the 2 existing ones (Laboratory, Forest). Each new theme has a distinct visual language, not just a color swap.

All themes use **Inter** as base font (+ JetBrains Mono for monospace). All have light + dark variants.

#### Generic Themes (style-driven)

| Theme | Signature | Borders | Shadows | Surfaces |
|-------|-----------|---------|---------|----------|
| **Slate** | Monochrome, compact, sharp | Subtle rgba | Micro | Opaque |
| **Frost** | Translucent, backdrop blur, layered depth | White glass | Very light | Translucent + blur |
| **Mist** | Zero borders, transparency layers, fading separators | None | Ultra-light | Translucent + blur |
| **Lapis** | Micro-gradients, blue-tinted shadows, navy dark mode | None | Tinted blue (rgba 50,50,93) | Vertical micro-gradient |

#### Cartographic Themes (grid + table cells + typographic symbols ●◐○)

| Theme | Palette | Accent | Metaphor |
|-------|---------|--------|----------|
| **Tidal** | Blue-slate | Teal/cyan #0e7490 | Nautical chart |
| **Basalt** | Stone gray (Tailwind stone) | Forest green #166534 | Geology, rock |
| **Ink** | Pure black + warm white | None — N&B only | Ink on paper, radical |

#### Brand Theme (logo-derived)

| Theme | Signature |
|-------|-----------|
| **Frond** | Fusion of Mist style (translucent surfaces, blur, glowing dots) with Niamoto logo colors (charcoal #2a2a2a, forest green #2d7a3a, ocean blue #2d8fcf, cyan #4bb8d4). Progress bars green→blue. Separators = green-tinted fading gradients. |

### New Dependencies

| Library | Purpose | Size |
|---------|---------|------|
| **framer-motion (motion)** | Page transitions, spring physics, gesture animations, shared layout | ~30KB gzip |
| **magicui** (selective) | Shimmer borders, spotlight cards, gradient effects | Per-component |

### What Changes

- **Token layer** (`themes/presets/`): 8 new theme files added alongside laboratory.ts and forest.ts
- **CSS variables** (`index.css`, `tailwind-utilities.css`): Refined shadow/border/surface tokens
- **Component styling** (CVA variants): More subtle defaults, tighter spacing, refined hover/active states
- **Animation layer**: New Framer Motion wrappers for page/card transitions
- **ThemeStore**: Updated to register all 10 themes, default switches to `frond`

### What Doesn't Change

- Layout structure (sidebar + topbar + main content)
- Component behavior (Radix primitives stay)
- Data flow, API, routing
- Build tooling

## Design Principles (from exploration)

1. **Borders quasi-invisible**: `rgba(0,0,0,0.04-0.06)` instead of `#e5e7eb`
2. **Tinted shadows**: `rgba(50,50,93,0.07)` (Lapis) or `rgba(45,122,58,0.04)` (Frond) — not neutral gray
3. **Tighter spacing**: -20% padding on cards (14-16px instead of 20-24px)
4. **Typography**: `letter-spacing: -0.02em` on headings, `font-variant-numeric: tabular-nums` on numbers, uppercase 10-11px labels with `letter-spacing: 0.05em`
5. **Separators**: Gradient fading lines instead of solid borders (Mist/Frond style)
6. **Status indicators**: Glowing dots with `box-shadow` instead of colored pill badges
7. **Surfaces**: Translucent `rgba + backdrop-filter: blur()` where appropriate
8. **Border radius**: 5-7px (refined) instead of 12px (playful)
9. **No violet/purple**: Accent colors are blue-slate, green, or logo-derived
10. **Active nav**: Subtle background + indicator (dot or left border), not heavy highlight

## Visual References

Mockups in `.superpowers/brainstorm/65276-1775148142/`:

- `all-8-themes.html` — **Final reference**: all 8 new themes on one page, light + dark
- `current-vs-polished.html` — Before/after comparison (shadcn vs polish)
- `style-directions.html` — First 4 directions (A-D)
- `style-directions-v2.html` — 4 distinctive directions (E-H: Raycast, Stripe, Cartographic, Arc)
- `cartographic-variants.html` — Cartographic color variants (Slate&Sage, Ocean, Mineral, Ink)
- `all-themes-renamed.html` — 7 generic themes with final names
- `brand-themes.html` — 4 logo-derived themes (Fern, Canopy, Lagoon, Frond)
- `theme-candidates-v2.html` — Light + dark side-by-side comparisons

## Open Questions

- **Implementation order**: Start with Frond (brand theme) as proof of concept, or start with token refactoring (benefits all themes)?
- **magicui scope**: Which specific components to adopt? Shimmer borders on cards? Spotlight on hover?
- **Performance**: Backdrop blur can be expensive — need to benchmark on target hardware
- **Laboratory & Forest**: Keep as-is or apply polish principles to align them with the new visual language?
