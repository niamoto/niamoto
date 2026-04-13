---
title: "feat: Animated motion graphics demo video"
type: feat
date: 2026-04-13
brainstorm: docs/brainstorms/2026-04-13-demo-video-motion-graphics-brainstorm.md
replaces: docs/plans/2026-04-08-feat-niamoto-demo-video-production-plan.md (Phase 2+)
---

# Animated Motion Graphics Demo Video

## Overview

Remplacer l'approche screencasts du plan initial par une **vidéo motion graphics complète** reproduisant l'interface Niamoto en composants React animés dans Remotion. 6 actes montrent le parcours utilisateur complet : Welcome → Project Creation → Import → Collections → Site Builder → Publish.

Le projet Remotion existant (`media/demo-video/`) est conservé — on nettoie les scènes obsolètes, on ajoute les nouveaux composants UI, et on reconstruit la composition principale.

## Technical Approach

### Architecture

```
media/demo-video/src/
  acts/                        # 6 actes du parcours utilisateur
    Act1Welcome.tsx
    Act2ProjectWizard.tsx
    Act3Import.tsx
    Act4Collections.tsx
    Act5SiteBuilder.tsx
    Act6Publish.tsx
  scenes/                      # Habillage (intro, labels, outro)
    IntroScene.tsx              # ex IntroLogo.tsx, affiné
    TransitionLabel.tsx         # Label contextuel entre actes
    OutroScene.tsx              # ex OutroCTA.tsx, affiné
  ui/                          # Composants mock reproduisant l'UI Niamoto
    AppWindow.tsx               # Frame macOS (traffic lights + titre + ombre)
    Sidebar.tsx                 # Navigation latérale avec items actifs
    MockInput.tsx               # Input avec typing animation
    MockButton.tsx              # Bouton gradient/outline
    MockCard.tsx                # Card générique (collections)
    MockTree.tsx                # Arbre de navigation (site builder)
    MockPreviewPanel.tsx        # Panel de prévisualisation
    FileUploadZone.tsx          # Zone d'upload drop
    FileTypeChip.tsx            # Chip de type de fichier coloré
    ProgressBar.tsx             # Barre de progression animée
    YamlPreview.tsx             # Bloc de code YAML
    TopBar.tsx                  # Barre supérieure (search + icônes)
  cursor/                      # Système de curseur animé
    CursorOverlay.tsx           # Wrapper positionnant le curseur au-dessus de tout
    cursorPaths.ts              # Waypoints par acte
  animations/                  # Primitives d'animation vendorées (PAS de dépendance remocn/shadcn)
    CursorFlow.tsx             # Curseur Bézier (inspiré remocn, réécrit maison)
    SpringPopIn.tsx            # Wrapper spring scale 0→1
    ShimmerText.tsx            # Texte avec balayage lumineux (interpolate, pas CSS)
  shared/                      # Existant, enrichi
    theme.ts                   # Inchangé
    fonts.ts                   # Inchangé
    config.ts                  # Durées recalculées pour 6 actes
    layout.ts                  # NOUVEAU : constantes AppWindow/sidebar/topbar
    mockData.ts                # NOUVEAU : données fictives pour les actes
    DESIGN_SYSTEM.md           # NOUVEAU : référence visuelle complète
  compositions/
    MarketingLandscape.tsx     # Refactorisé : TransitionSeries avec 6 actes
  Root.tsx                     # Mis à jour
```

### Timing Budget

Cible : **~100 secondes** (3000 frames @ 30fps). Transitions incluses.

| Séquence | Durée brute | Frames | Contenu |
|----------|-------------|--------|---------|
| IntroScene | 4s | 120 | Logo reveal + tagline |
| Act 1 — Welcome | 8s | 240 | Logo app + bouton CTA |
| Act 2 — Project Wizard | 12s | 360 | Typing nom + create |
| Act 3 — Import | 20s | 600 | File parade + auto-config + YAML |
| Act 4 — Collections | 14s | 420 | Card grid + badges |
| Act 5 — Site Builder | 20s | 600 | 3 panneaux + navigation arbre |
| Act 6 — Publish | 12s | 360 | Build progress + deploy confirm |
| OutroScene | 6s | 180 | Logo + URLs |
| **Total brut** | **96s** | **2880** | |
| 7 transitions × 15f | -3.5s | -105 | |
| **Total effectif** | **~92.5s** | **2775** | |

