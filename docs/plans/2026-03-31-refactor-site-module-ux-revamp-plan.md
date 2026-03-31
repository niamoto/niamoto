---
title: "refactor: Site module UX revamp — unified view + first-launch experience"
type: refactor
date: 2026-03-31
brainstorm: docs/brainstorms/2026-03-31-site-module-ux-revamp-brainstorm.md
---

# refactor: Site module UX revamp

## Overview

Refonte UX du module Site dans le GUI Niamoto. Deux problèmes d'ergonomie à résoudre : (1) la friction entre les sections Pages et Navigation qui oblige à des allers-retours, et (2) un démarrage laborieux pour les nouveaux projets. Solution : vue unifiée pages+navigation + expérience premier lancement avec presets.

**Scope** : GUI uniquement — aucun changement backend ni API. Trois sous-phases structurelles puis une phase first-launch.

## Brainstorm Reference

Toutes les décisions UX sont documentées dans le [brainstorm](../brainstorms/2026-03-31-site-module-ux-revamp-brainstorm.md).

| Décision | Choix |
|----------|-------|
| Pages + Navigation | Vue unifiée (une seule liste) |
| Collections | Draggables, nestables sous pages statiques |
| Premier lancement | Presets + auto-adaptation aux collections |
| Settings / Apparence | Boutons toolbar |
| Footer | Fonction de regénération one-shot (pas de mode auto permanent) |
| Preview | Inchangé |
| Vocabulaire | Inchangé |

---

## Décisions d'architecture

### D1. Source de vérité = arbre unifié (architecture cible, atteinte en Phase C)

L'objectif est que l'arbre unifié (`UnifiedTreeItem[]`) **remplace** `editedNavigation` et `editedPages` comme unique état de travail pour la structure du site. Ce basculement se fait **progressivement** :

- **Phase B** : l'arbre unifié est une **projection read-only** calculée depuis `editedNavigation` + `editedPages` (qui restent la source de vérité). L'arbre sert uniquement à l'affichage.
- **Phase C** : l'arbre unifié **devient** la source de vérité. `editedNavigation` et `editedPages` disparaissent. Le save décompose l'arbre vers l'API.

```
Phase B (read-only) :
  editedNavigation + editedPages  ← source de vérité
           ↓
  buildUnifiedTree()  → affichage seulement

Phase C (cible) :
  API load → buildUnifiedTree() → [UnifiedTreeItem[]]  ← source de vérité
                                          ↓
                                   mutations directes (drag, toggle, add, delete)
                                          ↓
  Save → decomposeUnifiedTree() → { navigation[], static_pages[] } → PUT /site/config
```

**Conséquences (Phase C) :**
- `editedNavigation` et `editedPages` disparaissent de SiteBuilder
- `editedSite` (settings) et `editedFooterNavigation` restent séparés (préoccupations indépendantes)
- `hasChanges` compare `unifiedTree` vs `buildUnifiedTree(siteConfig)` au lieu de 4 JSON.stringify
- Le hook `useUnifiedSiteTree` expose : `tree`, `setTree`, `buildFromConfig()`, `decomposeForSave()`

**Modèle de données frontend :**

```typescript
type UnifiedTreeItem = {
  id: string
  type: 'page' | 'collection' | 'external-link'
  label: LocalizedString
  visible: boolean          // dans le menu ou masqué
  pageRef?: string          // nom de la StaticPage liée (type 'page')
  collectionRef?: string    // nom du groupe lié (type 'collection')
  url?: string              // URL pour les liens externes
  template?: string         // template de la page (type 'page')
  hasIndex?: boolean        // collection avec index_output_pattern (type 'collection')
  children: UnifiedTreeItem[]
}
```

### D2. Collections sans index = non-menuables

Une collection sans `index_output_pattern` **apparaît dans l'arbre** (section "Hors menu") mais **ne peut pas être rendue visible** (`visible: true` interdit).

