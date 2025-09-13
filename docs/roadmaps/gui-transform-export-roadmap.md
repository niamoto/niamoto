# Roadmap : Interface GUI Transformation & Export
## MVP Niamoto - Décembre 2024 / Janvier 2025

---

## 📌 Vue d'ensemble

### Objectif Principal
Développer une interface graphique intuitive permettant aux utilisateurs de configurer visuellement les transformations de données et les exports dans Niamoto, sans nécessiter de connaissances techniques en YAML.

### Contexte
- **État actuel** : L'interface d'import est fonctionnelle
- **Besoin** : Interfaces pour les phases de transformation et d'export
- **Délai** : 3 semaines pour un MVP solide
- **Date de début** : 13 décembre 2024
- **Date cible de livraison** : 3 janvier 2025

### Principes Architecturaux
1. **Flexibilité** : Les noms de groupes sont définis par l'utilisateur (taxon, plot, shape sont des exemples)
2. **Sources multiples** : Chaque groupe peut avoir plusieurs sources de données (tables, CSV)
3. **Compatibilité** : Validation automatique de la compatibilité données-plugins-widgets
4. **Guidage** : Interface progressive avec validation proactive

---

## 🏗️ Architecture Technique

### Stack Frontend
- React 19 + TypeScript
- Vite (build tool)
- Tailwind CSS v4 + shadcn/ui
- React DnD (drag-and-drop)
- React Flow (pipeline visuel)
- Tanstack Query (state management)
- React Hook Form + Zod (validation)

### Stack Backend
- FastAPI (API REST)
- Pydantic (validation)
- SQLAlchemy + GeoAlchemy2
- Plugin Registry existant
- SQLite (database)

### Architecture des Données
```
Import (✅ Fait) → Tables de base → Transform → Tables agrégées → Export → Site statique
                                         ↑                             ↑
                                    [Notre focus]              [Notre focus]
```

---

## 📅 Planning Détaillé

### 🚀 Semaine 1 : Infrastructure et Transformation
**Du 16 au 20 décembre 2024**

#### Jour 1-2 (16-17 déc) : Infrastructure API
- [ ] **Backend - Endpoints de gestion des groupes**
  ```python
  GET /api/transform/groups
  POST /api/transform/groups
  PUT /api/transform/groups/{name}
  DELETE /api/transform/groups/{name}
  ```
- [ ] **Backend - Endpoints de sources**
  ```python
  GET /api/transform/groups/{name}/sources
  POST /api/transform/groups/{name}/sources
  GET /api/transform/available-sources
  ```
- [ ] **Backend - Analyse de compatibilité**
  ```python
  POST /api/plugins/analyze-compatibility
  GET /api/plugins/transformers
  GET /api/plugins/transformers/{name}/schema
  ```
- [ ] **Modèles Pydantic**
  - GroupConfig
  - SourceConfig
  - TransformPipeline
  - CompatibilityReport

#### Jour 3-4 (18-19 déc) : Interface de Gestion des Groupes
- [ ] **GroupManager.tsx**
  - Liste des groupes existants
  - Création/édition de groupes
  - Suppression avec confirmation
  - Indicateurs d'état (actif/inactif)

- [ ] **SourceSelector.tsx**
  - Sélection de tables disponibles
  - Upload et sélection de CSV
  - Configuration des relations (nested_set, stats_loader)
  - Interface de jointure visuelle

- [ ] **SourcePreview.tsx**
  - Aperçu des données sources
  - Statistiques rapides (nombre de lignes, colonnes)
  - Détection automatique des types

#### Jour 5 (20 déc) : Pipeline de Transformation
- [ ] **PipelineCanvas.tsx**
  - Canvas avec grille
  - Drag-and-drop de plugins depuis le catalogue
  - Connexions visuelles entre nœuds
  - Zoom et pan

- [ ] **PluginCatalog.tsx**
  - Liste des plugins par catégorie
  - Recherche et filtres
  - Documentation intégrée
  - Indicateur de compatibilité

### 🔧 Semaine 2 : Configuration et Validation
**Du 23 au 27 décembre 2024**

#### Jour 6-7 (23-24 déc) : Système de Compatibilité
- [ ] **CompatibilityEngine (Backend)**
  - Analyse de structure de données
  - Règles de compatibilité par plugin
  - Suggestions de transformations intermédiaires
  - Cache des analyses

