# Demo Video — Motion Graphics Animée

**Date** : 2026-04-13
**Statut** : Brainstorm validé, en attente de plan d'implémentation
**Remplace** : approche screencasts du plan initial (2026-04-08)

## Contexte

Le plan initial prévoyait des screencasts avec overlays texte. Après prototypage, le résultat est trop statique et peu engageant. On pivote vers une **vidéo motion graphics complète** qui reproduit l'interface Niamoto en composants React animés dans Remotion.

## Ce qu'on construit

Une vidéo marketing de ~90-120 secondes en 1920x1080 @ 30fps montrant le parcours utilisateur complet de Niamoto à travers 6 actes animés. Chaque acte reproduit semi-fidèlement l'interface réelle avec des composants React custom, un curseur simulé qui interagit avec l'UI, le tout encadré dans une fenêtre desktop macOS.

### Les 6 actes du parcours

| Acte | Scène | Ce qu'on montre |
|------|-------|-----------------|
| 1 | Welcome | Écran d'accueil avec logo Niamoto centré, bouton "Create New Project" en gradient vert |
| 2 | Project Wizard | Formulaire de création : nom du projet tapé au clavier, chemin affiché, bouton "Create" |
| 3 | Import | Zone d'upload + parade des types de fichiers (.csv, .gpkg, .tif) → auto-configuration → aperçu YAML |
| 4 | Collections | Grille de cards de collections avec compteurs, badges fraîcheur, widgets |
| 5 | Site Builder | Layout 3 panneaux : arbre de pages + éditeur contextuel + aperçu live |
| 6 | Publish | Barre de progression → site généré → déploiement confirmé |

**Pas de dashboard** — on montre le parcours de production, pas la consultation.

### Scènes d'habillage

- **Intro** : logo Niamoto + tagline (scène existante, à affiner)
- **Transitions entre actes** : labels contextuels minimaux ("Import your data", "Build your site"...)
- **Outro** : logo + arsis.dev + GitHub URL (scène existante, à affiner)

## Approche technique

### Design System MD

Création d'un `DESIGN_SYSTEM.md` décrivant le système visuel frond de Niamoto au format structuré (inspiré [awesome-design-md](https://github.com/VoltAgent/awesome-design-md)). Ce fichier sert de référence unique pour tous les composants de la vidéo.

Sections : palette de couleurs (hex, pas oklch), typographie (Plus Jakarta Sans + JetBrains Mono), composants UI (boutons, cards, inputs, sidebar), layout patterns, profondeur/ombres, do's & don'ts.

### Fidélité semi-fidèle

Les composants reproduisent l'interface Niamoto de manière **reconnaissable mais simplifiée** :
- Mêmes couleurs, typos, proportions
- Détails non essentiels omis (tooltips, badges secondaires, états hover complexes)
- Données simulées mais plausibles

### Curseur simulé

Un curseur macOS animé qui se déplace en courbes de Bézier entre les points d'interaction. Enchaîne clic, frappe clavier, drag. Source : composant SimulatedCursor de [remocn](https://github.com/kapishdima/remocn).

### Fenêtre desktop

Frame macOS tout au long de la vidéo : barre de titre avec traffic lights (rouge/jaune/vert), titre de la fenêtre "Niamoto", sidebar de navigation qui change selon l'acte. Donne le contexte "application desktop" immédiatement.

### Transitions

Minimalistes et polies. Pas de transitions spectaculaires, juste ce qu'il faut pour fluidifier les changements de scène :
- Fade entre intro et premier acte
- DirectionalWipe ou slide entre actes
- BlurReveal possible pour les moments clé (auto-config, publish)

## Architecture des fichiers

```
media/demo-video/src/
  acts/                    # 6 actes du parcours
    Act1Welcome.tsx
    Act2ProjectWizard.tsx
    Act3Import.tsx
    Act4Collections.tsx
    Act5SiteBuilder.tsx
    Act6Publish.tsx
  scenes/                  # Intro, transitions, outro
    IntroScene.tsx          # (ex IntroLogo.tsx, affiné)
    TransitionLabel.tsx     # Labels entre actes
    OutroScene.tsx          # (ex OutroCTA.tsx, affiné)
  ui/                      # Composants UI reproduisant Niamoto
    AppWindow.tsx           # Frame macOS + sidebar
    Sidebar.tsx             # Navigation latérale
    MockCard.tsx            # Card générique
    MockInput.tsx           # Champ texte animable
    MockButton.tsx          # Bouton avec états
    MockTree.tsx            # Arborescence (site builder)
    MockPreviewPanel.tsx    # Panneau de prévisualisation
    FileUploadZone.tsx      # Zone d'upload avec types
    FileTypeChip.tsx        # Chip de type de fichier coloré
    ProgressBar.tsx         # Barre de progression
    YamlPreview.tsx         # Bloc de code YAML
  cursor/                  # Système de curseur animé
    SimulatedCursor.tsx     # Curseur macOS animé (via remocn ou custom)
    CursorPath.ts           # Définition des trajets de Bézier
  shared/                  # Existant : theme, fonts, config
    theme.ts
    fonts.ts
    config.ts
    DESIGN_SYSTEM.md        # Référence visuelle pour l'IA
  compositions/
    MarketingLandscape.tsx  # Composition principale (refactorisée)
  Root.tsx
```

