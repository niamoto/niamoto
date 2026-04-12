---
title: "refactor: UI density compaction — dense/pro desktop"
type: refactor
date: 2026-04-12
brainstorm: docs/brainstorms/2026-04-12-ui-density-compaction-brainstorm.md
---

# refactor: UI density compaction — dense/pro desktop

## Overview

Compacter l'ensemble des primitives UI et des espacements de page via une première passe modérée, pour passer d'une densité "dashboard SaaS" (contrôles 40px, paddings 24px, titres 30px) à une densité "outil desktop pro" plus fine et plus compacte, sans tomber immédiatement dans une compaction agressive (première cible : contrôles 32px, paddings 16px, titres 20px).

## Problem Statement

L'app Niamoto utilise aujourd'hui un langage visuel web spacieux qui oblige l'utilisateur à agrandir la fenêtre même sur macOS. Les composants sont trop gros (boutons h-10, inputs h-9, cartes p-6, titres text-3xl), ce qui compresse l'espace de travail utile et donne une impression de manque de finesse inadaptée à un outil de productivité scientifique.

## Proposed Solution

Modifier directement les primitives shadcn/ui et les patterns de page, mais en deux temps :

1. une passe modérée sur les primitives cœur, le chrome desktop et les rythmes de page ;
2. une éventuelle passe plus dense uniquement si, après validation visuelle, l'app paraît encore trop grosse.

Pas de préférence utilisateur ni de thème de densité global. En revanche, les rares écrans volontairement spacieux garderont une échelle dédiée via des overrides explicites (`className`, tailles locales, variants existants) au lieu de dépendre des anciens defaults.

## Technical Approach

### Échelle typographique cible

| Usage | Actuel | Cible | Note |
|-------|--------|-------|------|
| Titres de page (h1) | `text-3xl` (30px) | `text-xl` (20px) | `font-semibold` au lieu de `font-bold` |
| Titres de section (h2) | `text-xl` (20px) | `text-base` (16px) | `font-medium` |
| Métriques KPI | `text-3xl` (30px) | `text-2xl` (24px) | Première passe conservatrice |
| Valeurs `text-2xl` existantes | `text-2xl` (24px) | `text-xl` (20px) | |
| Body / données | `text-sm` (14px) | `text-sm` (14px) | `text-[13px]` seulement sur surfaces denses validées |
| Labels / méta / contrôles | `text-sm` (14px) | `text-[13px]` | Éviter `text-xs` global dès la phase 1 |
| Badges, pills | `text-xs` (12px) | `text-xs` (12px) | Inchangé |

### Primitives cibles (Phase 1 modérée)

#### `button.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
default: h-10 px-4 py-2        h-8 px-3 py-1.5
sm:      h-9 px-3              h-7 px-2.5
lg:      h-11 px-8             h-9 px-4
icon:    h-10 w-10             h-8 w-8
text-sm                        text-sm
[&_svg]:size-4                  [&_svg]:size-4
```

> Première passe : on vise 32px pour le bouton par défaut, pas 28px. Les CTA vraiment compacts pourront venir en phase 3 si nécessaire.

#### `card.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
Card: gap-6 py-6               gap-4 py-4
CardHeader: gap-1.5 px-6       gap-1.5 px-4
CardContent: px-6              px-4
CardFooter: px-6               px-4
[.border-b]:pb-6               [.border-b]:pb-4
[.border-t]:pt-6               [.border-t]:pt-4
```

#### `input.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
h-9 px-3 py-1                  h-8 px-3 py-1
text-base md:text-sm            text-sm
```

#### `select.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
Trigger: h-9 px-3 py-2         h-8 px-3 py-1.5
Trigger sm: h-8                h-7
text-sm                        text-sm
Item: py-1.5 pl-2 pr-8         py-1.5 pl-2 pr-8  (INCHANGÉ)
```

> **Items de menu inchangés** : `py-1.5` sur les items de select/dropdown est déjà dense à 13px. Ne pas compresser davantage.

#### `tabs.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
TabsList: h-9 p-[3px]          h-8 p-[2px]
TabsTrigger: px-2 py-1 text-sm px-2 py-0.5 text-sm
```

#### `label.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
text-sm                        text-[13px]
```

#### `badge.tsx`

```
Inchangé : px-2 py-0.5 text-xs — déjà compact.
```

#### `dialog.tsx`

```
INCHANGÉ : p-6 gap-4 — les dialogs gardent leur padding actuel.
```

> Les dialogs contiennent des formulaires complexes (AddSourceDialog, ImportWizard, CombinedWidgetModal). Compresser le padding des dialogs écraserait les formulaires. Exception volontaire.

#### `table.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
text-sm                        text-[13px]
Head: h-10 px-2                h-8 px-2
Cell: p-2                      px-2 py-1.5
```

#### `toggle.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
default: h-9 px-2 min-w-9      h-8 px-2 min-w-8
sm: h-8 px-1.5                 h-7 px-1.5
lg: h-10 px-2.5                h-9 px-2
```

#### `textarea.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
min-h-16 px-3 py-2             min-h-14 px-3 py-1.5
text-base md:text-sm            text-sm
```

#### `accordion.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
Trigger: py-4                   py-3
Content: pb-4 pt-0             pb-3 pt-0
```

#### `sheet.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
INCHANGÉ en phase 1.
```

#### `popover.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
INCHANGÉ en phase 1.
```

#### `command.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
INCHANGÉ en phase 1.
```

#### `alert.tsx` / `alert-dialog.tsx`

```
INCHANGÉ en phase 1.
alert-dialog: INCHANGÉ (même logique que dialog)
```

#### `sidebar.tsx`

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
INCHANGÉ en phase 1.
```

