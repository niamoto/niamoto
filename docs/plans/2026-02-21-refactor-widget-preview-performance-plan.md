---
title: "Optimisation performances du système de preview widgets"
type: refactor
date: 2026-02-21
---

# Optimisation performances du système de preview widgets

## Overview

Le système de configuration et preview de widgets souffre de problèmes de performance significatifs : explosion d'iframes, absence de cache sur les hooks de data fetching, double refetch après mutations, et aucun debounce sur les actions coûteuses. React Query est installé et configuré mais utilisé dans seulement 2 endroits sur 7+ hooks de données.

## Problèmes identifiés

### P0 — Double refetch après chaque mutation
- `useWidgetConfig.updateWidget()` appelle `fetchConfigs()` en interne
- `ContentTab.handleUpdateWidget()` appelle `refetchWidgets()` (= `fetchConfigs`) si succès
- Résultat : **4 requêtes API au lieu de 2** après chaque update/delete/duplicate
- Fichiers : `useWidgetConfig.ts:355`, `ContentTab.tsx:116-125`

### P1 — Explosion d'iframes dans AddWidgetModal
- Chaque suggestion visible crée une iframe (`AddWidgetModal.tsx:1247-1253`)
- Chaque iframe déclenche : connexion DB → lecture config → SQL entité représentative → SQL données → transformation → rendu widget → empaquetage HTML + Plotly.js
- 15-20 iframes en parallèle, bloquant les 6 connexions HTTP du navigateur
- La preview large (`LargePreview`) duplique l'appel de la miniature (`WidgetPreview`)

### P2 — Aucun cache sur les hooks critiques
React Query est installé (`main.tsx:3,9-16`) mais les hooks suivants utilisent `useState + useEffect + fetch` sans cache :
- `useSuggestions()` — `useTemplates.ts:92-129`
- `useWidgetConfig()` — `useWidgetConfig.ts:232-494`
- `useClassObjectSuggestions()` — `widget-suggestions.ts:168-207`
- `useCombinedWidgetSuggestions()` — `widget-suggestions.ts:352-393`
- `useSemanticGroups()` — `widget-suggestions.ts:398-433`

Conséquence : chaque mount refetch, pas de déduplication, pas de stale-while-revalidate.

### P3 — Race conditions et debounce manquant
- `useCombinedWidgetSuggestions` : pas d'AbortController, requêtes concurrentes s'écrasent
- **Note :** `CombinedPreview` a déjà un AbortController (`AddWidgetModal.tsx:328`), le problème concerne les autres fetches
- Changement de champs combinés : chaque `toggleField` déclenche un fetch POST sans debounce
- Changement de référence : cascade complète de refetch sans annulation des requêtes en vol

## Solution proposée

Migration incrémentale en 5 phases (0→4), de la mesure à l'optimisation structurelle.

---

## Phase 0 : Baseline de mesure (effort faible, prérequis)

Avant toute modification, capturer les métriques actuelles pour valider les gains.

### 0.1 Mesurer l'état actuel

- Ouvrir DevTools Network, filtrer sur `/api/`
- Mesurer pour chaque scénario :
  - **Ouverture AddWidgetModal** : nombre de requêtes, temps total de chargement
  - **Changement de référence** : nombre de requêtes, durée de l'état loading
  - **Mutation widget** (update/delete) : nombre de requêtes déclenchées
  - **Scroll dans les suggestions** : concurrence iframe max observée

- [ ] Capturer le nombre de requêtes API à l'ouverture de AddWidgetModal
- [ ] Capturer le TTI (Time To Interactive) de la modale
- [ ] Capturer la latence moyenne d'une preview individuelle
- [ ] Capturer la concurrence max d'iframes simultanées
- [ ] Capturer le nombre de requêtes après une mutation widget

---

## Phase 1 : Éliminer le double refetch (effort faible, impact immédiat)

### 1.1 Supprimer les appels redondants dans ContentTab

**Fichier : `src/niamoto/gui/ui/src/components/content/ContentTab.tsx`**

