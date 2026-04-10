---
title: Enrichment Tab UX Redesign
type: refactor
date: 2026-04-10
brainstorm: docs/brainstorms/2026-04-10-enrichment-tab-ux-redesign-brainstorm.md
---

# Enrichment Tab UX Redesign

## Overview

Refonte de l'onglet "Enrichissement API" pour passer d'un composant monolithique de 3887 lignes avec scrolls imbriqués à un layout 3 colonnes redimensionnables avec sections accordéon. L'objectif est d'éliminer le scroll-dans-le-scroll et de rendre le cycle config → test → résultats visible d'un coup.

## Problem Statement

L'`EnrichmentTab.tsx` actuel (3887 lignes) concentre tous les problèmes UX classiques d'un composant qui a grandi organiquement :

- **14+ zones scrollables imbriquées** avec hauteurs en dur (7× `max-h-[420px]`, 2× `max-h-[360px]`, `h-[220px]`, `max-h-[620px]`, `max-h-[60vh]`, 9× `overflow-auto` brut)
- **Sous-onglets config/preview/results** qui obligent à naviguer en aveugle (on perd le contexte en switchant)
- **Sidebar 280px fixe** (CSS grid ligne 3204) alors que le reste de l'app utilise `ResizablePanelGroup`
- **~29 useState + ~10 useMemo** non extraits, état monolithique
- **Deux chemins de rendu complets** (quick mode ligne 2449, workspace mode ligne 2992)
- **Mix incohérent** de Radix ScrollArea et `overflow-auto` natif

## Proposed Solution

Layout 3 colonnes avec `ResizablePanelGroup` + config en accordéons + résultats toujours visibles.

```
┌──────────┬─────────────────────────────┬──────────────────────┐
│ Sources  │ [Start] [Pause] [Cancel]    │ Résultats / Preview  │
│          │─────────────────────────────│                      │
│ ● GBIF   │ ▼ Connexion                 │ ┌ Dernier test ────┐ │
│   12/21  │   URL: https://api.gbif...  │ │ ✔ Araucaria      │ │
│   ██░░░  │   Preset: [GBIF Rich ▾]    │ │ ✔ Agathis        │ │
│          │                             │ │ ✖ Ficus (timeout) │ │
│ ○ COL    │ ▶ Authentification          │ └──────────────────┘ │
│   0/21   │                             │                      │
│          │ ▼ Options profil            │ ┌ Tester ──────────┐ │
│ ○ BHL    │   ☑ Inclure synonymes      │ │ Entité: [______]  │ │
│   actif  │   ☑ Inclure distributions  │ │ [Lancer test]     │ │
│          │   ☐ Inclure media          │ └──────────────────┘ │
│ ○ iNat   │                             │                      │
│          │ ▶ Mapping avancé            │ Stats: 12/21 (57%)  │
│          │                             │ Erreurs: 3          │
│ [+ Ajout]│ [Sauver]  ● non sauvegardé │ Temps: 2m34s        │
└──────────┴─────────────────────────────┴──────────────────────┘
```

## Technical Approach

### Architecture cible

```
features/import/components/enrichment/
  EnrichmentTab.tsx              -- Orchestrateur (~250 lignes)
  SourceSidebar.tsx              -- Colonne 1 : liste sources + badges
  SourceConfigPanel.tsx          -- Colonne 2 : toolbar + accordéons config
  ResultsPanel.tsx               -- Colonne 3 : test + résultats + stats
  EnrichmentSummaryBar.tsx       -- Barre sticky résumé global
  ApiEnrichmentConfig.tsx        -- Refactorisé : accordéons au lieu de tabs
  enrichmentSources.ts           -- Inchangé

features/import/hooks/
  useEnrichmentState.ts          -- État + polling + actions extraits
```

### Patterns du codebase à suivre

