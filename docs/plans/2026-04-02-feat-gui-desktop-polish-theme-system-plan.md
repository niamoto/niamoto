---
title: "feat: GUI desktop polish — theme expansion + motion polish"
type: feat
date: 2026-04-02
brainstorm: docs/brainstorms/2026-04-02-gui-desktop-polish-brainstorm.md
mockups: .superpowers/brainstorm/65276-1775148142/all-8-themes.html
---

# feat: GUI desktop polish — theme expansion + motion polish

## Overview

Evolve the Niamoto desktop GUI from a generic shadcn baseline to a more distinctive product surface.

This plan adds 8 new desktop themes with clear visual identities, introduces a small motion layer, and migrates the most visible shell components to theme-aware utilities already present in the codebase.

The plan is intentionally constrained:

- it keeps the existing theme architecture
- it preserves persisted user choices
- it treats offline desktop font loading as a first-class requirement
- it avoids broad, hard-to-review styling churn
- it keeps experimental visual effects out of the critical path

**Brainstorm**: `docs/brainstorms/2026-04-02-gui-desktop-polish-brainstorm.md`
**Visual reference**: `.superpowers/brainstorm/65276-1775148142/all-8-themes.html`

## Goals

- Add 8 new themes: Slate, Frost, Mist, Lapis, Tidal, Basalt, Ink, Frond
- Make Frond the default for fresh installs and missing/invalid saved theme ids
- Keep existing saved theme preferences intact for current users
- Ensure the ThemeSwitcher gallery fully supports the new style categories
- Apply theme-aware radius, shadow, font, and surface utilities to the most visible desktop surfaces
- Add subtle page and card animations that respect reduced-motion preferences

## Explicit Non-Goals

- No full visual refactor of every screen in one pass
- No global spacing rewrite such as blanket `p-6 -> p-4`
- No sidebar motion rewrite beyond the existing CSS width transition
- No magicui adoption in this plan
- No new font families unless they are also bundled for offline desktop mode

## Current State

- 2 themes remain: Laboratory and Forest
- 3 old themes were already deleted: Neutral, Herbarium, Field
- Default fresh state is still `forest` in the store
- Theme choice is persisted in localStorage under `niamoto-theme`
- Desktop mode does not use Google Fonts directly; it loads `public/fonts/fonts.css`
- `ThemeSwitcher` currently assumes exactly 4 style categories and hardcodes their labels and preview ornaments
- Theme-aware utilities already exist in `tailwind-utilities.css` but are only partially adopted
- No motion library is installed in the frontend package

## Technical Approach

### Architecture

The existing architecture is good enough and should remain:

- `ThemeTokens` remains the single theme contract
- the registry pattern remains unchanged
- `applyTheme()` remains the only place where tokens become CSS variables
- Zustand persistence remains the storage mechanism for theme and mode

The work is split into 5 implementation phases:

1. Foundation and guardrails
2. New theme presets
3. ThemeSwitcher and shell polish
4. Motion layer
5. Verification and hardening

### Theme Style Categories

Extend `ThemeMetadata.style` in `src/niamoto/gui/ui/src/themes/index.ts`:

```typescript
// Before
style: 'classic' | 'scientific' | 'organic' | 'natural'

// After
style:
  | 'classic'
  | 'scientific'
  | 'organic'
  | 'natural'
  | 'minimal'
  | 'vitreous'
  | 'cartographic'
  | 'editorial'
  | 'brand'
```

Mapping:

- Slate -> `minimal`
- Frost -> `vitreous`
- Mist -> `vitreous`
- Lapis -> `classic`
- Tidal -> `cartographic`
- Basalt -> `cartographic`
- Ink -> `editorial`
- Frond -> `brand`

This extension must be implemented together with `ThemeSwitcher`, not before it.

### Default Theme Migration Strategy

The default-theme behavior must distinguish fresh installs from existing saved preferences.

Rules:

- if there is no persisted theme, use `frond`
- if a persisted theme id exists and is valid, preserve it
- if a persisted theme id exists but is invalid or removed, fall back to `frond`
- do not forcibly migrate existing `forest` users to `frond`

This avoids a silent preference reset for current users while still making Frond the new default experience.

### Font Strategy

Desktop mode is offline-first and loads fonts from `public/fonts/fonts.css`, not from `fontsUrl`.

Because of that, each new theme must follow one of these two paths:

1. Preferred: reuse a font family already bundled locally
2. Allowed only if needed: add the new font family to `public/fonts/fonts.css` and the matching font assets under `public/fonts/`

The plan should prefer the first option unless a new family is essential to the theme identity.

### Cartographic Background Strategy

The cartographic dot-grid must not be applied globally to the whole app.

Instead:

- add a utility or selector for an opted-in surface treatment
- apply it only to selected cards/panels where the pattern improves hierarchy
- scope activation to cartographic themes through `data-theme-style="cartographic"`