Les callbacks `handleUpdateWidget`, `handleDeleteWidget`, `handleDuplicateWidget` appellent `refetchWidgets()` alors que les fonctions internes de `useWidgetConfig` font déjà `fetchConfigs()`. Supprimer l'appel redondant dans ContentTab.

```typescript
// AVANT (ContentTab.tsx:116-125)
const handleUpdateWidget = useCallback(async (widgetId, config) => {
  const success = await updateWidget(widgetId, config)
  if (success) {
    refetchWidgets()  // ← REDONDANT : updateWidget fait déjà fetchConfigs()
  }
  return success
}, [updateWidget, refetchWidgets])

// APRÈS
const handleUpdateWidget = useCallback(async (widgetId, config) => {
  return await updateWidget(widgetId, config)
}, [updateWidget])
```

Même correction pour `handleDeleteWidget` et `handleDuplicateWidget`.

- [x] Supprimer `refetchWidgets()` dans `handleUpdateWidget` — `ContentTab.tsx`
- [x] Supprimer `refetchWidgets()` dans `handleDeleteWidget` — `ContentTab.tsx`
- [x] Supprimer `refetchWidgets()` dans `handleDuplicateWidget` — `ContentTab.tsx`
- [x] Valider : mutation widget → 2 requêtes API au lieu de 4

---

## Phase 2 : Optimiser les iframes de preview (effort moyen, impact fort sur la perf perçue)

### 2.1 Pool de chargement avec concurrence limitée

**Fichier : `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`**

Créer un hook `usePreviewQueue` qui limite le nombre d'iframes en chargement simultané :

- Maximum **4 previews** en chargement à la fois
- Queue FIFO avec priorité aux éléments visibles (IntersectionObserver)
- Annulation quand un élément sort du viewport
- Règle Vercel : **`rendering-content-visibility`** pour les éléments hors viewport

```typescript
// Nouveau hook usePreviewQueue.ts
function usePreviewQueue(maxConcurrent = 4) {
  // Gère une queue de templateIds à charger
  // Retourne { requestLoad(id), cancelLoad(id), isLoaded(id), loadedHtml(id) }
}
```

- [x] Créer `usePreviewQueue` — `src/niamoto/gui/ui/src/components/widgets/usePreviewQueue.ts`
- [x] Intégrer dans `WidgetPreview` — `AddWidgetModal.tsx`

### 2.2 Déduplication miniature ↔ preview large

Quand l'utilisateur focus une suggestion, la `LargePreview` charge la même URL que la miniature `WidgetPreview`. Réutiliser le contenu déjà chargé.

**Stratégie technique :** Passer les iframes de `src` (URL) à `srcDoc` (HTML injecté) :
1. `usePreviewQueue` (§2.1) fetch le HTML via `fetch()` au lieu de laisser l'iframe le faire via `src`
2. Le HTML récupéré est stocké dans un cache LRU module-level (clé = URL de preview, max 64 entrées)
3. `WidgetPreview` (miniature) utilise `<iframe srcDoc={cachedHtml} />` au lieu de `<iframe src={url} />`
4. `LargePreview` consulte le même cache — si le HTML est déjà présent, il l'utilise directement sans fetch supplémentaire
5. Résultat : une seule requête HTTP par preview, réutilisée entre miniature et panneau large

**Borne mémoire :** Le cache est un LRU avec max 64 entrées (une preview HTML fait ~50-100KB, donc ~6MB max). Implémentation simple : `Map` avec éviction du plus ancien quand la taille dépasse la limite.

```typescript
class LRUHtmlCache {
  private cache = new Map<string, string>()
  constructor(private maxSize = 64) {}
  get(key: string): string | undefined { /* ... promote to end ... */ }
  set(key: string, value: string): void { /* ... evict oldest if full ... */ }
}
const previewHtmlCache = new LRUHtmlCache(64)
```

