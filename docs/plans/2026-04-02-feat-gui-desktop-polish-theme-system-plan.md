---
title: "feat: GUI desktop polish — 8 new themes + animation layer"
type: feat
date: 2026-04-02
brainstorm: docs/brainstorms/2026-04-02-gui-desktop-polish-brainstorm.md
mockups: .superpowers/brainstorm/65276-1775148142/all-8-themes.html
---

# feat: GUI desktop polish — 8 new themes + animation layer

## Overview

Transform the Niamoto desktop GUI from a generic shadcn look to a polished, distinctive application. Add 8 new themes with strong visual identities (Slate, Frost, Mist, Lapis, Tidal, Basalt, Ink, Frond), integrate Framer Motion for animations, and migrate components to use theme-aware utilities.

**Brainstorm**: `docs/brainstorms/2026-04-02-gui-desktop-polish-brainstorm.md`
**Visual reference**: `.superpowers/brainstorm/65276-1775148142/all-8-themes.html`

## Current State

- 2 themes remain: Laboratory (scientific) and Forest (natural)
- 3 themes deleted: Neutral, Herbarium, Field (cleanup done)
- Default theme: `forest`
- Custom utilities defined but unused: `shadow-theme-*`, `rounded-theme-*`, `surface-glass`, `transition-theme-*`
- No animation library installed
- `ThemeStyle` union: `'classic' | 'scientific' | 'organic' | 'natural'` — needs extending

## Technical Approach

### Architecture

The existing theme system is solid — 55-token `ThemeTokens` interface, oklch color space, registry pattern, Zustand store with localStorage persistence. No architectural changes needed, only:

1. Extend the `ThemeStyle` union type for new visual categories
2. Add 8 new preset files following the exact same pattern as `forest.ts`
3. Install framer-motion and create animation wrappers
4. Migrate components from standard Tailwind classes to theme-aware utilities

### Theme Style Categories

Extend the `style` union in `src/niamoto/gui/ui/src/themes/index.ts:123`:

```typescript
// Before
style: 'classic' | 'scientific' | 'organic' | 'natural'

// After
style: 'classic' | 'scientific' | 'organic' | 'natural'
     | 'minimal' | 'vitreous' | 'cartographic' | 'editorial' | 'brand'
```

Mapping:
- **Slate** → `'minimal'`
- **Frost** → `'vitreous'`
- **Mist** → `'vitreous'`
- **Lapis** → `'classic'` (refined classic)
- **Tidal** → `'cartographic'`
- **Basalt** → `'cartographic'`
- **Ink** → `'editorial'`
- **Frond** → `'brand'`

### Implementation Phases

#### Phase 1: Frond theme (proof of concept)

The brand theme, most complex (translucent surfaces + logo colors). If this works, everything else follows.

**Tasks:**

- [ ] Extend `ThemeStyle` union in `themes/index.ts:123` — add `'minimal' | 'vitreous' | 'cartographic' | 'editorial' | 'brand'`
- [ ] Create `themes/presets/frond.ts` with full 55-token light + dark variants
  - Logo colors: charcoal `#2a2a2a`, forest green `#2d7a3a`, ocean blue `#2d8fcf`, cyan `#4bb8d4`
  - Convert all hex to oklch (e.g., `#2d7a3a` → `oklch(0.47 0.12 152)`)
  - Surfaces: translucent with `surfaceOpacity: '0.55'`, `backdropBlur: '8px'`
  - Shadows: green-tinted `oklch(0.47 0.08 152 / 0.04)`
  - Borders: near-invisible `oklch(0.47 0.06 152 / 0.05)`
  - Radius: 6-7px (refined, not playful)
  - Progress bars: green→blue gradient (CSS only, handled by chart tokens)
  - Separators: green-tinted fading (handled by border opacity)
- [ ] Register in `stores/themeStore.ts` — import + `registerTheme(frondTheme)`
- [ ] Export from `themes/index.ts` — add re-export line
- [ ] Set as default: `themeId: 'frond'` in store initial state
- [ ] Test: theme selector shows Frond, light/dark switch works, all components render correctly