This keeps the effect intentional and avoids making dense screens noisy.

## Implementation Phases

### Phase 1: Foundation and Guardrails

**Tasks**

- [ ] Extend `ThemeMetadata.style` in `src/niamoto/gui/ui/src/themes/index.ts`
- [ ] Update `src/niamoto/gui/ui/src/components/theme/ThemeSwitcher.tsx`
  - add labels for all new style categories
  - add preview ornaments for `minimal`, `vitreous`, `cartographic`, `editorial`, and `brand`
  - verify TypeScript exhaustiveness on `Record<Theme['style'], ...>`
- [ ] Update `src/niamoto/gui/ui/src/stores/themeStore.ts`
  - set `frond` as the default fresh theme id
  - preserve valid persisted theme ids
  - add fallback to `frond` when the persisted id is missing or no longer registered
- [ ] Audit desktop offline font inventory against the planned themes
  - decide which existing bundled families are reused
  - explicitly list any new families that would require asset bundling
- [ ] Add at least one targeted frontend test for theme fallback behavior

**Files**

- `src/niamoto/gui/ui/src/themes/index.ts`
- `src/niamoto/gui/ui/src/components/theme/ThemeSwitcher.tsx`
- `src/niamoto/gui/ui/src/stores/themeStore.ts`
- `src/niamoto/gui/ui/public/fonts/fonts.css` if new families are introduced

### Phase 2: Add New Theme Presets

Create 8 new presets, each with complete light and dark variants and full token coverage.

**Themes**

- [ ] `themes/presets/frond.ts`
- [ ] `themes/presets/slate.ts`
- [ ] `themes/presets/frost.ts`
- [ ] `themes/presets/mist.ts`
- [ ] `themes/presets/lapis.ts`
- [ ] `themes/presets/tidal.ts`
- [ ] `themes/presets/basalt.ts`
- [ ] `themes/presets/ink.ts`

**Tasks**

- [ ] Register all new themes in `src/niamoto/gui/ui/src/stores/themeStore.ts`
- [ ] Re-export all new themes from `src/niamoto/gui/ui/src/themes/index.ts`
- [ ] Keep all color tokens in `oklch(...)`
- [ ] Keep token semantics honest: no fake gradients or patterns encoded into unrelated tokens
- [ ] Reuse bundled fonts whenever possible

**Theme notes**

- Frond: brand-led desktop default, soft translucency, restrained green/blue accents
- Slate: minimal, opaque, monochrome desktop utility theme
- Frost: higher-blur glass theme with crisp borders
- Mist: softer glass theme with weaker boundaries
- Lapis: refined blue classic theme
- Tidal: cool cartographic theme with sharp structure
- Basalt: warmer cartographic theme with stronger earth tones
- Ink: editorial monochrome theme with assertive contrast

### Phase 3: Theme-Aware Utility Adoption and Shell Polish

Focus on the shell and shared UI primitives first. Do not try to restyle the entire product in one pass.

**Tasks**

- [ ] Audit current usages of `rounded-*`, `shadow-*`, and local font classes in high-visibility components
- [ ] Migrate core shared components to theme-aware utilities where it materially improves consistency
  - `components/ui/card.tsx`
  - `components/ui/button.tsx`
  - `components/ui/input.tsx`
  - `components/ui/dropdown-menu.tsx`
  - `components/ui/dialog.tsx`
  - `components/layout/*`
  - `components/theme/ThemeSwitcher.tsx`
- [ ] Apply `surface-glass` only to overlays and elevated surfaces that benefit from it
  - dropdowns
  - popovers
  - dialogs
  - command palette
- [ ] Use `font-display` and `font-body` where it strengthens hierarchy without reducing readability
- [ ] Add tabular numerals only to numeric UI where alignment matters
- [ ] Add cartographic dot-grid styling only to explicitly selected surfaces under cartographic themes

**Do not do in this phase**

- blanket spacing compression across the app
- opportunistic restyling of every feature screen
- hardcoded theme exceptions inside feature code

### Phase 4: Motion Layer

Use `motion` for subtle, product-level motion polish.

**Tasks**

- [ ] Install `motion`
- [ ] Create `components/motion/PageTransition.tsx`
  - wrap routed page content, not the entire shell
  - use short fade/translate transitions
- [ ] Create `components/motion/CardEntrance.tsx`
  - use staggered entrances for dashboard/onboarding card groups
- [ ] Respect `prefers-reduced-motion`
- [ ] Keep the sidebar on existing CSS transitions for now

**Not in scope**

- no `LayoutTransition` wrapper for the sidebar in this phase
- no animation of every list in the application

**Files**

