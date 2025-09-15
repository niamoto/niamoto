# Interface Pipeline Unifiée Niamoto - Spécifications et Roadmap

## 📌 Fichiers de Configuration de Référence

Les spécifications suivantes sont basées sur les fichiers de configuration d'une instance Niamoto complète :
- **Import** : `/Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-og/config/import.yml`
- **Transform** : `/Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-og/config/transform.yml`
- **Export** : `/Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-og/config/export.yml`

Ces fichiers définissent la structure exacte des données attendues pour chaque étape du pipeline.

---

## 🎯 Vision Globale

Créer une interface graphique unifiée basée sur ReactFlow permettant de visualiser et configurer l'ensemble du pipeline de données Niamoto (Import → Transform → Export) sous forme de graphe de flux interactif.

### Principes Fondamentaux
1. **Pipeline Séquentiel Obligatoire** : Import → Transform → Export
2. **Modularité** : Formulaires réutilisables et indépendants de ReactFlow
3. **Contextualisation** : Catalogue intelligent selon l'étape
4. **Compatibilité** : Validation stricte des connexions entre nodes
5. **Flexibilité** : Layout configurable (panel/modal)

---

## 📋 SPÉCIFICATIONS TECHNIQUES

### 1. Architecture des Composants

```
src/components/pipeline/
├── PipelineFlow.tsx                 # Composant principal ReactFlow
├── layouts/
│   ├── LayoutProvider.tsx          # Context pour gestion du layout
│   ├── SidePanelLayout.tsx         # Config panneau latéral
│   ├── ModalLayout.tsx             # Config modal
│   └── BottomPanelLayout.tsx      # Config panneau inférieur
│
├── sidebar/
│   ├── NodeCatalog.tsx             # Catalogue principal
│   ├── catalogs/
│   │   ├── ImportCatalog.tsx      # Sources disponibles
│   │   ├── TransformCatalog.tsx   # Plugins de transformation
│   │   └── ExportCatalog.tsx      # Formats d'export
│   └── CatalogFilter.tsx          # Système de filtrage
│
├── nodes/
│   ├── base/
│   │   ├── BaseNode.tsx           # Classe de base pour tous les nodes
│   │   └── NodeStateManager.tsx   # Gestion états (pending/running/success/error)
│   ├── import/
│   │   ├── ImportNode.tsx         # Node générique d'import
│   │   ├── TaxonomyNode.tsx       # Node spécifique taxonomie
│   │   ├── OccurrencesNode.tsx    # Node occurrences
│   │   ├── PlotNode.tsx           # Node plots
│   │   ├── ShapeNode.tsx          # Node shapes
│   │   └── LayerNode.tsx          # Node layers
│   ├── transform/
│   │   ├── TransformNode.tsx      # Node de transformation
│   │   └── PluginNode.tsx         # Node plugin spécifique
│   └── export/
│       ├── ExportNode.tsx         # Node générique d'export
│       ├── HtmlExportNode.tsx     # Export HTML
│       └── DataExportNode.tsx     # Export données (JSON/CSV)
│
├── forms/                          # Formulaires modulaires
│   ├── FormContainer.tsx          # Container adaptable
│   ├── import/
│   │   ├── TaxonomyForm.tsx       # Config taxonomie
│   │   ├── OccurrencesForm.tsx    # Config occurrences
│   │   ├── PlotForm.tsx           # Config plots
│   │   ├── ShapeForm.tsx          # Config shapes multiples
│   │   └── LayerForm.tsx          # Config layers (raster/vector)
│   ├── transform/
│   │   ├── PluginConfigForm.tsx   # Config générique plugin
│   │   ├── SourceRelationForm.tsx # Config relations entre sources
│   │   └── WidgetConfigForm.tsx   # Config widgets de sortie
│   └── export/
│       ├── HtmlPageForm.tsx       # Config pages HTML
│       ├── TemplateForm.tsx       # Sélection templates
│       └── DataExportForm.tsx     # Options export données
│
├── validation/
│   ├── PipelineValidator.tsx      # Validation globale du pipeline
│   ├── CompatibilityChecker.tsx   # Vérification compatibilité
│   └── DataFormatMatcher.tsx      # Matching formats de données
│
├── execution/
│   ├── PipelineRunner.tsx         # Orchestrateur d'exécution
│   ├── NodeExecutor.tsx           # Exécuteur par node
│   └── ProgressMonitor.tsx        # Monitoring temps réel
│
└── utils/
    ├── pipelineSerializer.ts      # YAML ↔ ReactFlow
    ├── nodeFactory.ts              # Factory pour création de nodes
    └── dataTypeDefinitions.ts     # Définitions des types de données
```

