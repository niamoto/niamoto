# Architecture du système de preview

## Vue d'ensemble

Le système de preview permet de prévisualiser les widgets Niamoto dans l'interface GUI
avant publication. Il utilise une architecture **deux niveaux** (`thumbnail` / `full`)
avec un moteur backend unique et un hook frontend unifié.

```text
                    ┌─────────────────────────────────────────┐
                    │           Grilles / Listes               │
                    │  ┌───────┐ ┌───────┐ ┌───────┐         │
                    │  │ thumb │ │ thumb │ │ thumb │  ...     │  ← Plotly staticPlot
                    │  └───────┘ └───────┘ └───────┘         │    ~1.3 MB JS (core)
                    └──────────────┬──────────────────────────┘
                                  │ clic / sélection
                                  ▼
                    ┌─────────────────────────────────────────┐
                    │          Vue détail / Plein écran        │
                    │  ┌───────────────────────────────┐      │
                    │  │   Plotly.js interactif         │      │  ← Full interactive
                    │  │   dans iframe srcDoc            │      │    ~1.3 MB ou ~2.2 MB
                    │  └───────────────────────────────┘      │
                    └─────────────────────────────────────────┘
```

## Backend : PreviewEngine

### Structure des fichiers

```text
src/niamoto/gui/api/services/preview_engine/
├── __init__.py                    # Exports publics
├── models.py                      # PreviewRequest, PreviewResult, PreviewMode
├── engine.py                      # PreviewEngine — résolution, données, rendu, wrapper
└── plotly_bundle_resolver.py      # Sélection du bundle Plotly (core / maps / none)

src/niamoto/gui/api/services/
├── preview_utils.py               # Utilitaires partagés : wrap_html, render_widget, etc.
└── map_renderer.py                # Rendu des cartes (Plotly scattermap / choropleth)

src/niamoto/gui/api/routers/
└── preview.py                     # Endpoints GET/POST unifiés
```

### Pipeline de rendu

Le moteur suit un pipeline principalement linéaire synchrone :

```text
resolve → load → transform → render → wrap
```

> **Note :** En pratique, `PreviewEngine.render()` comporte plusieurs branches de retour anticipé et des flux spécialisés (navigation widgets, general info, entity maps, etc.). Le pipeline ci-dessus décrit le cas nominal ; certains types de widgets court-circuitent des étapes ou empruntent un chemin de rendu dédié.

1. **Resolve** : identifie le transformer et le widget à partir du `template_id`
   (résolution via `transform.yml` et `export.yml`)
2. **Load** : charge les données depuis DuckDB avec limites selon le mode
3. **Transform** : exécute le plugin transformer sur les données
4. **Render** : génère le HTML du widget via le plugin widget
5. **Wrap** : encapsule dans un document HTML complet avec le bon bundle Plotly

### Modèles

```python
PreviewMode = Literal["thumbnail", "full"]

@dataclass(frozen=True)
class PreviewRequest:
    template_id: str | None = None
    group_by: str | None = None
    source: str | None = None
    entity_id: str | None = None
    mode: PreviewMode = "full"
    inline: dict[str, Any] | None = None

@dataclass(frozen=True)
class PreviewResult:
    html: str               # Document HTML complet pour iframe srcDoc
    etag: str               # Fingerprint pour cache HTTP 304
    preview_key: str        # Clé de cache interne
    warnings: tuple[str, ...] = ()
```

### 7 branches de rendu

Le moteur unifie 7 types de widgets :

| Type | Détection | Données |
|------|-----------|---------|
| Navigation widget | suffixe `_hierarchical_nav_widget` | Référentiel + CSS/JS |
| General info widget | préfixe `general_info_` | Agrégation champs |
| Entity map | suffixe `_entity_map` / `_all_map` | Géométries |
| Configured widget | résolution via `transform.yml` | Transform + Widget |
| Class object (CSV) | détection transformer class_object | Fichier CSV |
| Entity table | source non-occurrence | Requête DB |
| Occurrence | fallback | Requête DB + sampling |