| Pattern | Référence | Application |
|---------|-----------|-------------|
| ResizablePanelGroup 3 colonnes | `SiteBuilder.tsx:571-625` | Layout principal |
| Sizes en string % + id sur chaque panel | `ModuleLayout.tsx:94-128` | Toutes les colonnes |
| ScrollArea h-full dans les panels | `ModuleLayout.tsx:108`, `SiteBuilder.tsx:314` | Chaque colonne |
| Accordion type="multiple" avec icônes | `IndexConfigEditor.tsx:380-577` | Sections config |
| State hook extrait | `useSiteBuilderState.ts` | useEnrichmentState |
| Orchestrateur + sous-composants | Pattern SiteBuilder | EnrichmentTab |
| Panel collapsible | `ContentTab.tsx:182-306` | Sidebar responsive |

### Implementation Phases

#### Phase 1 : State extraction — `useEnrichmentState`

Extraire tout l'état local dans un hook dédié sans modifier le rendu.

**Fichier** : `features/import/hooks/useEnrichmentState.ts`

**Contenu extrait :**
- ~29 `useState` (referenceConfig, stats, job, results, entities, previewData, activeSource, etc.)
- ~10 `useMemo` (sources dérivées, normalisation, filtrage)
- Polling avec `useRef<setInterval>` — le poll vit dans le hook, indépendant du mount/unmount des sous-composants
- Actions : fetchConfig, saveConfig, startJob, pauseJob, resumeJob, cancelJob, runPreview, fetchResults
- Dirty-state tracking : `configDirty: boolean` + `configHash` pour détecter les changements non sauvés

```typescript
// features/import/hooks/useEnrichmentState.ts
interface UseEnrichmentStateOptions {
  referenceName: string
  hasEnrichment: boolean
  initialSourceId?: string | null
}

interface EnrichmentState {
  // Sources
  sources: NormalizedSource[]
  activeSourceId: string | null
  setActiveSourceId: (id: string | null) => void

  // Config
  referenceConfig: ReferenceConfigPayload | null
  configDirty: boolean
  updateSourceConfig: (sourceId: string, patch: Partial<SourceConfig>) => void
  saveConfig: () => Promise<void>

  // Job
  job: EnrichmentJob | null
  isPolling: boolean
  startJob: (sourceId?: string) => Promise<void>
  pauseJob: () => Promise<void>
  resumeJob: () => Promise<void>
  cancelJob: () => Promise<void>

  // Results & Preview
  results: EnrichmentResult[]
  previewData: PreviewResponse | null
  runPreview: (entityId: string, sourceId: string) => Promise<void>

  // Entities
  entities: EntityOption[]

  // Stats
  stats: EnrichmentStatsResponse | null

  // Loading / Error
  loading: boolean
  error: string | null
}

export function useEnrichmentState(options: UseEnrichmentStateOptions): EnrichmentState
```

**Critère de validation** : `EnrichmentTab.tsx` compile et fonctionne exactement comme avant, mais avec `const state = useEnrichmentState(...)` au lieu de ~29 `useState`.

#### Phase 2 : Component decomposition

Extraire les sections de rendu en composants dédiés, toujours avec le layout CSS grid actuel.

**2a. `EnrichmentSummaryBar.tsx`** (~80 lignes)
- Barre sticky en haut : badges sources actives, progression globale, boutons d'action globaux (Lancer toutes, Actualiser)
- Alerte offline (pleine largeur, span 3 colonnes)
- Extrait depuis le rendu sticky actuel (lignes ~3000-3100)

**2b. `SourceSidebar.tsx`** (~150 lignes)
- Liste des sources avec : nom, badge statut (actif/inactif/erreur/en cours), mini progress bar
- Bouton "+ Ajouter une source"
- Source sélectionnée mise en surbrillance
- Actions : sélection, ajout, suppression, réordonnement (les boutons move up/down existants)
- Props : `sources`, `activeSourceId`, `onSelectSource`, `onAddSource`, `onRemoveSource`, `onReorderSource`

**2c. `SourceConfigPanel.tsx`** (~200 lignes)
- **Toolbar persistante en haut** (JAMAIS dans un accordéon) : Start/Pause/Resume/Cancel pour la source active + toggle enable/disable + indicateur dirty-state ("● non sauvegardé")
- En-dessous : `ApiEnrichmentConfig` wrappé dans les accordéons (Phase 4)
- Bouton Sauver en bas de la toolbar ou du panneau
- Props : `source`, `configDirty`, `job`, `onSave`, `onStart`, `onPause`, `onResume`, `onCancel`, `onConfigChange`