| État collection | Dans l'arbre | Menuable | Action au toggle/drag vers menu |
|----------------|-------------|----------|-------------------------------|
| Avec `index_output_pattern` | Oui | Oui | Normal |
| Sans `index_output_pattern` | Oui (grisée) | Non | Dialog "Activer la page d'index ?" → `useUpdateGroupIndexConfig` |

Cela aligne le plan avec le filtre existant de `NavigationBuilder.tsx:650` (`groups.filter(g => g.index_output_pattern)`) et évite de promettre plus que ce que le modèle supporte.

### D3. Footer = regénération one-shot, pas de mode auto

Le backend stocke `footer_navigation: FooterSection[]` — un tableau concret, pas de flag "auto". Il n'y a **pas de mode footer** :

- **Fonction `generateFooterFromTree()`** : calcule un `FooterSection[]` depuis l'arbre unifié et l'écrit dans `editedFooterNavigation`
- **Bouton "Regénérer le footer"** : appelle cette fonction. L'utilisateur voit le résultat et peut ensuite l'éditer manuellement via `FooterSectionsEditor` (qui reste inchangé)
- **Presets** : appellent `generateFooterFromTree()` lors de l'application pour pré-remplir le footer
- **Sites existants** : aucun changement, leur `footer_navigation` reste tel quel

Pas de toggle auto/manuel. Pas de mode détaché. Pas de réconciliation. Le footer est toujours un tableau concret éditable.

### D4. Généricité des pages de présentation

Quand un preset génère une page de présentation pour une collection, le **nom par défaut = nom de la collection** (ex: collection "taxons" → page "Taxons"). Pas de mapping métier ("Taxons" → "Flore") — ce serait non-générique. L'utilisateur renomme manuellement s'il veut.

---

## Règles critiques

### NE PAS MODIFIER (contrat API backend)

- `SiteConfigResponse` / `SiteConfigUpdate` — interfaces API (`useSiteConfig.ts:185-193`)
- Endpoints : `GET/PUT /site/config`, `GET /site/groups`, `GET /site/templates`
- Structure `export.yml` : `static_pages[]`, `navigation[]`, `footer_navigation[]`
- `GroupInfo`, `GroupIndexConfig` — interfaces API (`useSiteConfig.ts:222-228`)
- Routes URL : `/site/*` — inchangées

### Gestion des cas limites

| Cas | Comportement |
|-----|-------------|
| Page sans lien navigation | Section "Hors menu" en bas de la liste |
| Nav item vers URL externe | Item type `'external-link'` dans la liste |
| Nav item vers URL inconnue | Item type `'external-link'` (fallback) |
| Collection avec index | Draggable, menuable, icône verte |
| Collection sans index | Présente mais grisée, non-menuable, dialog d'activation au clic |
| Collection ajoutée après config | Apparaît automatiquement dans "Hors menu" |
| Collection supprimée | Retirée silencieusement de l'arbre au prochain load |
| Footer existant | Conservé tel quel. Bouton "Regénérer" disponible |
| Nouveau site (preset) | Footer pré-rempli par `generateFooterFromTree()` |

---

## Phase A — Extraction sans changement de comportement

Décomposer le monolithe SiteBuilder.tsx. Aucun changement UX visible. Le module fonctionne exactement comme avant après cette phase.

### A1. Extraire les sous-composants de SiteBuilder

Actuellement SiteBuilder.tsx = 1566 lignes avec tout inline.

- [x] Extraire `SiteBuilderToolbar.tsx` (~100 lignes) :
  - Boutons Save, Preview toggle, Device switcher
  - Indicateur changements non-sauvegardés
  - Props : `{ hasChanges, onSave, previewEnabled, onTogglePreview, previewDevice, onDeviceChange }`
  - *Note : toolbar gardée inline dans SiteBuilder pour l'instant, sera extraite en Phase C quand les 3 boutons settings/theme/footer seront ajoutés*
