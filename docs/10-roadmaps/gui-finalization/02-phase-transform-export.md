# Phase 2 - Transform/Export : Configuration des Widgets

## Vue d'ensemble

La phase Transform/Export permet de configurer les widgets de visualisation pour chaque groupe d'entités (taxons, plots, shapes). Cette phase est majoritairement implémentée, avec une architecture hybride offrant une expérience utilisateur fluide.

> **Note :** Des tests et validations restent à effectuer — voir la Section 8 (Actions Restantes) pour le détail des points en suspens.

### Fonctionnalités implémentées

| Fonctionnalité | Status | Description |
|----------------|--------|-------------|
| Widget Gallery | ✅ | Suggestions intelligentes basées sur les données |
| ContentTab hybride | ✅ | Layout list + panel contextuel |
| WidgetDetailPanel | ✅ | 3 tabs (Preview/Params/YAML) |
| Drag-drop reordering | ✅ | Réorganisation avec persistance layout.order |
| JsonSchemaForm | ✅ | Formulaires dynamiques depuis Pydantic |
| Multi-field patterns | ✅ | 7 types de détection sémantique |
| Quick edit fields | ✅ | x_label, y_label pour axes |

---

## 1. Architecture des Composants

### 1.1 Vue d'ensemble

```text
GroupPanel.tsx (conteneur principal)
├── Tabs
│   ├── Sources (DataSourceConfig)
│   ├── Content (ContentTab) ← Principal
│   └── Index (IndexGeneratorConfig)
└── Header avec infos référentiel

ContentTab.tsx (layout hybride)
├── Left Panel (resizable)
│   ├── Search bar
│   ├── Add dropdown (Suggestions/Combined/Custom)
│   └── WidgetListPanel (liste des widgets)
└── Right Panel (contextuel)
    ├── LayoutOverview (si rien sélectionné)
    └── WidgetDetailPanel (si widget sélectionné)
```

### 1.2 ContentTab.tsx

Le composant principal pour la gestion des widgets utilise un layout hybride :

```typescript
// État de sélection
const [selectedWidgetId, setSelectedWidgetId] = useState<string | null>(null)

// Layout
<ResizablePanelGroup direction="horizontal">
  <ResizablePanel defaultSize={35} minSize={25}>
    {/* Liste des widgets avec recherche */}
    <WidgetListPanel
      widgets={widgets}
      selectedId={selectedWidgetId}
      onSelect={setSelectedWidgetId}
    />
  </ResizablePanel>

  <ResizableHandle />

  <ResizablePanel defaultSize={65}>
    {/* Affichage contextuel */}
    {selectedWidgetId ? (
      <WidgetDetailPanel widget={selectedWidget} />
    ) : (
      <LayoutOverview widgets={widgets} onReorder={handleReorder} />
    )}
  </ResizablePanel>
</ResizablePanelGroup>
```

**Fonctionnalités clés :**
- Panel gauche redimensionnable (25-50%)
- Recherche/filtre des widgets
- Dropdown d'ajout avec 3 modes
- Panel droit contextuel

### 1.3 WidgetDetailPanel.tsx

Affiche les détails d'un widget sélectionné avec 3 tabs :

```text
WidgetDetailPanel
├── Preview Tab
│   └── iframe avec widget rendu
├── Parameters Tab
│   ├── Accordion: Transformation
│   │   └── JsonSchemaForm (plugin transformer)
│   └── Accordion: Visualisation
│       └── JsonSchemaForm (plugin widget)
└── YAML Tab
    ├── transform.yml section
    └── export.yml section
```

**Fonctionnalités :**
- Preview temps réel avec iframe
- Formulaires générés depuis schémas Pydantic
- Export YAML pour copier/coller
- Bouton suppression avec confirmation

### 1.4 LayoutOverview.tsx

Vue grille pour la prévisualisation et le réordonnancement :

```typescript
// Drag and drop avec @dnd-kit
<DndContext onDragEnd={handleDragEnd}>
  <SortableContext items={widgets.map(w => w.id)}>
    <div className="grid grid-cols-2 gap-4">
      {widgets.map((widget, index) => (
        <SortableWidget
          key={widget.id}
          widget={widget}
          colspan={widget.layout?.colspan || 1}
          onColspanToggle={handleColspanToggle}
        />
      ))}
    </div>
  </SortableContext>
</DndContext>
```

**Fonctionnalités :**
- Grille 2 colonnes
- Drag-drop pour réordonner
- Toggle colspan (1 ou 2)
- Sélecteur d'entité pour preview
- Bouton save pour persister l'ordre

---

## 2. Système de Suggestions

### 2.1 AddWidgetModal

Modal d'ajout de widgets avec 3 modes :

```text
AddWidgetModal (90vw × 85vh)
├── Suggestions Tab
│   ├── Filtres (catégorie, source)
│   ├── Grid de widgets suggérés
│   └── Panel de personnalisation
├── Combined Tab
│   ├── Semantic groups (patterns détectés)
│   └── Sélection manuelle de champs
└── Custom Tab
    └── Wizard 4 étapes avec YAML preview
```