### Layout Constants (`layout.ts`)

```typescript
export const LAYOUT = {
  // Canvas
  canvas: { width: 1920, height: 1080 },

  // AppWindow — centré avec marge subtile
  window: {
    x: 40, y: 30,
    width: 1840, height: 1020,
    borderRadius: 12,
    shadow: "0 25px 80px rgba(0,0,0,0.6)",
  },

  // Traffic lights (macOS)
  trafficLights: {
    x: 56, y: 46,
    size: 12,
    gap: 8,
    colors: ["#FF5F57", "#FEBC2E", "#28C840"],
  },

  // Titlebar
  titlebar: { height: 32 },

  // Sidebar (mode full, hidden pour acts 1-2)
  sidebar: {
    width: 200,
    bgColor: "#13131A", // oklch(0.11 0.008 270) → hex
  },

  // TopBar
  topbar: { height: 48 },

  // Content area (calculé dynamiquement selon sidebar visible ou non)
  // Avec sidebar: x=240, y=80, w=1600, h=940
  // Sans sidebar: x=40, y=80, w=1800, h=940
} as const;
```

Toutes les coordonnées du curseur sont relatives à `LAYOUT.window` (pas au canvas 1920×1080).

### Mock Data (`mockData.ts`)

```typescript
// Collections (Act 4) — données génériques, pas NC-spécifiques
export const MOCK_COLLECTIONS = [
  { name: "Plots", count: 245, widgets: 3, exports: 2, status: "fresh" },
  { name: "Taxa", count: 1280, widgets: 5, exports: 3, status: "fresh" },
  { name: "Occurrences", count: 48500, widgets: 4, exports: 2, status: "stale" },
];

// Import YAML (Act 3)
export const MOCK_YAML = `sources:
  taxon_reference:
    type: csv
    path: taxa.csv
    identifier: id_taxon
  occurrences:
    type: csv
    path: occurrences.csv
    identifier: id_occurrence
  plots:
    type: geopackage
    path: study_plots.gpkg
    identifier: id_plot`;

// Site tree (Act 5)
export const MOCK_SITE_TREE = [
  { label: "Home", icon: "home", type: "page" },
  { label: "Species", icon: "layers", type: "collection", children: [
    { label: "Species Index", type: "page" },
    { label: "Species Detail", type: "template" },
  ]},
  { label: "Plots", icon: "layers", type: "collection", children: [
    { label: "Plot Map", type: "page" },
  ]},
  { label: "About", icon: "file", type: "page" },
];

// Project creation (Act 2)
export const MOCK_PROJECT = {
  name: "my-ecology-project",
  path: "~/projects/my-ecology-project",
};
```

### Sidebar State Per Act

| Acte | Sidebar visible | Item actif | Notes |
|------|----------------|------------|-------|
| 1 — Welcome | Non | — | Écran plein, pas de projet chargé |
| 2 — Project Wizard | Non | — | Overlay wizard sur fond Welcome |
| 3 — Import | Oui | Data | Sidebar slide-in au début de l'acte |
| 4 — Collections | Oui | Collections | Highlight change avec transition |
| 5 — Site Builder | Oui | Site | |
| 6 — Publish | Oui | Publish | |

La sidebar utilise le **mode full** (icônes + labels) pour la clarté — le spectateur doit comprendre la navigation.

### Primitives d'animation (vendorées, pas de dépendance remocn)

Le projet n'a **pas de setup shadcn** et n'en a pas besoin. On vendore 3 primitives maison dans `src/animations/`, inspirées de remocn mais réécrites pour garantir zéro CSS animations.

| Primitive | Pattern Remotion | Usage |
|-----------|-----------------|-------|
| `CursorFlow` | `interpolate()` sur courbes de Bézier cubiques + `spring()` pour click ripple | Curseur dans tous les actes |
| `SpringPopIn` | `spring({ from: 0.85, to: 1 })` sur scale + opacity fade | Entrée cards, boutons, modals |
| `ShimmerText` | `interpolate()` sur `backgroundPosition` d'un gradient `backgroundClip: text` | Texte "Auto-configuration" (Act 3) |

Pour l'intro tagline, on utilise un simple fade+blur via `interpolate()` sur `opacity` et `filter: blur()` — pas besoin d'un composant dédié.