**Files:**
- `src/niamoto/gui/ui/src/themes/index.ts` — extend style union
- `src/niamoto/gui/ui/src/themes/presets/frond.ts` — NEW
- `src/niamoto/gui/ui/src/stores/themeStore.ts` — register + set default

#### Phase 2: Generic themes (Slate, Frost, Mist, Lapis)

4 style-driven themes. Each follows the same 55-token pattern.

**Tasks:**

- [ ] Create `themes/presets/slate.ts`
  - Monochrome, accent bleu-ardoise `oklch(0.15 0.02 260)`
  - Tight radius: 5px
  - Micro shadows, opaque surfaces
  - `surfaceOpacity: '1'`, `backdropBlur: '0'`
- [ ] Create `themes/presets/frost.ts`
  - Translucent surfaces, backdrop blur 16px
  - Apple system blue accent `oklch(0.55 0.22 260)`
  - Glass borders: white `oklch(1 0 0 / 0.8)`
  - Radius: 8px
- [ ] Create `themes/presets/mist.ts`
  - Zero visible borders — all `oklch(... / 0.02-0.04)`
  - Layered transparency, blur 10px
  - Blue-gray accent `oklch(0.60 0.16 250)`
  - Fading gradient separators (border opacity near zero)
  - Radius: 7px
- [ ] Create `themes/presets/lapis.ts`
  - Micro-gradient surfaces (via shadow tokens layering)
  - Blue-tinted shadows: `oklch(0.30 0.06 260 / 0.07)`
  - Navy dark mode: background `oklch(0.15 0.04 240)`
  - Slate-blue text: `oklch(0.28 0.03 260)` / `oklch(0.55 0.03 260)`
  - Pill-shaped badges via `radiusFull`
  - Radius: 5px
- [ ] Register all 4 in `stores/themeStore.ts`
- [ ] Export all 4 from `themes/index.ts`
- [ ] Verify theme selector gallery displays all themes correctly

**Files:**
- `src/niamoto/gui/ui/src/themes/presets/slate.ts` — NEW
- `src/niamoto/gui/ui/src/themes/presets/frost.ts` — NEW
- `src/niamoto/gui/ui/src/themes/presets/mist.ts` — NEW
- `src/niamoto/gui/ui/src/themes/presets/lapis.ts` — NEW
- `src/niamoto/gui/ui/src/themes/index.ts` — add 4 re-exports
- `src/niamoto/gui/ui/src/stores/themeStore.ts` — add 4 imports + registrations

#### Phase 3: Cartographic themes (Tidal, Basalt, Ink)

3 themes with shared cartographic identity: dot-grid background, table-cell cards, typographic status symbols ●◐○.

**Tasks:**

- [ ] Create `themes/presets/tidal.ts`
  - Blue-slate `oklch(0.45 0.02 250)` + teal accent `oklch(0.50 0.12 195)`
  - Dot-grid: via `backgroundImage` on card slots (not in tokens — handled by CSS utility)
  - Table-cell cards: `radiusSm: '0'`, `radiusMd: '0'`, `radiusLg: '0'` (sharp corners)
  - Strong borders: `borderWidth: '1px'`, visible border color
  - No shadows: `shadowSm/Md/Lg/Xl: 'none'`
  - Dark mode: deep navy `oklch(0.12 0.03 240)`
- [ ] Create `themes/presets/basalt.ts`
  - Stone gray (Tailwind stone scale) `oklch(0.50 0.01 50)` + forest green `oklch(0.40 0.12 150)`
  - Same sharp corners and visible borders
  - Dark mode: warm dark `oklch(0.13 0.01 50)`
- [ ] Create `themes/presets/ink.ts`
  - Pure black `oklch(0.15 0 0)` / warm white `oklch(0.99 0.005 90)`
  - Zero color accent — all monochromeUnicode status symbols
  - Thick borders: `borderWidth: '1.5px'`
  - Bold weight emphasis: font-weight 700 in headings (via fontDisplay with weight hint)
  - Dark mode: inverted black/white
- [ ] Add CSS utility for dot-grid background pattern (cartographic themes)
  - Add to `tailwind-utilities.css`: `.bg-dot-grid` utility
  - Applied via `data-theme-style="cartographic"` CSS selector