- `src/niamoto/gui/ui/package.json`
- `src/niamoto/gui/ui/src/components/motion/PageTransition.tsx`
- `src/niamoto/gui/ui/src/components/motion/CardEntrance.tsx`
- `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`
- targeted dashboard/onboarding components

### Phase 5: Verification and Hardening

**Tasks**

- [ ] Verify ThemeSwitcher displays all 10 themes correctly
- [ ] Verify all 10 themes in light and dark modes
- [ ] Verify persisted theme preference survives refresh
- [ ] Verify missing or removed theme ids fall back to `frond`
- [ ] Verify desktop mode works offline with the selected font families
- [ ] Verify cartographic themes only affect intended surfaces
- [ ] Verify reduced-motion disables motion wrappers
- [ ] Verify blur-heavy themes on desktop hardware for acceptable responsiveness
- [ ] Run a contrast check for text and key interactive surfaces

## Acceptance Criteria

### Functional Requirements

- [ ] All 10 themes appear in the ThemeSwitcher gallery
- [ ] ThemeSwitcher supports all style categories without TypeScript gaps or placeholder fallbacks
- [ ] Each new theme has distinct light and dark variants
- [ ] Fresh installs and users without a saved preference default to `frond`
- [ ] Existing valid saved preferences are preserved
- [ ] Invalid or removed saved theme ids fall back to `frond`
- [ ] Theme switching applies all tokens without reload
- [ ] Cartographic themes expose the dot-grid treatment only on opted-in surfaces
- [ ] Page transitions and card entrances animate smoothly

### Non-Functional Requirements

- [ ] All theme color tokens use `oklch(...)`
- [ ] Desktop offline mode renders all theme fonts correctly
- [ ] `prefers-reduced-motion` disables motion behavior
- [ ] Existing Laboratory and Forest themes remain visually valid
- [ ] Added motion dependency remains modest in bundle impact
- [ ] Blur-heavy themes remain acceptable on desktop target hardware

### Quality Gates

- [ ] `pnpm build` succeeds
- [ ] Relevant frontend tests succeed
- [ ] Manual verification completed in both browser and Tauri desktop mode
- [ ] No regression in theme persistence or shell layout behavior

## Dependencies and Prerequisites

- Existing theme registry, CSS variable bridge, and store remain in place
- Existing local desktop font bundling remains the source of truth for offline mode
- New themes must either reuse already bundled font families or explicitly extend the bundled font set

## Risk Analysis and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Persisted users do not receive Frond | Low | Treat this as intentional preference preservation, not a bug |
| New themes reference fonts unavailable offline | High | Audit font inventory in Phase 1 and block theme completion until desktop assets are aligned |
| ThemeSwitcher breaks after style union expansion | High | Update style labels and preview rendering in the same phase as the type change |
| Cartographic pattern makes dense screens noisy | Medium | Restrict it to opted-in surfaces, not global backgrounds |
| Blur-heavy themes degrade desktop performance | Medium | Test Frost, Mist, and Frond early and fall back to more opaque surfaces if needed |
| Motion conflicts with existing shell transitions | Medium | Limit motion to routed content and card groups; keep sidebar on CSS transitions |

## Implementation Order Recommendation

```text
Phase 1  Foundations and guardrails
    │
Phase 2  Theme preset creation
    │
Phase 3  Theme-aware shell polish
    │
Phase 4  Motion layer
    │
Phase 5  Verification and hardening
```

Recommended delivery slices:

1. Frond + migration + ThemeSwitcher support
2. Remaining 7 themes
3. Shared shell polish
4. Motion layer
5. Hardening and contrast/offline verification

## Follow-Up Work

These are valid ideas, but they should not block this plan:

- selective loading shimmer effects
- spotlight hover treatments
- additional decorative empty-state effects
- a later second pass on feature-level spacing and density

If pursued later, they should live in a separate polish plan after the theme system is stable.

## References

### Internal

- Theme type definitions: `src/niamoto/gui/ui/src/themes/index.ts`
- Reference presets: `src/niamoto/gui/ui/src/themes/presets/laboratory.ts`, `src/niamoto/gui/ui/src/themes/presets/forest.ts`
- Theme store: `src/niamoto/gui/ui/src/stores/themeStore.ts`
- Theme switcher UI: `src/niamoto/gui/ui/src/components/theme/ThemeSwitcher.tsx`
- Theme utilities: `src/niamoto/gui/ui/src/tailwind-utilities.css`
- CSS variable bridge: `src/niamoto/gui/ui/src/index.css`
- Desktop local fonts: `src/niamoto/gui/ui/public/fonts/fonts.css`

### Visual Mockups

- Final 8-theme overview: `.superpowers/brainstorm/65276-1775148142/all-8-themes.html`
- Brand themes exploration: `.superpowers/brainstorm/65276-1775148142/brand-themes.html`
- Cartographic variants: `.superpowers/brainstorm/65276-1775148142/cartographic-variants.html`