> **Aucune dépendance npm ajoutée.** Ces 3 fichiers sont ~50-80 lignes chacun, 100% `interpolate()`/`spring()`, zéro `@keyframes`/`transition`/`animation` CSS.

### Transitions Between Scenes

Deux types de transitions seulement, pour la cohérence :
- **`fade`** (15 frames) — transition par défaut entre la plupart des scènes
- **`slide({ direction: "from-right" })`** (15 frames) — uniquement pour Act 2 → Act 3, quand le workspace apparaît avec sa sidebar pour la première fois

| Transition | Type | Justification |
|-----------|------|---------------|
| Intro → Act 1 | `fade` | Entrée douce |
| Act 1 → Act 2 | `fade` | Même contexte (Welcome) |
| Act 2 → Act 3 | `slide(from-right)` | Le workspace glisse — moment clé de la vidéo |
| Act 3 → Act 4 | `fade` | Changement de contenu dans le même frame |
| Act 4 → Act 5 | `fade` | Idem |
| Act 5 → Act 6 | `fade` | Idem |
| Act 6 → Outro | `fade` | Fermeture douce |

---

## Implementation Phases

Les phases sont réorganisées en ordre de production sûr : fondations d'abord, puis livraison incrémentale par blocs d'actes vérifiables dans Remotion Studio.

### Phase 1: Fondations

**Objectif** : Nettoyer, créer l'infrastructure, valider que le Studio démarre.

- [x] Supprimer les scènes obsolètes :
  - `src/scenes/StatsOrMap.tsx`
  - `src/scenes/PipelineAnimated.tsx`
  - `src/scenes/ScreencastBlock.tsx`
- [x] Supprimer les docs obsolètes :
  - `SCRIPT.md`
  - `STORYBOARD.md`
- [x] Mettre à jour `README.md` pour refléter l'architecture motion graphics (supprimer les références aux screencasts)
- [x] Créer les répertoires :
  - `src/acts/`
  - `src/ui/`
  - `src/cursor/`
  - `src/animations/`
- [ ] Créer `src/shared/DESIGN_SYSTEM.md` (Phase 5) (voir section Phase 6 pour le contenu)
- [x] Créer `src/shared/layout.ts` avec les constantes de layout (AppWindow, sidebar, topbar)
- [x] Créer `src/shared/mockData.ts` avec les données fictives génériques
- [x] Mettre à jour `src/shared/config.ts` : nouvelles durées pour 6 actes + intro/outro, nouveau calcul `totalFrames`
- [x] Bloquer le rendu sur le chargement des fonts : dans `MarketingLandscape.tsx`, appeler `delayRender()` au mount puis `ensureFontsLoaded().then(() => continueRender(handle))`. Le projet expose déjà `ensureFontsLoaded()` dans `fonts.ts` — il suffit de l'utiliser. Pattern :
  ```tsx
  const [handle] = useState(() => delayRender("Loading fonts"));
  useEffect(() => {
    ensureFontsLoaded().then(() => continueRender(handle));
  }, [handle]);
  ```
- [x] Écrire les 3 primitives d'animation vendorées :
  - `src/animations/CursorFlow.tsx` — curseur Bézier avec waypoints, click ripple spring, hold. ~80 lignes, 100% `interpolate()`/`spring()`
  - `src/animations/SpringPopIn.tsx` — wrapper scale 0.85→1 via `spring()` + opacity. ~30 lignes
  - `src/animations/ShimmerText.tsx` — gradient animé via `interpolate()` sur `backgroundPosition`, `backgroundClip: text`. ~50 lignes
- [x] Mettre à jour `Root.tsx` : supprimer les anciennes compositions, ajouter un placeholder `MarketingLandscape` vide
- [x] Vérifier que `pnpm dev` lance le Studio sans erreur

### Phase 2: UI Components + Actes 1-3

**Objectif** : Construire les composants UI nécessaires aux 3 premiers actes, implémenter les actes, vérifier dans le Studio.

#### 2a. Composants UI (bloc 1)

Construire dans cet ordre — chaque composant est testable isolément dans le Studio via une composition dédiée :