### 2.2 Pattern Detection

Le système détecte **7 types de patterns** pour suggérer des widgets combinés :

```python
# multi_field_detector.py

class PatternType(Enum):
    PHENOLOGY = "phenology"           # month + flower/fruit
    ALLOMETRY = "allometry"           # dbh + height
    TRAIT_COMPARISON = "trait"        # leaf_sla + leaf_area + ...
    TEMPORAL_SERIES = "temporal"      # date + mesures
    BOOLEAN_COMPARISON = "boolean"    # endemic + protected + ...
    NUMERIC_CORRELATION = "correlation"  # elevation + rainfall
    CATEGORICAL_COMPARISON = "categorical"
```

**Mots-clés utilisés :**
- Phénologie : `month`, `mois`, `date`, `flower`, `fruit`, `fertile`
- Dimensions : `dbh`, `height`, `diameter`, `hauteur`
- Traits : `leaf_area`, `leaf_sla`, `wood_density`, `bark_thickness`

### 2.3 Class Objects et Scoring

Le système analyse les données pour scorer les suggestions :

```python
# suggestion_service.py

class ClassObjectSuggestion:
    field: str
    class_type: str  # scalar, binary, ternary, multi_category, numeric_bins
    confidence: float  # 0.0 - 1.0
    suggested_widgets: List[WidgetSuggestion]
```

**Types de class objects :**
| Type | Condition | Widgets suggérés |
|------|-----------|------------------|
| `scalar` | Valeur unique | info_grid |
| `binary` | 2 catégories | donut_chart, bar_plot |
| `ternary` | 3 catégories | donut_chart, bar_plot |
| `multi_category` | 4-12 catégories | bar_plot |
| `numeric_bins` | Bins numériques | bar_plot avec gradient |
| `large_category` | >12 catégories | top_ranking |

---

## 3. Widgets Multi-Champs et Layers

### 3.1 Scatter Plot (Multi-dimensions)

Le widget scatter_plot supporte jusqu'à 5 dimensions :

```yaml
# export.yml
- plugin: scatter_plot
  data_source: dbh_height_correlation
  params:
    x_axis: dbh           # Dimension 1
    y_axis: height        # Dimension 2
    color_field: species  # Dimension 3 (optionnel)
    size_field: age       # Dimension 4 (optionnel)
    symbol_field: site    # Dimension 5 (optionnel)
    trendline: ols        # Régression linéaire
```

### 3.2 Raster Stats (Layers géographiques)

Extraction de statistiques depuis des rasters (MNT, pluviométrie) :

```yaml
# transform.yml
elevation_stats:
  plugin: raster_stats
  params:
    raster_path: imports/mnt100_epsg3163.tif
    shape_field: geometry
    stats: [min, max, mean, median, histogram]
    band: 1
```

**Statistiques disponibles :**
- min, max, mean, median, std
- Percentiles (P5, P25, P75, P95)
- Histogram avec classes

### 3.3 Forest Elevation (Combiné)

Combine couches vectorielles (forêt) et raster (altitude) :

```yaml
forest_elevation_analysis:
  plugin: forest_elevation
  params:
    forest_types_path: imports/forest_cover.gpkg
    dem_path: imports/mnt100_epsg3163.tif
    forest_type_field: type_foret
    elevation_bins: [0, 200, 400, 600, 800, 1000]
    forest_types: ["Core forest", "Mature forest", "Secondary"]
```

### 3.4 Land Use Analysis

Analyse multi-couches vectorielles :

> **Note :** Les chemins de fichiers dans les exemples ci-dessous (et dans les sections précédentes) sont résolus relativement à la racine du projet Niamoto.

```yaml
land_use_summary:
  plugin: land_use
  params:
    layers:
      - path: forest_cover.gpkg
        field: forest_type
        categories: [foret_dense, foret_secondaire]
      - path: protected_areas.gpkg
        field: status
        categories: [reserve_integrale, parc_provincial]
    area_unit: ha
```

---

## 4. Formulaires Dynamiques (JsonSchemaForm)

### 4.1 Génération depuis Pydantic

Les plugins définissent un `config_model` Pydantic qui génère automatiquement le formulaire :

```python
# Plugin transformer
class BinnedDistributionParams(BaseModel):
    field: str = Field(..., json_schema_extra={"ui:widget": "field_select"})
    bins: int = Field(10, ge=2, le=100)
    method: Literal["equal_width", "quantile"] = "equal_width"
```

### 4.2 Widgets UI supportés

| ui:widget | Description | Composant |
|-----------|-------------|-----------|
| `field_select` | Sélecteur de colonne | FieldSelectField |
| `entity_select` | Sélecteur d'entité | EntitySelectField |
| `color` | Sélecteur couleur | ColorField |
| `textarea` | Zone de texte | TextAreaField |
| `json` | Éditeur JSON | JsonField |
| `directory` | Sélecteur dossier | DirectorySelectField |

### 4.3 Dépendances conditionnelles

