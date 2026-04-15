---
title: "feat: Refonte landing teaser au design système Niamoto réel"
type: feat
status: active
date: 2026-04-14
origin: docs/brainstorms/2026-04-14-landing-teaser-refonte-brainstorm.md
parent_plan: docs/plans/2026-04-14-feat-landing-teaser-video-plan.md
alternative_plan: docs/plans/2026-04-14-feat-landing-teaser-hybride-plan.md
revised: 2026-04-15
---

> **Plan ré-activé le 2026-04-15** — après une parenthèse vers une approche hybride screen-recording (abandonnée parce que l'utilisateur préfère des mocks JSX bien animés qui s'alignent avec son identité de dev Remotion). Le plan hybride `2026-04-14-feat-landing-teaser-hybride-plan.md` reste disponible comme alternative. Ce plan refonte est **l'approche active**, enrichi maintenant de :
> - **21 screenshots pristine du produit** (`docs/plans/caps/`) comme pixel-reference pour chaque composant mock
> - **URL preview locale** `http://localhost:5173/api/site/preview-exported/fr/` pour consulter le vrai rendu à tout moment pendant le dev
> - **Audio gratuit** (YouTube Audio Library + Freesound / Mixkit) intégré comme Phase 5
> - **Corrections** vs v1 : les donuts existent bien dans le vrai produit (Distribution substrat), il n'y a PAS de bug carte (la carte Araucariaceae 3539 bubbles est splendide), palette verte produit confirmée via `_base.html` + `niamoto.css`

# feat: Refonte landing teaser au design système Niamoto réel

## Overview

Refondre intégralement les 5 scènes du `LandingTeaser` Remotion (`media/demo-video/src/compositions/LandingTeaser.tsx`) pour qu'elles parlent visuellement le même langage que le **vrai produit Niamoto publié** — palette verte dense scientifique, bandeaux verts sur les widgets, vraies cartes NC à bubbles, vrais bar charts denses (DBH, phénologie) — sans renoncer à la liberté de motion frame-par-frame que permet Remotion.

Trois piliers techniques :
1. **Palette produit isolée** : un `teaserTheme` séparé de `shared/theme.ts` pour ne pas casser `MarketingLandscape` (qui reste sur la palette éditoriale demo video).
2. **Vraies librairies de viz dans Remotion** : `recharts@^3.3` (avec `isAnimationActive={false}` partout) + `react-simple-maps` + `topojson-client` + `@remotion/paths` + `@remotion/motion-blur` + **`remocn`** (registre shadcn-style de composants Remotion prêts pour curseur animé, modal morphing, progress steps, browser flow).
3. **Données crédibles** : extraites des `.html` de l'instance test `test-instance/niamoto-nc/exports/web/taxons/*.html` (où Plotly inline le JSON des charts réels) via un petit script de build.

Brief original R1-R15 préservé : durée ~45 s, curseur sur 2 interactions seulement, endcard logo+wordmark sans CTA, ton sobre crédible scientifique éditorial.

## Problem Statement

### Constat utilisateur

> « certaines choses ne sont pas correctement alignées dans les charts, la carte ne va pas du tout, l'affichage des textes est bof »

### Cause racine

Le teaser livré le 14/04 a été codé sans grounding sur le vrai produit. Il s'appuie sur un `docs/DESIGN_SYSTEM.md` qui décrit **la palette du demo video** (light/airy/steel-blue éditorial), pas celle du produit publié. Conséquences mesurables :

| Symptôme | Code coupable | Vraie référence |
|----------|---------------|-----------------|
| Carte abstraite vs vraie carte NC | `CollectionMosaic.tsx:153-227` (`AbstractMapGraphic` SVG) | `public/reference/collections-nc-map-card.png` (Plotly bubbles sur topo NC) |
| Mini-gauge fictif | `CollectionMosaic.tsx:87-151` (mini-gauge) | À supprimer : le produit n'a pas de gauge. Remplacer par bar charts + phénologie + donut Distribution substrat (existe bien dans le produit) |
| Sidebar bleu acier | `theme.ts:sidebarActiveBg = "#5B86B0"` | Vert produit `#228b22`/`#2E7D32` (cf. `src/niamoto/publish/templates/_base.html:43-48`) |
| Cards sans bandeau vert | `PublicSiteFrame.tsx` | Gradient `#228b22 → #2d8f47 → #1f7a1f` sur tous les widgets (`src/niamoto/publish/assets/css/niamoto.css:313`) |
| Wordmark `theme.steelBlue` | `TeaserEndCard.tsx:34` | Vert produit |

L'effet "maquette" et non "produit" vient de cette divergence systématique sur palette + types de charts + densité d'info.

## Proposed Solution

Refonte en 4 phases, isolée du reste du repo (composition `MarketingLandscape` non impactée), avec validation visuelle après chaque phase.

**Phase 1 — Foundations (fork sans casser)** : `teaserTheme` séparé, `AppWindow` paramétrable par `colorScheme`, mise à jour `DESIGN_SYSTEM.md` v2, script `extract-taxon-data.ts` pour datasets crédibles.

**Phase 2 — Library de widgets fidèles** : 6 composants réutilisables (`BubbleMapNC`, `DBHDistribution`, `PhenologyCalendar`, `OccurrencesBarChart`, `WidgetCard`, `TaxonomicNav`) avec recharts/react-simple-maps + animations frame-driven.

**Phase 3 — Refonte scène par scène** dans cet ordre (du plus impactant au moins) : Structure → Publish → Opener → DataIntake → EndCard.