- [x] Extraire `SiteBuilderEditor.tsx` (~200 lignes) :
  - Le switch `renderEditor()` (8 cas : null, general, appearance, navigation, footer, page, group, new-page)
  - Props : `{ selection, editedSite, ..., handlers }`
  - *Note : renderEditor gardé inline, sera refactorisé en Phase C avec le changement de source de vérité*
- [x] Extraire `SiteBuilderPreview.tsx` (~150 lignes) :
  - Iframe de preview + logique de chargement template/group-index
  - Props : `{ selection, previewDevice, previewHtml, ... }`
- [x] Extraire `PagesOverview.tsx` (~240 lignes) :
  - Le contenu inline (lignes ~418-659) quand `selection === null`
  - Cards de pages + collections
- [x] Extraire `useSiteBuilderState.ts` (~200 lignes) :
  - Les 4 états (`editedSite`, `editedNavigation`, `editedFooterNavigation`, `editedPages`)
  - Les handlers (`handleSave`, `handleAddPage`, `handleDeletePage`, `handleUpdatePage`, `handleDuplicatePage`)
  - La logique `hasChanges`
  - Le sync `useEffect` depuis `siteConfig`

**Résultat :** `SiteBuilder.tsx` passe de ~1566 à ~300 lignes. C'est un orchestrateur avec `ResizablePanelGroup` qui compose les sous-composants. **Aucun changement de comportement.**

### A2. Validation extraction

- [x] `pnpm build` compile
- [ ] Vérifier visuellement que le module Site fonctionne exactement comme avant
- [ ] Toutes les sections de l'arbre fonctionnent
- [ ] Save/preview/navigation inchangés

---

## Phase B — Vue unifiée read-only

Remplacer le panneau gauche (arbre accordion) par la liste unifiée. Pas encore d'édition (drag, toggle) — juste l'affichage et la sélection.

### B1. Hook `useUnifiedSiteTree`

- [x] Créer `features/site/hooks/useUnifiedSiteTree.ts`
- [x] Type `UnifiedTreeItem` (voir section D1)
- [x] `buildUnifiedTree(navigation, staticPages, groups) → UnifiedTreeItem[]` :
  1. Parcourir `navigation[]` en ordre
  2. Pour chaque item : matcher par URL avec `staticPages` ou `groups` → créer `UnifiedTreeItem` avec le bon type
  3. Les enfants de nav items → `children[]` de l'item parent
  4. Pages orphelines (dans `staticPages` mais pas dans `navigation`) → items `visible: false` en fin de liste
  5. Collections non-référencées dans la nav → items `visible: false`, avec `hasIndex: !!group.index_output_pattern`
- [x] `decomposeUnifiedTree(tree) → { navigation: NavigationItem[], staticPages: StaticPage[] }` :
  1. Items `visible: true` au root + leurs children → `navigation[]` avec `text`, `url`, `children`
  2. Tous les items `type: 'page'` → `staticPages[]` dans l'ordre de l'arbre