### ETag et invalidation

L'ETag est basé sur un **fingerprint fichiers** (mtime de la DB + configs YAML).
Il est calculé une seule fois à l'initialisation et recalculé uniquement après
`engine.invalidate()` — appelé à la fois dans le callback de succès d'import et lors de la sauvegarde de configuration (config saves).

### Bundles Plotly

Deux bundles custom réduisent la taille JS :

| Bundle | Taille | Usage |
|--------|--------|-------|
| `plotly-niamoto-core.min.js` | 1.3 MB | Charts (bar, pie, scatter, heatmap, table, indicator) |
| `plotly-niamoto-maps.min.js` | 2.2 MB | Cartes (+ scattermap, choropleth_map, maplibre-gl) |

Le choix du bundle est automatique selon le type de widget.

## Frontend : hook unifié

### Structure des fichiers

```text
src/niamoto/gui/ui/src/
├── lib/preview/
│   ├── types.ts              # PreviewDescriptor, PreviewMode, PreviewState
│   └── usePreviewFrame.ts    # Hook TanStack Query + sémaphore concurrence
└── components/preview/
    ├── PreviewTile.tsx        # Miniature (IntersectionObserver, lazy loading)
    ├── PreviewPane.tsx        # Vue complète (ResizeObserver, re-mount au resize)
    ├── PreviewSkeleton.tsx    # Placeholder shimmer par type de widget
    └── PreviewError.tsx       # Affichage d'erreur
```

### Hook `usePreviewFrame`

Le hook central basé TanStack Query gère :

- **Cache** : `staleTime: Infinity` — les données écologiques ne changent qu'après import
- **Déduplication** : 10 composants demandant le même template_id = 1 requête
- **Concurrence** : sémaphore limitant à 3 rendus Plotly simultanés (réduit le jank CPU)
- **Abort** : annulation sur changement de visibilité via `AbortSignal.any`
- **Invalidation** : debouncée (300ms) avec `refetchType: 'active'`

```typescript
const { html, loading, error } = usePreviewFrame(descriptor, visible)
```

### Composants

**PreviewTile** — miniature pour les grilles :
- IntersectionObserver avec `rootMargin: 120px` pour le prefetch
- Debounce de visibilité (32ms) pour éviter le strobe au scroll
- `content-visibility: auto` + `contain-intrinsic-size` pour le rendering CSS
- Nettoyage iframe au démontage (`srcdoc = ''`)
- `sandbox="allow-scripts"` (pas de `allow-same-origin`)

**PreviewPane** — vue complète dans les panneaux détail :
- ResizeObserver qui force un re-mount de l'iframe au changement de largeur
- Masque le contenu pendant le refetch (shimmer visible)

### Invalidation côté frontend

```typescript
// Dans le callback de succès d'import
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'
invalidateAllPreviews(queryClient)
```

## Sécurité

- **Sandbox iframe** : `sandbox="allow-scripts"` sur toutes les iframes preview
  (pas de `allow-same-origin` → le contenu ne peut pas accéder au DOM parent)
- **html.escape()** : toutes les données et messages d'erreur interpolés dans
  le HTML des widgets sont échappés via `html.escape()`
- **Cache HTTP** : `Cache-Control: no-cache` avec ETag pour éviter le stale content
- **Bundle Plotly** : servi avec `Cache-Control: public, max-age=31536000, immutable`

## Métriques

| Métrique | Avant | Après |
|----------|-------|-------|
| P95 preview | non mesuré | 7ms |
| Bundle Plotly (non-map) | 4.7 MB | 1.3 MB (−72%) |
| Bundle Plotly (map) | 4.7 MB | 2.2 MB (−53%) |
| Chemins backend | 4 endpoints, 7 branches | 1 moteur, 3 routes |
| Composants frontend | 12 | 2 (PreviewTile, PreviewPane) |
| Wrappers HTML dupliqués | 2 | 1 |
| Iframes sans sandbox | 9/12 | 0/12 |