- [x] `AppWindow.tsx` — Frame macOS :
  - Fond arrondi (`borderRadius: 12`) avec ombre portée
  - Traffic lights (3 cercles colorés, statiques)
  - Titre "Niamoto" centré dans la titlebar
  - Props : `showSidebar: boolean`, `activeSidebarItem?: string`, `children`
  - Anime le slide-in de la sidebar quand `showSidebar` passe à `true`
  - Référence : `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`

- [x] `Sidebar.tsx` — Navigation latérale :
  - 5 items : Home (House), Data (Database), Collections (Layers), Site (Globe), Publish (Send)
  - Item actif avec highlight vert `lightGreen`
  - Logo Niamoto 28×28 en header
  - Largeur : `LAYOUT.sidebar.width` (200px)
  - Background : `LAYOUT.sidebar.bgColor` (#13131A)
  - Référence : `src/niamoto/gui/ui/src/components/layout/NavigationSidebar.tsx`

- [x] `TopBar.tsx` — Barre supérieure :
  - Hauteur `LAYOUT.topbar.height` (48px)
  - Barre de recherche factice (input arrondi, placeholder "Search... ⌘K")
  - Bordure inférieure subtile
  - Référence : `src/niamoto/gui/ui/src/components/layout/TopBar.tsx`

- [x] `MockButton.tsx` — Bouton avec états :
  - Props : `variant: "gradient" | "outline" | "default"`, `label`, `icon?`
  - Variant gradient : `background: linear-gradient(to right, #2E7D32, #26A69A)`
  - Spring scale on click (piloté par frame, pas par événement)
  - Référence : boutons de `WelcomeScreen.tsx` et `ProjectCreationWizard.tsx`

- [x] `MockInput.tsx` — Input avec typing animation :
  - Props : `text: string`, `typingStartFrame: number`, `charsPerSecond?: number`
  - Typing via string slicing + curseur clignotant (toggle toutes les 0.5s)
  - Font mono pour path/code, display pour noms
  - Pattern : `text.substring(0, revealedCount)` — jamais d'opacité par caractère
  - Référence : `ProjectCreationWizard.tsx` input field

- [x] `MockCard.tsx` — Card de collection :
  - Props : `name`, `count`, `status`, `widgets`, `exports`
  - Background `cardDark` (#2A2A2E), border radius 7px
  - Badge de statut coloré : fresh (vert), stale (ambre), error (rouge)
  - Compteurs en grille 3 colonnes
  - Entrée via `SpringPopIn` avec delay staggeré
  - Référence : `CollectionsOverview.tsx` → `CollectionCard`

- [x] `FileTypeChip.tsx` — Chip de type de fichier :
  - Props : `type: "csv" | "vector" | "raster"`, `extensions: string[]`
  - Couleurs : csv → `#3FA9F5` (steelBlue), vector → `#4BAF50` (lightGreen), raster → `#9333EA` (purple-600)
  - Icônes simplifiées : Table2, Map, Globe (formes géométriques, pas Lucide en direct)
  - Animation slide-in depuis la gauche
  - Référence : `FileUploadZone.tsx` color mapping

- [x] `FileUploadZone.tsx` — Zone d'upload :
  - Bordure pointillée (`2px dashed`), icône Upload au centre
  - États : vide → fichiers entrants (chips) → rempli
  - Background subtil au hover/active
  - Référence : `FileUploadZone.tsx` (la vraie)

- [x] `YamlPreview.tsx` — Bloc de code YAML :
  - Font JetBrains Mono, fond plus sombre que `cardDark`
  - Coloration syntaxique simplifiée (clés en lightGreen, valeurs en textWhite, strings en steelBlue)
  - Animation slide-up à l'entrée
  - Contenu : `MOCK_YAML` depuis `mockData.ts`

- [x] `ProgressBar.tsx` — Barre de progression :
  - Props : `startFrame`, `durationInFrames`, `label?`, `steps?: string[]`
  - Interpolation ease-out de 0% à 100%
  - Couleur : `lightGreen` sur fond `cardDark`
  - Label de pourcentage optionnel
  - Deux modes : simple (une barre) et steps (build → deploy avec étapes)

- [x] `MockTree.tsx` — Arborescence de pages :
  - Props : `items` (arbre), `activeItem?`, `expandedItems?`
  - Indentation par niveau, icônes par type (page/collection/template)
  - Highlight de l'item actif
  - Animation d'expansion progressive
  - Référence : `UnifiedSiteTree.tsx`

- [x] `MockPreviewPanel.tsx` — Prévisualisation :
  - Simule un iframe de site généré via un **mini-layout HTML en divs** (pas d'image statique)
  - Contenu : fond clair (`bgLight`), header vert avec titre "Species", grille 2×2 de placeholder cards, footer simple
  - Quand le curseur clique un item dans `MockTree`, le contenu du preview cross-fade vers un nouveau layout (header change de titre)
  - Bordure gauche subtile, fond distinct du panel éditeur
  - Cohérent avec le parti pris "tout animé, zéro asset externe"
  - Référence : `SiteBuilderPreview.tsx`

#### 2b. Cursor system

- [x] Créer `src/cursor/CursorOverlay.tsx` :
  - Wrapper `AbsoluteFill` avec `pointerEvents: none`, `z-index: 100`
  - Instancie `CursorFlow` avec les waypoints de l'acte courant
  - Coordonnées relatives à `LAYOUT.window` (pas au canvas)

- [x] Créer `src/cursor/cursorPaths.ts` — waypoints par acte :
  ```typescript
  // Estimations — à ajuster visuellement dans Remotion Studio
  export const CURSOR_PATHS = {
    act1: [
      { x: 960, y: 200, hold: 15 },
      { x: 920, y: 620, hold: 10, click: true }, // "Create New Project"
    ],
    act2: [
      { x: 700, y: 400, hold: 10, click: true }, // input name
      { x: 920, y: 580, hold: 15, click: true }, // "Create"
    ],
    act3: [
      { x: 800, y: 450, hold: 30 }, // survole upload zone
      { x: 800, y: 650, hold: 40 }, // observe YAML
    ],
    act4: [
      { x: 400, y: 400, hold: 20 },
      { x: 700, y: 400, hold: 20 },
      { x: 1000, y: 400, hold: 20 },
    ],
    act5: [
      { x: 300, y: 350, hold: 15, click: true }, // tree item
      { x: 300, y: 420, hold: 15, click: true }, // another item
      { x: 700, y: 400, hold: 20 },  // editor
      { x: 1200, y: 400, hold: 25 }, // preview
    ],
    act6: [
      { x: 920, y: 350, hold: 10, click: true }, // "Build & Publish"
      { x: 920, y: 500, hold: 60 }, // observe progress
    ],
  };
  ```

#### 2c. Actes 1-3

Chaque acte est un composant React autonome. `useCurrentFrame()` retourne le frame local (0-based dans la Sequence).

- [x] **Act1Welcome.tsx** — Écran d'accueil :
  - Pas d'`AppWindow` (écran plein, fond gradient)
  - Logo Niamoto centré (spring entrance, scale 0.8→1)
  - Tagline sous le logo (fade-in delayed 0.5s)
  - Deux boutons CTA : "Create New Project" (gradient) + "Open Project" (outline)
  - `CursorOverlay` : arrive et clique "Create New Project" → spring scale du bouton
  - Référence : `src/niamoto/gui/ui/src/features/welcome/views/WelcomeScreen.tsx`

- [x] **Act2ProjectWizard.tsx** — Création de projet :
  - Toujours pas d'`AppWindow` (overlay modal sur fond Welcome)
  - Card centrée avec :
    - Logo petit en haut
    - Input "Project name" → `MockInput` typing "my-ecology-project"
    - Affichage path en temps réel (font mono)
    - Bouton "Create" gradient
  - Le curseur clique l'input, le texte se tape, puis clique "Create"
  - Flash de transition vert (confirm) avant passage à l'Act 3
  - Référence : `src/niamoto/gui/ui/src/features/welcome/views/ProjectCreationWizard.tsx`

- [x] **Act3Import.tsx** — Import de données :
  - `AppWindow` avec sidebar (première apparition — sidebar slide-in animé)
  - Sidebar : "Data" actif
  - Séquence interne (3 phases) :
    1. **Phase upload** (0-7s) : `FileUploadZone` vide → 3 `FileTypeChip` glissent depuis la gauche (stagger 1s) → chips se transforment en liste de fichiers
    2. **Phase auto-config** (7-13s) : Icône Sparkles (forme géométrique ✨) pulsante au centre + `ShimmerText` sur "Auto-configuration..." → résolution
    3. **Phase review** (13-20s) : `YamlPreview` monte en slide-up avec le contenu `MOCK_YAML`
  - Le curseur survole et observe passivement (pas de clic complexe)
  - Référence : `src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx`

#### 2d. Validation checkpoint

- [x] `pnpm exec tsc --noEmit` passe sans erreurs
- [x] Vérifier dans `pnpm dev` (Remotion Studio) que les 3 actes fonctionnent isolément
- [x] Vérifier que les fonts sont bien chargées (pas de fallback système)
- [x] Vérifier que le curseur se déplace correctement dans chaque acte
- [x] Ajuster les coordonnées du curseur si nécessaire

### Phase 3: Actes 4-6

**Objectif** : Implémenter les 3 derniers actes. Tous les composants UI sont déjà construits en Phase 2a.

#### 3a. Actes 4-6

- [x] **Act4Collections.tsx** — Collections :
  - `AppWindow` avec sidebar, "Collections" actif
  - Header "Collections" avec badge compteur
  - Grille 3 colonnes de `MockCard` (données depuis `MOCK_COLLECTIONS`)
  - Entrée staggerée via `SpringPopIn` (delay 0.3s entre cards)
  - Le curseur survole les cards, hover effect subtil (border lightGreen)
  - Référence : `src/niamoto/gui/ui/src/features/collections/components/CollectionsOverview.tsx`

- [x] **Act5SiteBuilder.tsx** — Constructeur de site :
  - `AppWindow` avec sidebar, "Site" actif
  - Layout 3 panneaux fixes (20% / 50% / 30%) :
    - Gauche : `MockTree` avec `MOCK_SITE_TREE`
    - Centre : éditeur contextuel simplifié (titre + quelques champs mock)
    - Droite : `MockPreviewPanel` — mini-layout HTML (header vert, grille cards, footer)
  - Séquence : arbre se peuple → curseur clique "Species" → l'éditeur change de titre → la preview cross-fade vers un nouveau layout
  - Référence : `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`

- [x] **Act6Publish.tsx** — Publication :
  - `AppWindow` avec sidebar, "Publish" actif
  - Séquence en 2 phases :
    1. **Build** (0-7s) : `ProgressBar` "Building site..." de 0% à 100%, steps visibles (Generate pages → Process assets → Create index)
    2. **Deploy** (7-12s) : `ProgressBar` "Deploying..." de 0% à 100% → Badge vert "Published" avec check animé
  - Le curseur clique "Build & Publish" → observe la progression
  - Référence : publish views dans `src/niamoto/gui/ui/src/features/publish/`

#### 3b. Validation checkpoint

- [x] `pnpm exec tsc --noEmit` passe sans erreurs
- [x] Les 6 actes fonctionnent isolément dans le Studio
- [x] Les transitions sidebar entre actes sont fluides (highlight change)
- [x] `MockPreviewPanel` cross-fade fonctionne dans l'Act 5

### Phase 4: Composition & Polish

**Objectif** : Assembler le tout, affiner les timings, rendre le MP4 final.

#### 4a. Scenes d'habillage

- [x] Refactoriser `IntroScene.tsx` (ex `IntroLogo.tsx`) :
  - Garder le spring entrance du logo
  - Tagline avec fade+blur via `interpolate()` sur `opacity` et `filter: blur()` ("Ecological data, from field to web")
  - Fond `bgDark` uni

- [x] Créer `TransitionLabel.tsx` :
  - Label contextuel affiché en **début d'acte** (pas en overlay — les overlays ne peuvent pas être adjacents aux transitions dans TransitionSeries)
  - Props : `text: string`, `durationInFrames: number`
  - Fade-in 10f, hold, fade-out 10f. Font display, taille 32px, couleur `textMuted`, centré sur fond `bgDark`
  - Rendu en tant que `<Sequence>` dans les premières frames des actes 3, 5 et 6 :
    1. Act 3 (premiers 30f) : "Import your data"
    2. Act 5 (premiers 30f) : "Build your site"
    3. Act 6 (premiers 30f) : "Publish to the web"

- [x] Refactoriser `OutroScene.tsx` (ex `OutroCTA.tsx`) :
  - Logo Niamoto + github.com/niamoto/niamoto
  - `arsis.dev` en steelBlue (branding Arsis)
  - Spring staggeré pour les éléments
  - Fond `bgDark`

#### 4b. Composition principale

- [x] Reconstruire `MarketingLandscape.tsx` avec `TransitionSeries` :
  ```tsx
  <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={sec(4)}>
      <IntroScene />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={fade()} timing={linearTiming({ durationInFrames: 15 })}
    />
    <TransitionSeries.Sequence durationInFrames={sec(8)}>
      <Act1Welcome />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={fade()} timing={linearTiming({ durationInFrames: 15 })}
    />
    <TransitionSeries.Sequence durationInFrames={sec(12)}>
      <Act2ProjectWizard />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={slide({ direction: "from-right" })}
      timing={linearTiming({ durationInFrames: 15 })}
    />
    {/* Act 3 commence par un TransitionLabel "Import your data" dans ses premiers 30f */}
    <TransitionSeries.Sequence durationInFrames={sec(20)}>
      <Act3Import />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={fade()} timing={linearTiming({ durationInFrames: 15 })}
    />
    <TransitionSeries.Sequence durationInFrames={sec(14)}>
      <Act4Collections />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={fade()} timing={linearTiming({ durationInFrames: 15 })}
    />
    {/* Act 5 commence par un TransitionLabel "Build your site" dans ses premiers 30f */}
    <TransitionSeries.Sequence durationInFrames={sec(20)}>
      <Act5SiteBuilder />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={fade()} timing={linearTiming({ durationInFrames: 15 })}
    />
    {/* Act 6 commence par un TransitionLabel "Publish to the web" dans ses premiers 30f */}
    <TransitionSeries.Sequence durationInFrames={sec(12)}>
      <Act6Publish />
    </TransitionSeries.Sequence>
    <TransitionSeries.Transition
      presentation={fade()} timing={linearTiming({ durationInFrames: 15 })}
    />
    <TransitionSeries.Sequence durationInFrames={sec(6)}>
      <OutroScene />
    </TransitionSeries.Sequence>
  </TransitionSeries>
  ```
  > Notes :
  > - Toutes les transitions sont `fade` sauf Act 2 → Act 3 qui est `slide(from-right)`.
  > - Les `TransitionLabel` sont rendus en tant que `<Sequence>` dans les premiers 30f des actes 3, 5 et 6 (les overlays TransitionSeries ne peuvent pas être adjacents aux transitions).

- [ ] Mettre à jour `Root.tsx` :
  - Composition principale `MarketingLandscape` avec `durationInFrames` calculé
  - Folder "Acts" avec chaque acte en composition isolée (debug)
  - Supprimer les anciennes compositions (Pipeline, Stats, Screencast)

#### 4c. Polish

- [ ] Lecture complète dans le Studio (`pnpm dev`) — vérifier le rythme général
- [ ] Ajuster les durées par acte si nécessaire (modifier `config.ts` + recompter `totalFrames`)
- [ ] Vérifier les transitions (pas de flash blanc, pas de saut, sidebar cohérente)
- [ ] Vérifier la sidebar slide-in Act 2 → Act 3
- [ ] Rendu final : `npx remotion render MarketingLandscape --output=out/niamoto-demo.mp4`
- [ ] Vérifier le MP4 final (pas d'artefacts, timing correct)

### Phase 5: DESIGN_SYSTEM.md

**Objectif** : Documenter le système visuel a posteriori (après que les composants existent).

> Note : cette phase est volontairement en dernier. Le DESIGN_SYSTEM.md est plus utile comme documentation de ce qui a été construit que comme spec abstraite écrite avant d'avoir vu le rendu.

- [ ] Créer `src/shared/DESIGN_SYSTEM.md` (Phase 5) avec les 9 sections :
  1. **Visual Theme & Atmosphere** : Dark professional, data-forward, minimal chrome
  2. **Color Palette & Roles** : Hex tokens (charcoal, forestGreen, lightGreen, steelBlue, cardDark, textWhite, textMuted) + FileTypeChip colors (csv steelBlue, vector lightGreen, raster #9333EA)
  3. **Typography Rules** : Plus Jakarta Sans (display 400-700) + JetBrains Mono (code 400-500), échelle (48/40/32/24/20/16/14/12)
  4. **Component Stylings** : Catalogue des composants UI construits, avec dimensions et états réels
  5. **Layout Principles** : Canvas 1920×1080, grille 8px, AppWindow, sidebar/topbar, panels Site Builder
  6. **Depth & Elevation** : z-layers (fond 0, contenu 1, sidebar 2, topbar 3, modal 4, curseur 100)
  7. **Do's and Don'ts** : spring() pour entrées, interpolate() pour progressions, jamais de CSS animations, toujours `extrapolateRight: "clamp"`, données génériques
  8. **Scene Inventory** : Tableau des actes avec durées réelles, composants UI, primitives d'animation, transitions
  9. **Agent Prompt Guide** : Instructions pour régénérer ou modifier des scènes

---

## Acceptance Criteria

### Functional

- [ ] 6 actes visibles et enchaînés dans une vidéo fluide de ~90-100 secondes
- [ ] Chaque acte reproduit reconnaissablement l'interface Niamoto correspondante
- [ ] Le curseur simulé se déplace naturellement et clique/tape aux bons endroits
- [ ] La sidebar apparaît à l'Act 3 et change d'item actif à chaque acte suivant
- [ ] L'Act 3 montre clairement les 3 types de fichiers supportés (CSV, vector, raster)
- [ ] L'Act 6 montre build ET deploy
- [ ] Aucune donnée New Caledonia-spécifique visible

### Technical

- [ ] Zéro CSS `@keyframes`, `transition`, ou `animation` — uniquement `interpolate()`/`spring()`
- [ ] Les 3 primitives vendorées (`CursorFlow`, `SpringPopIn`, `ShimmerText`) sont autonomes, zéro dépendance externe
- [ ] Fonts chargées via `@remotion/fonts` et bloquées au démarrage (pas de fallback système sur les premières frames)
- [ ] `config.ts` calcule correctement `totalFrames` avec déduction des 7 transitions × 15 frames
- [ ] Chaque acte fonctionne comme composition isolée dans Remotion Studio (`pnpm dev`)
- [ ] Le rendu MP4 final est sans artefacts (`npx remotion render MarketingLandscape`)

### Quality

- [x] `pnpm exec tsc --noEmit` passe sans erreurs (`pnpm build` lance un render Remotion, pas un typecheck)
- [ ] Les composants UI sont réutilisables et paramétrables (pas de magic numbers)
- [ ] Le `DESIGN_SYSTEM.md` est complet et utilisable

---

## Dependencies & Risks

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Coordonnées curseur difficiles à caler | Mauvais rendu visuel | Ajustement itératif dans le Studio (checkpoints Phase 2d et 3c) |
| Durées par acte mal calibrées | Vidéo trop rapide/lente | Constantes centralisées dans `config.ts`, ajustables. Checkpoints après chaque bloc d'actes |
| Rendu final lent | ~100s × 30fps = 3000 frames à rendre | Acceptable (que du React, pas de vidéo/audio lourd) |
| Fonts flash sur premières frames | Texte en system font pendant 1-2 frames | `delayRender()`/`continueRender()` dans la composition racine (Phase 1) |
| Act 5 trop complexe (3 panneaux + interactions) | Dépasse le budget de 20s ou rendu confus | Le preview est un mini-layout simplifié, pas un vrai site — rester minimaliste |

## References

### Internal

- Brainstorm : `docs/brainstorms/2026-04-13-demo-video-motion-graphics-brainstorm.md`
- Plan initial : `docs/plans/2026-04-08-feat-niamoto-demo-video-production-plan.md`
- Theme source : `src/niamoto/gui/ui/src/themes/presets/frond.ts`
- Layout source : `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`
- Welcome : `src/niamoto/gui/ui/src/features/welcome/views/WelcomeScreen.tsx`
- Import : `src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx`
- Collections : `src/niamoto/gui/ui/src/features/collections/components/CollectionsOverview.tsx`
- Site Builder : `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`

### External

- [Remotion docs](https://www.remotion.dev/docs)
- [remocn registry](https://remocn.dev/)
- [remocn GitHub](https://github.com/kapishdima/remocn)
- [awesome-design-md](https://github.com/VoltAgent/awesome-design-md)
- Remotion best practices : skill `remotion-best-practices` (rules/animations.md, rules/transitions.md, rules/sequencing.md, rules/text-animations.md)
