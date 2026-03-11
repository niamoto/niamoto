# API Preview — Référence

## Endpoints

### GET `/api/preview/{template_id}`

Génère la preview HTML d'un widget identifié par son `template_id`.

**Paramètres query :**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `group_by` | `string` | auto-détecté | Référentiel de groupement (ex: `taxons`, `plots`) |
| `source` | `string` | `null` | Source de données (nom d'entité comme `plots`) |
| `entity_id` | `string` | `null` | ID d'une entité spécifique pour la preview |
| `mode` | `"thumbnail" \| "full"` | `"full"` | Mode de rendu |

**Réponse :**
- `200 OK` : document HTML complet (`<!DOCTYPE html>...`)
- `304 Not Modified` : si l'ETag correspond (données inchangées)
- `500` : HTML d'erreur encapsulé

**Headers de réponse :**
- `ETag` : fingerprint pour le cache conditionnel
- `Cache-Control: no-cache` : le navigateur doit revalider via ETag

**Exemple :**

```
GET /api/preview/plots_dbh_distribution_bar_plot?group_by=plots&entity_id=2&mode=full
```

### POST `/api/preview`

Génère une preview à partir d'une configuration inline (transformer + widget explicites).

**Body JSON :**

```json
{
  "template_id": null,
  "group_by": "taxons",
  "source": "plots",
  "entity_id": "5",
  "mode": "full",
  "inline": {
    "transformer_plugin": "categorical_distribution",
    "transformer_params": {
      "field": "strata",
      "categories": ["1", "2", "3"]
    },
    "widget_plugin": "bar_plot",
    "widget_params": {
      "x_axis": "categories",
      "y_axis": "counts"
    },
    "widget_title": "Distribution strates"
  }
}
```

Si `inline` est `null`, le `template_id` est utilisé pour la résolution.

**Réponse :** identique au GET, à l'exception du cache HTTP : POST effectue toujours un rendu complet (pas de support ETag/304), tandis que GET supporte les requêtes conditionnelles via `If-None-Match` et peut retourner `304 Not Modified`.

### GET `/api/templates/preview/{template_id}` (legacy)

Alias rétrocompatible vers `GET /api/preview/{template_id}`.
Mêmes paramètres et mêmes réponses.

## Format de réponse

La réponse est un **document HTML complet** prêt pour injection dans un iframe `srcDoc` :

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Preview</title>
    <style>/* styles de base */</style>
    <script>window.__NIAMOTO_PREVIEW__ = true;</script>
    <script src="/api/site/assets/js/vendor/plotly/plotly-niamoto-core.min.js"></script>
</head>
<body>
    <!-- HTML du widget -->
</body>
</html>
```

Le bundle Plotly injecté dépend du type de widget :
- **Charts** : `plotly-niamoto-core.min.js` (1.3 MB)
- **Cartes** : `plotly-niamoto-maps.min.js` (2.2 MB)
- **Widgets non-Plotly** (info_grid, navigation) : aucun bundle

## Modes de rendu

| Aspect | `thumbnail` | `full` |
|--------|-------------|--------|
| `staticPlot` Plotly | `true` | `false` |
| `displayModeBar` | `false` | `true` |
| Légende | Masquée | Visible |
| Marges | Réduites (5px) | Défaut plugin |
| Interactivité | Désactivée | Hover, zoom, pan |

## Cache et invalidation

### HTTP (navigateur ↔ serveur)

L'ETag est un hash MD5 de `template_id + group_by + source + entity_id + data_fingerprint`.
Le `data_fingerprint` est calculé à partir des `mtime` de la DB et des fichiers config.

Le frontend envoie `cache: 'no-store'` pour contourner le cache navigateur (pas de 304
automatique). Le hook `usePreviewFrame` gère son propre cache via TanStack Query.

### TanStack Query (mémoire frontend)

- `staleTime: Infinity` — les données sont toujours fraîches entre deux imports
- `gcTime: 5 min` — conservé en cache 5 minutes après démontage du composant
- Invalidation explicite via `invalidateAllPreviews(queryClient)` après import

## Types TypeScript

```typescript
type PreviewMode = 'thumbnail' | 'full'

interface PreviewDescriptor {
  templateId?: string
  groupBy?: string
  source?: string
  entityId?: string
  mode: PreviewMode
  inline?: InlinePreviewConfig
}

interface InlinePreviewConfig {
  transformer_plugin: string
  transformer_params: Record<string, unknown>
  widget_plugin: string
  widget_params?: Record<string, unknown> | null
  widget_title?: string
}
```

## Utilisation frontend

```typescript
import { usePreviewFrame } from '@/lib/preview/usePreviewFrame'

// Miniature dans une grille
const { html, loading, error } = usePreviewFrame(
  { templateId: 'plots_dbh_bar_plot', groupBy: 'plots', mode: 'thumbnail' },
  visible,  // IntersectionObserver
)

// Vue complète dans un panneau
const { html, loading, error } = usePreviewFrame(
  { templateId: 'plots_dbh_bar_plot', groupBy: 'plots', mode: 'full' },
  true,  // toujours visible
)
```