- [ ] **PluginConfigurator.tsx**
  - Génération dynamique de formulaires
  - Validation en temps réel
  - Autocomplétion des champs
  - Tooltips d'aide contextuelle

- [ ] **CompatibilityMatrix.tsx**
  - Visualisation matricielle données/plugins
  - Codes couleur (compatible/incompatible/possible)
  - Suggestions au survol

#### Jour 8-9 (25-26 déc) : Prévisualisation
- [ ] **DataInspector.tsx**
  - Table de données paginée
  - Filtres et tri
  - Export CSV d'échantillon
  - Statistiques descriptives

- [ ] **TransformPreview.tsx**
  - Exécution sur échantillon
  - Comparaison avant/après
  - Timeline d'exécution
  - Logs détaillés

#### Jour 10 (27 déc) : Intégration et Tests
- [ ] **Tests unitaires** des composants
- [ ] **Tests d'intégration** API
- [ ] **Optimisation** des performances
- [ ] **Gestion d'erreurs** améliorée

### 🎯 Semaine 3 : Export et Finalisation
**Du 30 décembre 2024 au 3 janvier 2025**

#### Jour 11-12 (30-31 déc) : Interface d'Export
- [ ] **ExportBuilder.tsx**
  - Sélection du groupe transformé
  - Affichage des colonnes disponibles
  - Templates d'export prédéfinis
  - Configuration globale du site

- [ ] **WidgetPicker.tsx**
  - Galerie visuelle de widgets
  - Filtrage par compatibilité automatique
  - Aperçu miniature
  - Catégories (Charts, Maps, Tables, Gauges)

- [ ] **DataColumnExplorer.tsx**
  - Liste des colonnes avec types
  - Aperçu des données
  - Indicateurs de compatibilité widget

#### Jour 13-14 (1-2 jan) : Éditeur de Mise en Page
- [ ] **PageLayoutEditor.tsx**
  - Grille responsive 12 colonnes
  - Drag-and-drop de widgets
  - Redimensionnement des widgets
  - Templates de mise en page

- [ ] **WidgetDataBinder.tsx**
  - Interface de liaison données-widget
  - Mapping des champs
  - Configuration des options d'affichage
  - Validation de configuration

- [ ] **WidgetConfigPanel.tsx**
  - Panneau latéral de configuration
  - Options spécifiques par widget
  - Styles et couleurs
  - Labels et descriptions

#### Jour 15 (3 jan) : Finalisation MVP
- [ ] **LivePreview.tsx**
  - iFrame avec rechargement automatique
  - Navigation entre pages
  - Mode responsive (desktop/tablet/mobile)
  - Bouton d'export final

- [ ] **Documentation utilisateur**
  - Guide de démarrage rapide
  - Tutoriels vidéo
  - FAQ

- [ ] **Tests end-to-end**
- [ ] **Déploiement**

---

## 🎨 Interfaces Principales

### 1. Gestionnaire de Groupes
```
┌─────────────────────────────────────────────────────┐
│ Mes Groupes d'Analyse                              │
├─────────────────────────────────────────────────────┤
│ [+] Créer un groupe                                │
│                                                     │
│ ┌─ Groupe: "especes" ──────────────────────┐      │
│ │ Sources de données:                       │      │
│ │ • occurrences (table) → via taxon_ref    │      │
│ │ • calculs_stats.csv → via species_id     │      │
│ │ [+ Ajouter une source]                    │      │
│ │ Transformations: 12 | Dernière: il y a 2h│      │
│ └────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

### 2. Pipeline de Transformation
```
┌─────────────────────────────────────────────────────┐
│ Pipeline: "especes"                    [Exécuter]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [occurrences] ══╗                                 │
│                  ╠══> [field_aggregator] ══> info  │
│                  ╠══> [top_ranking] ══> top_10     │
│                  ╚══> [geo_extractor] ══> map      │
│                                                     │
│  [stats.csv] ════> [direct_attribute] ══> dbh      │
│                                                     │
│ Catalogue │ Canvas                    │ Propriétés │
└─────────────────────────────────────────────────────┘
```

### 3. Constructeur d'Export
```
┌─────────────────────────────────────────────────────┐
│ Export: Page "especes"              [Prévisualiser]│
├─────────────────────────────────────────────────────┤
│ Données: ✓info ✓top_10 ✓map ✓dbh                  │
│                                                     │
│ ┌─────────────────────────────────────────┐       │
│ │ ┌─────────┐ ┌─────────┐ ┌─────────┐    │       │
│ │ │info_grid│ │  map    │ │bar_chart│    │       │
│ │ └─────────┘ └─────────┘ └─────────┘    │       │
│ │ ┌─────────────────────┐ ┌─────────┐    │       │
│ │ │    donut_chart     │ │  gauge  │    │       │
│ │ └─────────────────────┘ └─────────┘    │       │
│ └─────────────────────────────────────────┘       │
│                                                     │
│ Widgets disponibles: [8 compatibles] [5 tous]      │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Métriques de Succès