- [ ] Register all 3, export, verify gallery

**Files:**
- `src/niamoto/gui/ui/src/themes/presets/tidal.ts` — NEW
- `src/niamoto/gui/ui/src/themes/presets/basalt.ts` — NEW
- `src/niamoto/gui/ui/src/themes/presets/ink.ts` — NEW
- `src/niamoto/gui/ui/src/tailwind-utilities.css` — add `.bg-dot-grid`
- `src/niamoto/gui/ui/src/themes/index.ts` — add 3 re-exports
- `src/niamoto/gui/ui/src/stores/themeStore.ts` — add 3 imports + registrations

#### Phase 4: Component polish — adopt theme-aware utilities

Migrate components from standard Tailwind to the theme-aware custom utilities that are already defined but unused.

**Tasks:**

- [ ] Audit: grep all `.tsx` files for `rounded-xl`, `rounded-lg`, `shadow-sm`, `shadow-md` — list every occurrence
- [ ] Migrate border-radius: `rounded-xl` → `rounded-theme-lg`, `rounded-lg` → `rounded-theme-md`, etc.
  - `components/ui/card.tsx` — `rounded-xl` → `rounded-theme-lg`
  - `components/ui/button.tsx` — `rounded-md` → `rounded-theme-sm`
  - `components/ui/input.tsx` — implicit radius → `rounded-theme-sm`
  - All other `components/ui/*.tsx` and `features/**/*.tsx`
- [ ] Migrate shadows: `shadow-sm` → `shadow-theme-sm`, `shadow-md` → `shadow-theme-md`
- [ ] Add `transition-theme-fast` / `transition-theme-base` to interactive components
- [ ] Apply `surface-glass` to appropriate surfaces (Frost/Mist/Frond themes benefit)
  - Popovers, dropdowns, command palette — elements that overlay content
- [ ] Add `font-display` to heading components, `font-body` to body text
- [ ] Add `font-variant-numeric: tabular-nums` to all number displays (stats, counts)
- [ ] Tighten spacing: reduce card padding from `p-6` to `p-4` on data-dense views

**Files:** Multiple across `components/ui/` and `features/`

#### Phase 5: Install Framer Motion + animation wrappers

**Tasks:**

- [ ] Install: `cd src/niamoto/gui/ui && pnpm add motion`
  - Note: `motion` is the modern package name for framer-motion (v11+)
- [ ] Create `components/motion/PageTransition.tsx`
  - Wrap route outlet with `AnimatePresence` + `motion.div`
  - Fade + subtle slide-up on page enter, fade-out on exit
  - Duration: 150-200ms, ease-out enter, ease-in exit
- [ ] Create `components/motion/CardEntrance.tsx`
  - Staggered entrance animation for card grids
  - Fade-in + scale from 0.97 → 1.0
  - Stagger: 30-50ms between cards
- [ ] Create `components/motion/LayoutTransition.tsx`
  - `motion.div` with `layout` prop for smooth sidebar collapse/expand
- [ ] Apply `PageTransition` to `MainLayout.tsx` around `<Outlet />`
- [ ] Apply `CardEntrance` to dashboard stat cards and pipeline status
- [ ] Apply `LayoutTransition` to sidebar component
- [ ] Respect `prefers-reduced-motion`: disable animations when OS setting active

**Files:**
- `src/niamoto/gui/ui/package.json` — add `motion` dependency
- `src/niamoto/gui/ui/src/components/motion/PageTransition.tsx` — NEW
- `src/niamoto/gui/ui/src/components/motion/CardEntrance.tsx` — NEW
- `src/niamoto/gui/ui/src/components/motion/LayoutTransition.tsx` — NEW
- `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx` — wrap outlet
- `src/niamoto/gui/ui/src/features/dashboard/` — apply CardEntrance

#### Phase 6: Selective magicui effects (optional)

Cherry-pick specific visual effects. Not a full magicui adoption.

**Tasks:**

- [ ] Evaluate which magicui components add value without adding bloat
  - Candidate: shimmer border on cards during loading
  - Candidate: spotlight/glow effect on card hover
  - Candidate: animated gradient text for empty states
