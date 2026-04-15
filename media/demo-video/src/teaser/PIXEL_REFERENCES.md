# Pixel references — teaser refonte

Chaque composant mock de ce teaser doit répliquer **pixel par pixel** un écran réel du produit Niamoto. Ce fichier est la table de correspondance.

Règle d'or : **avant d'écrire un composant**, ouvre sa PNG de référence côte à côte avec le code (`cmd+Tab` vers l'Aperçu ou Preview). Sans référence active, tu retombes dans l'approximation « à la louche » qui a fait échouer la v1.

## Correspondance composant ↔ PNG / URL live

Les PNG sont dans `docs/plans/caps/`. Les URLs `http://localhost:5173/...` nécessitent que la GUI Niamoto tourne sur le projet `test-instance/nouvelle-caledonie`.

### GUI Tauri (Actes 1 à 5)

| Composant teaser | PNG référence | URL preview live |
|------------------|---------------|------------------|
| Splash / loading | [`01.splash-loading.png`](../../../../docs/plans/caps/01.splash-loading.png) | — |
| Welcome / project picker | [`02.welcome-project-picker.png`](../../../../docs/plans/caps/02.welcome-project-picker.png) | — |
| Project create form (empty) | [`03.project-create-empty.png`](../../../../docs/plans/caps/03.project-create-empty.png) | — |
| Project create (typing name) | [`04.project-create-name.png`](../../../../docs/plans/caps/04.project-create-name.png) | — |
| Project create (ready) | [`05.project-create-ready.png`](../../../../docs/plans/caps/05.project-create-ready.png) | — |
| **Dashboard** (entry point Acte 2) | [`06.dashboard-get-started.png`](../../../../docs/plans/caps/06.dashboard-get-started.png) | GUI Tauri |
| Import sources review | [`08.import-sources-review.png`](../../../../docs/plans/caps/08.import-sources-review.png) | GUI Tauri |
| Import analysis progress | [`10.import-analysis-progress.png`](../../../../docs/plans/caps/10.import-analysis-progress.png) | — |
| Import config detected | [`11.import-config-detected.png`](../../../../docs/plans/caps/11.import-config-detected.png) | — |
| **Data dashboard summary** | [`13.data-dashboard-summary.png`](../../../../docs/plans/caps/13.data-dashboard-summary.png) | GUI Tauri |
| Collections overview | [`15.collections-overview.png`](../../../../docs/plans/caps/15.collections-overview.png) | GUI Tauri |
| **Add widget modal** | [`16.collections-add-widget-modal.png`](../../../../docs/plans/caps/16.collections-add-widget-modal.png) | — |
| Widget catalog | [`17.collections-widget-catalog.png`](../../../../docs/plans/caps/17.collections-widget-catalog.png) | — |
| Collection page | [`16.collection-page.png`](../../../../docs/plans/caps/16.collection-page.png) | — |
| Collection computation | [`19.collection-computation.png`](../../../../docs/plans/caps/19.collection-computation.png) | — |
| Site builder home | [`21.site-builder-home-page.png`](../../../../docs/plans/caps/21.site-builder-home-page.png) | GUI Tauri |
| Site builder methodology | [`22.site-builder-methodology-page.png`](../../../../docs/plans/caps/22.site-builder-methodology-page.png) | — |
| Publish generation preview | [`25.publish-generation-preview.png`](../../../../docs/plans/caps/25.publish-generation-preview.png) | — |
| Deploy provider picker | [`26.deploy-provider-picker.png`](../../../../docs/plans/caps/26.deploy-provider-picker.png) | — |
| Deploy GitHub Pages config | [`27.deploy-github-pages-config.png`](../../../../docs/plans/caps/27.deploy-github-pages-config.png) | — |
| Deploy build log | [`28.deploy-build-log.png`](../../../../docs/plans/caps/28.deploy-build-log.png) | — |
| Deploy success | [`29.deploy-success.png`](../../../../docs/plans/caps/29.deploy-success.png) | — |

### Site publié (Acte 3 — payoff)

| Composant teaser | URL preview live |
|------------------|------------------|
| **Hero forêt plein écran** | [`/fr/index.html` top](http://localhost:5173/api/site/preview-exported/fr/index.html) |
| Partenaires + 4 chiffres clés | [`/fr/index.html` scroll 1](http://localhost:5173/api/site/preview-exported/fr/index.html) |
| Pitch kanak « mötö » | [`/fr/index.html` scroll 2](http://localhost:5173/api/site/preview-exported/fr/index.html) |
| **Liste taxons grille photos** | [`/fr/taxons/index.html`](http://localhost:5173/api/site/preview-exported/fr/taxons/index.html) |
| **Page taxon Araucariaceae top** | [`/fr/taxons/948049381.html`](http://localhost:5173/api/site/preview-exported/fr/taxons/948049381.html) |
| Page taxon — sous-taxons + DBH | [`/fr/taxons/948049381.html` scroll 1](http://localhost:5173/api/site/preview-exported/fr/taxons/948049381.html) |
| Page taxon — phénologie + Holdridge | [`/fr/taxons/948049381.html` scroll 2](http://localhost:5173/api/site/preview-exported/fr/taxons/948049381.html) |
| Page taxon — **donut substrat** + pluviométrie | [`/fr/taxons/948049381.html` scroll 3](http://localhost:5173/api/site/preview-exported/fr/taxons/948049381.html) |
| Présentation peuplements | [`/fr/plots.html`](http://localhost:5173/api/site/preview-exported/fr/plots.html) |
| Présentation arbres | [`/fr/trees.html`](http://localhost:5173/api/site/preview-exported/fr/trees.html) |
| Présentation forêt | [`/fr/forests.html`](http://localhost:5173/api/site/preview-exported/fr/forests.html) |

## Palette tokens extraits

Source de vérité : `src/niamoto/publish/templates/_base.html:43-48` + `src/niamoto/publish/assets/css/niamoto.css:313`.

### Brand

| Token | Hex | Rôle |
|-------|-----|------|
| `primary` | `#228b22` | Nav header site publié, bouton CTA primary, sidebar active |
| `primaryMid` | `#2d8f47` | Gradient mid sur widget headers |
| `primaryDark` | `#1f7a1f` | Gradient end sur widget headers |
| `secondary` | `#4caf50` | Accent vert |
| `widgetHeaderGradient` | `linear-gradient(135deg, #228b22, #2d8f47, #1f7a1f)` | Signature visuelle des cards site |

### Surfaces

| Token | Hex | Rôle |
|-------|-----|------|
| `pageBg` | `#f9fafb` | Fond de page site publié |
| `cardWhite` | `#ffffff` | Cards blanches |
| `sidebarBgDark` | — (à eyedropper sur `06.dashboard-get-started.png`) | Sidebar IDE Tauri sombre/charcoal |

### Text

| Token | Hex | Rôle |
|-------|-----|------|
| `textPrimary` | `#111827` | Titre, body text |
| `textSecondary` | `#6b7280` | Muted |
| `textOnPrimary` | `#ffffff` | Texte sur fond vert |

### Semantic

| Token | Hex | Rôle |
|-------|-----|------|
| `success` | `#4caf50` | Published badges, success states |
| `chart1..chart5` | voir `src/niamoto/gui/ui/src/themes/presets/frond.ts` | Palette charts |

## 8 décisions locked (2026-04-14)

1. **CTA EndCard activé** — bouton « niamoto.org » vert + accroche sobre (renverse R15)
2. **Hook hybride** — texte user-centric Acte 1 + tagline marque `Import. Structure. Publish.` sous logo EndCard
3. **Taxon vedette : Araucariaceae** (ID `948049381`, 3 539 occurrences, 10 sous-taxons, famille endémique NC)
4. **Curseur post-anime Remotion** — pas de screen recording, curseur entièrement codé via `@remotion/paths` + `remocn` SimulatedCursor, paths dessinés via SceneDirector
5. **Audio first-class** — Phase 5 dédiée, YouTube Audio Library + Freesound/Mixkit, mix DaVinci Resolve -14 LUFS
6. **Format v1 : 1920×1080 seul** — 1:1 / 9:16 différés
7. **Audio hors-repo** — `recordings/audio-src/` gitignored, tracking URL + licence + hash dans `AUDIO.md`
8. **Durée ~60 s** — 4 actes narratifs (ou 5 scènes selon découpage final Phase 3)

## Règles d'implémentation

- **Pas de CSS `@keyframes`, `transition`, `animation`** — tout via `interpolate()` / `spring()` / `@remotion/paths` frame-driven
- **`isAnimationActive={false}`** sur chaque série recharts (`<Bar>`, `<Line>`, `<Cell>`, `<Pie>`)
- **`extrapolateLeft: "clamp"` + `extrapolateRight: "clamp"`** sur chaque `interpolate(spring(...), ...)`
- **`premountFor={30}`** sur chaque `TransitionSeries.Sequence` (fix régression v1)
- **Spring config signature code** : `{ damping: 12-14, stiffness: 180-220 }` pour overshoot léger
- **Stagger cards** : 3 frames entre items = 0.1 s à 30 fps
- **Ombre triple-couche** sur les cards style « vrai produit » :
  ```css
  box-shadow:
    0 2px 4px rgba(17, 24, 39, 0.12),
    0 16px 32px rgba(17, 24, 39, 0.06),
    0 32px 64px rgba(17, 24, 39, 0.04);
  ```
- **Pas de `backdrop-filter`** — ignoré au render headless Chromium

## Checks pixel-perfect

Avant de dire « ce composant est fini » :
1. Overlap sur la PNG référence (ou preview live) via outil 50% opacity (Figma, Pixelmator, ou juste split-screen Chrome Studio)
2. Vérifier : typo (font-family, font-size, font-weight, line-height), couleurs (picker les éléments), espacement (verbes `gap`, `padding`, `margin`), dimensions exactes, ombres
3. Si divergence > 5% à l'œil → refaire jusqu'à convergence