#### Primitives inchangées

- `checkbox.tsx` (`size-4`) — déjà compact
- `radio-group.tsx` (`size-4`) — déjà compact
- `switch.tsx` (`h-[1.15rem] w-8`) — déjà compact
- `slider.tsx` (track `h-1.5`, thumb `size-4`) — déjà compact
- `separator.tsx` — pas de sizing
- `tooltip.tsx` (`px-3 py-1.5 text-xs`) — déjà compact
- `dropdown-menu.tsx` — inchangé en phase 1
- `skeleton.tsx`, `scroll-area.tsx`, `collapsible.tsx`, `resizable.tsx` — pas de sizing direct
- `command.tsx`, `alert.tsx`, `sheet.tsx`, `popover.tsx`, `sidebar.tsx` — reportés à une éventuelle phase 3

### Focus rings (attention)

Le button utilise `ring-offset-2` + `focus-visible:ring-2` = 4px de débordement visuel. À h-8 avec `space-y-4` (16px de gap), le risque est plus faible mais reste à vérifier visuellement sur les écrans pilotes ; si problème, réduire à `ring-1 ring-offset-1`.

### Exemptions — écrans à NE PAS compacter

Ces écrans sont conçus pour être spacieux (première impression, onboarding) :

- `OnboardingView.tsx` — garder `p-6 lg:p-8`, `h-12` CTA, `h-11 w-11` icons
- `WelcomeScreen.tsx` — garder l'échelle actuelle
- `SourcesEmptyState.tsx` — garder `text-3xl`, `space-y-6`
- `ProjectCreationWizard.tsx` — garder la densité actuelle

> **Important** : ces exemptions ne survivront pas à une compaction globale des primitives par simple inertie. Elles doivent recevoir des overrides explicites dans la même phase que les changements de primitives, par exemple :
>
> - CTA onboarding en `size="lg"` + `className="h-12 px-5 text-sm"`
> - cards spacieux avec `className="gap-6 py-6"` / `CardContent className="p-6"`
> - titres hero conservés localement (`text-3xl` / `text-4xl`) sur Welcome/Onboarding
>
> Ce n'est pas un système de densité runtime, seulement une liste d'exceptions codées en dur sur les surfaces d'accueil.

### Pattern de page (Phase 2+3)

Remplacer le pattern récurrent sur tous les écrans outils :

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
container mx-auto space-y-6 p-6    space-y-4 p-4
text-3xl font-bold tracking-tight  text-xl font-semibold
gap-6                              gap-4
max-w-4xl (sur Dashboard)          SUPPRIMER
```

> Supprimer `container mx-auto` sur les écrans outils pour utiliser toute la largeur disponible. Le garder uniquement sur les écrans de lecture/formulaire long (Settings formulaire de config).

### Composant métier : MetricCard

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
CardContent p-4                 CardContent p-4
value: text-3xl font-bold       text-2xl font-semibold
label: text-xs uppercase        text-xs uppercase (INCHANGÉ)
sublabel: text-sm               text-[13px]
```