**Fallback si srcDoc échoue :** Certains widgets pourraient mal se comporter en `srcDoc` (scripts avec `document.location`, CSP, etc.). Prévoir un mode dégradé :
- Si le HTML injecté en `srcDoc` produit une erreur (détectable via `iframe.onload` + vérification du contenu), fallback automatique vers `<iframe src={url} />`
- Contrôlable via un flag par widget dans le cache : `{ html, useSrcDoc: true/false }`
- En cas de problème généralisé, un flag global `PREVIEW_USE_SRCDOC = true` dans la config permet de couper le `srcDoc` sans rollback de code

Règle Vercel : **`js-cache-function-results`**

- [x] Créer `LRUHtmlCache` (max 64 entrées) — `src/niamoto/gui/ui/src/lib/lru-cache.ts`
- [x] Modifier `WidgetPreview` : passer de `src` à `srcDoc` avec fetch explicite — `AddWidgetModal.tsx`
- [x] Ajouter fallback `src` si `srcDoc` échoue — `AddWidgetModal.tsx`
- [x] `LargePreview` lit le cache HTML avant de fetch — `AddWidgetModal.tsx`

### 2.3 Cache HTTP côté serveur

**Fichier : `src/niamoto/gui/api/routers/templates.py`** et **`preview_service.py`**

**GET preview :** Utiliser `Cache-Control: no-cache` + `ETag` au lieu de `max-age`.
Le `max-age` causerait des previews stale dans le cache navigateur des iframes après un import/save — le backend peut invalider son cache mais pas celui du navigateur.
Avec `no-cache` + `ETag`, le navigateur revalide à chaque requête mais sert le cache si l'ETag match (304 Not Modified, sans retransmettre le HTML).

**Calcul de l'ETag sans régénérer le HTML :** L'ETag est calculé à partir des paramètres d'entrée et de la fraîcheur des données (pas du HTML de sortie). Clé = hash de `(template_id, group_by, source, entity_id, config_mtime, data_version)` :
- `config_mtime` : timestamp de dernière modification de transform.yml/export.yml
- `data_version` : mtime du fichier DB DuckDB, ou un compteur d'import incrémenté à chaque `run import`

Sans `data_version`, un import de nouvelles données sans changement de config donnerait un faux 304 (config identique mais données différentes). Le cache `TTLCache` backend stocke le résultat HTML indexé par cette même clé, donc le 304 court-circuite complètement la génération.

```python
def compute_preview_etag(template_id: str, group_by: str, source: str, entity_id: str) -> str:
    config_mtime = os.path.getmtime(transform_yml_path)
    db_mtime = os.path.getmtime(db_path)  # fraîcheur des données
    key = f"{template_id}:{group_by}:{source}:{entity_id}:{config_mtime}:{db_mtime}"
    return hashlib.md5(key.encode()).hexdigest()
```

**POST preview :** Cache mémoire Python robuste :
- Clé : `hashlib.sha256(json.dumps(params, sort_keys=True))` sur les paramètres normalisés
- `maxsize` : 128 entrées (LRU)
- TTL : 300s (5 minutes)
- **Invalidation explicite** : vider le cache après un import de données ou un save de config (hooks dans les endpoints correspondants)

```python
from cachetools import TTLCache

_preview_cache = TTLCache(maxsize=128, ttl=300)

def invalidate_preview_cache():
    """Appelé après import ou save config."""
    _preview_cache.clear()
```

- [x] Ajouter `Cache-Control: no-cache` + `ETag` sur GET preview — `templates.py`
- [x] Ajouter cache TTLCache sur POST preview — `templates.py`
- [x] Appeler `invalidate_preview_cache()` dans les endpoints d'import et de save config
- [x] `cachetools` déjà dans les dépendances

---

## Phase 3 : Migration vers React Query (effort moyen, impact fort)

### 3.1 Migrer useWidgetConfig vers React Query

**Fichier : `src/niamoto/gui/ui/src/components/widgets/useWidgetConfig.ts`**

Remplacer le pattern `useState + useCallback + useEffect + fetch` par `useQuery` + `useMutation`.

- `useQuery` avec `queryKey: ['widget-config', groupBy]` et `staleTime: 30_000`
- `useMutation` pour update/delete/duplicate avec `onSuccess: () => queryClient.invalidateQueries({ queryKey: ['widget-config', groupBy] })`
- Le `useMemo` existant qui parse et filtre par groupBy reste identique

