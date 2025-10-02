# Roadmap : Système de Liaison Configuration/Base de Données
## Niamoto GUI - Décembre 2024 / Janvier 2025

---

## 📌 Vue d'ensemble

### Problématique Actuelle
L'interface GUI de Niamoto fonctionne actuellement de manière isolée, sans prendre en compte :
- Les configurations existantes (import.yml, transform.yml, export.yml)
- Les données déjà présentes dans la base SQLite
- L'état d'avancement du pipeline (import effectué, transform en cours, etc.)

Cela crée plusieurs problèmes :
1. **Perte de contexte** : L'utilisateur ne sait pas où il en est
2. **Duplication de travail** : Reconfiguration de ce qui existe déjà
3. **Incohérence** : Les données affichées ne correspondent pas à la réalité
4. **Valeurs en dur** : Tables et plugins codés en dur au lieu d'être dynamiques

### Objectif Principal
Créer un système de liaison bidirectionnelle entre l'interface GUI et le backend, permettant de :
- Charger et afficher les configurations existantes
- Récupérer dynamiquement les données depuis la base
- Modifier les configurations existantes via l'interface
- Suivre l'état d'avancement du pipeline

### Bénéfices Attendus
- **Meilleure UX** : L'utilisateur voit exactement où il en est
- **Cohérence** : Une source de vérité unique (fichiers config + base)
- **Efficacité** : Pas de reconfiguration inutile
- **Flexibilité** : Support de n'importe quelle structure de données

---

## 🏗️ Architecture Technique

### Flux de Données

```
┌─────────────────────────────────────────────────────────────────┐
│                          Interface GUI                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    [Import Page] ←→ [Transform Page] ←→ [Export Page]          │
│         ↑↓                ↑↓                ↑↓                  │
└─────────────────────────────────────────────────────────────────┘
          ↕                  ↕                  ↕
┌─────────────────────────────────────────────────────────────────┐
│                        API FastAPI                               │
├─────────────────────────────────────────────────────────────────┤
│   /api/config/*      /api/database/*      /api/plugins/*        │
│   /api/status/*      /api/transform/*     /api/export/*         │
└─────────────────────────────────────────────────────────────────┘
          ↕                  ↕                  ↕
┌─────────────────────────────────────────────────────────────────┐
│                     Backend Niamoto                              │
├─────────────────────────────────────────────────────────────────┤
│  [Config Files]      [SQLite DB]      [Plugin Registry]         │
│  - import.yml        - Tables         - Loaders                 │
│  - transform.yml     - Views          - Transformers            │
│  - export.yml        - Indexes        - Exporters               │
│                                        - Widgets                 │
└─────────────────────────────────────────────────────────────────┘
```

### Endpoints API Nécessaires

#### 1. Status & Configuration
```python
# État global du pipeline
GET /api/status
Response: {
    "import": {
        "configured": true,
        "executed": true,
        "last_run": "2024-12-13T10:00:00Z",
        "records_imported": 15234
    },
    "transform": {
        "configured": false,
        "executed": false,
        "groups": []
    },
    "export": {
        "configured": false,
        "executed": false,
        "exports": []
    }
}

# Configuration par étape
GET /api/config/{step}  # step: import, transform, export
POST /api/config/{step}
PUT /api/config/{step}
DELETE /api/config/{step}

# Validation de configuration
POST /api/config/{step}/validate
```

#### 2. Base de Données
```python
# Schéma de la base
GET /api/database/schema
Response: {
    "tables": [
        {
            "name": "occurrences",
            "row_count": 15234,
            "columns": [
                {"name": "id", "type": "INTEGER", "nullable": false},
                {"name": "taxon_ref", "type": "TEXT", "nullable": true},
                {"name": "geo_pt", "type": "GEOMETRY", "nullable": true}
            ]
        }
    ]
}

# Aperçu des données
GET /api/database/tables/{table_name}/preview?limit=100

# Statistiques
GET /api/database/tables/{table_name}/stats
```