- [ ] Tests unitaires du round-trip (à faire en Phase C quand l'arbre devient source de vérité) :
  - Config vide → arbre vide → config vide
  - Config avec nav + pages matchées → arbre → décompose → identique
  - Config avec pages orphelines → arbre avec section hors-menu → décompose → pages préservées
  - Config avec nav pointant vers URLs externes → arbre avec external-links → décompose → nav préservée
  - Config avec nav children → arbre avec nesting → décompose → children préservés

### B2. Composant `UnifiedSiteTree` (lecture seule)

- [x] Créer `features/site/components/UnifiedSiteTree.tsx`
- [x] Affiche la liste issue de `buildUnifiedTree()`
- [ ] Pour chaque item :
  - Icône selon le type (`FileText` page, `Layers` collection, `ExternalLink` externe)
  - Label : nom de page, nom de collection, ou texte du lien
  - Badge template pour les pages (comme dans `SiteTreeView` actuel)
  - Indicateur visuel `visible` / "Hors menu" (badge discret, pas de toggle encore)
  - Pour les collections sans index : icône grisée + tooltip "Index page not configured"
- [ ] Indentation visuelle pour les children (padding-left)
- [ ] Séparateur visuel avant les items "Hors menu"
- [ ] Clic sur un item → `onSelect(item)` callback → SiteBuilder affiche l'éditeur correspondant dans le panneau central

### B3. Intégrer dans SiteBuilder

- [x] Dans `SiteBuilder.tsx` :
  - Remplacer l'accordion `SiteTree` (panneau gauche) par `<UnifiedSiteTree>`
  - Mapper la sélection d'un `UnifiedTreeItem` vers le type `Selection` existant (`SiteBuilder.tsx:118-122` — `{ type: SelectionType, id?: string }`) :
    - `type: 'page'` → `{ type: 'page', id: item.pageRef }`
    - `type: 'collection'` → `{ type: 'group', id: item.collectionRef }`
    - `type: 'external-link'` → `{ type: 'external-link', id: item.id }` (nouveau cas à ajouter dans `SelectionType` et `renderEditor`)
  - Garder les sections Settings/Appearance dans le tree **pour l'instant** (elles migrent en Phase C)
  - L'arbre affiche les items mais le save passe encore par `editedNavigation` + `editedPages` (la migration vers l'arbre comme source de vérité se fait en Phase C)

### B4. i18n vue unifiée

- [x] Nouvelles clés dans `en/site.json` et `fr/site.json` :
  - `unifiedTree.notInMenu` — "Not in menu" / "Hors menu"
  - `unifiedTree.noIndexPage` — "Index page not configured" / "Page d'index non configurée"
  - `unifiedTree.enableIndex` — "Enable index page" / "Activer la page d'index"

### B5. Validation vue read-only

- [x] `pnpm build` compile
- [ ] L'arbre affiche toutes les pages, collections et liens externes
- [ ] Les pages orphelines apparaissent dans "Hors menu"
- [ ] Les collections sans index sont grisées
- [ ] Cliquer un item ouvre le bon éditeur dans le panneau central
- [ ] Le save fonctionne (round-trip via ancien état)

---

## Phase C — Vue unifiée avec édition

La source de vérité bascule vers l'arbre unifié. Drag-and-drop, toggle visibilité, et décomposition pour le save.

### C1. Source de vérité → arbre unifié

- [ ] Dans `useSiteBuilderState.ts` :
  - Remplacer `editedNavigation` + `editedPages` par un seul état : `unifiedTree: UnifiedTreeItem[]`
  - Au load (sync useEffect) : `setUnifiedTree(buildUnifiedTree(siteConfig.navigation, siteConfig.static_pages, groups))`
  - `hasChanges` : comparer `unifiedTree` vs `buildUnifiedTree(siteConfig...)` (une seule comparaison au lieu de 4)
  - `handleSave` : appeler `decomposeUnifiedTree(unifiedTree)` → injecter dans `SiteConfigUpdate`