```python
class ChartParams(BaseModel):
    show_legend: bool = True
    legend_position: str = Field(
        "right",
        json_schema_extra={
            "ui:depends": {"show_legend": True}  # Affiché seulement si show_legend=true
        }
    )
```

---

## 5. API Backend

### 5.1 Endpoints Templates

```python
# routers/templates.py

GET /api/templates/suggestions/{group_name}
# Retourne les suggestions de widgets pour un groupe

GET /api/templates/{entity_type}
# Liste les templates disponibles par type d'entité

POST /api/templates/generate-config
# Génère la configuration depuis des templates sélectionnés

# Endpoints preview unifiés (PreviewEngine) :
GET /api/preview/{template_id}
# Preview avec support ETag/304 conditionnel

POST /api/preview
# Preview inline (toujours rendu complet, pas de cache 304)

GET /api/templates/preview/{widget_id}   # DEPRECATED — alias legacy
# Redirige vers GET /api/preview/{widget_id}
```

### 5.2 Endpoints Config

```python
# routers/config.py

GET /api/config/widgets/{group_name}
# Retourne les widgets configurés pour un groupe

PUT /api/config/widgets/{group_name}
# Met à jour les widgets d'un groupe

PUT /api/config/widgets/{group_name}/reorder
# Réordonne les widgets (layout.order)
```

---

## 6. Hooks Frontend

### 6.1 useWidgetConfig

Hook principal pour la gestion des widgets :

```typescript
export function useWidgetConfig(groupName: string) {
  const { data, isLoading } = useQuery({
    queryKey: ['widgets', groupName],
    queryFn: () => fetchWidgets(groupName)
  })

  const updateWidget = useMutation({...})
  const deleteWidget = useMutation({...})
  const reorderWidgets = useMutation({...})
  const duplicateWidget = useMutation({...})

  return { widgets: data, isLoading, updateWidget, deleteWidget, ... }
}
```

### 6.2 useSemanticGroups

Hook pour les suggestions de patterns :

```typescript
export function useSemanticGroups(groupName: string) {
  return useQuery({
    queryKey: ['semantic-groups', groupName],
    queryFn: () => fetchSemanticGroups(groupName)
  })
}
```

---

## 7. Fichiers Concernés

### Frontend

```text
src/niamoto/gui/ui/src/
├── components/
│   ├── content/
│   │   ├── ContentTab.tsx           # Layout principal
│   │   ├── WidgetListPanel.tsx      # Liste des widgets
│   │   ├── WidgetDetailPanel.tsx    # Détails widget
│   │   ├── LayoutOverview.tsx       # Vue grille
│   │   └── AddWidgetModal.tsx       # Modal d'ajout
│   ├── forms/
│   │   ├── JsonSchemaForm.tsx       # Générateur de formulaires
│   │   └── WidgetConfigForm.tsx     # Formulaire widget
│   └── gallery/
│       └── WidgetGallery.tsx        # Galerie de suggestions
├── hooks/
│   ├── useWidgetConfig.ts           # CRUD widgets
│   ├── useTemplates.ts              # Templates API
│   └── useSemanticGroups.ts         # Patterns API
└── pages/
    └── flow/
        └── GroupPanel.tsx           # Panel de groupe
```

### Backend

```text
src/niamoto/gui/api/
├── routers/
│   ├── templates.py                 # Suggestions API
│   ├── config.py                    # Configuration API
│   ├── transform.py                 # Exécution transform
│   └── export.py                    # Exécution export
└── services/
    └── templates/
        └── suggestion_service.py    # Logique de suggestions

src/niamoto/core/
├── plugins/
│   ├── transformers/
│   │   ├── binned_distribution.py
│   │   ├── statistical_summary.py
│   │   ├── raster_stats.py
│   │   └── forest_elevation.py
│   └── exporters/
│       ├── bar_plot.py
│       ├── scatter_plot.py
│       └── donut_chart.py
└── imports/
    └── multi_field_detector.py      # Pattern detection
```

---

## 8. Actions Restantes

### 8.1 À Tester

| Action | Priorité | Description |
|--------|----------|-------------|
| Intégration shapes | P1 | Vérifier que les 3 groupes (taxons, plots, shapes) fonctionnent |
| Widgets raster | P2 | Tester raster_stats avec données réelles |
| Preview performance | P2 | Optimiser le rendu des previews iframe |

### 8.2 Améliorations Futures

| Action | Priorité | Description |
|--------|----------|-------------|
| Édition avancée | P3 | Formulaires plus riches pour plugins complexes |
| Import/Export config | P3 | Partage de configurations entre projets |
| Undo/Redo | P3 | Historique des modifications |

---

## 9. Dépendances

```text
Données importées (import.yml)
        │
        ▼
Pattern Detection ──► Suggestions intelligentes
        │
        ▼
Widget Configuration (transform.yml + export.yml)
        │
        ▼
Transform Execution ──► JSON Data
        │
        ▼
Export Execution ──► HTML Pages
```

La phase Transform/Export dépend de l'import réussi des données. Les widgets sont configurés puis exécutés séquentiellement (transform avant export).
