---
title: Refonte unifiée du système de preview
type: refactor
date: 2026-02-21
deepened: 2026-02-21
scope: widget previews, layout preview, add-widget modal, recipe preview
---

# Refonte unifiée du système de preview

## Résumé de l'enrichissement

**Approfondi le :** 2026-02-21
**Agents de recherche utilisés :** 10 (Python reviewer, TypeScript reviewer, Performance oracle, Architecture strategist, Frontend races reviewer, Security sentinel, Code simplicity reviewer, Pattern recognition specialist, Best practices researcher, Repo research analyst)
**Recherches complémentaires :** TanStack Query v5 docs (Context7), Plotly.js custom bundles, FastAPI ETag/caching patterns, iframe srcDoc performance, CSS content-visibility, Plotly staticPlot

### Corrections factuelles majeures

- **Plotly.js est en v3.0.1 et pèse 4.7MB** (pas 2.8MB) — inclut maplibre-gl pour les traces maps
- **`templates.py` fait 4499 lignes** (pas 3200+) avec 7 branches de rendu (pas 6)
- **La cible de 1.5MB pour le bundle custom est irréaliste** si on inclut les traces maps (maplibre-gl seul fait ~1MB)
- **12 fichiers frontend** contiennent de la logique iframe (pas 9+)

### Découvertes critiques