### Performance
- ⏱️ Temps de configuration d'un pipeline simple : < 5 minutes
- 🚀 Prévisualisation des données : < 2 secondes pour 1000 lignes
- 💾 Génération d'export : < 30 secondes pour un site complet

### Qualité
- 🎯 Taux d'erreur de configuration : < 5%
- ✅ Couverture de tests : > 80%
- 📱 Compatibilité navigateurs : Chrome, Firefox, Safari, Edge

### Expérience Utilisateur
- 😊 Interface intuitive sans formation préalable
- 🔍 Documentation contextuelle complète
- ♿ Accessibilité WCAG 2.1 niveau AA

---

## 🚧 Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|------------|--------|------------|
| Complexité du drag-and-drop | Moyenne | Élevé | Utiliser une librairie éprouvée (React DnD) |
| Performance avec gros volumes | Moyenne | Moyen | Pagination et échantillonnage intelligent |
| Compatibilité données-widgets | Faible | Élevé | Système de validation robuste |
| Délais serrés (3 semaines) | Élevée | Élevé | Priorisation stricte du MVP |

---

## 📦 Livrables

### Semaine 1
- ✅ API de gestion des groupes fonctionnelle
- ✅ Interface de création de groupes avec sources multiples
- ✅ Pipeline visuel de transformation basique

### Semaine 2
- ✅ Système de validation de compatibilité
- ✅ Configuration dynamique des plugins
- ✅ Prévisualisation des transformations

### Semaine 3
- ✅ Interface d'export complète
- ✅ Éditeur de mise en page
- ✅ MVP testé et documenté

---

## 🔄 Suivi et Communication

### Points de synchronisation
- **Daily standup** : 9h30 (15 min)
- **Review hebdomadaire** : Vendredi 16h
- **Demo utilisateurs** : Fin de chaque semaine

### Canaux
- GitHub Issues pour le suivi des tâches
- Pull Requests pour la revue de code
- Documentation dans `/docs/gui/`

---

## 🎯 Définition de "Done"

Une fonctionnalité est considérée comme terminée quand :
1. ✅ Le code est écrit et testé
2. ✅ La documentation est à jour
3. ✅ Les tests passent (unitaires + intégration)
4. ✅ La revue de code est approuvée
5. ✅ La fonctionnalité est déployée en environnement de test

---

## 📈 Évolutions Post-MVP

### Phase 2 (Janvier 2025)
- Mode collaboratif multi-utilisateurs
- Historique et versioning des configurations
- Système de templates communautaires
- Export vers d'autres formats (PDF, PowerBI)

### Phase 3 (Février 2025)
- IA pour suggestions de transformations
- Optimisation automatique des pipelines
- Monitoring et alertes
- API publique pour intégrations tierces

---

## 📝 Notes et Décisions

### Décisions Techniques
- **13/12/2024** : Choix de React Flow pour le pipeline visuel
- **13/12/2024** : Validation côté serveur prioritaire sur client

### Points d'Attention
- Les noms de groupes sont libres (pas de contrainte sur "taxon", "plot", "shape")
- Les sources multiples doivent être gérées avec flexibilité
- La compatibilité données-widgets est critique pour l'UX

---

## 👥 Équipe

- **Product Owner** : Julien Barbe
- **Lead Developer** : Julien Barbe
- **UI/UX Assistant** : Claude
- **QA** : À définir

---

*Document créé le 13/12/2024*
*Dernière mise à jour : 13/12/2024*
*Version : 1.0*