**Phase 4 — Perf, polish, CI** : memoïsation, `delayRender` pour assets async, bench du render time, fix régressions Remotion best practices identifiées dans la revue précédente (premountFor, clamp, magic frames).

## Technical Approach

### Architecture decisions

#### 1. Isoler la palette : `teaserTheme` séparé

**Décision** : créer `media/demo-video/src/teaser/theme.ts` (palette produit verte) à côté de `media/demo-video/src/shared/theme.ts` (palette demo video éditoriale, intacte).

**Pourquoi** : `MarketingLandscape` ne doit pas être touchée (R1 du plan original). Forker la palette plutôt que muter `shared/theme.ts` évite tout effet de bord cross-composition.

```typescript
// media/demo-video/src/teaser/theme.ts (nouveau)
export const teaserTheme = {
  // Brand produit (extrait de src/niamoto/publish/templates/_base.html:43-48)
  primary: "#228b22",        // vert nav header site publié
  primaryDark: "#1f7a1f",    // gradient end widget headers
  primaryMid: "#2d8f47",     // gradient mid
  secondary: "#4caf50",      // green accent
  // Surfaces (extrait niamoto.css)
  pageBg: "#f9fafb",
  cardWhite: "#ffffff",
  // Text
  textPrimary: "#111827",
  textSecondary: "#6b7280",
  textOnPrimary: "#ffffff",
  // Borders & shadows
  border: "#e5e7eb",
  shadowCard: "0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.05)",
  // Widget header gradient (signature visuelle)
  widgetHeaderGradient: "linear-gradient(135deg, #228b22, #2d8f47, #1f7a1f)",
  // Charts palette (extrait gui/ui/src/themes/presets/frond.ts)
  chart1: "#2E7D32", chart2: "#5B86B0", chart3: "#7CB342",
  chart4: "#F2B94B", chart5: "#9333EA",
} as const;
```

#### 2. AppWindow paramétrable par `colorScheme`

**Décision** : ajouter prop `colorScheme: "marketing" | "teaser"` à `AppWindow` (`media/demo-video/src/ui/AppWindow.tsx`), default `"marketing"` (rétrocompatible). Le teaser passe `"teaser"` partout.

**Pourquoi** : éviter la duplication du composant (711 lignes dans CollectionMosaic + AppWindow forké = combinatoire ingérable) tout en laissant `MarketingLandscape` intact.

#### 3. Bibliothèques de viz : recharts + react-simple-maps + @remotion/paths

| Lib | Version | Usage | Justification |
|-----|---------|-------|---------------|
| `recharts` | `^3.3.0` | Bar charts (DBH, phénologie, occurrences/taxon) | React 19 OK, SVG pur, `isAnimationActive={false}` désactive les anims internes |
| `react-simple-maps` | `^3.0.0` | Carte NC + bubbles | TopoJSON statique, 100% offline, ~80 KB. À tester React 19 — fallback `react19-simple-maps` (fork) si peer dep refuse |
| `topojson-client` | `^3.1.0` | Décode TopoJSON NC vers GeoJSON pour react-simple-maps | Léger, BSD-3 |
| `@remotion/paths` | `^4.0.448` | `evolvePath()` + `getPointAtLength()` pour curseur sur chemin Bézier | Officiel Remotion |
| `@remotion/motion-blur` | `^4.0.448` | `CameraMotionBlur` pour le curseur en déplacement rapide (segments entre 2 targets) | Officiel Remotion. Coûteux en render, à utiliser sélectivement |
| **`remocn`** | via `npx shadcn add` | Composants Remotion prêts à l'emploi : SimulatedCursor, MorphingModal, ProgressSteps, BrowserFlow, ToastNotification | Registre shadcn-style (code copié dans le repo, pas de dépendance runtime). Voir https://github.com/kapishdima/remocn |
| `claude-remotion-editor` / SceneDirector | local tool | Dessiner visuellement les chemins de curseur + exporter JSON | github.com/ytrofr/claude-remotion-editor — à cloner en local, pas une dépendance npm |
| ❌ `@remotion/maps` | — | non installé | **N'existe pas** comme package npm officiel (vérifié) |
| ❌ Plotly.js | — | non installé | Bundle 3.5 MB, animations internes incontrôlables en headless |

**Règle absolue** : `isAnimationActive={false}` sur **chaque** série recharts (`<Bar>`, `<Line>`, `<Cell>`). Toute animation pilotée par `useCurrentFrame()` + `spring()` + `interpolate()` uniquement. Sinon flickering au render headless.

#### 4. Carte NC : TopoJSON statique + bubbles SVG animées

**Décision** : workflow build-time, zéro réseau au render :

1. Télécharger une fois Geofabrik NC (`download.geofabrik.de/australia-oceania/new-caledonia.html`) → Shapefile.
2. `ogr2ogr -f GeoJSON nc.geojson nc-admin-level-4.shp`
3. `npx toposimplify -p 1e-7 nc.geojson | npx geo2topo nc=- > public/maps/nc.topojson` — cible ≤ 200 KB.
4. Bundler dans `media/demo-video/public/maps/nc.topojson`, charger via `staticFile()` Remotion + `delayRender` pendant le decode.