**2d. `ResultsPanel.tsx`** (~250 lignes)
- **Zone test** (haut) : sélecteur d'entité + bouton "Lancer test"
- **Résultat preview** (milieu) : rendu structuré (GBIF, Tropicos, COL, BHL, iNat) — les helpers `renderXxxStructuredSummary` deviennent des composants internes
- **Indicateur stale** : si `configDirty === true`, afficher un badge "Résultats basés sur la config précédente"
- **Stats** (bas) : progression, erreurs, durée
- **Résultats persistés** : liste des résultats avec détail inline (expandable row au lieu du Dialog modal)
- Props : `source`, `entities`, `previewData`, `results`, `stats`, `configDirty`, `onRunPreview`

**2e. `EnrichmentTab.tsx` refactorisé** (~250 lignes)
- Orchestrateur : `useEnrichmentState` + layout + câblage des sous-composants
- Pas de logique métier, pas de rendu de détail

**Critère de validation** : fonctionnalité identique, layout identique (CSS grid), mais chaque fichier < 300 lignes.

#### Phase 3 : Layout migration — ResizablePanelGroup

Remplacer le CSS grid par un layout 3 colonnes redimensionnables.

**Layout structure :**

```tsx
// EnrichmentTab.tsx (orchestrateur)
<div className="flex h-full flex-col overflow-hidden">
  <EnrichmentSummaryBar ... />

  <ResizablePanelGroup direction="horizontal" className="flex-1">
    {/* Colonne 1 : Sources */}
    <ResizablePanel id="enrichment-sources" defaultSize="18%" minSize="14%" maxSize="25%">
      <ScrollArea className="h-full">
        <SourceSidebar ... />
      </ScrollArea>
    </ResizablePanel>

    <ResizableHandle withHandle />

    {/* Colonne 2 : Config */}
    <ResizablePanel id="enrichment-config" defaultSize="45%" minSize="30%">
      <ScrollArea className="h-full">
        <SourceConfigPanel ... />
      </ScrollArea>
    </ResizablePanel>

    <ResizableHandle withHandle />

    {/* Colonne 3 : Résultats */}
    <ResizablePanel id="enrichment-results" defaultSize="37%" minSize="22%">
      <ScrollArea className="h-full">
        <ResultsPanel ... />
      </ScrollArea>
    </ResizablePanel>
  </ResizablePanelGroup>
</div>
```

**Responsive collapse (< 1200px)** :

Quand la fenêtre Tauri passe sous ~1200px, la colonne résultats se collapse en panneau escamotable (pattern `ContentTab.tsx` avec `collapsible` + `collapsedSize={0}`). Un bouton toggle dans la summary bar permet de la rouvrir. Sous ~900px, la sidebar se collapse aussi (mode icônes ou cachée).

```tsx
<ResizablePanel
  id="enrichment-results"
  defaultSize="37%"
  minSize="22%"
  collapsible
  collapsedSize={0}
  onResize={(size) => setResultsCollapsed(size.asPercentage === 0)}
>
```

**Suppression des 14+ hauteurs en dur** : tous les `max-h-[420px]` (×7), `max-h-[360px]` (×2), `h-[220px]`, `max-h-[620px]`, `max-h-[60vh]` et les 9× `overflow-auto` brut sont remplacés par le `ScrollArea h-full` du panel parent. Les contenus dans chaque colonne s'empilent naturellement et scrollent ensemble.

**Critère de validation** : 3 colonnes redimensionnables, chaque colonne scrolle indépendamment, aucun scroll imbriqué, resize fluide.

#### Phase 4 : Config accordion

Remplacer les sous-onglets de `ApiEnrichmentConfig` par des sections Accordion.

**Pattern à suivre** — `IndexConfigEditor.tsx:380-577` :

```tsx
<Accordion type="multiple" defaultValue={['connection', 'profile-options']} className="space-y-2">
  <AccordionItem value="connection" className="border rounded-lg">
    <AccordionTrigger className="px-4 py-3 hover:no-underline">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 border border-blue-200">
          <Plug className="h-4 w-4 text-blue-600" />
        </div>
        <div>
          <p className="text-sm font-medium text-left">Connexion</p>
          <p className="text-xs text-muted-foreground text-left">URL, preset, paramètres</p>
        </div>
      </div>
    </AccordionTrigger>
    <AccordionContent className="px-4 pb-4">
      {/* Champs connexion existants */}
    </AccordionContent>
  </AccordionItem>

  {/* Idem pour auth, profile-options, mapping */}
</Accordion>
```