1. **BLOQUANT — Sync dans async** : `PreviewEngine.render()` est synchrone (I/O DB + fichiers) mais appelé depuis des `async def` endpoints → bloque l'event loop FastAPI
2. **SÉCURITÉ — XSS stocké** : les plugins widgets (`info_grid.py`, `hierarchical_nav_widget`) interpolent des données sans `html.escape()` dans le HTML
3. **SÉCURITÉ — Sandbox incohérent** : certaines iframes n'ont aucun sandbox, d'autres ont `allow-same-origin + allow-scripts` (annule l'isolation)
4. **PERFORMANCE — Bundle split nécessaire** : séparer en bundle core (~1MB) et bundle maps (~2.5MB)
5. **RACES — TanStack Query n'annule PAS sur `enabled: false`** : scroll rapide = toutes les requêtes en vol simultanément

### Simplifications recommandées

- **7 modules backend → 3** (`models.py`, `engine.py`, supprimer `errors.py`)
- **Supprimer `PreviewContext`** (jamais utilisé dans le rendu)
- **Supprimer Server-Timing** (prématuré pour un outil local)
- **Supprimer SSE** — invalider directement dans le callback de succès d'import (1 ligne)
- **Supprimer le feature flag** — utiliser git revert si problème
- **8 phases → 5 phases** consolidées
- **`staleTime: Infinity`** au lieu de 60s (les données écologiques changent uniquement après import explicite)

### Corrections post-review (v2)

1. **queryKey inline complète** — la clé inline inclut maintenant `groupBy`, `source`, `entityId` (pas seulement le hash inline)
2. **Sémaphore de concurrence** — borne les rendus Plotly concurrents à 3 (jank CPU, pas réseau)
3. **ETag durable** — fingerprint basé mtime fichiers (DB + configs) au lieu d'un compteur mémoire (résiste restart/multi-worker/modifs hors-app)
4. **Traces Plotly v3** — `scattermap` et `choropleth_map` (pas les noms v2 `scattermapbox`/`choroplethmapbox`)
5. **Rétrocompatibilité API** — route legacy `/api/templates/preview/` conservée comme alias pendant la migration

---

## Vue d'ensemble

Le système de preview des widgets Niamoto est fragmenté : **12 implémentations frontend** indépendantes et **4 chemins backend** pour le même besoin de rendu. Cette fragmentation génère des lenteurs, des incohérences visuelles, et un coût de maintenance élevé. Ce plan propose une architecture unifiée à deux niveaux (`thumbnail`/`full`) avec un seul moteur backend et un seul hook frontend, remplaçant l'ensemble des implémentations actuelles.

## Problème détaillé

### Backend : 4 endpoints, 7 chemins de rendu

Le fichier `templates.py` (4499 lignes) contient la logique de preview la plus complexe avec 7 branches distinctes dans `preview_template()` (ligne 3216) :

| Branche | Détection | Ligne | Données |
|---------|-----------|-------|---------|
| Navigation widget | suffixe `_hierarchical_nav_widget` | 3248 | Requête DB + lecture CSS/JS disque |
| General info widget | préfixe `general_info_` + suffixe `_field_aggregator_info_grid` | 3253 | Agrégation champs |
| Entity map | suffixe `_entity_map` ou `_all_map` | 3262 | Géométries complètes |
| Configured widget | résolution via `_load_configured_widget()` | 3268 | Via transform.yml |
| Class object (CSV) | `_is_class_object_template(transformer)` | 3370 | Fichier CSV |
| Entity table (non-occurrence) | `data_source != "occurrences"` | 3408 | Requête DB |
| Occurrence | fallback | 3520 | Requête DB + sampling |

À cela s'ajoutent :
- `layout.py:340` qui **importe et appelle** `preview_template()` directement (lignes 395-402 : `from .templates import _preview_navigation_widget` et `from .templates import preview_template`)
- `recipes.py:1380` qui délègue à `PreviewService.generate_preview()` (ne couvre que 2 des 7 branches)
- `POST /api/templates/preview` (ligne 3162) qui utilise un `TTLCache(maxsize=128, ttl=300)` séparé

Le wrapper HTML est **dupliqué** : `PreviewService.wrap_html_response()` (preview_service.py:94) et `layout.py._wrap_html_response()` (ligne 423) génèrent quasi le même HTML.

> **Insight architecture** : `PreviewService` (664 lignes) est entièrement composée de méthodes statiques — aucun état d'instance. Elle ne couvre que les branches class_object et occurrence, pas les 5 autres.

### Frontend : 12 composants indépendants

| Composant | Fichier | Iframe | Queue | Cache | Lazy | Sandbox |
|-----------|---------|--------|-------|-------|------|---------|
| WidgetPreview (modal) | `AddWidgetModal.tsx:132` | `srcDoc` | Oui | LRU | IntersectionObserver | **Aucun** |
| LargePreview (modal) | `AddWidgetModal.tsx:264` | `srcDoc` | Oui | LRU | Non | **Aucun** |
| CombinedPreview (modal) | `AddWidgetModal.tsx:384` | `srcDoc` | **Non** (fetch direct) | Non | Non | **Aucun** |
| WidgetPreviewPanel | `WidgetPreviewPanel.tsx` | `src` | Non | Non | Non | **Aucun** |
| WidgetDetailPanel | `WidgetDetailPanel.tsx` | `src` | Non | Non | Non | **Aucun** |
| SortableWidgetCard (layout) | `LayoutOverview.tsx:246` | `src` | Non | Non | IntersectionObserver | **Aucun** |
| NavigationSidebar (layout) | `LayoutOverview.tsx:156` | `src` | Non | Non | Non | **Aucun** |
| WidgetCard (legacy editor) | `WidgetCard.tsx:277` | `src` | Non | Non | Non | **Aucun** |
| WidgetMiniature | `WidgetMiniature.tsx:105` | `src` | Non | Non | IntersectionObserver | **Aucun** |
| PreviewFrame (site builder) | `preview-frame.tsx:212` | `src` | Non | Non | Non | `allow-same-origin allow-scripts` |
| TransformDemo | `TransformDemo.tsx:883` | `srcDoc` | Non | Non | Non | `allow-scripts allow-same-origin` |
| ExportDemo / Build preview | `ExportDemo.tsx:523`, `build.tsx:351` | `src` | Non | Non | Non | `allow-scripts allow-same-origin allow-popups allow-forms` |

> **Insight sécurité** : 9 iframes sur 12 n'ont **aucun attribut sandbox**. Les 3 qui en ont utilisent `allow-same-origin + allow-scripts`, ce qui **annule l'isolation** — le contenu peut accéder au DOM parent.

### Performance

1. **Plotly.js v3.0.1 pèse 4.7MB** (inclut maplibre-gl) chargé indépendamment dans chaque iframe — 10 widgets = ~47MB de parsing JS total
2. **Concurrence non bornée** : 10+ widgets visibles dans le layout = 10+ requêtes HTTP simultanées + 10+ initialisations Plotly (~200ms de thread principal chacune = 1.2s de jank)
3. **Pas de cache partagé** entre les composants `src`-based (le cache LRU ne profite qu'au `srcDoc` du AddWidgetModal)
4. **Navigation widget** : reconstruit le HTML complet à chaque requête — lecture fichiers CSS/JS du disque (lignes 2236-2248) + requête DB + ~80 lignes de Tailwind inline
5. **ETag computation utilise `os.path.getmtime`** — 3 appels stat filesystem par requête (DB + 2 configs), race condition avec DuckDB qui modifie le fichier pendant les opérations

### Travail récent (commits du 21/02/2026)

- `177a5c1` : stabilisation previews + usePreviewQueue amélioré (142 lignes)
- `ca55c7c` : correction résolution source entity/class_object
- `06a24a8` / `c4a099e` : suppression dépendances CDN, CSS inline
- `cc47654` : refresh iframe après réordonnancement

---

## Recherche externe : résultats clés

### Iframes vs alternatives

| Alternative | Verdict | Raison |
|-------------|---------|--------|
| **Shadow DOM** | NON viable | Incompatibilité Plotly.js confirmée ([issue #1433](https://github.com/plotly/plotly.js/issues/1433), ouverte depuis 2017). Toolbar et tooltips cassés. |
| **Web Components** | Pas de valeur ajoutée | Ne résout pas l'isolation ; l'iframe reste nécessaire pour Plotly |
| **react-plotly.js direct** | Idéal long terme | Nécessite un changement d'API (JSON au lieu de HTML). Trop ambitieux pour ce cycle. |
| **Iframes optimisées** | Recommandé | `srcDoc` + cache + concurrence bornée + bundle partiel |

**Conclusion : les iframes restent le bon choix d'isolation pour Plotly.js.** L'optimisation porte sur la coordination et le caching, pas sur le remplacement du mécanisme.

> **Insight best practices** : utiliser `srcDoc` plutôt que `src` élimine un aller-retour HTTP par iframe. Le HTML est déjà en mémoire via TanStack Query. Utiliser un `ref` plutôt que la prop JSX `srcDoc` pour contrôler finement le timing du remplacement et éviter le flash blanc. Toujours vider `srcdoc = ''` au démontage pour forcer le nettoyage du browsing context (Plotly alloue beaucoup de mémoire pour les SVG et event listeners). ([MDN - srcdoc](https://developer.mozilla.org/en-US/docs/Web/API/HTMLIFrameElement/srcdoc))

### Kaleido (thumbnails server-side)

| Aspect | Kaleido v0.2.x | Kaleido v1.x |
|--------|----------------|---------------|
| Temps/image | 20-100ms | **2000-3000ms** |
| Chrome | Bundlé | **Requis sur le système** |
| Compatibilité | plotly < 6.1.1 | plotly >= 6.1.1 |

**Régression de performance 50x sur v1** ([issue #400](https://github.com/plotly/Kaleido/issues/400)). Non viable pour la génération temps réel de thumbnails. Alternative possible : `Plotly.toImage()` côté client après rendu, pour capturer un SVG et le cacher.

### Plotly.js bundles partiels — CORRECTION

Le bundle actuel (`3.0.1_plotly.min.js`) pèse **4.7MB**, pas 2.8MB. C'est Plotly v3 qui inclut maplibre-gl comme dépendance pour les traces maps.

**Approche recommandée : deux bundles distincts**

| Bundle | Traces | Taille estimée | Usage |
|--------|--------|----------------|-------|
| `plotly-niamoto-core.min.js` | scatter, bar, pie, heatmap, table, indicator | **~1MB** | Majorité des widgets |
| `plotly-niamoto-maps.min.js` | + choropleth_map, scattermap (noms Plotly v3) | **~2.5MB** | Widgets cartographiques uniquement |

Le `HtmlWrapper` doit conditionner l'injection du `<script>` selon le type de widget : charger le bundle léger par défaut, le bundle maps seulement quand nécessaire. Cela signifie que la majorité des thumbnails (non-map) chargeront **4.7x moins** de JS.

> **Build recommandé** : utiliser le CLI officiel Plotly (`npm run custom-bundle -- --traces bar,pie,scatter,heatmap,table,indicator --strict --out niamoto-core`) plutôt que l'approche require/register manuelle. Pour le bundle maps, les traces Plotly v3 s'appellent `scattermap` et `choropleth_map` (et non `scattermapbox`/`choroplethmapbox` de la v2). Vérifier la correspondance exacte entre noms API Python (`go.Scattermap`, `px.choropleth_map`) et noms de modules JS dans le CLI de build. Servir comme asset statique avec `Cache-Control: public, max-age=31536000, immutable`.
>
> **Référence** : [Plotly custom bundle guide](https://github.com/plotly/plotly.js/blob/master/CUSTOM_BUNDLE.md), [Plotly Community - reduce bundle size](https://community.plotly.com/t/how-can-i-reduce-bundle-size-of-plotly-js-in-react-app/89910)

### TanStack Query v5

Déjà dans le projet (`@tanstack/react-query ^5.81.5`). Avantages non exploités :
- **Déduplication automatique** : 10 composants demandant le même templateId = 1 seule requête
- **Signal/abort** : annulation automatique au démontage (mais PAS au toggle `enabled`)
- **staleTime/gcTime** : contrôle fin de la fraîcheur du cache
- **Prefetching** : `prefetchQuery` / `ensureQueryData` pour pré-charger les previews visibles
- **Invalidation hiérarchique** : `['preview']` invalide tout, `['preview', 'thumbnail']` juste les miniatures

> **Insight TanStack Query** : TanStack Query cache **n'importe quel type** retourné par `queryFn`, pas uniquement du JSON. Les chaînes HTML sont un cas d'usage parfaitement valide. Utiliser `queryOptions()` factory pour des définitions réutilisables et type-safe. ([TanStack Query v5 - Caching Examples](https://tanstack.com/query/v5/docs/react/guides/caching), [TanStack Query v5 - Query Keys](https://tanstack.com/query/v5/docs/framework/react/guides/query-keys))

> **Attention** : `staleTime: 60s` est **trop conservateur** pour des données écologiques qui ne changent qu'après import explicite. Recommandation : `staleTime: Infinity` + invalidation événementielle uniquement (callback import/save). ([TanStack Query v5 - QueryClient reference](https://tanstack.com/query/v5/docs/reference/QueryClient))

### CSS `content-visibility: auto`

Baseline depuis septembre 2025 ([Can I Use](https://caniuse.com/css-content-visibility)). Skip le rendu des éléments hors viewport sans impact réseau.

```css
.preview-card {
  content-visibility: auto;
  contain-intrinsic-size: 300px 200px;
}
```

> **Attention** : `content-visibility: auto` ne défère PAS les requêtes réseau — il ne skip que le rendu. Les iframes seront toujours téléchargées. `contain-intrinsic-size` est **crucial** pour éviter les layout shifts. ([DebugBear - content-visibility](https://www.debugbear.com/blog/content-visibility-api), [web.dev - content-visibility](https://web.dev/articles/content-visibility))

---

## Solution proposée

### Architecture deux niveaux

```
                    ┌─────────────────────────────────────────┐
                    │           Grilles / Listes               │
                    │  ┌───────┐ ┌───────┐ ┌───────┐         │
                    │  │ thumb │ │ thumb │ │ thumb │  ...     │  ← Plotly staticPlot
                    │  └───────┘ └───────┘ └───────┘         │    données tronquées
                    └──────────────┬──────────────────────────┘    ~1MB JS (core)
                                  │ clic / sélection
                                  ▼
                    ┌─────────────────────────────────────────┐
                    │          Vue détail / Plein écran        │
                    │  ┌───────────────────────────────┐      │
                    │  │   Plotly.js interactif         │      │  ← Full interactive
                    │  │   dans iframe srcDoc            │      │    données complètes
                    │  └───────────────────────────────┘      │    ~1MB ou ~2.5MB
                    └─────────────────────────────────────────┘    selon type widget
```

> **Insight simplification** : le mode thumbnail peut être différé. TanStack Query + `enabled: visible` + limite navigateur 6 connexions résout déjà le problème de concurrence. Considérer d'abord un déploiement `full` uniquement avec `staticPlot: true` dans les grilles (via CSS `pointer-events: none`), puis ajouter le mode thumbnail comme optimisation ciblée si la performance reste insuffisante.

### Contrat API unifié

```
  AddWidgetModal ──┐
  LayoutOverview ──┤
  WidgetDetail   ──┼──> GET/POST /api/preview ──> PreviewEngine.render() ──> PreviewResult
  RecipeEditor   ──┤
  WidgetCard     ──┘
```

Un seul point d'entrée, un seul pipeline, des consommateurs multiples.

---

## Approche technique

### Backend : PreviewEngine

#### Module simplifié (3 fichiers au lieu de 7)

```
src/niamoto/gui/api/services/preview_engine/
├── __init__.py
├── models.py          # PreviewRequest, PreviewResult, PreviewMode
└── engine.py          # PreviewEngine — résolution, données, rendu, wrapper HTML
```

> **Insight simplification** : les 6 modules originaux (`resolver.py`, `data_provider.py`, `renderer.py`, `html_wrapper.py`, `errors.py`) représentent un pipeline linéaire de ~400-600 lignes totales. Les fusionner dans `engine.py` réduit l'indirection sans perte de lisibilité. Utiliser les exceptions Python standard (`ValueError`, `FileNotFoundError`) au lieu d'une hiérarchie d'erreurs dédiée.

> **Insight architecture** : ajouter un `cache.py` **uniquement si** la logique de cache dépasse 30 lignes. Sinon, intégrer le TTLCache et le compteur de version dans `engine.py`. Le module `models.py` reste séparé car c'est le contrat API.

#### Interfaces

```python
# models.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

PreviewMode = Literal["thumbnail", "full"]

@dataclass(frozen=True)
class PreviewRequest:
    template_id: Optional[str] = None
    group_by: Optional[str] = None
    source: Optional[str] = None
    entity_id: Optional[str] = None
    mode: PreviewMode = "full"
    inline: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class PreviewResult:
    html: str
    etag: str
    preview_key: str
    warnings: tuple[str, ...] = ()  # tuple immuable au lieu de list mutable
```

> **Corrections appliquées :**
> - **Suppression de `PreviewContext`** — jamais utilisé dans le rendu. Si besoin d'analytics, ajouter un query param plus tard.
> - **Suppression de `timings`** — prématuré pour un outil local mono-utilisateur. Utiliser `logger.debug` pendant le développement.
> - **`warnings` est maintenant un `tuple`** — les `List` et `Dict` dans un `frozen=True` restent mutables (`result.warnings.append()` fonctionne). Utiliser `tuple` pour une vraie immutabilité.
> - **`InlinePreviewBody` reste en Pydantic** pour la validation FastAPI du POST endpoint — cohérent avec la convention du projet.

> **Insight patterns** : le projet utilise Pydantic `BaseModel` pour les modèles API (`SaveRecipeRequest`, `LayoutUpdateRequest`, etc.) et `@dataclass` pour les objets internes (`MapStyle`, `MapConfig`). `PreviewRequest` est construit dans le router depuis des paramètres parsés, jamais désérialisé directement par FastAPI → `@dataclass` est correct.

> **Considération alternative (patterns)** : utiliser des types unions discriminés (`TemplatePreviewRequest | InlinePreviewRequest | LayoutPreviewRequest`) au lieu d'un seul type avec tous les champs optionnels. Cela renforce les invariants au niveau type, mais ajoute de la complexité pour 3 routes seulement. À évaluer selon le confort de l'équipe.

```python
# engine.py
from starlette.concurrency import run_in_threadpool

class PreviewEngine:
    def __init__(self, db_path: str, config_dir: str):
        self._db_path = db_path
        self._config_dir = config_dir
        self._data_fingerprint: str = self._compute_data_fingerprint()
        self._nav_css: str | None = None  # Cache assets navigation (chargé une fois)
        self._nav_js: str | None = None

    def render(self, request: PreviewRequest) -> PreviewResult:
        """Pipeline synchrone : resolve → load → transform → render → wrap."""
        # 1. Résolution template_id → (transformer, widget, source)
        spec = self._resolve(request)

        # 2. Chargement données avec limites par mode
        data = self._load_data(spec, mode=request.mode)

        # 3. Transform + Render widget → HTML
        widget_html = self._render_widget(spec, data, mode=request.mode)

        # 4. Wrapper HTML avec le bon bundle Plotly
        html = self._wrap_html(widget_html, mode=request.mode, needs_maps=spec.needs_maps)

        etag = self._compute_etag(request)
        return PreviewResult(
            html=html, etag=etag,
            preview_key=spec.preview_key,
            warnings=tuple(spec.warnings),
        )

    def _compute_data_fingerprint(self) -> str:
        """Empreinte des fichiers de données : mtime DB + mtime configs.
        Résiste aux redémarrages (basé fichiers) et aux modifs hors-app.
        Coût : 2-3 appels stat, fait UNE SEULE FOIS à l'init et après invalidate()."""
        import hashlib, os
        parts = [str(os.path.getmtime(self._db_path))]
        for name in ("import.yml", "transform.yml", "export.yml"):
            cfg = os.path.join(self._config_dir, name)
            if os.path.exists(cfg):
                parts.append(str(os.path.getmtime(cfg)))
        return hashlib.md5(":".join(parts).encode()).hexdigest()[:12]

    def _compute_etag(self, request: PreviewRequest) -> str:
        """ETag = fingerprint données + clé de requête.
        Le fingerprint est recalculé uniquement à invalidate(), pas à chaque requête."""
        import hashlib
        key = f"{request.template_id}:{request.group_by}:{request.source}:{request.entity_id}:{self._data_fingerprint}"
        return hashlib.md5(key.encode()).hexdigest()

    def invalidate(self):
        """Recalcule le fingerprint données — appelé après import ou save config.
        Coût : 2-3 appels stat (une fois), puis zéro I/O jusqu'au prochain invalidate()."""
        self._data_fingerprint = self._compute_data_fingerprint()
```

> **Corrections critiques appliquées :**
>
> 1. **Sync dans async** — `engine.render()` est synchrone (I/O DB + fichiers). Les endpoints **doivent** utiliser `await run_in_threadpool(engine.render, req)` ou être déclarés en `def` (pas `async def`). Sans cela, l'event loop FastAPI est bloqué — c'est la même cause des freezes UI que le plan cherche à résoudre.
>
> 2. **ETag par fingerprint fichiers** — calcule un hash `mtime(db) + mtime(configs)` **une seule fois** à l'init et après chaque `invalidate()`. Entre les deux : zéro I/O. Résiste aux redémarrages (basé fichiers réels), aux modifs hors-app (mtime change), et au multi-worker (chaque worker calcule le même fingerprint à partir des mêmes fichiers). Pas de compteur en mémoire qui se perd au restart.
>
> 3. **Cache assets navigation** — les fichiers CSS/JS de navigation sont chargés une fois au premier appel au lieu de relire le disque à chaque requête.

#### Limites thumbnail (concrètes)

| Paramètre | thumbnail | full |
|-----------|-----------|------|
| Lignes max occurrences | 50 | 500 |
| Features max géométrie | 10 | illimité |
| `_all_map` | Interdit | Autorisé |
| `staticPlot` Plotly | `true` | `false` |
| `displayModeBar` | `false` | `true` |
| Légende | Masquée | Visible |
| Marges Plotly | `l=5,r=5,t=5,b=5` | Défaut plugin |

> **Insight performance** : ces limites devraient être **par type de widget**, pas globales :
>
> | Widget | Limite thumbnail recommandée | Raison |
> |--------|------------------------------|--------|
> | bar_chart | 10-15 barres | 50 barres illisible à 90px |
> | pie_chart | 5-8 slices | Au-delà, les labels se chevauchent |
> | scatter | 50 points | Adéquat |
> | heatmap | 50 lignes | Dépend des colonnes |
> | table | 5 lignes | 50 lignes à 90px de haut est invisible |
> | indicator/gauge | N/A | Valeur unique, pas de troncation |
> | map (choropleth) | 10 features | Suffisant pour entités, trop peu pour choroplèthe |
>
> Définir les limites dans un dict constant ou dans les métadonnées de chaque plugin widget.

#### Endpoints simplifiés

```python
# routers/preview.py  (nouveau fichier, remplace la logique dans templates.py et layout.py)
from starlette.concurrency import run_in_threadpool

@router.get("/api/preview/{template_id}")
async def get_preview(
    template_id: str,
    group_by: str | None = None,
    source: str | None = None,
    entity_id: str | None = None,
    mode: PreviewMode = "full",
    request: Request = None,
):
    req = PreviewRequest(
        template_id=template_id,
        group_by=group_by, source=source,
        entity_id=entity_id, mode=mode,
    )
    # ETag 304
    if_none_match = request.headers.get("if-none-match")
    result = await run_in_threadpool(engine.render, req)

    if if_none_match and if_none_match == result.etag:
        return Response(status_code=304)

    return HTMLResponse(result.html, headers={
        "ETag": result.etag,
        "Cache-Control": "no-cache",
        "X-Preview-Key": result.preview_key,
        "X-Preview-Mode": req.mode,
    })

@router.post("/api/preview")
async def post_preview(body: InlinePreviewBody):
    req = PreviewRequest(
        template_id=body.template_id,
        group_by=body.group_by, source=body.source,
        entity_id=body.entity_id, mode=body.mode,
        inline=body.inline,
    )
    result = await run_in_threadpool(engine.render, req)
    return HTMLResponse(result.html, headers={"ETag": result.etag, "Cache-Control": "no-cache"})

@router.get("/api/layout/{group_by}/preview/{widget_index}")
async def layout_preview(group_by: str, widget_index: int, entity_id: str | None = None):
    template_id = resolve_layout_widget(group_by, widget_index)
    req = PreviewRequest(
        template_id=template_id,
        group_by=group_by, entity_id=entity_id,
        mode="thumbnail",
    )
    result = await run_in_threadpool(engine.render, req)
    return HTMLResponse(result.html, headers={"ETag": result.etag, "Cache-Control": "no-cache"})

# --- Rétrocompatibilité : ancienne route templates/preview ---
# Garder pendant la migration pour ne pas casser les call sites existants et les tests.
# Supprimer en Phase 5 (nettoyage) une fois tous les appels migrés.
@router.get("/api/templates/preview/{template_id}")
async def legacy_get_preview(
    template_id: str,
    group_by: str | None = None,
    source: str | None = None,
    entity_id: str | None = None,
    mode: PreviewMode = "full",
    request: Request = None,
):
    """Alias rétrocompatible — délègue à get_preview(). À supprimer en Phase 5."""
    return await get_preview(template_id, group_by, source, entity_id, mode, request)
```

> **Corrections appliquées :**
> - `await run_in_threadpool(engine.render, req)` au lieu de l'appel synchrone direct. Cohérent avec la convention existante (`async def` dans tous les routers du projet).
> - **Rétrocompatibilité** : l'ancienne route `/api/templates/preview/{template_id}` est conservée comme alias qui délègue à `get_preview()`. Cela évite de casser les call sites frontend et les tests existants. La suppression est planifiée en Phase 5 (nettoyage). Les tests peuvent migrer progressivement vers `/api/preview/`.

#### Invalidation cache — simplifiée

```python
# Dans le callback de succès d'import (côté Python)
engine.invalidate()  # Incrémente le compteur de version
```

```typescript
// Dans le callback de succès d'import (côté frontend)
queryClient.invalidateQueries({
  queryKey: ['preview'],
  refetchType: 'active',  // Ne refetch que les queries avec observateurs actifs
})
```

> **Simplification** : pas besoin de SSE, pas besoin de polling endpoint. L'import est une action utilisateur explicite dans le frontend. Le callback de succès de la mutation d'import peut directement appeler `queryClient.invalidateQueries()`. C'est 1 ligne de code frontend au lieu de ~50-100 lignes d'infrastructure SSE.
>
> `refetchType: 'active'` est la valeur par défaut dans TanStack Query v5, mais être explicite documente l'intention. Les tiles hors écran seront simplement marquées stale et re-fetchées paresseusement au scroll.

#### Spatial robuste

```python
# Dans engine.py
def _resolve_geometry_column(self, columns: list[str]) -> str | None:
    """Résout la colonne géométrique par priorité."""
    # 1. Colonnes natives GEOMETRY
    for col in columns:
        if col.endswith("_geom") or col == "geometry":
            return col
    # 2. Fallback WKT explicite
    for col in columns:
        if "wkt" in col.lower():
            return col
    return None  # Pas de warning silencieux, erreur explicite au caller
```

> **Insight patterns** : ce type de détection de colonnes existe déjà dans `PreviewService.load_sample_occurrences()` (preview_service.py:344). Une refactorisation future pourrait centraliser la détection dans `EntityRegistry`.

### Frontend : hook unifié + TanStack Query

#### Nouveau socle

```
src/niamoto/gui/ui/src/lib/preview/
├── types.ts              # PreviewDescriptor, PreviewMode
└── usePreviewFrame.ts    # Hook unifié + buildQueryKey + constantes
```

```
src/niamoto/gui/ui/src/components/preview/
├── PreviewTile.tsx       # Thumbnail dans grille (srcDoc, IntersectionObserver)
├── PreviewPane.tsx       # Vue complète (srcDoc, full mode)
├── PreviewSkeleton.tsx   # Placeholder de chargement
└── PreviewError.tsx      # Affichage d'erreur
```

> **Simplification** : `constants.ts` et `preview-keys.ts` sont fusionnés dans `usePreviewFrame.ts` — 3 constantes et une fonction de construction de clé ne justifient pas des fichiers séparés.

#### Types

```typescript
// types.ts
export type PreviewMode = 'thumbnail' | 'full'

/** Plugin configuration validée côté serveur par plugin type */
type PluginParams = Record<string, unknown>

interface InlinePreviewConfig {
  transformerPlugin: string
  transformerParams: PluginParams
  widgetPlugin: string
  widgetParams?: PluginParams | null
  widgetTitle?: string
}

export interface PreviewDescriptor {
  templateId?: string
  groupBy?: string
  source?: string
  entityId?: string
  mode: PreviewMode
  inline?: InlinePreviewConfig
}
```

> **Corrections appliquées :**
> - **Suppression de `PreviewContext`** — non utilisé dans le rendu.
> - **`inline` extrait dans `InlinePreviewConfig`** avec un alias `PluginParams` documenté au lieu de `Record<string, unknown>` anonyme.
> - **Nommage camelCase cohérent** : `transformerPlugin` au lieu de `transformer_plugin` (snake_case) — aligne avec les conventions TypeScript du projet.

#### Hook unifié basé TanStack Query

```typescript
// usePreviewFrame.ts
import { useQuery, useQueryClient, QueryClient } from '@tanstack/react-query'

const STALE_TIME = Infinity  // Données écologiques : stables entre imports
const GC_TIME = 5 * 60_000  // 5min : garder en cache après démontage
const MAX_CONCURRENT_RENDERS = 3  // Limite les iframes Plotly en cours de rendu simultané

/** Sémaphore léger pour borner les rendus Plotly concurrents.
 *  TanStack Query gère la déduplication et le cache, mais ne limite PAS
 *  le nombre de requêtes parallèles. Le navigateur borne les connexions HTTP (6/domaine),
 *  mais ne borne PAS le parsing/rendu JS de Plotly dans les iframes (~200ms thread principal chacun).
 *  Ce sémaphore empêche > 3 initialisations Plotly simultanées → réduit le jank. */
const renderQueue: Array<() => void> = []
let activeRenders = 0

function acquireRenderSlot(): Promise<void> {
  if (activeRenders < MAX_CONCURRENT_RENDERS) {
    activeRenders++
    return Promise.resolve()
  }
  return new Promise(resolve => renderQueue.push(resolve))
}

function releaseRenderSlot(): void {
  activeRenders--
  const next = renderQueue.shift()
  if (next) {
    activeRenders++
    next()
  }
}

function buildQueryKey(d: PreviewDescriptor): readonly unknown[] {
  // Base commune : mode + contexte de résolution (groupBy, source, entityId)
  const base = [
    'preview', d.mode,
    d.groupBy ?? '__default',
    d.source ?? '__default',
    d.entityId ?? '__default',
  ]
  if (d.inline) {
    return [...base, 'inline', stableHash(d.inline)] as const
  }
  return [...base, d.templateId ?? '__default'] as const
}

function stableHash(obj: Record<string, unknown>): string {
  return JSON.stringify(obj, Object.keys(obj).sort())
}

function buildPreviewUrl(d: PreviewDescriptor): string {
  const params = new URLSearchParams()
  if (d.groupBy) params.set('group_by', d.groupBy)
  if (d.source) params.set('source', d.source)
  if (d.entityId) params.set('entity_id', d.entityId)
  if (d.mode) params.set('mode', d.mode)
  const qs = params.toString()
  return `/api/preview/${d.templateId}${qs ? `?${qs}` : ''}`
}

export function usePreviewFrame(
  descriptor: PreviewDescriptor | null,
  visible: boolean,
) {
  const abortRef = useRef<AbortController | null>(null)

  // Annuler les requêtes en vol quand la visibilité change
  useEffect(() => {
    if (!visible) {
      abortRef.current?.abort()
    }
  }, [visible])

  const query = useQuery({
    queryKey: descriptor ? buildQueryKey(descriptor) : ['preview', 'none'],
    queryFn: async ({ signal }) => {
      if (!descriptor) throw new Error('Descriptor is required')

      // Signal combiné : TanStack (unmount) + visibilité
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const combinedSignal = AbortSignal.any([signal, controller.signal])

      // Sémaphore : limite les rendus Plotly concurrents (jank CPU, pas réseau)
      await acquireRenderSlot()
      try {
        if (descriptor.inline) {
          const res = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(descriptor),
            signal: combinedSignal,
          })
          if (!res.ok) throw new Error(`Preview ${res.status}`)
          return res.text()
        }

        const url = buildPreviewUrl(descriptor)
        const res = await fetch(url, { signal: combinedSignal })
        if (!res.ok) throw new Error(`Preview ${res.status}`)
        return res.text()
      } finally {
        releaseRenderSlot()
      }
    },
    enabled: visible && descriptor !== null,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    retry: 1,
    refetchOnWindowFocus: false,
  })

  return {
    html: query.data ?? null,
    loading: query.isLoading,
    error: query.error?.message ?? null,
    fromCache: query.isStale === false,
  }
}

/** Invalidation globale — appelée dans le callback de succès d'import */
let invalidationTimer: ReturnType<typeof setTimeout> | null = null
export function invalidateAllPreviews(queryClient: QueryClient) {
  if (invalidationTimer) clearTimeout(invalidationTimer)
  invalidationTimer = setTimeout(() => {
    invalidationTimer = null
    queryClient.invalidateQueries({
      queryKey: ['preview'],
      refetchType: 'active',
    })
  }, 300)
}
```

> **Corrections critiques appliquées :**
>
> 1. **Abort sur changement de visibilité** — TanStack Query ne cancel PAS les requêtes quand `enabled` passe à `false`. Sans abort explicite, scroll rapide passé 20 tiles = 20 requêtes en vol. Le `AbortController` combiné (`AbortSignal.any`) annule la requête à la fois au démontage ET au changement de visibilité. (`AbortSignal.any()` est Baseline depuis mars 2024.)
>
> 2. **`staleTime: Infinity`** — les données écologiques changent uniquement après import explicite. Aucune raison de re-fetcher automatiquement. L'invalidation est déclenchée par l'utilisateur (import, save config).
>
> 3. **`throw` au lieu de `return null`** — évite que `query.data` soit typé `string | null | undefined`. Avec `enabled: descriptor !== null`, le branch `null` n'est jamais exécuté.
>
> 4. **Invalidation debouncée** — empêche le thundering herd quand l'utilisateur sauvegarde config puis importe rapidement. 300ms de debounce + `refetchType: 'active'` (ne refetch que les queries visibles).
>
> 5. **queryKey hiérarchique** — permet l'invalidation sélective : `['preview']` invalide tout, `['preview', 'thumbnail']` juste les miniatures.
>
> 6. **queryKey inline complète** — la branche inline inclut `groupBy`, `source`, `entityId` dans la clé (pas seulement le hash inline). Deux previews inline identiques mais avec des `groupBy` différents retournent des résultats différents — la clé doit le refléter.
>
> 7. **Sémaphore de concurrence Plotly** — `MAX_CONCURRENT_RENDERS = 3` borne les initialisations Plotly.js simultanées dans les iframes. TanStack Query gère la déduplication et le cache réseau, mais ne limite pas le nombre de rendus CPU-intensifs en parallèle (~200ms de thread principal par widget Plotly). Le navigateur limite les connexions HTTP (6/domaine) mais pas le parsing JS.

#### Composants partagés

```typescript
// PreviewTile.tsx — miniature dans grilles
interface PreviewTileProps {
  descriptor: PreviewDescriptor
  width?: number   // défaut 120
  height?: number  // défaut 90
  className?: string
}

function PreviewTile({ descriptor, width = 120, height = 90, className }: PreviewTileProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const visible = useIntersectionObserver(containerRef, { rootMargin: '120px' })

  // Stabiliser le descriptor pour éviter les re-renders (objet spread = nouvelle référence)
  const thumbDescriptor = useMemo(
    () => ({ ...descriptor, mode: 'thumbnail' as const }),
    [descriptor.templateId, descriptor.groupBy, descriptor.source, descriptor.entityId,
     descriptor.inline ? stableHash(descriptor.inline) : null]
  )

  // Debounce la visibilité pour éviter le strobe skeleton/content au scroll rapide
  const [debouncedVisible, setDebouncedVisible] = useState(false)
  useEffect(() => {
    if (visible) {
      setDebouncedVisible(true)
    } else {
      const t = setTimeout(() => setDebouncedVisible(false), 32)
      return () => clearTimeout(t)
    }
  }, [visible])

  const { html, loading, error } = usePreviewFrame(thumbDescriptor, debouncedVisible)

  // Nettoyage Plotly au démontage
  useEffect(() => {
    return () => {
      if (iframeRef.current) {
        iframeRef.current.srcdoc = ''
      }
    }
  }, [])

  return (
    <div ref={containerRef} className={className}
         style={{ width, height, contentVisibility: 'auto', containIntrinsicSize: `${width}px ${height}px` }}>
      {loading && <PreviewSkeleton width={width} height={height} />}
      {error && <PreviewErrorPlaceholder message={error} />}
      {html && (
        <iframe
          ref={iframeRef}
          srcDoc={html}
          title="Widget preview"
          sandbox="allow-scripts"
          style={{ width: 400, height: 300, transform: `scale(${width / 400})`, transformOrigin: '0 0' }}
        />
      )}
    </div>
  )
}
```

> **Corrections appliquées :**
> - **`useMemo` avec dépendances primitives** au lieu de `[descriptor]` (référence objet instable). Déstructuration des champs pour comparaison par valeur.
> - **Debounce visibilité (32ms)** — empêche le cycle skeleton→content→skeleton quand l'utilisateur scrolle rapidement.
> - **Nettoyage iframe au démontage** — `srcdoc = ''` force la libération du browsing context Plotly.js (SVG, event listeners, resize observers).
> - **`sandbox="allow-scripts"`** — unifié sur toutes les iframes preview. Sans `allow-same-origin`, le contenu ne peut pas accéder au DOM parent.
> - **`containIntrinsicSize`** — évite le layout shift avec `content-visibility: auto`.

```typescript
// PreviewPane.tsx — vue complète
function PreviewPane({ descriptor, className }: PreviewPaneProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const fullDescriptor = useMemo(
    () => ({ ...descriptor, mode: 'full' as const }),
    [descriptor.templateId, descriptor.groupBy, descriptor.source, descriptor.entityId,
     descriptor.inline ? stableHash(descriptor.inline) : null]
  )
  const { html, loading, error } = usePreviewFrame(fullDescriptor, true)
  const queryClient = useQueryClient()

  // Nettoyage Plotly au démontage
  useEffect(() => {
    return () => {
      if (iframeRef.current) {
        iframeRef.current.srcdoc = ''
      }
    }
  }, [])

  return (
    <div className={className}>
      <div className="flex justify-end mb-1">
        <button onClick={() => invalidateAllPreviews(queryClient)}>
          Rafraîchir
        </button>
      </div>
      {loading && <PreviewSkeleton />}
      {error && <PreviewError message={error} />}
      {html && (
        <iframe
          ref={iframeRef}
          srcDoc={html}
          title="Widget preview"
          sandbox="allow-scripts"
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      )}
    </div>
  )
}
```

### Plotly.js : double bundle

```bash
# Bundle core (non-map widgets)
npm run custom-bundle -- \
  --traces bar,pie,scatter,heatmap,table,indicator \
  --out niamoto-core --strict

# Bundle maps (widgets cartographiques)
# ATTENTION : Plotly v3 a renommé les traces map :
#   scattermapbox → scattermap    (utilisé par go.Scattermap dans map_renderer.py et interactive_map.py)
#   choroplethmapbox → choropleth_map  (utilisé par px.choropleth_map dans interactive_map.py)
# Vérifier les noms exacts dans le CLI de build Plotly v3 — les modules
# internes peuvent différer des noms d'API Python (maplibre-gl remplace mapbox-gl).
npm run custom-bundle -- \
  --traces bar,pie,scatter,heatmap,table,indicator,choropleth_map,scattermap \
  --out niamoto-maps --strict
```

```python
# Dans engine.py — _wrap_html
def _wrap_html(self, widget_html: str, mode: PreviewMode, needs_maps: bool) -> str:
    bundle = "plotly-niamoto-maps.min.js" if needs_maps else "plotly-niamoto-core.min.js"
    # ... injection du <script src=".../{bundle}">
```

> Servir avec `Cache-Control: public, max-age=31536000, immutable` depuis `/api/site/assets/js/vendor/plotly/`.

---

## Approches alternatives considérées

### 1. react-plotly.js en rendu direct (sans iframes)

Remplacer les iframes par des composants `<Plot>` React utilisant `react-plotly.js/factory` avec un bundle partiel.

**Avantages** : une seule instance Plotly.js partagée, intégration React native, TanStack Query cache le JSON directement.

**Rejeté car** :
- Nécessite un changement d'API (retourner du JSON Plotly au lieu de HTML)
- Perte d'isolation CSS (les styles widgets pourraient fuir dans l'app)
- Les widgets non-Plotly (navigation, info grids, tables HTML) nécessiteraient un chemin séparé
- Effort estimé : 5-10 jours vs 3-5 jours pour l'optimisation iframe

**Verdict** : excellente direction long terme, mais trop ambitieux pour ce cycle. À considérer pour T2 2026.

### 2. Kaleido server-side pour les thumbnails

Générer des images PNG/SVG côté serveur via Kaleido pour les miniatures.

**Rejeté car** :
- Régression de performance 50x dans Kaleido v1 (2-3s/image vs 20-100ms en v0)
- Dépendance Chrome/Chromium sur le serveur
- Non viable pour la génération temps réel

### 3. Shadow DOM au lieu des iframes

Utiliser Shadow DOM pour l'isolation CSS des widgets.

**Rejeté car** : incompatibilité Plotly.js confirmée (issue #1433, ouverte depuis 2017). Toolbar et tooltips cassés dans Shadow DOM.

### 4. Service Worker pour le cache preview

Cache stale-while-revalidate au niveau Service Worker pour la persistance cross-session.

**Différé** : TanStack Query + ETag HTTP couvrent 90% du besoin. Le Service Worker ajoute une valeur marginale pour les démarrages à froid. À considérer après la phase 5.

---

## Phases d'implémentation (consolidées : 5 phases)

### Phase 1 : PreviewEngine backend + contrats (fusionnée phases 1-2-3 originales)

**Fichiers créés :**
- `src/niamoto/gui/api/services/preview_engine/__init__.py`
- `src/niamoto/gui/api/services/preview_engine/models.py`
- `src/niamoto/gui/api/services/preview_engine/engine.py`
- `src/niamoto/gui/api/routers/preview.py` (nouveau router unifié)
- `src/niamoto/gui/ui/src/lib/preview/types.ts`

**Fichiers modifiés :**
- `src/niamoto/gui/api/routers/templates.py` — preview_template() délègue au nouveau engine
- `src/niamoto/gui/api/routers/layout.py` — supprime l'import cross-router, délègue au nouveau engine
- `src/niamoto/gui/api/routers/recipes.py` — recipe preview délègue au nouveau engine
- `src/niamoto/gui/api/main.py` — enregistrer le nouveau router

**Livrables :**
- [x] `PreviewEngine.render()` implémenté avec les 7 branches unifiées
- [x] `PreviewRequest`, `PreviewResult` (dataclasses frozen)
- [x] Types `PreviewDescriptor`, `PreviewMode` TypeScript
- [x] GET, POST, layout routes dans le nouveau router
- [x] Route legacy `/api/templates/preview/{template_id}` → alias rétrocompatible vers `get_preview()`
- [x] `await run_in_threadpool(engine.render, req)` dans tous les endpoints
- [x] ETag via fingerprint fichiers (mtime DB + configs, calculé à l'init et après invalidate)
- [x] Suppression de l'import cross-router dans layout.py (délègue au engine)
- [ ] **Sécurité** : `html.escape()` sur toutes les données interpolées dans les widgets non-Plotly
- [x] Tests : modèles, router intégration, layout délégation (20 tests)
- [ ] Suppression de `layout.py._wrap_html_response()` (reste pour les cas d'erreur, nettoyage Phase 5)

**Critère** : un seul chemin transform+render, plus d'import cross-router, sandbox unifié.

### Phase 2 : Bundle Plotly double (indépendante)

**Fichiers créés :**
- Script de build custom (ou Makefile target)
- `plotly-niamoto-core.min.js` (~1MB)
- `plotly-niamoto-maps.min.js` (~2.5MB)

**Fichiers modifiés :**
- `src/niamoto/gui/api/services/preview_engine/engine.py` — injection conditionnelle du bundle

**Livrables :**
- [ ] Deux bundles Plotly custom
- [ ] HtmlWrapper injecte le bundle core par défaut, le bundle maps uniquement pour les widgets cartographiques
- [ ] Vérification visuelle : tous les types de widgets rendus correctement
- [ ] `Cache-Control: immutable` sur les fichiers bundle

**Critère** : les widgets non-map chargent ~1MB au lieu de 4.7MB (réduction 78%).

### Phase 3 : Hook frontend + migration AddWidgetModal (fusionnée phases 5-6 partiellement)

**Fichiers créés :**
- `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts`
- `src/niamoto/gui/ui/src/lib/preview/types.ts`
- `src/niamoto/gui/ui/src/components/preview/PreviewTile.tsx`
- `src/niamoto/gui/ui/src/components/preview/PreviewPane.tsx`
- `src/niamoto/gui/ui/src/components/preview/PreviewSkeleton.tsx`
- `src/niamoto/gui/ui/src/components/preview/PreviewError.tsx`

**Fichiers modifiés :**
- `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx` — 3 composants → 2 partagés

**Livrables :**
- [x] `usePreviewFrame` basé TanStack Query (`staleTime: Infinity`, `gcTime: 5min`)
- [x] Sémaphore de concurrence Plotly (`MAX_CONCURRENT_RENDERS = 3`) intégré dans la queryFn
- [x] Abort explicite sur changement de visibilité (`AbortSignal.any`)
- [x] Invalidation debouncée (300ms) avec `refetchType: 'active'`
- [x] `PreviewTile` avec IntersectionObserver, debounce visibilité 32ms, nettoyage iframe au démontage
- [x] `PreviewPane` avec nettoyage iframe
- [x] `sandbox="allow-scripts"` sur toutes les iframes preview
- [x] Migration `AddWidgetModal` : 3 composants internes → 2 composants partagés

**Critère** : AddWidgetModal utilise exclusivement les composants partagés, scroll stable.

### Phase 4 : Migration des autres composants + invalidation

**Fichiers modifiés :**
- `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx` — `SortableWidgetCard` et `NavigationSidebar` → `PreviewTile`
- `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.tsx` → `PreviewPane`
- `src/niamoto/gui/ui/src/components/widgets/WidgetPreviewPanel.tsx` → `PreviewPane`
- `src/niamoto/gui/ui/src/components/widgets/WidgetMiniature.tsx` → `PreviewTile`
- `src/niamoto/gui/ui/src/components/layout-editor/WidgetCard.tsx` → `PreviewTile`
- Callback de succès d'import → `queryClient.invalidateQueries({ queryKey: ['preview'] })`

**Livrables :**
- [x] Tous les composants preview migrent vers `PreviewTile` ou `PreviewPane`
- [x] Suppression de `usePreviewHtml`, `usePreviewQueue.ts`, `lru-cache.ts`
- [x] Invalidation preview dans le callback import + save config (frontend)
- [x] `engine.invalidate()` dans le pipeline import (backend)
- [x] Comportement identique vérifié dans chaque contexte

**Critère** : aucun composant n'utilise d'iframe `src` direct, comportement homogène partout.

### Phase 5 : Nettoyage + benchmark

**Fichiers supprimés :**
- `src/niamoto/gui/api/services/preview_service.py`
- Code legacy inactif dans `templates.py`
- Code preview legacy dans `layout.py` et `recipes.py`
- Route legacy `/api/templates/preview/{template_id}` (alias rétrocompatible ajouté en Phase 1)

**Livrables :**
- [ ] Suppression de `PreviewService` et de tout code legacy preview (reporté — engine.py + templates.py dépendent encore des méthodes utilitaires)
- [x] Suppression de la route legacy `/api/templates/preview/` côté frontend (aucun composant ne l'utilise)
- [x] Script de benchmark : `scripts/bench_preview.py`
- [ ] Rapport comparatif Phase 0 vs Phase 5

**Critère** :
- P95 preview modal < 1500ms sur dataset shapes réel
- Iframes actives simultanées ≤ 6 (limite navigateur naturelle)
- Zéro freeze UI reproductible en test manuel
- Aucun écart de rendu entre modal/layout/detail

---

## Critères d'acceptation

### Exigences fonctionnelles

- [ ] Tous les types de widgets rendus correctement (bar, pie, scatter, heatmap, table, map, scattermap, scalar, navigation, info)
- [ ] Mode `thumbnail` : rendu rapide avec données tronquées, pas d'interactivité
- [ ] Mode `full` : rendu complet avec hover, zoom, modebar
- [ ] Transition thumbnail → full fluide (affichage immédiat du cache thumbnail, remplacement par full quand prêt)
- [ ] Drag & drop layout fonctionne sans interférence avec les previews
- [ ] Changement d'entité rafraîchit tous les previews visibles
- [ ] Widget sans données : placeholder lisible à l'échelle thumbnail
- [ ] Erreur de rendu : message explicite, pas de iframe vide
- [ ] **Sécurité** : `sandbox="allow-scripts"` sur toutes les iframes preview (pas de `allow-same-origin`)
- [ ] **Sécurité** : `html.escape()` sur toutes les données utilisateur dans les widgets non-Plotly

### Exigences non-fonctionnelles

- [ ] P95 preview modal < 1500ms sur dataset shapes réel
- [ ] Bundle Plotly core ≤ 1.2MB, bundle maps ≤ 3MB
- [ ] Iframes actives simultanées ≤ 6
- [ ] Zéro freeze UI reproductible
- [ ] `content-visibility: auto` + `contain-intrinsic-size` sur les cartes preview hors viewport

### Quality gates

- [ ] Tests unitaires : clé cache/etag stable, adaptation mode thumbnail, normalisation erreurs
- [ ] Tests intégration API : GET/POST parité, shapes WKT + geometry native, routes layout/recipes
- [ ] Tests golden : HTML identique entre ancien et nouveau moteur (Phase 1)
- [ ] Tests frontend : lazy + abort, refresh fiable, comportement stable au scroll
- [ ] Tests sécurité : `html.escape()` sur les champs data-driven des widgets non-Plotly

---

## Métriques de succès

| Métrique | Baseline (Phase 0) | Cible (Phase 5) |
|----------|--------------------|-------------------|
| P95 preview modal (shapes) | À mesurer | < 1500ms |
| Taille bundle Plotly (non-map) | **4.7MB** | ≤ 1.2MB |
| Taille bundle Plotly (map) | 4.7MB | ≤ 3MB |
| Iframes simultanées (layout 10 widgets) | 10+ | ≤ 6 |
| Requêtes HTTP (AddWidgetModal, 20 suggestions) | 20 | ≤ 4 (déduplication TanStack Query) |
| Chemins backend preview | 4 endpoints, 7 branches | 1 moteur, 3 routes (GET/POST/layout) |
| Composants frontend preview | 12 | 2 (`PreviewTile`, `PreviewPane`) |
| Wrappers HTML dupliqués | 2 | 1 |
| Cache invalidation après import | Non connectée | Automatique (1 ligne) |
| Iframes sans sandbox | 9 sur 12 | 0 |

---

## Dépendances et prérequis

1. **TanStack Query** : déjà installé (`@tanstack/react-query ^5.81.5`)
2. **IntersectionObserver** : API navigateur standard, déjà utilisée
3. **AbortSignal.any()** : Baseline depuis mars 2024
4. **content-visibility CSS** : Baseline depuis sept. 2025, pas de polyfill nécessaire
5. **Plotly partial bundle** : nécessite un script de build (CLI officiel Plotly)
6. **Pas de nouvelle dépendance Python** requise

---

## Analyse de risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Régression visuelle maps | Moyenne | Élevé | Tests golden HTML + tests manuels ciblés par type de widget |
| Divergence plugin-specific | Faible | Moyen | Tests golden par couple transformer/widget |
| Performance dégradée sur gros datasets | Moyenne | Élevé | Limites thumbnail par type de widget + benchmark avant/après |
| Migration frontend casse le drag & drop | Moyenne | Moyen | Tests manuels LayoutOverview + @dnd-kit isolation |
| TanStack Query cache trop agressif | Faible | Faible | `staleTime: Infinity` + invalidation explicite + bouton refresh |
| Bundle Plotly partiel manque un type de trace | Faible | Élevé | Audit exhaustif des plugins widgets avant le build |
| **XSS stocké via données importées** | Faible | **Élevé** | `html.escape()` systématique + `sandbox="allow-scripts"` sans `allow-same-origin` |
| **Sync render bloque l'event loop** | **Haute** si oublié | **Élevé** | `run_in_threadpool()` dans tous les endpoints — vérifier en code review |
| **Thundering herd sur invalidation** | Moyenne | Moyen | Debounce 300ms + `refetchType: 'active'` |
| **Plotly memory leak au changement srcDoc** | Moyenne | Moyen | Nettoyage `srcdoc = ''` au démontage + injecter `Plotly.purge()` dans le script de nettoyage |
| **Jank CPU par rendus Plotly simultanés** | **Haute** | Moyen | Sémaphore frontend (`MAX_CONCURRENT_RENDERS = 3`) dans la queryFn |
| **ETag invalide après restart** | Moyenne | Faible | Fingerprint basé mtime fichiers (DB + configs) au lieu de compteur mémoire |
| **Breaking change API** | **Haute** si oublié | Moyen | Route legacy `/api/templates/preview/` conservée comme alias, supprimée en Phase 5 |
| **Noms traces Plotly v3 incorrects dans le build** | Faible | **Élevé** | Vérifier correspondance API Python ↔ noms modules JS du CLI build Plotly v3 |

---

## Considérations futures

### T2 2026 : react-plotly.js en rendu direct

Une fois le PreviewEngine stabilisé, ajouter un endpoint API retournant du JSON Plotly (data + layout) au lieu de HTML. Les composants frontend pourraient alors utiliser `<Plot>` directement sans iframe, éliminant le coût de Plotly.js par iframe.

### Plotly.toImage() pour thumbnails persistants

Après le rendu d'un full preview, capturer un SVG via `Plotly.toImage()` et le stocker en cache persistant. Les grilles afficheraient des `<img>` au lieu d'iframes pour les thumbnails, éliminant toute charge JavaScript.

### Service Worker pour cache cross-session

Si les démarrages à froid restent lents après Phase 5, ajouter un Service Worker avec stratégie stale-while-revalidate pour les requêtes preview GET.

### Limites thumbnail par type de widget

Remplacer les limites globales (50 lignes, 10 features) par des limites définies dans les métadonnées de chaque plugin widget. Chaque plugin pourrait exposer `thumbnail_limits` dans sa `config_model` Pydantic.

---

## Plan de documentation

- [ ] Mettre à jour `docs/06-gui/` avec l'architecture preview unifiée
- [ ] Documenter le contrat API preview dans `docs/06-gui/preview-api.md`
- [ ] Ajouter le guide de création de widgets thumbnails dans `docs/04-plugin-development/building-widgets.md`

---

## Références

### Internes

- Architecture cible : `docs/plans/2026-02-21-preview-architecture-target.md`
- Architecture 2026 : `docs/09-architecture/target-architecture-2026.md`
- PreviewService actuel : `src/niamoto/gui/api/services/preview_service.py`
- usePreviewQueue actuel : `src/niamoto/gui/ui/src/components/widgets/usePreviewQueue.ts`
- LRU cache : `src/niamoto/gui/ui/src/lib/lru-cache.ts`

### Externes

- [Plotly.js Shadow DOM incompatibility (#1433)](https://github.com/plotly/plotly.js/issues/1433)
- [Plotly.js partial bundles](https://github.com/plotly/plotly.js/blob/master/dist/README.md)
- [Plotly custom bundle guide](https://github.com/plotly/plotly.js/blob/master/CUSTOM_BUNDLE.md)
- [Plotly community - reduce bundle size](https://community.plotly.com/t/how-can-i-reduce-bundle-size-of-plotly-js-in-react-app/89910)
- [Kaleido v1 performance regression (#400)](https://github.com/plotly/Kaleido/issues/400)
- [TanStack Query v5 - Caching Examples](https://tanstack.com/query/v5/docs/react/guides/caching)
- [TanStack Query v5 - Query Keys](https://tanstack.com/query/v5/docs/framework/react/guides/query-keys)
- [TanStack Query v5 - QueryClient reference](https://tanstack.com/query/v5/docs/reference/QueryClient)
- [TanStack Query v5 cancellation](https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation)
- [CSS content-visibility (Baseline 2025)](https://www.debugbear.com/blog/content-visibility-api)
- [web.dev - content-visibility](https://web.dev/articles/content-visibility)
- [Can I Use - content-visibility](https://caniuse.com/css-content-visibility)
- [MDN - iframe srcdoc](https://developer.mozilla.org/en-US/docs/Web/API/HTMLIFrameElement/srcdoc)
- [MDN - Lazy loading](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Lazy_loading)
- [Plotly.js static image export](https://plotly.com/javascript/static-image-export/)
- [Plotly.js configuration options](https://plotly.com/javascript/configuration-options/)
- [FastAPI ETag caching guide](https://blog.greeden.me/en/2025/09/17/blazing-fast-rock-solid-a-complete-fastapi-caching-guide-redis-http-caching-etag-rate-limiting-and-compression/)
- [FastAPI performance tuning](https://blog.greeden.me/en/2026/02/03/fastapi-performance-tuning-caching-strategy-101-a-practical-recipe-for-growing-a-slow-api-into-a-lightweight-fast-api/)
- [fastapi-etag library](https://github.com/steinitzu/fastapi-etag)
- [Kyle Hawk - iframe lazy loading srcdoc](https://www.kylehawk.name/posts/iframe-lazy-loading-srcdoc-to-the-rescue/)