- [ ] Install only needed components (magicui supports individual imports)
- [ ] Apply shimmer effect to skeleton loaders
- [ ] Apply spotlight hover to interactive cards (dashboard, sources list)
- [ ] Ensure effects respect theme tokens (use CSS variables, not hardcoded colors)

**Files:** TBD based on selected components

## Acceptance Criteria

### Functional Requirements

- [ ] All 10 themes (2 existing + 8 new) appear in the ThemeSwitcher gallery
- [ ] Each theme has distinct light and dark variants that are visually differentiated
- [ ] Switching themes applies all 55 tokens correctly (colors, typography, shapes, shadows, effects, animations)
- [ ] Default theme is Frond (brand theme)
- [ ] Cartographic themes (Tidal, Basalt, Ink) show dot-grid background pattern
- [ ] Page transitions animate smoothly on navigation
- [ ] Card grids use staggered entrance animation

### Non-Functional Requirements

- [ ] All color tokens use oklch format — no hex or rgb
- [ ] WCAG AA contrast (4.5:1 text, 3:1 large text) verified for all themes light + dark
- [ ] `prefers-reduced-motion` disables all Framer Motion animations
- [ ] `backdrop-filter: blur()` performance acceptable on target hardware (check CPU usage)
- [ ] No visual regression on existing Laboratory and Forest themes
- [ ] Bundle size increase from framer-motion ≤ 35KB gzip

### Quality Gates

- [ ] `pnpm build` succeeds with zero errors
- [ ] Theme switching works without page reload
- [ ] localStorage persistence works (theme survives refresh)
- [ ] Offline mode: all themes render correctly without network (fonts bundled)

## Dependencies & Prerequisites

- Theme cleanup done (Neutral, Herbarium, Field already deleted)
- Existing theme infrastructure (registry, store, CSS bridge) — no changes needed
- Local font bundling system for desktop (already in place)

## Risk Analysis & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| `backdrop-filter` performance on Linux | Medium | Benchmark; Mist/Frost/Frond can fall back to opaque with `surfaceOpacity: '1'` |
| oklch browser support | Low | Tailwind v4 handles fallbacks; all modern Chromium (Tauri's engine) supports oklch |
| Theme token count bloat (10 themes × 55 × 2 modes) | Low | Tokens are plain strings, no runtime cost; only active theme is applied |
| Framer Motion bundle size | Low | Tree-shakeable; only import used features (`motion`, `AnimatePresence`) |
| Font loading for 10 themes | Medium | Most new themes use Inter (already loaded); only Laboratory and Forest use special fonts |

## Implementation Order Recommendation

```
Phase 1 (Frond)     ─── proof of concept, validate approach
    │
Phase 2 (4 themes)  ─── Slate, Frost, Mist, Lapis in parallel
    │
Phase 3 (3 themes)  ─── Tidal, Basalt, Ink + dot-grid utility
    │
Phase 4 (polish)    ─── Component migration to theme-aware utilities
    │
Phase 5 (motion)    ─── Framer Motion integration
    │
Phase 6 (effects)   ─── Optional magicui cherry-pick
```

Phases 1-3 are theme content (can be done rapidly).
Phase 4 is the biggest impact — components actually use the theme tokens.
Phase 5-6 add animation polish.

## References

### Internal

- Theme type definitions: `src/niamoto/gui/ui/src/themes/index.ts`
- Reference preset: `src/niamoto/gui/ui/src/themes/presets/forest.ts` (217 lines, full token example)
- Theme store: `src/niamoto/gui/ui/src/stores/themeStore.ts`
- Theme switcher UI: `src/niamoto/gui/ui/src/components/theme/ThemeSwitcher.tsx`
- Custom utilities: `src/niamoto/gui/ui/src/tailwind-utilities.css`
- CSS variables bridge: `src/niamoto/gui/ui/src/index.css`

### Visual Mockups

- Final 8-theme overview: `.superpowers/brainstorm/65276-1775148142/all-8-themes.html`
- Brand themes exploration: `.superpowers/brainstorm/65276-1775148142/brand-themes.html`
- Cartographic variants: `.superpowers/brainstorm/65276-1775148142/cartographic-variants.html`