### 2. Types de Nodes et Structures de Données

#### 2.1 Import Nodes

```typescript
interface ImportNodeData {
  nodeType: 'import'
  subType: 'taxonomy' | 'occurrences' | 'plots' | 'shapes' | 'layers'
  status: 'idle' | 'configured' | 'running' | 'success' | 'error'

  // Configuration spécifique selon subType
  config: {
    // Pour taxonomy (basé sur import.yml)
    taxonomy?: {
      path: string
      hierarchy: {
        levels: Array<{name: string, column: string}>
        taxon_id_column: string
      }
      api_enrichment?: {
        enabled: boolean
        plugin: string
        api_url: string
        // ... autres params API
      }
    }

    // Pour occurrences
    occurrences?: {
      type: 'csv'
      path: string
      identifier: string
      location_field: string
    }

    // Pour plots
    plots?: {
      type: 'csv'
      path: string
      identifier: string
      locality_field: string
      location_field: string
      link_field: string
      occurrence_link_field: string
    }

    // Pour shapes (multiples)
    shapes?: Array<{
      type: string
      path: string
      name_field: string
    }>

    // Pour layers
    layers?: Array<{
      name: string
      type: 'vector' | 'raster'
      format?: string
      path: string
      description: string
    }>
  }

  // Données de sortie
  output: {
    format: 'table' | 'geometry' | 'raster' | 'hierarchical'
    schema?: DataSchema
    preview?: any
  }
}
```

#### 2.2 Transform Nodes

```typescript
interface TransformNodeData {
  nodeType: 'transform'
  pluginId: string  // field_aggregator, top_ranking, etc.
  pluginType: 'loader' | 'transformer' | 'aggregator'
  status: NodeStatus

  // Configuration basée sur transform.yml
  config: {
    // Groupe de transformation
    group_by: 'taxon' | 'plot' | 'shape'

    // Sources d'entrée
    sources: Array<{
      name: string
      data: string  // Table ou fichier
      grouping: string  // Table de référence
      relation?: {
        plugin: string
        key?: string
        fields?: Record<string, string>
      }
    }>

    // Configuration du widget
    widget: {
      name: string  // ex: "top_species"
      plugin: string  // ex: "top_ranking"
      params: Record<string, any>  // Params spécifiques au plugin
    }
  }

  // Validation des entrées
  inputRequirements: {
    dataFormat: DataFormat[]
    requiredFields?: string[]
    optional?: boolean
  }

  // Format de sortie
  output: {
    widgetType: string  // bar_chart, map, table, etc.
    dataStructure: any  // Structure attendue par le widget
  }
}
```

#### 2.3 Export Nodes

```typescript
interface ExportNodeData {
  nodeType: 'export'
  format: 'html' | 'json' | 'csv' | 'geojson'
  status: NodeStatus

  // Configuration basée sur export.yml
  config: {
    // Pour export HTML
    html?: {
      name: string
      exporter: 'html_page_exporter'
      params: {
        template_dir: string
        output_dir: string
        site: {
          title: string
          logo_header?: string
          logo_footer?: string
          lang: string
          primary_color: string
          nav_color: string
        }
        navigation: Array<{text: string, url: string}>
        static_pages?: Array<{
          name: string
          template: string
          output_file: string
        }>
        groups?: Array<{
          group_by: string
          output_pattern: string
          index_output_pattern: string
        }>
      }
    }

    // Pour export data
    data?: {
      format: 'json' | 'csv' | 'geojson'
      output_path: string
      options?: any
    }
  }

  // Widgets à inclure
  widgets?: string[]
}
```

### 3. Système de Compatibilité et Validation

#### 3.1 Règles de Connexion

```typescript
class PipelineRules {
  // Règles de base du pipeline
  static readonly SEQUENCE_RULES = {
    // Un pipeline DOIT commencer par au moins un Import
    minimumImports: 1,

    // Connexions autorisées entre types de nodes
    allowedConnections: {
      'import': ['transform', 'export'],
      'transform': ['transform', 'export'],
      'export': []  // Terminal
    },

    // Cardinalité des connexions
    connectionCardinality: {
      'import': { minOut: 1, maxOut: Infinity },
      'transform': { minIn: 1, maxIn: Infinity, minOut: 1, maxOut: Infinity },
      'export': { minIn: 1, maxIn: Infinity, maxOut: 0 }
    }
  }

  static validateConnection(source: Node, target: Node): ValidationResult {
    // Vérifier type de connexion autorisé
    // Vérifier compatibilité des formats de données
    // Vérifier cardinalité
    return { valid: boolean, errors: string[] }
  }
}
```