Règles Vercel React à appliquer :
- **`rerender-defer-reads`** : les callbacks de mutation ne doivent pas lire l'état de la query
- **`client-swr-dedup`** : React Query déduplique automatiquement les requêtes avec le même queryKey
- **`async-parallel`** : les 2 fetch configs (`transform` + `export`) doivent rester en `Promise.all()`

- [ ] Créer `useWidgetConfig` avec `useQuery` pour le fetch — `useWidgetConfig.ts`
- [ ] Créer les mutations avec `useMutation` et `invalidateQueries` — `useWidgetConfig.ts`
- [ ] Supprimer `fetchConfigs`, `useState` loading/error — `useWidgetConfig.ts`

### 3.2 Migrer useSuggestions vers React Query

**Fichier : `src/niamoto/gui/ui/src/components/widgets/useTemplates.ts`**

- `useQuery` avec `queryKey: ['suggestions', groupBy, entity]` et `staleTime: 60_000`
- Les suggestions ne changent pas pendant une session (données stables après import)

- [ ] Convertir `useSuggestions` en `useQuery` — `useTemplates.ts`
- [ ] Supprimer `useState` suggestions/loading/error — `useTemplates.ts`

### 3.3 Migrer les hooks de widget-suggestions.ts

**Fichier : `src/niamoto/gui/ui/src/lib/api/widget-suggestions.ts`**

- `useClassObjectSuggestions` → `useQuery` avec `queryKey: ['class-object-suggestions', groupBy, sourceName]`
- `useSemanticGroups` → `useQuery` avec `queryKey: ['semantic-groups', referenceName, entity]`
- `useCombinedWidgetSuggestions` → **`useQuery`** (pas `useMutation`) avec :
  - `queryKey: ['combined-suggestions', referenceName, normalizedFields, sourceName]`
    - **`normalizedFields`** = `[...new Set(selectedFields)].sort()` — normaliser pour éviter la fragmentation du cache (même set, ordre différent = même clé)
  - `enabled: normalizedFields.length >= 2` pour ne fetch que quand pertinent
  - Debounce via un état `debouncedFields` (voir Phase 4.1)
  - **`queryFn: ({ signal }) => fetch(url, { signal })`** — brancher explicitement le `signal` de React Query dans le `fetch` pour que l'annulation fonctionne réellement

**Note :** `useMutation` ne résout pas les race conditions automatiquement. `useQuery` avec `queryKey` dynamique gère nativement l'annulation des requêtes obsolètes quand le `queryKey` change, **à condition que le `signal` soit passé au `fetch`**.

**Important :** Tous les `queryFn` de cette migration doivent utiliser le pattern `({ signal }) => fetch(url, { signal })` pour que l'annulation fonctionne.

- [ ] Convertir `useClassObjectSuggestions` en `useQuery` — `widget-suggestions.ts`
- [ ] Convertir `useSemanticGroups` en `useQuery` — `widget-suggestions.ts`
- [ ] Convertir `useCombinedWidgetSuggestions` en `useQuery` avec `enabled` + `normalizedFields` — `widget-suggestions.ts`
- [ ] Tous les `queryFn` utilisent `({ signal }) => fetch(url, { signal })` — tous les hooks migrés

---

## Phase 4 : Debounce et stabilisation (effort faible, impact moyen)

### 4.1 Debounce sur toggleField (onglet Combiné)

**Fichier : `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`**

Ajouter un état `debouncedFields` dérivé de `selectedFields` avec un délai de 300ms. Le `useQuery` de `useCombinedWidgetSuggestions` utilise `debouncedFields` dans son `queryKey`, ce qui throttle naturellement les appels.

```typescript
const [debouncedFields] = useDebouncedValue(selectedFields, 300)
const { data: combinedSuggestions } = useCombinedWidgetSuggestions(
  referenceName, debouncedFields, sourceName
)
```

Règle Vercel : **`rerender-move-effect-to-event`** — le fetch est contrôlé par le debounce, pas un effect naïf.