#### 3. Plugins
```python
# Liste des plugins disponibles
GET /api/plugins?type={plugin_type}
Response: {
    "plugins": [
        {
            "id": "field_aggregator",
            "name": "Field Aggregator",
            "type": "transformer",
            "description": "Aggregate fields from multiple sources",
            "parameters_schema": {...},
            "compatible_inputs": ["table", "csv"],
            "output_format": "aggregated_data"
        }
    ]
}

# Schéma de configuration d'un plugin
GET /api/plugins/{plugin_id}/schema

# Test de compatibilité
POST /api/plugins/check-compatibility
Body: {
    "source_data": {...},
    "plugin_id": "field_aggregator"
}
```

#### 4. Transform Spécifiques
```python
# Groupes de transformation
GET /api/transform/groups
POST /api/transform/groups
PUT /api/transform/groups/{group_name}
DELETE /api/transform/groups/{group_name}

# Sources disponibles pour un groupe
GET /api/transform/groups/{group_name}/available-sources

# Pipeline de transformation
GET /api/transform/groups/{group_name}/pipeline
POST /api/transform/groups/{group_name}/pipeline
```

---

## 📅 Plan d'Implémentation

### Phase 1 : Infrastructure Backend (3-4 jours)
**Objectif** : Créer les endpoints API nécessaires

#### Jour 1-2 : Endpoints de Status et Configuration
- [ ] Créer `api/routers/status.py`
  - Endpoint `/api/status` pour l'état global
  - Calcul des statistiques depuis la base
  - Vérification des fichiers de configuration

- [ ] Créer `api/routers/config.py`
  - CRUD pour les configurations
  - Parser YAML bidirectionnel
  - Validation avec Pydantic

#### Jour 3 : Endpoints Database et Plugins
- [ ] Créer `api/routers/database.py`
  - Introspection du schéma SQLite
  - Preview avec pagination
  - Statistiques par table

- [ ] Créer `api/routers/plugins.py`
  - Liste depuis le registry
  - Schémas de configuration
  - Tests de compatibilité

#### Jour 4 : Tests et Documentation
- [ ] Tests unitaires des endpoints
- [ ] Tests d'intégration
- [ ] Documentation OpenAPI

### Phase 2 : Adaptation Frontend Import (2-3 jours)
**Objectif** : Modifier l'interface Import pour utiliser les données réelles

#### Jour 5 : État et Configuration
- [ ] Créer `hooks/useConfigStatus.ts`
  - Hook pour récupérer l'état
  - Cache avec React Query
  - Gestion des erreurs

- [ ] Modifier `pages/import.tsx`
  - Affichage mode lecture si config existe
  - Bouton "Modifier" pour édition
  - Indicateurs d'état

#### Jour 6 : Chargement Dynamique
- [ ] Créer `services/configService.ts`
  - Chargement des configurations
  - Sauvegarde des modifications
  - Validation côté client

- [ ] Adapter les composants Import
  - Tables depuis l'API
  - Colonnes depuis le schéma
  - Preview des données réelles

#### Jour 7 : Polish et Tests
- [ ] Gestion des états de chargement
- [ ] Messages d'erreur explicites
- [ ] Tests des composants

### Phase 3 : Adaptation Frontend Transform (3-4 jours)
**Objectif** : Connecter l'interface Transform aux données réelles

#### Jour 8-9 : GroupManager Dynamique
- [ ] Modifier `GroupManager.tsx`
  - Charger groupes depuis API
  - Synchronisation bidirectionnelle
  - Persistance automatique

- [ ] Modifier `SourceSelector.tsx`
  - Tables depuis database/schema
  - Relations disponibles depuis plugins
  - Validation en temps réel

#### Jour 10 : Pipeline Visuel
- [ ] Modifier `PipelineCanvas.tsx`
  - Reconstruire depuis config existante
  - Sauvegarder les modifications
  - Validation de compatibilité

- [ ] Modifier `PluginCatalog.tsx`
  - Plugins depuis API
  - Filtrage par compatibilité
  - Documentation dynamique

#### Jour 11 : Intégration
- [ ] Synchronisation globale
- [ ] Tests end-to-end
- [ ] Optimisations

### Phase 4 : Interface Export avec Liaison (4-5 jours)
**Objectif** : Développer l'interface Export en utilisant le système de liaison

