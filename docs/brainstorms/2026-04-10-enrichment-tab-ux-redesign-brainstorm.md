# Enrichment Tab UX Redesign

**Date**: 2026-04-10
**Status**: Brainstorm complete
**Scope**: Refonte de l'onglet "Enrichissement API" dans les collections

## What We're Building

Refonte du layout et de l'ergonomie de l'onglet Enrichissement API pour éliminer les scrolls imbriqués, améliorer la visibilité, et rendre le cycle config → test → résultats fluide.

### Problèmes actuels

- **Scroll dans le scroll** : 7+ zones scrollables imbriquées avec des hauteurs en dur (220px, 360px, 420px, 620px)
- **Va-et-vient config/résultats** : les sous-onglets config/preview/results obligent à switcher de contexte
- **Config longue** : connexion, auth, options de profil, mapping — tout dans un seul flux vertical
- **Sidebar fixe** : 280px non redimensionnable, alors que le reste de l'app utilise `ResizablePanelGroup`
- **Incohérence technique** : mix Radix ScrollArea et `overflow-auto` natif, pas de transitions

### Fichiers impactés

| Fichier | Lignes | Rôle |
|---------|--------|------|
| `EnrichmentTab.tsx` | 3887 | Composant monolithique principal |
| `ApiEnrichmentConfig.tsx` | 1702 | Éditeur config par source |
| `enrichmentSources.ts` | 447 | Utilitaires normalisation |
| `EnrichmentWorkspaceSheet.tsx` | - | Wrapper mode quick (Sheet) |

## Why This Approach

### Layout choisi : Split 3 colonnes avec ResizablePanelGroup

```
┌──────────┬─────────────────────────────┬──────────────────────┐
│ Sources  │ Config source               │ Résultats / Preview  │
│          │                             │                      │
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
│ [+ Ajout]│ [Sauver]                    │ Temps: 2m34s        │
└──────────┴─────────────────────────────┴──────────────────────┘
```

**Raisons du choix :**

1. **Split permanent** plutôt que tabs : élimine le va-et-vient config ↔ résultats. Le cycle test est immédiat — on modifie la config à gauche, on lance le test, le résultat apparaît à droite sans navigation.

2. **Accordéons** plutôt que tabs/wizard/compact : la config a 4 sections de tailles inégales (connexion = principal, auth = souvent vide, options profil = checkboxes rapides, mapping = rarement touché). Les accordéons permettent d'ouvrir uniquement ce qui est pertinent, sans scroll vertical forcé.

3. **ResizablePanelGroup** plutôt que CSS grid fixe : cohérent avec le pattern du reste de l'app (ContentTab, ModuleLayout, SiteBuilder). L'utilisateur peut ajuster les proportions selon son besoin (plus de place pour la config lors du setup initial, plus de place pour les résultats lors du monitoring).

4. **Sidebar simple avec badges** : pas besoin de mini-cards — le nom, le statut (badge coloré), et une barre de progression suffisent. La sidebar est un index de navigation, pas un dashboard.

## Key Decisions

### D1 — Layout 3 colonnes split

- **Colonne gauche** (~200-280px, min 180px) : liste des sources avec badge statut + mini progress bar
- **Colonne centrale** (flex) : config de la source sélectionnée en accordéons
- **Colonne droite** (~300-400px, min 280px) : résultats + zone de test
- Toutes redimensionnables via `ResizablePanelGroup`

### D2 — Config en accordéons (Collapsible)

4 sections :
1. **Connexion** (ouvert par défaut) — preset, URL, query, params
2. **Authentification** (fermé par défaut) — méthode, clé API, bearer, basic
3. **Options profil** (ouvert par défaut) — switches spécifiques au profil (include_synonyms, etc.)
4. **Mapping avancé** (fermé par défaut) — response_mapping JSON, chained_endpoints

Logique : ouvrir par défaut les sections les plus utilisées, fermer celles qui sont rarement modifiées.

### D3 — Colonne résultats toujours visible

La colonne droite contient :
- **Zone de test** (en haut) : sélection entité + bouton test
- **Résultat du dernier test** (milieu) : rendu structuré du résultat
- **Stats d'enrichissement** (bas) : progression globale, erreurs, temps

Plus de sous-onglets "Tester l'API" / "Résultats" — tout est dans la même colonne, scrollable indépendamment.

### D4 — Un seul scroll par colonne

Chaque colonne a son propre `ScrollArea` avec `h-[calc(100vh-offset)]`. Plus de hauteurs fixes en dur, plus de scrolls imbriqués. Les accordéons dans la config contribuent à la hauteur naturelle du contenu.

### D5 — Sticky summary bar

La barre de résumé en haut (badges sources actives, progression globale, boutons d'action) reste sticky au-dessus des 3 colonnes.

### D6 — Utiliser ResizablePanelGroup

Aligner avec le pattern existant de l'app :
- `ResizablePanelGroup direction="horizontal"`
- `ResizablePanel` avec `defaultSize`, `minSize`, `maxSize`
- `ResizableHandle` entre chaque panneau

## Open Questions

1. **Mode quick (Sheet)** : Est-ce qu'on garde le mode quick séparé ou est-ce que le nouveau layout 3 colonnes rend le Sheet inutile ?
2. **Responsive < 1024px** : Faut-il un fallback en layout empilé (tabs) pour les petits écrans, ou on assume desktop-only pour cet onglet ?
3. **Persistance des tailles** : Sauvegarder les proportions des colonnes en localStorage pour qu'elles persistent entre sessions ?

## Technical Notes

- `EnrichmentTab.tsx` (3887 lignes) devra être décomposé. Extraction probable :
  - `SourceSidebar` — liste des sources
  - `SourceConfigPanel` — accordéons config
  - `ResultsPanel` — zone test + résultats
  - `EnrichmentSummaryBar` — barre sticky
- Remplacer les 7+ `max-h-[Npx] overflow-auto` par des `ScrollArea` Radix avec hauteurs relatives au viewport
- Remplacer `xl:grid-cols-[280px_minmax(0,1fr)]` par `ResizablePanelGroup`
- Les render helpers inline (`renderGbifStructuredSummary`, etc.) deviennent des composants dédiés

## Out of Scope

- Refonte du mode quick (Sheet) — à traiter séparément si le nouveau layout ne le rend pas obsolète
- Ajout de nouvelles fonctionnalités d'enrichissement
- Modification des endpoints API backend
- Refonte de `ApiEnrichmentConfig` interne (juste son intégration dans les accordéons)
