# Plan détaillé d'amélioration du système de plugins Niamoto

## 1. Vision et objectifs
- **Simplifier la configuration** : réduire la complexité d'`import.yml`, `transform.yml` et `export.yml`, fluidifier l'onboarding des équipes métier.
- **Sécuriser et fiabiliser l'exécution** : garantir la validation systématique des greffons, tracer les exécutions et éliminer les secrets en clair.
- **Automatiser l'outillage** : générer les configurations et formulaires à partir des schémas existants pour limiter les opérations manuelles.

## 2. Piliers stratégiques

### Pilier 1 – Gouvernance des greffons
- **Manifeste standard** : ajouter `plugin.json` (ou `manifest.yml`) par greffon avec nom, version, compatibilité Niamoto, I/O et dépendances.
- **Enrichir le registre** : étendre `PluginRegistry` pour charger, vérifier et refuser les versions incompatibles (`src/niamoto/core/plugins/registry.py:24`).
- **Exposer l’état** : fournir une API (REST/CLI) listant les manifests et publiant un rapport de santé (plugins manquants, versions obsolètes, dépendances cassées).

### Pilier 2 – Validation et résilience
- **Validation Pydantic centralisée** : dans le service de transformation, valider les paramètres via `param_schema` avant l’appel au greffon (`src/niamoto/core/services/transformer.py:186`).
- **Exceptions normalisées** : introduire `PluginExecutionError` avec contexte (plugin, phase, item, configuration) et journalisation structurée.
- **Journal d’exécution** : stocker un log par run (identifiant, hash de config, durée, warnings) pour faciliter le support.

### Pilier 3 – Gestion de la configuration
- **Modulariser `transform.yml`** : scinder par domaine (`transform/taxons.yml`, `transform/plots.yml`, etc.) et supporter `!include`.
- **Générer l’UI** : dériver formulaires CLI/GUI à partir de `param_schema` (`src/niamoto/gui/api/routers/plugins.py:144`).
- **Mettre en cache la découverte** : centraliser la résolution de chemins via `Config.get_imports_config` pour éviter les relectures répétées (`src/niamoto/core/plugins/transformers/aggregation/field_aggregator.py:157`).

### Pilier 4 – Sécurité et secrets
- **Variables de substitution** : remplacer les clés API en clair par des références (`${NIAMOTO_API_KEY}`) (`test-instance/niamoto-og/config/import.yml:22`).
- **Gestionnaire de secrets** : ajouter `niamoto secrets set/list` (stockage chiffré local ou intégration Vault).
- **Culture sécurité** : documenter les bonnes pratiques et ajouter un lint détectant les secrets hardcodés dans YAML/Python.

### Pilier 5 – Expérience développeur
- **Scaffolding CLI** : `uv run niamoto plugins scaffold transformer` pour générer squelette Pydantic + manifest + tests.
- **Tests contractuels** : exécuter chaque greffon sur un dataset minimal dans la CI.
- **Cookbook** : produire une documentation « recettes » (enrichissement API, agrégations multi-sources, widgets avancés).

### Pilier 6 – Performance et observabilité
- **Instrumentation** : exporter métriques Prometheus/OpenTelemetry (temps par greffon, nombre d’items, erreurs).
- **Cache inter-run** : mémoriser les données immuables (CSV, rasters) pour accélérer les exécutions.
- **Mode dry-run** : permettre une validation complète du pipeline sans générer les exports lourds.

## 3. Organisation de la feuille de route

| Période | Livrables clés | Commentaires |
|---------|----------------|--------------|
| **Semaines 1-2** | Manifestes plugins, validation centralisée, coffre à secrets | Quick Wins visibles et sécurités critiques |
| **Semaines 3-4** | Découpage YAML, générateur de formulaires, outil de scaffolding | Composants transverses réutilisables |
| **Semaines 5-6** | Observabilité (metrics, journal), mode dry-run | Prépare la montée en charge et le support |
| **Semaine 7** | Tests end-to-end, documentation finale, migration progressive des configs | Stabilisation avant communication externe |

## 4. Risques et plans de mitigation
- **Adoption partielle des manifestes** : fournir un script de migration, maintenir l’ancien mode en dépréciation pendant 2 releases.
- **Explosion du nombre de fichiers YAML** : documenter une convention de nommage et proposer un utilitaire d’agrégation/visualisation.
- **Charge de formation** : organiser une session interne et mettre à jour le guide « Quick start simplification ».
- **Temps de développement** : découper les tâches en tickets courts pour garder la vélocité.

## 5. Prochaines actions
1. Valider la feuille de route en comité produit/tech.
2. Créer et prioriser les tickets avec l’étiquette `plugins-architecture`.
3. Démarrer la POC manifeste + validation pour livrer rapidement des Quick Wins.
4. Planifier les ateliers de formation (équipe plugin + équipes métier).

## 6. Annexes

### Exemple de manifeste (proposition)
```json
{
  "name": "field_aggregator",
  "version": "1.2.0",
  "niamoto_version": ">=0.8",
  "entrypoint": "field_aggregator.FieldAggregator",
  "inputs": [
    {"type": "dataframe", "alias": "occurrences", "schema": "occurrences_v2"}
  ],
  "outputs": [
    {"type": "mapping", "schema": "general_info_v2"}
  ],
  "dependencies": ["pandas>=2.1", "geopandas"]
}
```

### Exemple de validation centralisée (pseudo-code)
```python
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

class TransformerService:
    def _call_plugin(self, widget_cfg: dict, data: Any) -> Any:
        plugin_cls = PluginRegistry.get_plugin(widget_cfg["plugin"], PluginType.TRANSFORMER)
        plugin = plugin_cls(self.db)
        params_model = plugin.param_schema
        validated_params = params_model.model_validate(widget_cfg.get("params", {}))
        try:
            return plugin.transform(data, validated_params)
        except Exception as exc:
            raise PluginExecutionError(
                plugin=widget_cfg["plugin"],
                phase="transform",
                item=widget_cfg.get("group_id"),
                original=exc,
            ) from exc
```

### Commande CLI secrets (concept)
```bash
$ niamoto secrets set ENDEMIA_API_KEY "********"
$ niamoto secrets list
Key                Updated
----------------------------
ENDEMIA_API_KEY    2025-03-04
```

---
Ce document guide la mise en œuvre coordonnée des améliorations du système de plugins. Il servira de base à la planification produit/tech et à la communication avec les équipes métier.