#### Jour 12-13 : Structure Export
- [ ] Créer `pages/export.tsx`
  - Multi-onglets (Site, Pages, Groups, Templates, Preview)
  - État depuis API

- [ ] Créer `components/export/SiteConfig.tsx`
  - Configuration générale
  - Navigation
  - Thème

#### Jour 14-15 : Widgets et Preview
- [ ] Créer `components/export/WidgetSelector.tsx`
  - Widgets compatibles depuis API
  - Drag-and-drop layout
  - Configuration par widget

- [ ] Créer `components/export/LivePreview.tsx`
  - iFrame avec rechargement
  - Navigation entre pages
  - Mode responsive

#### Jour 16 : Finalisation
- [ ] Tests complets
- [ ] Documentation
- [ ] Déploiement

---

## 📊 Métriques de Succès

### Performance
- Temps de chargement initial : < 2s
- Temps de synchronisation : < 500ms
- Cache efficace : 90% hit rate

### Fiabilité
- Synchronisation sans perte : 100%
- Gestion d'erreurs : 100% coverage
- Rollback automatique si échec

### UX
- Temps pour comprendre l'état : < 5s
- Temps pour modifier une config : < 30s
- Satisfaction utilisateur : > 4/5

---

## 🔧 Stack Technique

### Frontend
```typescript
// Hooks personnalisés
useConfigStatus() // État global
useTableSchema(tableName) // Schéma d'une table
usePluginList(type) // Liste des plugins
useCompatibility(source, plugin) // Test compatibilité

// Services
configService // CRUD configurations
databaseService // Introspection base
pluginService // Gestion plugins
syncService // Synchronisation
```

### Backend
```python
# Nouveaux modules
api/routers/status.py
api/routers/config.py
api/routers/database.py
api/routers/plugins.py

# Services
services/config_manager.py
services/database_inspector.py
services/plugin_compatibility.py
services/pipeline_status.py
```

---

## 🚧 Risques et Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Conflits de synchronisation | Élevé | Moyenne | Versioning et locks optimistes |
| Performance avec grosses configs | Moyen | Faible | Pagination et lazy loading |
| Incompatibilité versions | Élevé | Faible | Migration automatique |
| Corruption de config | Élevé | Très faible | Backups automatiques |

---

## 🔄 Migration des Utilisateurs Existants

### Stratégie
1. **Détection automatique** : Au chargement, vérifier si configs existent
2. **Mode compatibilité** : Supporter ancien et nouveau format
3. **Migration assistée** : Wizard pour migrer les anciennes configs
4. **Rollback possible** : Garder backup des anciennes configs

### Timeline
- Semaine 1 : Coexistence des deux systèmes
- Semaine 2 : Migration progressive
- Semaine 3 : Nouveau système par défaut
- Semaine 4 : Dépréciation ancien système

---

## 📈 Évolutions Futures

### Court terme (Q1 2025)
- Historique des modifications
- Diff entre versions
- Import/Export de configurations

### Moyen terme (Q2 2025)
- Collaboration temps réel
- Commentaires sur configs
- Templates partagés

### Long terme (Q3+ 2025)
- IA pour suggestions
- Optimisation automatique
- Marketplace de configs

---

## 📝 Décisions Techniques

### Prises
- **13/12/2024** : Architecture API REST (pas GraphQL)
- **13/12/2024** : React Query pour state management
- **13/12/2024** : YAML comme format de config

### À Prendre
- Format de cache (localStorage vs IndexedDB)
- Stratégie de versioning
- Fréquence de synchronisation

---

## 🎯 Critères d'Acceptation

Une fonctionnalité est complète quand :
1. ✅ L'API endpoint fonctionne
2. ✅ L'interface se synchronise
3. ✅ Les tests passent
4. ✅ La documentation est à jour
5. ✅ Les performances sont acceptables

---

## 👥 Responsabilités

- **Product Owner** : Julien Barbe
- **Architecture** : Julien Barbe + Claude
- **Développement** : Julien Barbe
- **Tests** : Automatisés + Manuels
- **Documentation** : Au fur et à mesure

---

*Document créé le 13/12/2024*
*Version : 1.0*
*Prochaine révision : 20/12/2024*
