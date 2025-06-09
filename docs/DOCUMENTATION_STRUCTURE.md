# Proposition de Nouvelle Structure de Documentation

## Structure Actuelle vs Structure Proposée

### Structure Actuelle
```
docs/
├── api/                    # Documentation API auto-générée
├── assets/                 # Images et diagrammes
├── guides/                 # Guides existants (6 fichiers)
├── references/             # Références (1 fichier)
├── troubleshooting/        # Dépannage (1 fichier)
├── conf.py                 # Configuration Sphinx
└── index.rst              # Index Sphinx (minimal)
```

### Structure Proposée
```
docs/
├── _static/               # Assets statiques (renommé depuis assets/)
├── _templates/            # Templates Sphinx personnalisés
├── api/                   # Documentation API auto-générée (conservé)
│
├── getting-started/       # NOUVEAU - Guide de démarrage
│   ├── installation.md
│   ├── quickstart.md
│   └── concepts.md
│
├── guides/                # Guides pratiques (enrichi)
│   ├── configuration.md   # ✅ Existant
│   ├── data-import.md     # NOUVEAU
│   ├── data-preparation.md # NOUVEAU
│   ├── transform_chain_guide.md # ✅ Existant
│   ├── plugin_top_ranking.md # ✅ Existant
│   ├── custom_plugin.md   # ✅ Existant
│   ├── plugin_reference.md # ✅ Existant
│   ├── api_taxonomy_enricher.md # ✅ Existant
│   ├── export-guide.md    # NOUVEAU
│   └── deployment.md      # NOUVEAU
│
├── tutorials/             # NOUVEAU - Tutoriels pratiques
│   ├── biodiversity-site.md
│   ├── forest-plots.md
│   └── external-data.md
│
├── references/            # Documentation de référence (enrichi)
│   ├── plugin-system-overview.md # ✅ Existant
│   ├── database-schema.md # NOUVEAU
│   ├── pipeline-architecture.md # NOUVEAU
│   ├── cli-commands.md    # NOUVEAU
│   └── yaml-reference.md  # NOUVEAU
│
├── development/           # NOUVEAU - Pour les développeurs
│   ├── contributing.md
│   └── widget-development.md
│
├── advanced/              # NOUVEAU - Sujets avancés
│   ├── optimization.md
│   └── gis-integration.md
│
├── troubleshooting/       # Guide de dépannage (enrichi)
│   ├── template-not-found.md # ✅ Existant
│   └── common-issues.md   # NOUVEAU
│
├── faq/                   # NOUVEAU - Questions fréquentes
│   └── general.md
│
├── resources/             # NOUVEAU - Ressources additionnelles
│   ├── glossary.md
│   └── links.md
│
├── migration/             # NOUVEAU - Guides de migration
│   └── migration-guide.md
│
├── DOCUMENTATION_INDEX.md # ✅ Créé - Index principal
├── DOCUMENTATION_STRUCTURE.md # Ce fichier
├── conf.py               # Configuration Sphinx (à mettre à jour)
├── index.rst             # Index Sphinx principal (à enrichir)
└── CHANGELOG.md          # NOUVEAU - Historique des versions
```

## Plan d'Action pour la Réorganisation

### Phase 1 - Préparation (Immédiat)
1. ✅ Créer DOCUMENTATION_INDEX.md
2. ✅ Créer DOCUMENTATION_STRUCTURE.md
3. Créer les nouveaux dossiers
4. Mettre à jour conf.py pour inclure markdown
5. Enrichir index.rst avec la nouvelle structure

### Phase 2 - Documentation Fondamentale (Priorité Haute)
1. **Getting Started** (3 documents)
   - Installation avec exemples concrets
   - Quickstart basé sur niamoto-og
   - Concepts avec diagrammes

2. **Guides Pratiques** (4 nouveaux)
   - Import de données avec exemples CSV
   - Préparation des données
   - Guide d'export complet
   - Guide de déploiement

3. **Références CLI** (1 document)
   - Documentation complète des commandes
   - Exemples d'utilisation
   - Options et flags

### Phase 3 - Documentation Avancée (Priorité Moyenne)
1. **Tutoriels** (3 documents)
   - Cas d'usage complets
   - Step-by-step avec captures
   - Code source d'exemple

2. **Architecture** (2 documents)
   - Schéma de base de données
   - Architecture du pipeline

3. **Troubleshooting** (1 document)
   - Compilation des problèmes courants
   - Solutions testées

### Phase 4 - Ressources Complémentaires (Priorité Basse)
1. **Development** (2 documents)
2. **Advanced** (2 documents)
3. **Resources** (2 documents)
4. **FAQ** (1 document)

## Recommandations

### 1. Utiliser le Projet niamoto-og comme Base
- Tous les exemples devraient être basés sur la configuration réelle de niamoto-og
- Inclure des captures d'écran du site généré
- Utiliser les vrais fichiers de données comme exemples

### 2. Standardiser le Format
- Utiliser Markdown pour tous les nouveaux documents
- Structure cohérente : Introduction, Prérequis, Contenu, Exemples, Troubleshooting
- Inclure des snippets de code testables

### 3. Intégration Sphinx
- Configurer MyST parser pour supporter Markdown
- Créer un thème personnalisé si nécessaire
- Générer une documentation navigable

### 4. Versioning et Maintenance
- Documenter chaque version dans CHANGELOG.md
- Maintenir l'index à jour
- Réviser la documentation à chaque release

## Prochaines Étapes Concrètes

1. **Créer la structure de dossiers**
   ```bash
   cd docs/
   mkdir -p getting-started tutorials development advanced faq resources migration
   ```

2. **Déplacer/Renommer les assets**
   ```bash
   mv assets _static
   ```

3. **Mettre à jour conf.py pour MyST**
   - Ajouter myst_parser aux extensions
   - Configurer les options MyST

4. **Commencer par le Getting Started**
   - Installation.md
   - Quickstart.md basé sur niamoto-og

5. **Créer un template pour les nouveaux guides**
   - Structure standard
   - Checklist de contenu

Cette restructuration permettra d'avoir une documentation complète, bien organisée et facilement navigable pour tous les types d'utilisateurs de Niamoto.