**4 sections :**

| Section | Icône | Couleur | defaultOpen | Contenu |
|---------|-------|---------|-------------|---------|
| Connexion | `Plug` | blue | oui | Preset, URL, query, params |
| Authentification | `KeyRound` | amber | non | Méthode, API key, bearer, basic |
| Options profil | `SlidersHorizontal` | green | oui | Switches include_*, limits, name verifier |
| Mapping avancé | `Braces` | purple | non | response_mapping JSON, chained_endpoints |

Les sections Connexion et Options profil sont ouvertes par défaut (les plus utilisées). Auth et Mapping sont fermées (rarement modifiées).

**Important** : les contrôles de job (Start/Pause/Cancel) restent dans la toolbar persistante de `SourceConfigPanel`, JAMAIS dans un accordéon.

**Critère de validation** : toutes les options de configuration existantes restent accessibles, accordéons ouvrent/ferment sans perte de données, le scroll vertical est minimal.

#### Phase 5 : Polish et edge cases

**5a. Dirty-state guard**
- Quand `configDirty === true` et l'utilisateur clique une autre source dans la sidebar : `AlertDialog` "Changements non sauvegardés. Sauvegarder / Abandonner / Annuler"
- Indicateur visuel : petit dot orange à côté du bouton Sauver + texte "non sauvegardé"

**5b. Stale results indicator**
- Si `configDirty === true`, la colonne résultats affiche un bandeau subtil : "Résultats basés sur la config précédente"
- Le bandeau disparaît après un nouveau test ou un save + re-run

**5c. Résultat detail inline**
- Remplacer le `Dialog` modal pour le détail d'un résultat par un expandable row dans la liste (click pour déplier, re-click pour replier)
- Pattern Collapsible existant

**5d. Accessibilité de base**
- `role="region"` + `aria-label` sur chaque colonne (`"Liste des sources"`, `"Configuration"`, `"Résultats"`)
- Source list navigable au clavier (arrow up/down)
- Focus automatique sur la colonne config quand on sélectionne une source

**5e. Quick mode**
- Conserver le mode quick (Sheet) tel quel pour l'instant — il est utilisé depuis `EnrichmentView.tsx` pour des tests rapides
- Le mode quick bénéficiera automatiquement du hook `useEnrichmentState` extrait en Phase 1
- Décision de le supprimer ou le fusionner reportée à plus tard (open question du brainstorm)

## Acceptance Criteria

### Functional Requirements

- [ ] Layout 3 colonnes redimensionnables (sources | config | résultats)
- [ ] Config en 4 sections accordéon (connexion, auth, options profil, mapping)
- [ ] Résultats et zone de test visibles en permanence (colonne 3)
- [ ] Toolbar job (Start/Pause/Cancel) persistante, hors des accordéons
- [ ] Dirty-state guard : confirmation avant perte de changements non sauvés
- [ ] Indicateur "résultats stale" quand la config a changé
- [ ] Toutes les fonctionnalités existantes préservées (ajout/suppression/réordonnement de sources, preview, résultats, stats)
- [ ] Mode quick (Sheet) continue de fonctionner

### Non-Functional Requirements

- [ ] Aucun scroll imbriqué — un seul `ScrollArea h-full` par colonne
- [ ] `EnrichmentTab.tsx` < 300 lignes (orchestrateur)
- [ ] Chaque sous-composant < 300 lignes
- [ ] Aucune hauteur en dur (plus de `max-h-[Npx]`) — 14+ à supprimer
- [ ] `ResizablePanelGroup` avec sizes en string % et `id` sur chaque panel (convention codebase)
- [ ] Colonnes responsive : collapse résultats sous 1200px, collapse sidebar sous 900px
- [ ] `role="region"` + `aria-label` sur chaque colonne

### Quality Gates