- [ ] Créer ou importer `useDebouncedValue` — utilitaire
- [ ] Utiliser `debouncedFields` comme paramètre de `useCombinedWidgetSuggestions` — `AddWidgetModal.tsx`

### 4.2 AbortController sur les fetches manuels restants

- **`CombinedPreview`** : a déjà un AbortController (`AddWidgetModal.tsx:328`) ✅
- Pour tout autre fetch non migré vers React Query, ajouter un AbortController dans le cleanup du `useEffect`
- Après migration React Query (Phase 3), la plupart des fetches manuels auront disparu

- [ ] Audit des fetches manuels restants après Phase 3
- [ ] Ajouter AbortController si nécessaire

---

## Acceptance Criteria

### Fonctionnel
- [ ] Les previews de widgets se chargent correctement dans les 3 onglets (Suggestions, Combiné, Personnalisé)
- [ ] Les mutations (update/delete/duplicate) ne déclenchent qu'un seul cycle de refetch
- [ ] Le changement de référence ne recharge pas les données si elles sont encore fraîches (< 30s)
- [ ] La sélection d'une suggestion réutilise la preview miniature dans le panneau large

### Performance (vs baseline Phase 0)
- [ ] Maximum 4 iframes en chargement simultané dans AddWidgetModal
- [ ] Pas de régénération backend ni de payload HTML dupliqué pour le même (templateId, groupBy, source) — les requêtes 304 (ETag match) sont acceptables
- [ ] Les hooks retournent les données du cache immédiatement si disponibles (pas de loading flash)

### Qualité
- [ ] Tous les tests existants passent (`uv run pytest`)
- [ ] Lint propre (`uvx ruff check`, `pnpm lint` dans ui/)
- [ ] Pas de régression visuelle dans la modale AddWidget

## Success Metrics (à comparer avec baseline Phase 0)

- Nombre de requêtes API lors de l'ouverture de AddWidgetModal : de ~20 à ~5-6
- Temps de réponse perçu au changement de référence : suppression du flash de loading
- Nombre de requêtes après une mutation widget : de 4 à 2

## Dependencies & Risks

- **React Query déjà configuré** : `@tanstack/react-query` dans `main.tsx` avec `QueryClient`. Pas de nouvelle dépendance frontend.
- **`cachetools`** : à ajouter côté Python pour le cache TTL backend (si pas déjà présent)
- **Risque de régression** : La migration des hooks change le timing des re-renders. Les composants qui dépendent de `loading` ou `error` doivent être vérifiés.
- **Risque de cache stale** : Si l'utilisateur importe de nouvelles données pendant la session, les previews cachées montreront l'ancienne version. Mitigation : invalidation explicite du cache côté backend + `invalidateQueries` côté frontend après un import.

## Références

### Fichiers critiques
- `src/niamoto/gui/ui/src/components/content/ContentTab.tsx` — orchestration widgets
- `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx` — modale 1789 lignes, previews, iframes
- `src/niamoto/gui/ui/src/components/widgets/useWidgetConfig.ts` — hook CRUD configs
- `src/niamoto/gui/ui/src/components/widgets/useTemplates.ts` — hook suggestions
- `src/niamoto/gui/ui/src/lib/api/widget-suggestions.ts` — hooks combined/semantic
- `src/niamoto/gui/api/routers/templates.py` — endpoints preview backend
- `src/niamoto/gui/api/services/preview_service.py` — service de génération preview

### Patterns existants à suivre
- `useReferences.ts` — exemple de hook migré vers React Query avec `staleTime: 30000`
- `LayoutOverview.tsx` — utilise `useQuery` + `useMutation` avec `invalidateQueries`

### Règles Vercel React appliquées
- `client-swr-dedup` — déduplication automatique via React Query
- `rerender-defer-reads` — callbacks de mutation stables
- `rerender-move-effect-to-event` — debounce sur événements, pas effects
- `rendering-content-visibility` — contenu hors viewport
- `async-parallel` — `Promise.all()` pour les fetch indépendants
- `js-cache-function-results` — cache des previews HTML rendues