#### 3.2 Compatibilité des Données

```typescript
interface DataCompatibility {
  // Formats de données supportés
  formats: {
    'table': ['csv', 'json', 'database'],
    'spatial': ['geojson', 'shapefile', 'geometry'],
    'hierarchical': ['nested_set', 'tree'],
    'temporal': ['time_series', 'dated_records']
  }

  // Mapping plugin → format requis
  pluginRequirements: {
    'field_aggregator': ['table', 'hierarchical'],
    'geospatial_extractor': ['spatial'],
    'top_ranking': ['hierarchical'],
    'time_series_analysis': ['temporal'],
    'binned_distribution': ['table'],
    'statistical_summary': ['table']
  }

  // Mapping widget → structure requise
  widgetRequirements: {
    'bar_chart': {
      required: ['labels', 'values'],
      format: 'array'
    },
    'map': {
      required: ['geometry'],
      format: 'geojson'
    },
    'gauge': {
      required: ['value', 'max'],
      format: 'object'
    },
    'table': {
      required: ['rows', 'columns'],
      format: 'table'
    }
  }
}
```

### 4. Catalogue Contextuel

```typescript
class CatalogContext {
  private currentStep: 'import' | 'transform' | 'export'
  private selectedNode: Node | null
  private pipelineState: PipelineState

  getAvailableNodes(): CatalogItem[] {
    switch(this.currentStep) {
      case 'import':
        return this.getImportNodes()

      case 'transform':
        // Filtrer par compatibilité
        const previousOutput = this.getPreviousNodeOutput()
        return this.filterCompatiblePlugins(previousOutput)

      case 'export':
        // Proposer exports selon widgets configurés
        const widgets = this.getConfiguredWidgets()
        return this.getCompatibleExporters(widgets)
    }
  }

  private filterCompatiblePlugins(dataFormat: DataFormat): Plugin[] {
    return plugins.filter(plugin => {
      const requirements = DataCompatibility.pluginRequirements[plugin.id]
      return requirements.includes(dataFormat)
    })
  }

  // Option pour afficher tous les plugins
  showAll: boolean = false

  // Message contextuel
  getHelpMessage(): string {
    if (!this.hasImportNodes()) {
      return "Commencez par ajouter une source de données"
    }
    if (!this.hasTransformNodes()) {
      return "Ajoutez des transformations pour traiter vos données"
    }
    return "Terminez par un export pour générer les résultats"
  }
}
```

### 5. Layout Flexible

```typescript
interface LayoutConfig {
  type: 'side-panel' | 'modal' | 'bottom-panel'
  position?: 'left' | 'right' | 'top' | 'bottom'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  collapsible?: boolean
  defaultCollapsed?: boolean
}

// Provider pour gérer le layout
const LayoutProvider: React.FC = ({ children }) => {
  const [config, setConfig] = useState<LayoutConfig>({
    type: 'side-panel',
    position: 'right',
    size: 'lg',
    collapsible: true
  })

  // Sauvegarder préférences utilisateur
  useEffect(() => {
    localStorage.setItem('pipeline-layout', JSON.stringify(config))
  }, [config])

  return (
    <LayoutContext.Provider value={{ config, setConfig }}>
      {children}
    </LayoutContext.Provider>
  )
}
```

### 6. Interface Utilisateur