## Acte 3 — Import (détail)

L'import est l'acte le plus technique à montrer simplement. Voici le déroulé :

### Séquence "File Type Parade"

1. Zone d'upload vide avec bordure pointillée et icône Upload au centre
2. Trois chips de fichier glissent depuis la gauche, staggerés :
   - **Bleu** (icône Table2) → `.csv` — "Données tabulaires"
   - **Vert** (icône Map) → `.gpkg` `.geojson` — "Données spatiales"
   - **Violet** (icône Globe) → `.tif` — "Données raster"
3. Les chips atterrissent dans la zone, pulse léger
4. Le curseur survole la zone → clic → les chips se transforment en liste de fichiers sélectionnés
5. Icône Sparkles apparaît → texte "Auto-configuration" → transition
6. Aperçu YAML qui monte en slide-up

Les couleurs et icônes correspondent exactement au code réel (`FileUploadZone.tsx`).

## Bibliothèques et outils

| Outil | Usage |
|-------|-------|
| **Remotion 4.0.448** | Framework vidéo React |
| **remocn** | SimulatedCursor, SpringPopIn, BlurReveal, DirectionalWipe, ShimmerSweep |
| **@remotion/transitions** | TransitionSeries pour l'enchaînement des scènes |
| **@remotion/fonts** | Chargement local Plus Jakarta Sans + JetBrains Mono |
| **Plus Jakarta Sans** | Police d'affichage (déjà installée) |
| **JetBrains Mono** | Police mono pour code/paths (déjà installée) |

### remocn — composants ciblés

- **SimulatedCursor** : curseur animé avec trail optionnel, click ripple
- **SpringPopIn** : entrée springy pour les éléments UI
- **BlurReveal** : révélation avec blur pour les moments forts
- **DirectionalWipe** : transition entre actes
- **ShimmerSweep** : effet shimmer sur les éléments en chargement

Les composants UI Niamoto (AppWindow, Sidebar, Cards, etc.) restent entièrement custom car ils reproduisent une interface spécifique.

## Thème visuel (résumé)

| Propriété | Valeur |
|-----------|--------|
| Background principal | `#1E1E22` (charcoal) |
| Vert primaire | `#4BAF50` (lightGreen) |
| Vert foncé | `#2E7D32` (forestGreen) |
| Bleu accent | `#3FA9F5` (steelBlue) |
| Texte principal | `#FAFAFA` (textWhite) |
| Texte secondaire | `#9CA3AF` (textMuted) |
| Cards | `#2A2A2E` (cardDark) |
| Police display | Plus Jakarta Sans (400-700) |
| Police mono | JetBrains Mono (400-500) |
| Border radius | 7px (frond theme) |

## Ce qu'on garde de l'existant

- `theme.ts`, `fonts.ts` — inchangés
- `config.ts` — durées à recalculer pour 6 actes + transitions
- `IntroLogo.tsx` → renommé `IntroScene.tsx`, affiné
- `OutroCTA.tsx` → renommé `OutroScene.tsx`, affiné
- Infrastructure Remotion (package.json, tsconfig, remotion.config)

## Ce qu'on supprime

- `StatsOrMap.tsx` — scène de stats, pas pertinente
- `PipelineAnimated.tsx` — remplacé par le parcours réel
- `ScreencastBlock.tsx` — plus de screencasts
- `SCRIPT.md`, `STORYBOARD.md` — à réécrire

## Décisions clés

1. **Motion graphics > screencasts** — Plus engageant, contrôle total sur le rythme et le rendu
2. **Semi-fidèle > pixel-perfect** — On veut que ce soit reconnaissable, pas une copie CSS complète
3. **6 actes linéaires** — Parcours complet sans dashboard, storytelling clair
4. **Desktop window frame** — Ancre visuellement le contexte "application"
5. **Curseur simulé** — Rend l'interaction tangible sans screencast
6. **Design System MD** — Référence unique pour maintenir la cohérence visuelle
7. **remocn pour les primitives** — Pas réinventer le curseur et les transitions
8. **Custom pour l'UI Niamoto** — Les composants spécifiques restent maison

## Questions résolues

- Import : "File Type Parade" avec chips colorés glissant dans la zone d'upload
- Dashboard : supprimé du parcours
- Habillage : minimaliste et poli, pas de transitions spectaculaires
- Fidelité : semi-fidèle (reconnaissable mais simplifié)