**Bubbles** : positionnées en lon/lat depuis le dataset extrait (Phase 1, script d'extraction), animées via `spring()` avec stagger par île pour le reveal.

#### 5. Données crédibles via script d'extraction

**Décision** : nouveau script `media/demo-video/scripts/extract-taxon-data.mjs` qui :
- lit `test-instance/niamoto-nc/exports/web/taxons/*.html`
- regex/cheerio sur les `<script>` Plotly inline
- extrait : distribution DBH, phénologie 12 mois, occurrences par sub-taxon, lon/lat des points
- écrit `media/demo-video/src/teaser/data/taxon-vedette.json`
- exécuté via `pnpm run extract:teaser-data`

**Taxon vedette** : à choisir par script en sélectionnant celui qui maximise (a) nombre de widgets renseignés (b) hiérarchie taxonomique riche (c) lisibilité visuelle de la distribution. Candidat par défaut : **Araucariaceae** (famille, hiérarchie riche, distribution dense en NC). Décision finale dans Phase 1.

### Implementation Phases

#### Phase 0 — Pixel-reference setup (~1h)

Avant de coder quoi que ce soit, établir la grounding visuel qui manquait à la v1.

**Deliverables** :

- **Table de correspondance composant ↔ PNG référence** dans `media/demo-video/src/teaser/PIXEL_REFERENCES.md` :

| Composant teaser | PNG référence pixel-perfect | Source preview live |
|------------------|------------------------------|---------------------|
| AppWindow chrome (sidebar sombre + header) | `docs/plans/caps/06.dashboard-get-started.png` | GUI Tauri |
| Welcome / splash | `docs/plans/caps/01.splash-loading.png`, `02.welcome-project-picker.png` | — |
| Import data list | `docs/plans/caps/08.import-sources-review.png` | GUI Tauri |
| Import progress | `docs/plans/caps/10.import-analysis-progress.png`, `11.import-config-detected.png` | — |
| Data dashboard | `docs/plans/caps/13.data-dashboard-summary.png` | — |
| Collections overview | `docs/plans/caps/15.collections-overview.png` | GUI Tauri |
| Widget modal | `docs/plans/caps/16.collections-add-widget-modal.png` | — |
| Widget catalog | `docs/plans/caps/17.collections-widget-catalog.png` | — |
| Site builder | `docs/plans/caps/21.site-builder-home-page.png`, `22.site-builder-methodology-page.png` | GUI Tauri |
| Publish preview | `docs/plans/caps/25.publish-generation-preview.png` | — |
| Site publié hero | `http://localhost:5173/api/site/preview-exported/fr/index.html` | preview live |
| Liste taxons grille | `http://localhost:5173/api/site/preview-exported/fr/taxons/index.html` | preview live |
| Page taxon Araucariaceae | `http://localhost:5173/api/site/preview-exported/fr/taxons/948049381.html` | preview live |

- **Règle d'or de l'implémentation** : chaque composant mock nouveau ouvre **à côté** la PNG correspondante (cmd+Tab visuel) et réplique pixel-par-pixel : typo, espacement, couleur exacte, densité d'info. Pas d'approximation « à la louche ».
- **Palette tokens extraits** (via `eyedropper` sur les PNG + lecture de `src/niamoto/publish/assets/css/niamoto.css`) :
  - `primary`: `#228b22`
  - `widgetHeaderGradient`: `linear-gradient(135deg, #228b22, #2d8f47, #1f7a1f)`
  - `sidebarBg`: noir/charcoal (voir `06.dashboard-get-started.png`)
  - `cardWhite`: `#ffffff`
  - `pageBg`: `#f9fafb`
  - `textPrimary`: `#111827`
  - `textSecondary`: `#6b7280`
- **URL preview live toujours ouverte** pendant le dev pour valider en temps réel. Bookmark dans Chrome.

**Décisions locked** (héritées de la session brainstorm + hybride) :

| # | Décision | Implication pour la refonte mocks |
|---|----------|-----------------------------------|
| 1 | CTA Acte 4/EndCard activé (renverse R15) | Bouton « niamoto.org » vert + accroche « Open source. Auto-hébergeable. » |
| 2 | Hook hybride | Acte 1/Opener : texte user-centric sobre ; tagline marque `Import. Structure. Publish.` en EndCard sous le logo |
| 3 | Taxon vedette : Araucariaceae | 3 539 occurrences, 10 sous-taxons, carte NC dense (hot spots Poindimié + Nouméa). Toutes les données extract via script Phase 1 |
| 4 | Curseur post-anime en Remotion | Aucun screen recording, donc curseur entièrement codé (cubic Bézier paths, click ripple). Permet plus de polish que le curseur système |
| 5 | Audio first-class | Phase 5 dédiée. YouTube Audio Library (musique) + Freesound/Mixkit (SFX). Mix DaVinci Resolve. Fichiers hors-repo, sources documentées dans `AUDIO.md` |
| 6 | Format v1 | 1920×1080 seul. Formats 1:1 / 9:16 différés |
| 7 | Audio hors-repo | `recordings/audio-src/` gitignored ; `AUDIO.md` tracking URL + licence + hash |
| 8 | Durée totale | ~60 s (55–65 s), 4 actes narratifs (ou 5 scènes éditoriales selon découpage final Phase 3) |

#### Phase 1 — Foundations (~4h)

**Deliverables** :

- `media/demo-video/src/teaser/theme.ts` — nouvelle palette verte produit
- `media/demo-video/src/ui/AppWindow.tsx` — ajout prop `colorScheme: "marketing" | "teaser"` (default `"marketing"`)
- `media/demo-video/src/teaser/components/TeaserAppChrome.tsx` — wrapper qui passe `colorScheme="teaser"` + adapte sidebar items pour ressembler à `site-pages-editor.png` (icônes denses, fil d'Ariane, bouton Save vert)
- `media/demo-video/scripts/extract-taxon-data.mjs` — script Node d'extraction Plotly JSON
- `media/demo-video/src/teaser/data/taxon-vedette.json` — output du script (committé)
- `docs/DESIGN_SYSTEM.md` — section nouvelle "Teaser Theme (palette produit réelle)" avec table de tokens, ne touche pas la section existante "Demo Video"
- `media/demo-video/public/maps/nc.topojson` — TopoJSON simplifié de la NC (≤ 200 KB)
- `package.json` — ajout `recharts`, `react-simple-maps` (ou fork), `topojson-client`, `@remotion/paths`, `@remotion/motion-blur`
- **`remocn` composants Remotion prêts à l'emploi** (registre shadcn-style) via `npx shadcn@latest add https://remocn.dev/r/<name>.json` — installer dans `src/teaser/components/remocn/` :
  - `SimulatedCursor` (curseur animé avec states pointer/click + click ripple)
  - `MorphingModal` (dialog slide-in via clip-path depuis un point d'origine)
  - `ProgressSteps` (barre de progression frame-driven)
  - `BrowserFlow` (mock navigateur avec transitions de page)
  - Optionnel : `ToastNotification` (pour feedback « Import réussi »)
- Tester chaque composant remocn installé via une `Composition` isolée dans `Root.tsx` (folder `Remocn-Tests`)

**Acceptance** :
- `pnpm install` réussit, aucune peer dep warning bloquante
- `pnpm exec tsc --noEmit` passe
- Le script `extract:teaser-data` produit un JSON valide non vide
- Le TopoJSON est lisible via `topojson.feature(...)` dans un test isolé

#### Phase 2 — Library de widgets fidèles (~4h avec remocn, vs ~6h from scratch)

**Stratégie** : les composants « génériques » (curseur, modal, progress bar, browser chrome) viennent de **`remocn`**, customisés avec la palette Niamoto. Les composants **spécifiques au produit** (widgets charts, taxonomic nav) restent codés à la main avec recharts / react-simple-maps.

**Cursor paths via SceneDirector** :
- Télécharger `claude-remotion-editor` (github.com/ytrofr/claude-remotion-editor) en local
- Ouvrir l'éditeur web, dessiner visuellement les 2 trajectoires de curseur du teaser :
  1. Curseur vers bouton « Ouvrir l'import » (Dashboard cap 06) + click ripple
  2. Curseur vers bouton « Ajouter widget » (Collections cap 15) + click ripple
- Exporter chaque path en JSON `[{x, y, frame, gesture}]`
- Importer dans `src/teaser/data/cursor-paths.json`
- Le composant `SimulatedCursor` de remocn consomme directement ce format

**Components remocn customisés (dans `src/teaser/components/remocn/`)** :
- `SimulatedCursor` — override styles pour curseur agrandi style Niamoto, click ripple vert `#22C55E`, optionnellement wrap dans `<CameraMotionBlur>` sur segments rapides
- `MorphingModal` — override pour correspondre au modal « Ajout de widget » (cap 16) : clip-path qui s'ouvre depuis le bouton `+ Ajouter widget`, contenu = catalog remocn (cap 17)
- `ProgressSteps` — customisé en vert Niamoto pour simuler import progression (0% → 33% → 66% → 100%, aligné sur caps 08 → 10 → 11 → 13)
- `BrowserFlow` — Chrome frame customisé pour le site publié (Acte 3), avec URL bar `niamoto.org/fr/taxons/araucariaceae`

**Components Niamoto-spécifiques (coded from scratch dans `src/teaser/widgets/`)** :

##### widgets/WidgetCard.tsx
Card blanche, **ombre triple-couche** signature code vs screen recording :
```css
box-shadow:
  0 2px 4px rgba(17, 24, 39, 0.12),
  0 16px 32px rgba(17, 24, 39, 0.06),
  0 32px 64px rgba(17, 24, 39, 0.04);
```
Header gradient `#228b22 → #2d8f47 → #1f7a1f`, titre blanc, icône info.

##### widgets/BubbleMapNC.tsx
- `react-simple-maps` `<ComposableMap>` + projection geoMercator NC
- `<Geographies>` charge `nc.topojson` via `staticFile()` + `delayRender`
- `<Marker>` × N depuis `taxon-vedette.json` lon/lat
- `<circle>` r animé via `spring({ frame, fps, delay: index * 2 })` clamped
- Stagger `3 frames` entre bubbles = signature code
- Légende droite (rampe count bleu→violet→orange→jaune matching vrai produit)

##### widgets/DBHDistribution.tsx
- `recharts` `<BarChart>` avec `<Bar isAnimationActive={false}>`
- Chaque `<Cell>` avec `transform: scaleY(spring(...))` `transformOrigin: 'bottom'`
- Stagger `delay: i * 3` frames entre bins
- Axes X (bins cm) + Y (count)
- Easing Material `bezier(0.4, 0, 0.2, 1)`

##### widgets/PhenologyCalendar.tsx
- `recharts` `<BarChart>` 12 mois, bars empilées
- Couleurs : orange/vert/bleu (matching vrai produit cap exploration)
- Reveal mois par mois via stagger spring `damping: 12`

##### widgets/SubstrateDonut.tsx (nouveau, remplace les mini-donut fake)
- `recharts` `<PieChart>` avec `innerRadius` (donut) — **existe bien dans le vrai produit** (Distribution substrat UM/non-UM)
- 2 `<Cell>` : `#C28E5F` (Ultramafique 82.8%) + `#A0693F` (non-UM 17.1%)
- Révélation via `clip-path` angulaire ou `strokeDasharray` animé
- Labels rotés en SVG

##### widgets/OccurrencesBarChart.tsx
- `<BarChart>` horizontal des sub-taxons
- Palette multicolore matching le vrai produit (Araucaria montana bleu, Agathis ovata magenta, etc.)
- Reveal par stagger frame-driven

##### widgets/TaxonomicNav.tsx
- Sidebar gauche dense avec arbre taxonomique
- État sélectionné = background vert clair `#D1FAE5`, texte vert foncé, left border 3px vert `#22C55E`
- Data depuis `taxon-vedette.json` hierarchy
- Reproduit fidèlement `/fr/taxons/948049381.html` zone gauche

**Règle d'or Phase 2** : pour chaque widget, ouvrir **à côté** (cmd+Tab) la PNG référence correspondante (table Phase 0) et comparer pixel-par-pixel avant validation.

**Tous les widgets** : props typées strictes, FC pures, `React.memo` sur les charts statiques, données depuis `taxon-vedette.json`. Aucune CSS animation (`@keyframes`, `transition`, `animation` interdits). Spring config recommandée `damping: 12-14` pour overshoot signature code. Stagger 3 frames entre items.

**Acceptance Phase 2** :
- `remocn` installé avec 4+ composants customisés (Cursor, Modal, Progress, Browser)
- Chaque widget a une `Composition` Remotion d'isolation dans `Root.tsx` sous `Folder name="Teaser-Widgets"` pour preview Remotion Studio
- 2 cursor paths exportés depuis SceneDirector + validés en preview
- Snapshot visuel manuel vs PNG référence (table Phase 0) widget par widget — divergence palette/typo < 5% à l'œil
- `pnpm exec tsc --noEmit` passe
- Render d'une compo widget seule en < 30 s à 30 fps × 5 s

#### Phase 3 — Refonte scène par scène (~10h)

Ordre : du plus impactant au moins, pour valider l'approche libs-réelles tôt.

##### 3.1 — Structure (la mosaïque cassée)
- Réécriture complète `media/demo-video/src/teaser/scenes/TeaserStructure.tsx` (430 lignes)
- Réécriture complète `media/demo-video/src/teaser/components/CollectionMosaic.tsx` (711 lignes → ~250 attendues)
- Layout : sidebar `TaxonomicNav` (gauche) + grid 2×3 de `WidgetCard` contenant : `BubbleMapNC`, `OccurrencesBarChart`, `DBHDistribution`, `PhenologyCalendar`, info card "General overview", + 1 distribution complémentaire
- Reveal séquentiel via `assembleProgress` interpolé, stagger par index widget
- Curseur préservé sur "Add widgets" (R12) — repositionné en coordonnées relatives à `LANDING_TEASER.width/height` (fix régression revue précédente)

##### 3.2 — Publish (le payoff)
- Réécriture `media/demo-video/src/teaser/scenes/TeaserPublish.tsx` (350 lignes)
- Réécriture `media/demo-video/src/teaser/components/PublicSiteFrame.tsx` (287 lignes)
- Header vert `#228b22` plein largeur avec logo Niamoto blanc + nav (Accueil, Méthodologie, Ressources, Peuplements, Arbres, Forêt, FR/EN)
- Sidebar `TaxonomicNav` à gauche, grid de `WidgetCard` à droite reproduisant fidèlement `public/site-previews/site-taxon.png`
- Curseur préservé sur "Publish site" (R12) — coordonnées relatives
- URL fictive : retirer `atlas.example.org/taxa/myrtaceae` (R10 — éviter ancrage géographique nommé) → générique `niamoto.example/taxon/[famille]`

##### 3.3 — Opener
- Garde la structure narrative (hero + AppWindow slide + FilePill flottantes)
- Migration `theme` → `teaserTheme`, `colorScheme="teaser"` sur AppWindow
- Fond gradient ajusté vers nuance verte douce plutôt que steel-blue
- Hero text apparaît seul d'abord (frame 0-30), puis AppWindow slide-in (frame 42+) — fix R5 (« phrase éditoriale courte avant l'interface »)

##### 3.4 — DataIntake
- Migration palette uniquement (FilePill colors restent codés couleur par type de fichier — `.csv`, `.gpkg`, etc., codes couleur conservés mais alignés sur la palette `chart1-5` du theme produit)
- Animation FilePill : ajouter `extrapolateLeft/Right: "clamp"` sur les `interpolate(opacity, ...)` (fix régression revue)

##### 3.5 — EndCard
- Wordmark `theme.steelBlue` → `teaserTheme.primary` (vert)
- Logo `NiamotoLogo` : vérifier que le fill est paramétrable par prop `color` ; sinon, refonte du composant pour accepter `color`
- Spring config : ajout clamp sur opacity (fix overshoot identifié dans la revue)

**Acceptance Phase 3** :
- Toutes les scènes rendent sans erreur en `pnpm exec remotion render LandingTeaser`
- Durée totale ~45 s ±2 s respectée
- `pnpm exec tsc --noEmit` passe
- Curseur visible uniquement dans Structure + Publish (R11/R12)
- EndCard sans URL ni CTA (R15)

#### Phase 4 — Perf, polish, CI (~3h)

- **Perf** : ajouter `premountFor={30}` sur chaque `TransitionSeries.Sequence` dans `LandingTeaser.tsx` (fix critique revue), bench le render time avant/après refonte
- **delayRender** : encapsuler le chargement de `nc.topojson` dans un `delayRender` dédié, libérer dans le `.then()`. Idem pour le decode du JSON taxon
- **Memoïsation** : `React.memo` sur les 6 widgets, vérifier que les props ne changent pas inutilement
- **Clamp partout** : audit final de toutes les `interpolate(spring(...), ...)` pour garantir `extrapolateLeft/Right: "clamp"`
- **backdropFilter** : remplacer dans `EditorialOverlay.tsx:45` par un fond semi-transparent + `box-shadow` (le `backdrop-filter` est ignoré au render headless — fix critique revue)
- **CI** : pas de touch des workflows ; vérifier que `pnpm install` + `pnpm exec tsc --noEmit` continuent de passer (Node 22 — cf. memoire feedback `feedback_ci_node_version.md`)
- **Cleanup** : supprimer le code mort `cursorSegments` dans `storyboard.ts:19` (jamais consommé)

#### Phase 5 — Audio (~2h)

Ajout critique vs plan v1 : aucun teaser B2B 2026 ne fonctionne sans audio (cf. recherche indépendante). Stack 100% gratuite.

**Sources** :
- **Musique** : [YouTube Audio Library](https://studio.youtube.com/) → Audio Library → filtres : Genre `Ambient` ou `Cinematic`, Mood `Calm` ou `Inspirational`, Attribution `Not required`, durée ≥ 60 s. Format export MP3 320 kbps.
- **SFX** : [Freesound.org](https://freesound.org/) (filtrer licence `Creative Commons 0`) ou [Mixkit](https://mixkit.co/free-sound-effects/) (Mixkit Free License = usage commercial sans attribution).

**5 SFX à placer** :
- 1× `soft pop UI` — apparition des mots Acte 1 / Opener
- 1× `low swoosh transition` — transitions entre scènes
- 1× `UI click minimal` — clics simulés du curseur (Acte 2-3)
- 1× `soft ping notification` — apparition logo EndCard
- 1× `cinematic swell soft` — montée Acte 3 / Publish payoff

**Critères musique** : instrumentale, tempo medium 90-110 BPM, mood calm/inspirational, pas de drop électronique, pas de violons sentimentaux. Test loop : si après 3 écoutes c'est encore agréable, c'est bon.

**Workflow mixage (DaVinci Resolve gratuit)** :
1. Importer MP4 Remotion comme video track
2. Audio track 1 = musique fond, niveau **-30 LUFS**
3. Audio track 2 = SFX alignés sur beats, niveau **-18 LUFS**
4. Master intégré final = **-14 LUFS** (standard web 2026)
5. Export : H.264 1920×1080, audio AAC 192 kbps stéréo

**Deliverables** :
- `media/demo-video/recordings/audio-src/` (gitignored) : WAV/MP3 locaux
- `media/demo-video/recordings/AUDIO.md` — tracking URL source + licence + hash MD5 de chaque asset
- Version MP4 finale avec audio mixé dans `out/landing-teaser-final.mp4`

**Alternative payante si qualité insuffisante** : Artlist personal ($199/an) couvre musique + SFX avec licence landing/social, ou achat single track AudioJungle ($30-50 one-shot).

## Alternative Approaches Considered

| Approche | Pourquoi rejetée |
|----------|------------------|
| Screenshot-first cinématique (PNG du vrai produit + motion overlay) | Choix utilisateur explicite → perte de liberté motion frame-par-frame ; mais reste backup si recharts pose des problèmes de perf irrésolubles en Phase 2 |
| Capture screencast live de l'instance | Demande instance test parfaite, choreography rigide, fragile aux changements de version |
| Garder mocks JSX au DS éditorial actuel (le polish only) | Ne résout pas la cause racine "ne ressemble pas au vrai produit" |
| Plotly.js dans Remotion | Bundle 3.5 MB, animations internes incontrôlables, aucun exemple public Remotion qui marche |
| Mapbox GL via @remotion/maps | `@remotion/maps` n'existe pas comme package npm ; mapbox-gl direct demande clé API, fragile en headless, overkill pour un contour NC fixe |
| visx pour tous les charts | Plus verbeux que recharts pour le 80% des cas standards ; à réserver à un éventuel custom layout futur |

## Acceptance Criteria

### Functional Requirements

- [ ] Composition `LandingTeaser` rend en `pnpm exec remotion render LandingTeaser out/landing-teaser.mp4` sans erreur
- [ ] Durée totale = 45 s ±2 s
- [ ] 5 scènes dans l'ordre : Opener, DataIntake, Structure, Publish, EndCard
- [ ] Curseur visible uniquement dans Structure (sur "Add widgets") et Publish (sur "Publish site") — R11/R12
- [ ] EndCard = logo + wordmark "Niamoto" uniquement, pas d'URL, pas de CTA — R15
- [ ] Types de charts utilisés = exclusivement ceux présents dans le vrai produit (validés 14/04 via exploration `test-instance/nouvelle-caledonie`) : bar horizontal multicolore (sous-taxons), bar vertical beige (DBH), bar empilé 12 mois (phénologie), bar horizontal bleu (pluviométrie), **donut** (Distribution substrat UM/non-UM), cards stats, bubble map Plotly (Distribution géographique). Pas de gauge (n'existe pas dans le produit).
- [ ] `MarketingLandscape` rend toujours à l'identique (snapshot frame avant/après refonte)

### Non-Functional Requirements

- [ ] Render time ≤ 1.5× le render time actuel du teaser (bench avant/après)
- [ ] Bundle size augmente de ≤ 1.5 MB (recharts ~600 KB + react-simple-maps ~80 KB + topojson ~50 KB + nc.topojson ~200 KB)
- [ ] Aucun warning React 19 peer deps bloquant
- [ ] Aucune CSS `@keyframes` ou `transition` ou `animation` dans le code teaser (audit grep)
- [ ] Tous les `interpolate()` ont `extrapolateLeft/Right: "clamp"` (audit grep)
- [ ] Tous les `<Bar>`, `<Line>`, `<Cell>` recharts ont `isAnimationActive={false}` (audit grep)
- [ ] `delayRender` couvre : fonts, TopoJSON decode, JSON taxon decode

### Quality Gates

- [ ] `pnpm exec tsc --noEmit` passe
- [ ] `pnpm exec remotion render LandingTeaser` produit un `.mp4` lisible
- [ ] Comparaison visuelle manuelle frame-par-frame : Structure scène ressemble à `public/site-previews/site-taxon.png` à 80% min (header vert, sidebar taxonomique, grid widgets verts)
- [ ] Comparaison visuelle Publish scène ressemble à `site-taxon.png` à 90% min (le payoff doit être quasi-identique au vrai site)
- [ ] La carte NC contient des bubbles aux bonnes positions géographiques (vérification visuelle vs `collections-nc-map-card.png`)
- [ ] Code review interne validée (cf. `/compound-engineering:workflows:review`)

## Success Metrics

- **Reconnaissance produit** : un utilisateur Niamoto reconnaît l'app en < 3 s sur la scène Publish
- **Crédibilité scientifique** : les charts montrent des données plausibles (DBH bins réalistes, phénologie 12 mois cohérente)
- **Pérennité** : les 6 widgets sont réutilisables dans d'autres compositions Remotion futures (social cuts, screencasts produit)
- **Maintenabilité** : `CollectionMosaic` passe de 711 à ~250 lignes, `PublicSiteFrame` de 287 à ~150 lignes

## Dependencies & Prerequisites

### NPM (à ajouter dans `media/demo-video/package.json`)
- `recharts@^3.3.0`
- `react-simple-maps@^3.0.0` (fallback : `react19-simple-maps` si peer dep React 19 refuse)
- `topojson-client@^3.1.0`
- `@remotion/paths@^4.0.448`
- `@remotion/motion-blur@^4.0.448`
- **`remocn` components** via `npx shadcn@latest add https://remocn.dev/r/<name>.json` (pas une dépendance runtime — le code est copié dans `src/teaser/components/remocn/`)

### Système
- `ogr2ogr` (GDAL) pour la conversion Geofabrik Shapefile → GeoJSON (Phase 1, one-shot, pas de dépendance runtime)
- `toposimplify` + `geo2topo` (npx, pas d'install permanente)
- Node 22 (déjà CI)

### Sources de données
- Instance test `test-instance/niamoto-nc/exports/web/taxons/*.html` doit exister et être à jour
- Si absent : régénérer via `niamoto run` dans `test-instance/niamoto-nc/` avant de lancer le script d'extraction

### Documentation existante
- `docs/DESIGN_SYSTEM.md` — sera étendu (section "Teaser Theme") sans casser l'existant
- `docs/brainstorms/2026-04-14-landing-teaser-refonte-brainstorm.md` — origin
- `docs/plans/2026-04-14-feat-landing-teaser-video-plan.md` — brief R1-R15 préservé
- Skill `/Users/julienbarbe/.claude/skills/remotion-best-practices/rules/{charts,maps,sequencing,timing}.md`

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| `react-simple-maps` peer dep refuse React 19 | Moyenne | Haut | Fallback `react19-simple-maps` (fork connu). Tester en Phase 1 dès l'install |
| `recharts` × 1380 frames trop lent | Moyenne | Haut | `React.memo` strict + valeurs interpolées calculées à l'avance. Si toujours trop lent, fallback : Phase 2.5 = remplacer recharts par visx ou SVG hand-coded sur les widgets bottleneck |
| TopoJSON NC > 500 KB après simplification | Faible | Moyen | `toposimplify -p` plus agressif (1e-6 → 1e-5). Si toujours trop gros, charger via `staticFile()` + `fetch()` paresseux + `delayRender` |
| `MarketingLandscape` régression visuelle | Faible | Haut | `colorScheme` default `"marketing"` + theme isolé garantit zéro impact. Snapshot avant/après render |
| Données extraites incohérentes (taxon sans phénologie p.ex.) | Moyenne | Moyen | Le script d'extraction filtre les taxons selon "complétude data" et choisit un fallback |
| `backdropFilter` toujours dans l'output (oubli Phase 4) | Faible | Faible | Audit grep `backdropFilter` dans le CI / pre-commit |
| Curseur en pixels absolus (régression revue) reproduite | Moyenne | Moyen | Helper `relCoord(x%, y%)` qui retourne `LANDING_TEASER.width * x/100` à utiliser dans cursorPaths |
| Render time 10× plus long → CI timeout | Faible | Haut | Bench en Phase 4. Si > 5min, exclure le render du CI (déjà le cas), garder uniquement `tsc --noEmit` |

## Resource Requirements

- **Effort estimé** : ~23h (4h Phase 1 + 6h Phase 2 + 10h Phase 3 + 3h Phase 4)
- **Compétences** : React 19, Remotion 4, recharts, SVG/D3, basics GDAL pour conversion topojson
- **Outils locaux** : Node 22, pnpm, ogr2ogr (`brew install gdal`), Remotion Studio pour preview

## Future Considerations

- **Variantes sociales** (9:16, 1:1) : la library de widgets Phase 2 est réutilisable, restera à adapter le layout
- **Lift-and-shift dans `MarketingLandscape`** : à terme, le `MarketingLandscape` peut bénéficier des widgets fidèles aussi (suppression des MockCard fakes)
- **Auto-data-refresh** : le script d'extraction peut être branché en pre-build pour toujours rendre depuis les dernières données instance test
- **Theme produit canonique** : `teaserTheme` peut devenir la base d'un futur `niamotoTheme` partagé entre `MarketingLandscape` et teaser (post-V1)

## Documentation Plan

- [ ] `docs/DESIGN_SYSTEM.md` — nouvelle section "Teaser Theme — palette produit réelle" (extracted from `niamoto.css` + `_base.html`)
- [ ] `media/demo-video/src/teaser/widgets/README.md` — bref guide d'usage des 6 widgets
- [ ] `media/demo-video/scripts/extract-taxon-data.mjs` — header de fichier explicite (input HTML path, output JSON schema)
- [ ] CHANGELOG note dans `media/demo-video/` (si CHANGELOG existe — sinon skip)
- [ ] Pas de mise à jour CLAUDE.md projet (la refonte ne change pas les conventions globales)

## References & Research

### Internal References

- Brainstorm : `docs/brainstorms/2026-04-14-landing-teaser-refonte-brainstorm.md`
- Plan original (R1-R15) : `docs/plans/2026-04-14-feat-landing-teaser-video-plan.md`
- Audit fidelity : `docs/brainstorms/2026-04-13-demo-video-fidelity-audit-brainstorm.md`
- Theme actuel : `media/demo-video/src/shared/theme.ts`
- AppWindow : `media/demo-video/src/ui/AppWindow.tsx`
- CollectionMosaic à refondre : `media/demo-video/src/teaser/components/CollectionMosaic.tsx:153-227` (`AbstractMapGraphic`), `:87-151` (mini-donut/gauge)
- PublicSiteFrame à refondre : `media/demo-video/src/teaser/components/PublicSiteFrame.tsx`
- Source de vérité palette produit : `src/niamoto/publish/templates/_base.html:43-48`, `src/niamoto/publish/assets/css/niamoto.css:313`
- Source de vérité GUI desktop : `src/niamoto/gui/ui/src/themes/presets/frond.ts:46`
- Données crédibles : `test-instance/niamoto-nc/exports/web/taxons/*.html` (Plotly inline)
- Memory feedback CI Node 22 : `~/.claude/.../memory/feedback_ci_node_version.md`

### External References

- Remotion charts skill : `/Users/julienbarbe/.claude/skills/remotion-best-practices/rules/charts.md`
- Remotion maps skill : `/Users/julienbarbe/.claude/skills/remotion-best-practices/rules/maps.md`
- Remotion sequencing : `/Users/julienbarbe/.claude/skills/remotion-best-practices/rules/sequencing.md`
- Recharts isAnimationActive : https://recharts.github.io/en-US/api/Bar/
- react-simple-maps docs : https://www.react-simple-maps.io/docs/getting-started/
- **remocn** (composants Remotion shadcn-style) : https://github.com/kapishdima/remocn
- **claude-remotion-editor / SceneDirector** (outil web pour dessiner les chemins de curseur) : https://github.com/ytrofr/claude-remotion-editor
- @remotion/paths — evolvePath : https://www.remotion.dev/docs/paths/evolve-path
- @remotion/paths — getPointAtLength : https://www.remotion.dev/docs/paths/get-point-at-length
- @remotion/motion-blur — CameraMotionBlur : https://www.remotion.dev/docs/motion-blur/camera-motion-blur
- react19-simple-maps fork : https://github.com/vnedyalk0v/react19-simple-maps
- Remotion player flicker (charts) : https://www.remotion.dev/docs/troubleshooting/player-flicker
- Geofabrik Nouvelle-Calédonie : https://download.geofabrik.de/australia-oceania/new-caledonia.html
- TopoJSON workflow : https://github.com/topojson/topojson-server

### Related Work

- Composition `MarketingLandscape` (préservée) : `media/demo-video/src/compositions/MarketingLandscape.tsx`
- Acts existants (préservés) : `media/demo-video/src/acts/Act{1..6}*.tsx`

### Open Questions Resolved

| Q | Réponse |
|---|---------|
| Lib chart précise | `recharts` priorité, visx en backup, Plotly écarté |
| Approche carte | TopoJSON statique + `react-simple-maps` (PAS Mapbox) |
| Source design tokens | Extraits de `src/niamoto/publish/templates/_base.html` + `niamoto.css` |
| `DESIGN_SYSTEM.md` v2 timing | Avant Phase 2 (drive Phase 2 components) |
| Données factices source | Script d'extraction des `.html` instance test, taxon vedette = Araucariaceae (à confirmer Phase 1) |
| Conflit MarketingLandscape | Resolved via theme isolé + AppWindow `colorScheme` prop |