- [ ] Tests existants passent (`uv run pytest`)
- [ ] Lint clean (`uvx ruff check src/ && uvx ruff format src/`)
- [ ] GUI build clean (`cd src/niamoto/gui/ui && pnpm build`)
- [ ] Test manuel : config → test → résultats fonctionne end-to-end
- [ ] Test manuel : resize des colonnes fluide, pas de overflow

## Dependencies & Prerequisites

- `react-resizable-panels` — déjà installé (utilisé par `resizable.tsx`)
- `@radix-ui/react-accordion` — déjà installé (utilisé par `accordion.tsx`)
- `@radix-ui/react-collapsible` — déjà installé (utilisé par `collapsible.tsx`)
- Aucune nouvelle dépendance requise

## Risk Analysis & Mitigation

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Régression fonctionnelle (3887 lignes à refactoriser) | Élevé | Phases séquentielles : chaque phase produit un état fonctionnel. Phase 1 ne change pas le rendu. |
| Polling cassé après extraction du hook | Moyen | Le poll vit dans le hook via `useRef`, indépendant du mount des sous-composants. Tester spécifiquement le cycle start → pause → resume. |
| Performance de 3 ResizablePanel + 3 ScrollArea | Faible | Pattern déjà validé dans SiteBuilder (3 colonnes). Pas de virtualisation nécessaire avec ~50 items max. |
| Quick mode cassé | Moyen | Phase 1 (hook) bénéficie au quick mode. Le layout 3 colonnes ne touche que le workspace mode. |

## Implementation Order

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
  hook       split       layout     accordion    polish
 (safe)     (safe)     (visible)   (visible)    (edge)
```

Chaque phase est committable et déployable indépendamment. Les phases 1-2 sont invisibles pour l'utilisateur (refactoring pur). Les phases 3-4 changent le visuel. La phase 5 ajoute les garde-fous.

## Files Impacted

### New files

| Fichier | Rôle | Phase |
|---------|------|-------|
| `features/import/hooks/useEnrichmentState.ts` | Hook état + actions + polling | 1 |
| `features/import/components/enrichment/SourceSidebar.tsx` | Colonne 1 : liste sources | 2 |
| `features/import/components/enrichment/SourceConfigPanel.tsx` | Colonne 2 : toolbar + accordéons | 2 |
| `features/import/components/enrichment/ResultsPanel.tsx` | Colonne 3 : test + résultats | 2 |
| `features/import/components/enrichment/EnrichmentSummaryBar.tsx` | Barre sticky résumé | 2 |

### Modified files

| Fichier | Changement | Phase |
|---------|-----------|-------|
| `EnrichmentTab.tsx` | 3887 → ~300 lignes (orchestrateur) | 1-3 |
| `ApiEnrichmentConfig.tsx` | Tabs → Accordion sections | 4 |

### Unchanged

| Fichier | Raison |
|---------|--------|
| `enrichmentSources.ts` | Utilitaires purs, pas de changement |
| `EnrichmentWorkspaceSheet.tsx` | Mode quick préservé tel quel |
| `EnrichmentView.tsx` | Dashboard overview, pas impacté |
| Backend `enrichment.py` | Aucun changement API |

## References

### Internal

- Brainstorm : `docs/brainstorms/2026-04-10-enrichment-tab-ux-redesign-brainstorm.md`
- Pattern ResizablePanelGroup 3 colonnes : `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx:571-625`
- Pattern Accordion config : `src/niamoto/gui/ui/src/components/index-config/IndexConfigEditor.tsx:380-577`
- Pattern state hook : `src/niamoto/gui/ui/src/features/site/hooks/useSiteBuilderState.ts`
- Pattern collapsible panel : `src/niamoto/gui/ui/src/components/content/ContentTab.tsx:182-306`
- Composant source actuel : `src/niamoto/gui/ui/src/features/import/components/enrichment/EnrichmentTab.tsx`

### shadcn components used

- `@/components/ui/resizable` — ResizablePanelGroup, ResizablePanel, ResizableHandle
- `@/components/ui/accordion` — Accordion, AccordionItem, AccordionTrigger, AccordionContent
- `@/components/ui/collapsible` — Collapsible, CollapsibleContent, CollapsibleTrigger
- `@/components/ui/scroll-area` — ScrollArea