```
┌──────────────────────────────────────────────────────────────────────┐
│  Niamoto Pipeline Editor                    [▶ Run] [💾 Save] [⚙️]   │
├──────────────────────────────────────────────────────────────────────┤
│ ┌────────────┬─────────────────────────────┬──────────────────────┐ │
│ │            │                              │                      │ │
│ │  CATALOG   │      PIPELINE CANVAS         │   CONFIGURATION      │ │
│ │            │                              │                      │ │
│ │ Filter: ▼  │   ┌──────┐                  │  ┌────────────────┐  │
│ │            │   │Taxo  │                   │  │ Selected Node: │  │
│ │ IMPORT     │   │Import│                   │  │ Taxonomy Import│  │
│ │ ○ Taxonomy │   └──┬───┘                   │  │                │  │
│ │ ○ Occurr.  │      │                       │  │ Path: [____]   │  │
│ │ ○ Plots    │   ┌──▼───┐   ┌──────┐       │  │ Hierarchy:     │  │
│ │ ○ Shapes   │   │Field │──→│Top   │       │  │  - family      │  │
│ │ ○ Layers   │   │Aggr. │   │Rank  │       │  │  - genus       │  │
│ │            │   └──────┘   └───┬──┘       │  │  - species     │  │
│ │ TRANSFORM  │                  │           │  │                │  │
│ │ ✓ Compat.  │              ┌───▼──┐        │  │ [Apply] [Reset]│  │
│ │ □ Show All │              │HTML  │        │  └────────────────┘  │
│ │            │              │Export│        │                      │
│ │ EXPORT     │              └──────┘        │  Layout: [Panel ▼]  │
│ │ ○ HTML     │                              │                      │
│ │ ○ JSON     │   [Drop Zone Active]         │                      │
│ │ ○ CSV      │                              │                      │
│ └────────────┴─────────────────────────────┴──────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Status: ✓ Import (1) → ✓ Transform (2) → ✓ Export (1) | Ready   │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 ROADMAP D'IMPLÉMENTATION

### Phase 0 : Préparation (3 jours)
- [ ] Analyse approfondie des fichiers de configuration
- [ ] Documentation des structures de données
- [ ] Setup environnement de développement
- [ ] Tests de ReactFlow avec données mockées

### Phase 1 : Infrastructure de Base (1 semaine)

#### Semaine 1 - Fondations
**Lundi-Mardi**
- [ ] Créer structure de dossiers complète
- [ ] Installer dépendances (reactflow, zustand)
- [ ] Créer `PipelineFlow.tsx` avec ReactFlow basique
- [ ] Implémenter `BaseNode.tsx` et états

**Mercredi-Jeudi**
- [ ] Créer système de layout flexible (`LayoutProvider`)
- [ ] Implémenter `SidePanelLayout` et `ModalLayout`
- [ ] Créer `FormContainer` adaptable
- [ ] Tests de changement de layout

**Vendredi**
- [ ] Créer `NodeCatalog` de base
- [ ] Implémenter drag & drop depuis catalogue
- [ ] Créer `PipelineValidator` basique
- [ ] Tests d'intégration

### Phase 2 : Nodes d'Import (1 semaine)

#### Semaine 2 - Import Forms
**Lundi**
- [ ] Créer `ImportNode.tsx` générique
- [ ] Migrer `TaxonomyForm` depuis code existant
- [ ] Créer `TaxonomyNode` avec icône

**Mardi**
- [ ] Migrer `OccurrencesForm`
- [ ] Créer `OccurrencesNode`
- [ ] Tester connexion API `/api/imports`

**Mercredi**
- [ ] Migrer `PlotForm`
- [ ] Créer `PlotNode`
- [ ] Implémenter validation des champs

**Jeudi**
- [ ] Créer `ShapeForm` pour shapes multiples
- [ ] Créer `ShapeNode`
- [ ] Gérer upload de fichiers shapefile

**Vendredi**
- [ ] Créer `LayerForm` pour rasters/vectors
- [ ] Créer `LayerNode`
- [ ] Tests complets des imports

### Phase 3 : Nodes de Transform (1 semaine)

#### Semaine 3 - Transformations
**Lundi-Mardi**
- [ ] Créer `TransformNode` générique
- [ ] Adapter `PluginConfigPanel` existant
- [ ] Créer `PluginConfigForm` modulaire
- [ ] Implémenter sélection de sources multiples

**Mercredi**
- [ ] Créer `SourceRelationForm` pour relations
- [ ] Implémenter configuration nested_set
- [ ] Gérer fields mapping

**Jeudi**
- [ ] Créer `WidgetConfigForm`
- [ ] Implémenter preview des widgets
- [ ] Validation des paramètres de plugins

**Vendredi**
- [ ] Créer `CompatibilityChecker`
- [ ] Implémenter filtrage intelligent du catalogue
- [ ] Tests de compatibilité

### Phase 4 : Nodes d'Export (3 jours)

#### Semaine 4 - Exports (Lun-Mer)
**Lundi**
- [ ] Créer `ExportNode` générique
- [ ] Créer `HtmlPageForm` pour config HTML
- [ ] Implémenter sélection de templates

**Mardi**
- [ ] Créer `DataExportForm` pour JSON/CSV
- [ ] Implémenter options d'export
- [ ] Créer preview des exports

**Mercredi**
- [ ] Intégration avec système de widgets
- [ ] Tests exports multiples
- [ ] Validation complète du pipeline

### Phase 5 : Sérialisation (3 jours)

#### Semaine 4 - Sérialisation (Jeu-Ven)
**Jeudi**
- [ ] Créer `pipelineSerializer.ts`
- [ ] Implémenter ReactFlow → YAML
- [ ] Gérer tous les types de nodes

**Vendredi**
- [ ] Implémenter YAML → ReactFlow
- [ ] Charger configurations existantes
- [ ] Tests bidirectionnels

### Phase 6 : Exécution et Monitoring (1 semaine)

#### Semaine 5 - Runner
**Lundi-Mardi**
- [ ] Créer `PipelineRunner`
- [ ] Implémenter WebSocket client
- [ ] Créer `ProgressMonitor`

**Mercredi**
- [ ] Implémenter progress bars sur nodes
- [ ] Gérer états (pending/running/success/error)
- [ ] Afficher logs en temps réel

**Jeudi-Vendredi**
- [ ] Gestion des erreurs
- [ ] Retry mechanism
- [ ] Tests end-to-end

### Phase 7 : Optimisations et Polish (1 semaine)

#### Semaine 6 - Finalisation
**Lundi-Mardi**
- [ ] Optimisation performances ReactFlow
- [ ] Amélioration UX (animations, tooltips)
- [ ] Responsive design

**Mercredi-Jeudi**
- [ ] Documentation utilisateur
- [ ] Tests utilisateurs
- [ ] Corrections bugs

**Vendredi**
- [ ] Review code complet
- [ ] Préparation déploiement
- [ ] Documentation développeur

---

## 📊 Métriques de Succès

### Critères Techniques
- ✅ Pipeline valide YAML ↔ ReactFlow
- ✅ Compatibilité stricte entre nodes
- ✅ Exécution temps réel avec monitoring
- ✅ Formulaires modulaires réutilisables
- ✅ Layout flexible et mémorisé

### Critères UX
- ✅ Création pipeline en < 5 minutes
- ✅ Compréhension immédiate du flux
- ✅ Messages d'aide contextuels
- ✅ Validation en temps réel
- ✅ Preview des résultats

### Critères de Performance
- ✅ Rendu < 100ms pour 50+ nodes
- ✅ Sauvegarde < 500ms
- ✅ Chargement config < 1s
- ✅ WebSocket latence < 50ms

---

## 🔧 Technologies et Dépendances

### Core
- **React 19** + **TypeScript**
- **ReactFlow** v11+ pour le canvas
- **Zustand** pour l'état global
- **React Hook Form** pour les formulaires

### UI
- **shadcn/ui** composants
- **Tailwind CSS v4** styling
- **Lucide React** icônes

### Communication
- **WebSocket** pour monitoring temps réel
- **Axios** pour API REST
- **YAML** parser/serializer

### Testing
- **Vitest** pour tests unitaires
- **React Testing Library** pour composants
- **Playwright** pour E2E

---

## 📝 Notes d'Implémentation

### Points d'Attention
1. **Modularité** : Chaque formulaire doit être indépendant de ReactFlow
2. **Validation** : Toujours vérifier la compatibilité avant connexion
3. **Performance** : Lazy loading des formulaires complexes
4. **État** : Utiliser Zustand pour synchronisation globale
5. **Erreurs** : Gestion gracieuse avec recovery

### Conventions
- Noms de fichiers en PascalCase pour composants
- Hooks custom préfixés par `use`
- Types dans fichiers `.types.ts`
- Tests dans `__tests__` adjacents

### Exemples de Code à Réutiliser
- Import forms : `/src/components/import/`
- Plugin config : `/src/components/transform/PluginConfigPanel.tsx`
- API calls : `/src/services/api.ts`
- Types : `/src/types/`

---

## 🚦 Prochaines Étapes

1. **Validation des specs** avec l'équipe
2. **Setup environnement** de développement
3. **POC ReactFlow** avec nodes basiques
4. **Début Phase 1** selon roadmap

---

*Document créé le 15/09/2025 - Version 1.0*