### Composant métier : NavigationSidebar

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
header: h-14                    h-12
nav items: px-3 py-2.5 text-sm  px-2.5 py-2 text-sm
icons: h-5 w-5                  h-4 w-4
sub-items: px-2 py-1.5 text-xs  px-2 py-1.5 text-xs
footer: p-3                     p-2.5
CmdK hint: text-xs px-2 py-1.5  text-xs px-2 py-1
```

> La largeur de la sidebar (`w-52` / `w-16` compact) ne change pas dans ce chantier.

### Composant métier : TopBar + BreadcrumbNav

```
Actuel                          Cible
─────────────────────────────── ───────────────────────────────
TopBar: h-14                    h-12
BreadcrumbNav: h-9              h-8
```

## Implementation Phases

### Phase 1 : Primitives cœur + exemptions critiques (~10-12 fichiers + 2-4 écrans)

Modifier les composants shadcn/ui dans `src/niamoto/gui/ui/src/components/ui/` :

- [ ] `button.tsx` — h-10→h-8, h-9→h-7, h-11→h-9, icon h-10→h-8. Garder `text-sm`
- [ ] `card.tsx` — gap-6→gap-4, py-6→py-4, px-6→px-4, border conditionals pb-6→pb-4, pt-6→pt-4
- [ ] `input.tsx` — h-9→h-8, garder `text-sm`
- [ ] `select.tsx` — trigger h-9→h-8, h-8→h-7. Items inchangés
- [ ] `tabs.tsx` — h-9→h-8, p-[3px]→p-[2px], garder `text-sm`
- [ ] `label.tsx` — text-sm→text-[13px]
- [ ] `table.tsx` — head h-10→h-8, cell p-2→px-2 py-1.5, texte plus dense si la lisibilité reste bonne
- [ ] `toggle.tsx` — h-9→h-8, h-8→h-7, h-10→h-9
- [ ] `textarea.tsx` — min-h-16→min-h-14, garder `text-sm`
- [ ] `accordion.tsx` — trigger py-4→py-3, content pb-4→pb-3

**Ne pas toucher en phase 1** : badge, checkbox, radio-group, switch, slider, separator, tooltip, skeleton, scroll-area, dialog, alert-dialog, command, alert, sheet, popover, sidebar, dropdown-menu.

Dans cette même phase, restaurer explicitement les exemptions critiques impactées par les nouveaux defaults :

- [ ] `OnboardingView.tsx` — réappliquer les CTA, paddings et titres hero localement
- [ ] `WelcomeScreen.tsx` — réappliquer les grosses CTA, cards et titres hero localement
- [ ] `SourcesEmptyState.tsx` — vérifier que le hero et les CTA gardent une échelle volontairement spacieuse
- [ ] `ProjectCreationWizard.tsx` — vérifier qu'aucun formulaire d'entrée ne devient trop compact

**Vérification** : `cd src/niamoto/gui/ui && pnpm build` doit passer sans erreur.

### Phase 2 : Écrans pilotes + chrome desktop

Appliquer le nouveau pattern de page et ajuster les composants métier :

- [ ] **DashboardView.tsx** — supprimer `max-w-4xl`, `space-y-6`→`space-y-4`, `p-6`→`p-4`, `text-2xl`→`text-xl`
- [ ] **DataExplorer.tsx** — supprimer `container mx-auto`, `space-y-6`→`space-y-4`, `p-6`→`p-4`, `text-3xl`→`text-xl`, `gap-6`→`gap-4`
- [ ] **Settings.tsx** — `space-y-6`→`space-y-4`, `p-6`→`p-4`, `text-3xl`→`text-xl`. Garder `container mx-auto` (formulaire long)

Composants métier associés :
- [ ] **MetricCard.tsx** — value text-3xl→text-2xl, sublabel text-sm→text-[13px]
- [ ] **NavigationSidebar.tsx** — h-14→h-12, items py-2.5→py-2, icons h-5→h-4
- [ ] **TopBar.tsx** — h-14→h-12
- [ ] **BreadcrumbNav.tsx** — h-9→h-8

**Vérification** :

1. `cd src/niamoto/gui/ui && pnpm build`
2. `./scripts/dev/dev_desktop.sh test-instance/niamoto-nc`
3. Vérifier visuellement les 3 écrans pilotes à 1280x900
4. Vérifier aussi les surfaces transverses impactées par les primitives globales :
   - palette de commande (`CommandPalette.tsx`)
   - menus/selects/dropdowns via Settings + ProjectSwitcher
   - tables + textarea via DataExplorer
   - au moins un sheet/panneau latéral et un dialog complexe, par exemple `DashboardConfigEditorSheet` et `AddSourceDialog` ou `CombinedWidgetModal`

Checklist :
- Pas de scroll horizontal
- Pas de troncature gênante
- Focus rings ne chevauchent pas
- Icônes proportionnées dans les boutons
- Texte lisible à 13-14px
- Command palette, menus, sheets et dialogs restent utilisables

### Phase 3 : Propagation du pass modéré

Appliquer le pattern `space-y-6→space-y-4, p-6→p-4, text-3xl→text-xl, gap-6→gap-4` sur :

- [ ] `features/import/` — ImportWizard, SourcesOverview, StageCard, VerificationView, EnrichmentView, DatasetDetailPanel, ReferenceDetailPanel
- [ ] `features/collections/` — CollectionsOverview, CollectionPanel, API settings associés
- [ ] `features/site/` — SiteBuilder, StaticPageEditor, PagesOverview, formulaires de configuration
- [ ] `features/publish/` — `views/index.tsx`, `views/deploy.tsx`, `views/history.tsx`
- [ ] `features/tools/` — ConfigEditor, LivePreview, Plugins, ApiDocs
- [ ] `features/dashboard/` — DashboardView et composants métier associés
- [ ] `features/import/module/` — DataModule et son shell

**Exemptions confirmées** :
- [ ] Vérifier que OnboardingView, SourcesEmptyState, ProjectCreationWizard gardent leur densité

**Vérification finale** : parcourir chaque module dans l'app desktop, vérifier qu'aucun écran n'est cassé.

### Phase 4 : Second pass optionnel si l'app paraît encore trop grosse

Uniquement si la phase 3 reste insuffisante visuellement :

- [ ] tester `button` par défaut à `h-7`
- [ ] tester labels/navigation en `text-xs`
- [ ] tester `Card` en `p-3` / `gap-3`
- [ ] tester `TopBar` à `h-10`
- [ ] tester `BreadcrumbNav` à `h-7`
- [ ] compacter ensuite `command.tsx`, `dropdown-menu.tsx`, `sheet.tsx`, `popover.tsx`, `alert.tsx`, `sidebar.tsx`

Cette phase doit être validée visuellement avant d'être propagée partout.

## Acceptance Criteria

- [ ] Les surfaces de travail desktop utilisent des contrôles compacts (button, input, select, tabs) à 32-36px de hauteur par défaut
- [ ] Le body text des surfaces de travail desktop reste lisible à 13-14px, sans basculer trop tôt tout le produit en 12px
- [ ] Les titres de page des surfaces de travail desktop sont en `text-xl` (20px) maximum lors du premier pass, sauf exemptions documentées
- [ ] Les cartes des surfaces de travail desktop utilisent `p-4` et `gap-4` par défaut lors du premier pass
- [ ] Les écrans outils utilisent toute la largeur disponible, sauf exceptions documentées de type formulaire long centré (`Settings`) ou écrans d'accueil/onboarding
- [ ] Les dialogs gardent leur padding actuel (p-6)
- [ ] L'onboarding, WelcomeScreen et les empty states explicitement exemptés gardent leur échelle spacieuse via des overrides locaux
- [ ] `cd src/niamoto/gui/ui && pnpm build` passe sans erreur
- [ ] Aucun scroll horizontal à 1280x900
- [ ] L'app est visuellement cohérente — pas de mélange ancien/nouveau sizing

## Dependencies & Risks

**Risque principal** : régression visuelle large. Chaque primitive impacte des dizaines de fichiers. Mitigation : phase 1 plus conservatrice, puis phase 2 permet de valider le rendu avant propagation.

**Risque focus rings** : à vérifier visuellement en phase 2. Fallback : `ring-1 ring-offset-1` si chevauchement.

**Risque 13px** : valeur arbitraire Tailwind (`text-[13px]`). Si ça pose des problèmes de consistance, fallback à `text-sm` (14px) sur davantage de surfaces.

**Risque de sur-compaction** : si la phase 4 est engagée trop tôt, l'app peut perdre en lisibilité et en hiérarchie visuelle. La traiter comme un chantier séparé, pas comme une conséquence automatique.

**Aucune dépendance externe** — tout est local au frontend.

## References

- Brainstorm : `docs/brainstorms/2026-04-12-ui-density-compaction-brainstorm.md`
- Primitives UI : `src/niamoto/gui/ui/src/components/ui/` (38 fichiers, ~20 à modifier)
- Écrans pilotes : `DashboardView.tsx`, `DataExplorer.tsx`, `Settings.tsx`
- Windows Fluent Compact sizing : recommande densité compacte pour apps riches en information
- Apple HIG macOS Layout : recommande fenêtres flexibles avec contenu dense