- [ ] `editedSite` et `editedFooterNavigation` restent des états séparés (préoccupations indépendantes)
- [ ] Mettre à jour les handlers de page (add, delete, duplicate, update) pour muter `unifiedTree` au lieu de `editedPages` + `editedNavigation`
- [ ] **Adapter les props de `StaticPageEditor`** : ce composant reçoit aujourd'hui `navigation` et `onUpdateNavigation` (`StaticPageEditor.tsx:92,100`) pour le lien page↔menu. En Phase C, ces props sont remplacées par des callbacks qui mutent l'arbre unifié :
  - `isInMenu(pageName) → boolean` : dérivé de `unifiedTree` (cherche l'item page et retourne `visible`)
  - `onToggleMenu(pageName)` : bascule `visible` sur l'item correspondant dans `unifiedTree`
  - Le reste de l'interface `StaticPageEditor` (édition contenu, template, markdown) reste inchangé

### C2. Toggle visibilité menu

- [ ] Dans `UnifiedSiteTree.tsx`, ajouter un bouton toggle par item :
  - `Eye` / `EyeOff` (lucide-react)
  - Clic → `item.visible = !item.visible` → mutate `unifiedTree`
  - Pour les collections sans index : le toggle est **disabled**. Clic → Dialog "Activer la page d'index pour cette collection ?" avec bouton qui appelle `useUpdateGroupIndexConfig`
- [ ] Quand un item passe de visible → masqué : il se déplace dans la section "Hors menu"
- [ ] Quand un item passe de masqué → visible : il se déplace à la fin de la section menu

### C3. Drag-and-drop avec nesting

- [ ] Réutiliser `@dnd-kit` (déjà installé via `NavigationBuilder`)
- [ ] Approche flattened tree :
  - `flattenTree(tree) → FlatItem[]` avec `parentId`, `depth`, `index`
  - `buildTreeFromFlat(flatItems) → UnifiedTreeItem[]`
- [ ] `getProjection(flatItems, activeId, overId, offsetLeft)` :
  - Calcule `projectedDepth` depuis l'offset horizontal
  - Clamp : `Math.min(projectedDepth, 1)` — max 1 niveau de nesting
  - Calcule `projectedParentId`
- [ ] Règles de drop :
  - Un item peut être nesté sous un autre item **de profondeur 0** uniquement
  - Une collection sans index ne peut pas être nestée sous un item menu (elle reste en "Hors menu")
  - Les items "Hors menu" ne peuvent pas recevoir d'enfants
- [ ] Indicateurs visuels :
  - Ligne d'insertion horizontale (position)
  - Décalage de la ligne (indentation = nesting)
  - Ghost semi-transparent de l'item dragué
- [ ] Sensors : `PointerSensor` (activationConstraint: distance 8px) + `KeyboardSensor`
- [ ] `handleDragEnd` : recalcule l'arbre depuis les flat items + projection, met à jour `unifiedTree`

### C4. Ajout et suppression d'items

- [ ] Bouton "+ Page" en bas de la liste menu :
  - Ouvre `TemplateList` dans le panneau central
  - Après sélection du template → crée la `StaticPage` + l'ajoute à l'arbre (`visible: true`)
- [ ] Bouton "+ Lien externe" en bas de la liste menu :
  - Crée un item `type: 'external-link'` avec texte et URL éditables inline
- [ ] Suppression d'un item page : supprime le `StaticPage` et le retire de l'arbre
- [ ] Suppression d'un lien externe : retire de l'arbre
- [ ] Les collections ne sont pas supprimables (viennent de l'export config)

### C5. Édition inline des liens externes

- [ ] Quand un item `type: 'external-link'` est sélectionné :
  - Le panneau central affiche un formulaire simple : texte (LocalizedInput) + URL
  - Pas besoin de composant dédié — un petit formulaire inline suffit

### C6. Toolbar Settings, Apparence & Footer

Trois boutons dans la toolbar, au même niveau, pour les préoccupations globales du site :

- [ ] Ajouter trois boutons dans `SiteBuilderToolbar.tsx` :
  - Bouton engrenage (`Settings`) → sélection `{ type: 'general' }` → `SiteConfigForm` dans le panneau central
  - Bouton palette (`Paintbrush`) → sélection `{ type: 'appearance' }` → `ThemeConfigForm` dans le panneau central
  - Bouton footer (`PanelBottom`) → sélection `{ type: 'footer' }` → `FooterSectionsEditor` dans le panneau central, avec un bouton "Regénérer" en haut du formulaire
- [ ] Retirer les sections "Settings", "Appearance" et "Footer" de `UnifiedSiteTree` (l'arbre ne contient que les pages et collections)
- [ ] État visuel : bouton avec `variant="secondary"` quand la section correspondante est active

### C7. Footer regénération

- [ ] Créer `features/site/utils/generateFooter.ts`
- [ ] `generateFooterFromTree(tree, siteSettings) → FooterSection[]` :
  - Colonne "Navigation" → les items `visible: true` de profondeur 0 (sauf accueil)
  - Colonne "Collections" → les items `type: 'collection'` visibles
  - Copyright → `siteSettings.title` + année courante
- [ ] Bouton "Regénérer le footer depuis la structure" en haut du `FooterSectionsEditor` (quand ouvert via toolbar) :
  - Appelle `generateFooterFromTree()` → remplace `editedFooterNavigation`
  - Confirmation avant écrasement si le footer n'est pas vide
  - L'utilisateur voit le résultat et peut éditer manuellement ensuite
- [ ] Les presets appellent cette fonction pour pré-remplir le footer initial

### C8. Presets de site

- [ ] Créer `features/site/data/sitePresets.ts`
- [ ] 3 presets :

**Minimaliste** : Accueil (index.html) + collections détectées (top-level, visible si index existe)

**Scientifique** : Accueil + Méthodologie (page.html) + Équipe (team.html) + Bibliographie (bibliography.html) + Contact (contact.html) + collections

**Complet** : Accueil + Méthodologie + Équipe + Ressources (resources.html) + Bibliographie + Glossaire (glossary.html) + Contact + collections

- [ ] `applySitePreset(preset, groups) → { tree: UnifiedTreeItem[], footerSections: FooterSection[], site: Partial<SiteSettings> }` :
  - Crée les `UnifiedTreeItem` pages avec `visible: true`
  - Ajoute les collections : une par item top-level si elles ont un index, sinon dans "Hors menu"
  - Le nom de la page de présentation = nom de la collection (pas de mapping métier)
  - Appelle `generateFooterFromTree()` pour le footer
  - Retourne un thème par défaut (neutral)
- [ ] UI sélecteur : affiché dans le panneau central quand le `siteConfig` initial chargé depuis l'API a `static_pages.length === 0 && navigation.length === 0` (condition évaluée sur les données API, pas sur l'état local édité)
  - 3 cartes + option "Partir de zéro"
  - Après sélection : remplit `unifiedTree` + `editedFooterNavigation` + `editedSite`
  - L'utilisateur voit le résultat et peut modifier avant de sauvegarder

### C9. Routing

- [ ] `/site/navigation` → redirect vers `/site/pages` (la section Navigation n'existe plus)
- [ ] `/site/general` et `/site/appearance` → `SiteBuilder` avec le bouton toolbar correspondant pré-activé
- [ ] Mettre à jour `navigationStore.ts` : retirer le breadcrumb "Navigation"
- [ ] `SiteNavigationPage.tsx` → `Navigate to="/site/pages"`

### C10. i18n compléments

- [ ] Clés supplémentaires `unifiedTree.*` :
  - `unifiedTree.addPage` — "Add page" / "Ajouter une page"
  - `unifiedTree.addExternalLink` — "Add external link" / "Ajouter un lien externe"
  - `unifiedTree.inMenu` — "In menu" / "Dans le menu"
  - `unifiedTree.hidden` — "Hidden" / "Masqué"
  - `unifiedTree.dragToReorder` — "Drag to reorder" / "Glisser pour réordonner"
- [ ] Clés `toolbar.*` :
  - `toolbar.settings` / `toolbar.theme` / `toolbar.footer`
- [ ] Clés `presets.*` :
  - `presets.title`, `presets.minimal`, `presets.scientific`, `presets.complete`, `presets.startFromScratch`
  - Descriptions courtes pour chaque preset
- [ ] Clés `footer.*` :
  - `footer.regenerate` — "Regenerate footer" / "Regénérer le footer"
  - `footer.regenerateConfirm` — "This will replace your current footer" / "Cela remplacera votre footer actuel"

### C11. Validation Phase C

- [ ] `pnpm build` compile
- [ ] Round-trip : modifier la liste → save → reload → identique
- [ ] Drag-and-drop : réordonner, nester (1 niveau), dé-nester
- [ ] Toggle visibilité : masquer/afficher du menu
- [ ] Collection sans index : toggle disabled, dialog d'activation
- [ ] Collection avec index activé après dialog → toggle fonctionne
- [ ] Toolbar : Settings, Theme, Footer ouvrent les bons éditeurs
- [ ] Liens externes : ajout, édition inline, suppression
- [ ] Presets : sélection sur site vide, application correcte
- [ ] Footer regénéré : correct et éditable après
- [ ] Migration : site existant (pré-revamp) → tout s'affiche correctement
- [ ] Route `/site/navigation` redirige vers `/site/pages`

---

## Phase D — First-launch experience

Après Phase C. Commit(s) séparé(s).

### D1. Wizard onboarding

- [ ] Créer `features/site/components/SiteSetupWizard.tsx`
- [ ] 4 étapes via `useState` stepper :
  1. **Choisir un modèle** — les 3 presets en cartes (avec miniatures Phase D3)
  2. **Vérifier la structure** — `UnifiedSiteTree` pré-rempli, éditable
  3. **Personnaliser le thème** — `ThemeConfigForm` simplifié (couleurs + logo)
  4. **Aperçu** — preview du site
- [ ] Bouton "Passer" par étape (applique les défauts)
- [ ] Bouton "Passer la configuration" global (preset Minimaliste → save → fin)
- [ ] Condition d'affichage : `siteConfig` initial depuis l'API a `static_pages.length === 0 && navigation.length === 0` (données API, pas état local)
- [ ] Le wizard remplace le contenu du panneau central (pas un modal)
- [ ] Après complétion : save auto → wizard disparaît → module Site normal
- [ ] Bouton "Reconfigurer" dans la toolbar (avertissement destructif avant)

### D2. Miniatures visuelles

- [ ] Créer des SVG statiques dans `features/site/assets/templates/` :
  - Un wireframe simplifié par template (index, page, team, contact, bibliography, resources, glossary)
- [ ] Mettre à jour `TemplateList.tsx` : miniature à côté de l'icône
- [ ] Cartes de preset dans le wizard : miniature composite
- [ ] Fallback : icône actuelle si miniature absente
- [ ] Assets locaux (pas de CDN → fonctionne offline)

### D3. Smart defaults

- [ ] Création de page : templates non-utilisés proposés en premier
- [ ] `output_file` pré-rempli depuis le template choisi
- [ ] Nouvelles pages : `visible: true` par défaut
- [ ] Nesting d'une collection : proposer l'activation de l'index generator si pas fait

### D4. i18n wizard

- [ ] Clés `wizard.*` : title, step1-4, skip, skipAll, finish, reconfigure, reconfigureWarning

### D5. Validation Phase D

- [ ] `pnpm build` compile
- [ ] Wizard complet : 4 étapes, save en fin
- [ ] Wizard avec collections : pages de présentation = nom de la collection
- [ ] Wizard sans collections : pages statiques uniquement
- [ ] "Passer la config" : preset Minimaliste appliqué
- [ ] Miniatures affichées
- [ ] Mode offline (Tauri) : tout fonctionne
- [ ] Bouton "Reconfigurer" : avertissement + relance

---

## Fichiers impactés — inventaire

### Nouveaux fichiers

| Fichier | Phase | Description |
|---------|-------|-------------|
| `features/site/components/SiteBuilderToolbar.tsx` | A | Toolbar extraite |
| `features/site/components/SiteBuilderEditor.tsx` | A | Panneau éditeur extrait |
| `features/site/components/SiteBuilderPreview.tsx` | A | Panneau preview extrait |
| `features/site/components/PagesOverview.tsx` | A | Vue d'ensemble extraite |
| `features/site/hooks/useSiteBuilderState.ts` | A | État extrait de SiteBuilder |
| `features/site/hooks/useUnifiedSiteTree.ts` | B | Hook merge/decompose |
| `features/site/components/UnifiedSiteTree.tsx` | B | Liste unifiée pages+nav |
| `features/site/utils/generateFooter.ts` | C | Fonction regénération footer |
| `features/site/data/sitePresets.ts` | C | Définition des 3 presets |
| `features/site/components/SiteSetupWizard.tsx` | D | Wizard onboarding |
| `features/site/assets/templates/*.svg` | D | Miniatures templates |

### Fichiers à modifier

| Fichier | Phase | Changement |
|---------|-------|-----------|
| `features/site/components/SiteBuilder.tsx` | A | 1566→~300 lignes (orchestrateur) |
| `features/site/views/SiteNavigationPage.tsx` | C | Redirect vers /site/pages |
| `app/App.tsx` | C | Route navigation → redirect |
| `stores/navigationStore.ts` | C | Retirer breadcrumb "Navigation" |
| `i18n/locales/en/site.json` | B+C+D | Nouvelles clés |
| `i18n/locales/fr/site.json` | B+C+D | Nouvelles clés |
| `features/site/components/StaticPageEditor.tsx` | C | Props navigation→menu adaptées (callbacks unifiedTree) |

### Fichiers conservés tels quels

| Fichier | Raison |
|---------|--------|
| `shared/hooks/useSiteConfig.ts` | Interfaces API — le hook unifié l'enveloppe |
| `features/site/components/GroupPageViewer.tsx` | Viewer collection — inchangé |
| `features/site/components/SiteConfigForm.tsx` | Form settings — inchangé |
| `features/site/components/ThemeConfigForm.tsx` | Form thème — inchangé |
| `features/site/components/FooterSectionsEditor.tsx` | Éditeur footer — inchangé, appelé depuis toolbar |
| `features/site/components/NavigationBuilder.tsx` | Conservé comme référence DnD. Retiré des imports quand UnifiedSiteTree le remplace |
| `features/site/components/forms/*.tsx` | Formulaires templates — inchangés |
| Backend Python | Hors scope |

## Risques et mitigations

| Risque | Mitigation |
|--------|-----------|
| Round-trip lossy | Tests unitaires avec configs variées (orphelines, externes, nesting) |
| DnD nesting complexe | Phase A = extraction pure (pas de DnD). Phase B = read-only. Le DnD n'arrive qu'en Phase C, sur des fondations stables |
| Sites existants cassés | `buildUnifiedTree` est déterministe depuis les données existantes. Phase B = read-only, aucun risque de corruption |
| Collection sans index rendue visible | Guard explicite (D2) : toggle disabled + dialog d'activation |
| Perte de données footer | Pas de mode auto — le footer existant n'est jamais remplacé automatiquement |
| Phase trop large | 4 sous-phases A/B/C/D, chacune livrable et testable indépendamment |
| Performance DnD | Sites écologiques = 5-15 pages. Pas de virtualisation nécessaire |

## Références

- Brainstorm : `docs/brainstorms/2026-03-31-site-module-ux-revamp-brainstorm.md`
- Plan Collections : `docs/plans/2026-03-31-refactor-groups-to-collections-plan.md`
- Frontend architecture : `docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md`
- dnd-kit tree : flattened tree + `getProjection()` pour le nesting
- SiteBuilder état actuel : `editedNavigation` (ligne 805), `editedPages` (807), sync (900-907), save (933-957)
- Collection filter existant : `NavigationBuilder.tsx:650` — `groups.filter(g => g.index_output_pattern)`
- Backend footer : `site.py:320` — `footer_navigation: List[FooterSection] = []`
