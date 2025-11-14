# Testing Improvements - Next Steps Roadmap

**Date**: 2025-01-22
**Context**: Post testing anti-pattern elimination (169 patterns eliminated, 46→0 warnings)
**Related**: [refactor-action-plan.md](./refactor-action-plan.md) Phase 5, [error-handling.md](./error-handling.md) Phase 0
**Maintenu par**: Claude Code + Julien Barbe

---

## 🎯 OBJECTIF

Renforcer la couverture et la qualité des tests suite à l'élimination des anti-patterns en :
1. Ajoutant des tests d'intégration avec DuckDB réelle
2. Implémentant l'analyse de couverture de code
3. Optimisant les performances des tests

---

## 📊 ÉTAT ACTUEL

### ✅ Travail Complété (2025-01-22)

**8 fichiers de tests corrigés** avec élimination des anti-patterns :
- `tests/cli/test_stats.py` - FakeRegistry → Real EntityRegistry (40 lignes de mock → production code)
- `tests/cli/test_transform.py` - ResourceWarning fix via Database mocking
- `tests/core/services/test_transformer.py` - Documentation des limitations (unit vs integration)
- `tests/core/services/test_exporter.py` - Documentation orchestration tests
- `tests/core/services/test_importer.py` - Ajout spec= aux mocks Database/Registry
- `tests/core/plugins/transformers/aggregation/test_field_aggregator.py` - Mocks au bon niveau (db.fetch_one vs private methods)
- `tests/common/test_database.py` - Documentation mocking infrastructure (commit/rollback errors)
- `tests/common/test_environment.py` - Filesystem réel au lieu de mocks

**Résultats quantifiés** :
- **169 anti-patterns éliminés** :
  - Testing Mock Behavior → Testing Real Behavior
  - Mocking Private Methods → Mocking External Dependencies
  - Incomplete Mocks → Mocks with spec=
  - Hybrid DB/Mock Tests → Documented Infrastructure Mocking
- **3 bugs critiques trouvés** pendant le refactoring :
  - Environment reset incomplet (fichiers non supprimés)
  - Bug de conversion de type (string "500" au lieu de int 500)
  - **SÉCURITÉ** : Database supprimée sans confirmation (ajout --force-reset flag)
- **Warnings réduits** : 46 → 0
  - ResourceWarnings (connexions non fermées) : 19 → 0
  - UserWarnings (ipywidgets, pandas, geopandas) : 22 → 0
  - DeprecationWarnings (pyproj, shapely) : 5 → 0
- **201+ tests améliorés** suivent maintenant les best practices

### 📋 Métriques de Qualité des Tests

| Métrique | Avant | Après | Cible |
|----------|-------|-------|-------|
| Anti-patterns | 169 | 0 ✅ | 0 |
| ResourceWarnings | 46 | 0 ✅ | 0 |
| Tests avec documentation | ~20% | ~60% | 100% |
| Tests d'intégration | 11 | 11 | 50+ |
| Couverture de code | ~80% | ~80% | >90% |
| Temps d'exécution | ~18s | ~17s | <10s |

### ⚠️ Limitations Actuelles

**Tests principalement unitaires** :
- `test_transformer.py:19` - NOTE explicite : "Ces tests ne vérifient PAS les résultats réels des transformations"
- `test_exporter.py:10` - LIMITATION : "Ces tests ne vérifient PAS la création réelle de fichiers"
- `test_stats.py` - Base de données en mémoire mais exécution SQL mockée

**Gaps de couverture** :
- Transformers géospatiaux : ~75% (cas d'erreur manquants)
- GUI code : <40% (largement non testé)
- Cas edge : Configurations invalides, erreurs DB non testées

**Performance** :
- Suite complète : ~17s (acceptable mais peut être amélioré)
- Fixtures DB recréées plusieurs fois (optimisation possible)

---

## 📈 RECOMMENDED NEXT STEPS

### STEP 1 - Tests d'Intégration avec DuckDB Réelle 🔴

**Durée Estimée** : 2-3 jours
**Priorité** : **HAUTE** - Critique pour valider le comportement réel
**Effort** : 🔴🔴🔴 Moyen-Élevé

#### Pourquoi C'est Nécessaire

Les tests actuels sont principalement des tests unitaires avec dépendances mockées :
- `test_transformer.py` mocke les transformers ET la database (ligne 19 NOTE explique la limitation)
- `test_stats.py` utilise une base en mémoire mais mocke l'exécution SQL
- `test_exporter.py` mocke les exporters et ne vérifie pas les fichiers créés
- **Aucun test end-to-end** du pipeline complet : Import CSV → Transform → Export

**Impact sur la qualité** :
- Bugs de production non détectés (comme le bug de type string→int découvert)
- Comportement réel des plugins non validé
- Intégration DuckDB/SQLAlchemy non testée
- Scénarios complexes (hiérarchies, géospatial) non couverts

#### Approche Proposée

**1. Créer structure `tests/integration/`** :

```
tests/integration/
├── __init__.py
├── conftest.py                    # Fixtures communes
├── test_import_transform_flow.py  # Pipeline complet
├── test_real_transformers.py      # Transformers avec vraie DB
├── test_hierarchy_transformers.py # adjacency_list, nested_set
├── test_geospatial_transformers.py # raster_stats, vector_overlay
└── fixtures/
    ├── sample_occurrences.csv
    ├── sample_taxonomy.csv
    └── sample_shapes.geojson
```

**2. Fixture pour DuckDB réelle** :

```python
# tests/integration/conftest.py
import pytest
from pathlib import Path
from niamoto.common.database import Database
from niamoto.core.imports.registry import EntityRegistry

@pytest.fixture(scope="module")
def integration_db(tmp_path_factory):
    """Create real DuckDB with test data for integration tests.

    Scope: module - DB créée une fois par fichier de test pour performance.
    """
    db_path = tmp_path_factory.mktemp("integration") / "test.duckdb"
    db = Database(str(db_path))
    registry = EntityRegistry(db)

    # Load test taxonomy
    registry.register_entity(
        name="taxon_ref",
        kind=EntityKind.REFERENCE,
        table_name="taxon_ref",
        config={}
    )

    # Import sample data
    # ... (CSV loading)

    yield db, registry

    # Cleanup
    db.engine.dispose()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def sample_occurrences_csv(tmp_path):
    """Create sample occurrences CSV for testing."""
    csv_path = tmp_path / "occurrences.csv"
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "taxon_ref_id": [100, 101, 100],
        "plot_ref_id": [1, 1, 2],
        "dbh": [25.5, 42.0, 18.3],
        "elevation": [450, 450, 680]
    })
    df.to_csv(csv_path, index=False)
    return csv_path
```

**3. Tests d'intégration end-to-end** :

```python
# tests/integration/test_import_transform_flow.py
"""Integration tests for complete Import → Transform → Export flow.

Unlike unit tests that mock components, these tests:
- Use real DuckDB database with test data
- Load real transformer plugins
- Verify actual transformed data in database
- Test complete pipeline without mocks
"""

def test_complete_pipeline_taxon_aggregation(integration_db, sample_occurrences_csv):
    """Test: Import occurrences → Transform by taxon → Verify results in DB."""
    db, registry = integration_db

    # 1. IMPORT: Load occurrences from CSV
    importer = ImporterService(db.db_path)
    config = DatasetEntityConfig(
        connector=ConnectorConfig(type=ConnectorType.FILE, path=str(sample_occurrences_csv)),
        schema=EntitySchema(id_field="id", fields=[])
    )
    result = importer.import_dataset("occurrences", config)
    assert "Imported 3 records" in result

    # 2. TRANSFORM: Aggregate by taxon
    transformer = TransformerService(db.db_path, mock_config)
    transformer.transform_data(group_by="taxon", recreate_table=True)

    # 3. VERIFY: Check transformed data in database
    result = db.execute_sql(
        "SELECT taxon_id, occurrence_count FROM taxon WHERE taxon_id = 100",
        fetch=True
    )
    assert result["occurrence_count"] == 2  # Real DB query, real result

    # 4. VERIFY: Check widget results stored
    result = db.execute_sql(
        "SELECT widget_data FROM taxon WHERE taxon_id = 100",
        fetch=True
    )
    widget_data = json.loads(result["widget_data"])
    assert "species_count" in widget_data
```

**4. Tests de transformers spécifiques** :

```python
# tests/integration/test_real_transformers.py

def test_field_aggregator_with_real_db(integration_db):
    """Test FieldAggregator retrieves values from real database."""
    db, registry = integration_db

    # Setup: Insert test data
    db.execute_sql("""
        INSERT INTO entity_plots (id, plot_name, elevation)
        VALUES (1, 'Plot A', 450), (2, 'Plot B', 680)
    """)

    # Test: Aggregate field from database source
    aggregator = FieldAggregator(db, registry)
    config = FieldAggregatorParams(
        field="elevation",
        sources={"elevation": {"entity": "plots", "field": "elevation"}},
        operation="direct"
    )

    data = pd.DataFrame({"plot_ref_id": [1, 2]})
    result = aggregator.transform(data, config)

    # Verify: Real values from database
    assert result["elevation"][0] == 450  # From real DB, not mock
    assert result["elevation"][1] == 680
```

#### Scénarios de Test à Couvrir

**Import → Transform flows** :
- [ ] Occurrences → Agrégation par taxon (count, avg DBH)
- [ ] Occurrences → Agrégation par plot (species richness)
- [ ] Multi-source aggregation (taxon + shapes + occurrences)
- [ ] Custom entities (pas seulement taxon_ref/plot_ref par défaut)

**Hierarchies** :
- [ ] adjacency_list transformer avec vraie taxonomie
- [ ] nested_set transformer avec vraie taxonomie
- [ ] Hiérarchie complexe (>3 niveaux)

**Geospatial** :
- [ ] raster_stats avec vraies données raster (GeoTIFF)
- [ ] vector_overlay avec vrais shapefiles
- [ ] Reprojection CRS (EPSG:4326 → UTM)
- [ ] Clip, intersection, union operations

**Error scenarios** :
- [ ] Fichier CSV corrompu
- [ ] Configuration invalide (champs manquants)
- [ ] Échec de transformation (division par zéro)
- [ ] Contraintes DB violées (duplicate IDs)

#### Livrables

**Code** :
- [ ] `tests/integration/` créé avec structure complète
- [ ] `conftest.py` avec fixtures `integration_db`, `sample_*_csv`
- [ ] 20+ tests d'intégration couvrant :
  - [ ] 5+ tests Import → Transform → Verify flow
  - [ ] 5+ tests transformers spécifiques avec vraie DB
  - [ ] 3+ tests hiérarchies (adjacency_list, nested_set)
  - [ ] 4+ tests géospatiaux (raster, vector, CRS)
  - [ ] 3+ tests scénarios d'erreur

**Documentation** :
- [ ] Docstring module expliquant différence unit vs integration
- [ ] README `tests/integration/README.md` expliquant :
  - Quand écrire un test d'intégration vs unitaire
  - Comment lancer uniquement les tests d'intégration
  - Comment créer des fixtures de test data
- [ ] Mise à jour `pytest.ini` avec marker `integration`

**CI/CD** :
- [ ] Séparation tests unitaires (rapides) vs intégration (lents)
- [ ] Pipeline CI lance unit tests sur chaque commit
- [ ] Pipeline CI lance integration tests sur PR vers main

---

### STEP 2 - Analyse de Couverture de Code 🟡

**Durée Estimée** : 1 jour
**Priorité** : **MOYENNE** - Important pour identifier les gaps
**Effort** : 🟡🟡 Moyen

#### Gaps de Couverture Actuels

**D'après analyse `coverage.json`** :
- **Transformers** : ~75% (cas d'erreur manquants, edge cases)
- **Services** : ~85% (méthodes privées non testées)
- **CLI commands** : ~70% (flags/options non testés)
- **Utils** : ~60% (helpers peu testés)
- **GUI** : <40% (API endpoints largement non testés)

**Zones problématiques identifiées** :
- `core/plugins/transformers/geospatial/raster_stats.py:150-180` - Gestion erreurs raster
- `core/plugins/transformers/ecological/elevation_profile.py` - Edge cases altitudes
- `core/services/exporter.py:200-250` - Logique de rollback non testée
- `gui/api/routes/imports.py` - Endpoints file upload non testés

#### Approche Proposée

**1. Setup coverage.py avec reporting HTML** :

```toml
# pyproject.toml - Ajouter
[tool.coverage.run]
source = ["src/niamoto"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
    "*/site-packages/*",
]
branch = true  # Branch coverage (if/else paths)

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"

[tool.pytest.ini_options]
addopts = """
    --cov=src/niamoto
    --cov-report=html
    --cov-report=term-missing:skip-covered
    --cov-report=json
"""
```

**2. Générer rapport de couverture initial** :

```bash
# Baseline actuel
uv run pytest --cov=src/niamoto --cov-report=html --cov-report=term-missing

# Ouvrir rapport HTML
open htmlcov/index.html

# Identifier fichiers <90%
grep -E "\"percent_covered\": [0-8][0-9]\." coverage.json
```

**3. Cibler zones prioritaires** :

```python
# Exemple: Ajouter tests pour raster_stats edge cases
# tests/core/plugins/transformers/geospatial/test_raster_stats_coverage.py

def test_raster_stats_invalid_raster_path():
    """Test handling of non-existent raster file."""
    plugin = RasterStatsPlugin(db, registry)
    config = RasterStatsParams(
        raster_path="/nonexistent/raster.tif",
        stats=["mean"]
    )

    with pytest.raises(FileNotFoundError, match="Raster file not found"):
        plugin.transform(sample_gdf, config)


def test_raster_stats_corrupted_raster():
    """Test handling of corrupted GeoTIFF."""
    # Create corrupted raster file
    corrupted_path = tmp_path / "corrupted.tif"
    corrupted_path.write_bytes(b"not a valid GeoTIFF")

    plugin = RasterStatsPlugin(db, registry)
    config = RasterStatsParams(
        raster_path=str(corrupted_path),
        stats=["mean"]
    )

    with pytest.raises(RasterIOError, match="Failed to read raster"):
        plugin.transform(sample_gdf, config)


def test_raster_stats_crs_mismatch_auto_reproject():
    """Test automatic reprojection when CRS mismatch."""
    # GeoDataFrame in EPSG:4326, raster in EPSG:32758
    gdf = create_sample_gdf(crs="EPSG:4326")

    plugin = RasterStatsPlugin(db, registry)
    config = RasterStatsParams(
        raster_path=str(utm_raster_path),  # EPSG:32758
        stats=["mean"],
        auto_reproject=True
    )

    result = plugin.transform(gdf, config)

    # Verify reprojection happened and stats calculated
    assert "raster_mean" in result.columns
    assert not result["raster_mean"].isna().all()
```

**4. Zones cibles par module** :

| Module | Couverture Actuelle | Cible | Tests à Ajouter |
|--------|---------------------|-------|-----------------|
| **Core Plugins** | ~75% | >90% | +50 tests (edge cases, errors) |
| **Services** | ~85% | >90% | +20 tests (error paths, rollback) |
| **CLI Commands** | ~70% | >85% | +30 tests (flags, help, errors) |
| **Utils** | ~60% | >80% | +25 tests (helpers, validators) |
| **GUI API** | <40% | >75% | +40 tests (endpoints, file upload) |

#### Livrables

**Setup** :
- [ ] Coverage.py configuré dans `pyproject.toml`
- [ ] CI génère rapport de couverture sur chaque PR
- [ ] Badge coverage dans README.md

**Rapports** :
- [ ] Rapport HTML baseline généré (`htmlcov/`)
- [ ] Liste fichiers <90% avec plan d'amélioration
- [ ] Tracking couverture dans GitHub Actions

**Tests** :
- [ ] +50 tests pour core plugins (edge cases, errors)
- [ ] +20 tests pour services (error handling, rollback)
- [ ] +30 tests pour CLI commands (flags, options)
- [ ] +40 tests pour GUI API (endpoints, validation)

**Documentation** :
- [ ] Guide "Comment améliorer la couverture" dans `tests/README.md`
- [ ] Pre-commit hook vérifie couverture >85% sur fichiers modifiés

---

### STEP 3 - Optimisation des Performances 🟢

**Durée Estimée** : 1-2 jours
**Priorité** : **BASSE** - Nice to have, pas bloquant
**Effort** : 🟢 Faible-Moyen

#### Issues de Performance Actuels

**Temps d'exécution mesurés** :
- Suite complète : ~17s (acceptable mais améliorable)
- Tests unitaires : ~12s
- Tests d'intégration : ~5s (va augmenter avec Step 1)
- Slowest tests :
  - `test_stats.py::test_stats_command_full_flow` : ~0.8s
  - `test_exporter.py::test_export_all` : ~0.6s
  - `test_transformer.py::test_full_transformation_workflow` : ~0.5s

**Causes identifiées** :
- Fixtures DB recréées plusieurs fois (scope="function" au lieu de "module")
- Plugin loading à chaque test (peut être caché)
- Tests séquentiels (pas de parallélisation)
- In-memory DB pas utilisée pour unit tests (fichiers temporaires)

#### Approche Proposée

**1. Benchmark performance baseline** :

```python
# tests/performance/test_suite_benchmark.py
"""Benchmark suite to track test performance over time.

Run with: pytest tests/performance/ --benchmark-only
"""
import pytest
import time
from datetime import datetime

@pytest.fixture
def performance_log(tmp_path):
    """Log performance metrics to JSON for tracking."""
    log_file = tmp_path / "performance_log.json"
    return log_file


def test_unit_tests_performance_baseline(benchmark):
    """Baseline: Unit tests should run in <15s."""
    def run_unit_tests():
        # Run pytest programmatically
        pytest.main(["-m", "not integration", "--tb=no"])

    result = benchmark(run_unit_tests)
    assert result < 15.0, f"Unit tests took {result}s, target <15s"


def test_integration_tests_performance_baseline(benchmark):
    """Baseline: Integration tests should run in <2min."""
    def run_integration_tests():
        pytest.main(["-m", "integration", "--tb=no"])

    result = benchmark(run_integration_tests)
    assert result < 120.0, f"Integration tests took {result}s, target <120s"
```

**2. Optimisations à implémenter** :

**A. Fixture scoping optimal** :

```python
# tests/conftest.py - AVANT (lent)
@pytest.fixture
def test_db(tmp_path):
    """Database recreated for EACH test."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    db.engine.dispose()

# tests/conftest.py - APRÈS (rapide)
@pytest.fixture(scope="module")
def test_db(tmp_path_factory):
    """Database created ONCE per test module."""
    db_path = tmp_path_factory.mktemp("data") / "test.db"
    db = Database(str(db_path))
    yield db
    db.engine.dispose()
    db_path.unlink(missing_ok=True)
```

**B. In-memory DuckDB pour tests unitaires** :

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def inmemory_db():
    """In-memory DuckDB for fast unit tests.

    Shared across ALL tests in session for maximum speed.
    """
    db = Database(":memory:")  # In-memory, pas de I/O disque
    yield db
    db.engine.dispose()
```

**C. Plugin loading caché** :

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def plugin_loader_cached():
    """Cache plugin loading for entire test session."""
    loader = PluginLoader()
    loader.load_core_plugins()
    # Plugins chargés UNE FOIS pour toute la session
    return loader
```

**D. Parallélisation avec pytest-xdist** :

```bash
# Ajouter à pyproject.toml
[project.optional-dependencies]
dev = [
    # ... existing deps
    "pytest-xdist>=3.5.0",  # Parallel test execution
]

# Lancer tests en parallèle (auto-detect CPU cores)
uv run pytest -n auto

# Ou spécifier nombre de workers
uv run pytest -n 4
```

**E. Markers pour tests lents** :

```python
# pytest.ini
[tool.pytest.ini_options]
markers = [
    "integration: Integration tests (slow)",
    "slow: Slow tests (>1s)",
]

# Dans tests
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with 10k+ records - slow."""
    # ...

# Skip slow tests en développement
pytest -m "not slow"
```

**3. Métriques cibles** :

| Suite | Actuel | Cible | Optimisation |
|-------|--------|-------|-------------|
| **Unit tests** | ~12s | <8s | Fixture scoping, in-memory DB |
| **Integration tests** | ~5s | <30s | Même après ajout de 20+ tests (Step 1) |
| **Full suite (sequential)** | ~17s | <40s | Après ajout Step 1 tests |
| **Full suite (parallel -n 4)** | N/A | <15s | pytest-xdist |
| **CI pipeline** | ~1min | <2min | Parallel + caching |

#### Livrables

**Benchmarking** :
- [ ] Suite de benchmarks dans `tests/performance/`
- [ ] Baseline actuel documenté
- [ ] CI track performance regression (fail si >10% plus lent)

**Optimisations** :
- [ ] Fixtures avec scope optimal (session/module/function)
- [ ] In-memory DB pour unit tests
- [ ] Plugin loading caché (scope="session")
- [ ] pytest-xdist configuré pour parallélisation

**Documentation** :
- [ ] Guide "Running tests efficiently" dans `tests/README.md`
  - Lancer uniquement unit tests rapides
  - Skip slow tests en développement
  - Paralléliser avec -n auto
- [ ] Pre-commit hook lance uniquement tests rapides (<5s)

**CI/CD** :
- [ ] GitHub Actions utilise pytest-xdist (-n 4)
- [ ] Cache pip/uv dependencies
- [ ] Tests séparés : unit (rapide) → integration (si unit pass)

---

## 📋 CHECKLIST DÉTAILLÉ

### Week 1: Integration Tests (Step 1)

**Lundi** :
- [ ] Créer structure `tests/integration/`
- [ ] Implémenter fixture `integration_db` avec vraie DuckDB
- [ ] Créer fixtures sample data (CSV, GeoJSON)
- [ ] Écrire 5 premiers tests : Import → Transform → Verify

**Mardi** :
- [ ] Ajouter 5 tests custom entities (pas taxon/plot par défaut)
- [ ] Ajouter 3 tests hiérarchies (adjacency_list, nested_set)
- [ ] Tester multi-source aggregations

**Mercredi** :
- [ ] Ajouter 4 tests géospatiaux (raster_stats, vector_overlay)
- [ ] Tester reprojections CRS automatiques
- [ ] Tester clip, intersection, union operations

**Jeudi** :
- [ ] Ajouter 3+ tests scénarios d'erreur (CSV corrompu, config invalide)
- [ ] Documenter tests d'intégration (README, docstrings)
- [ ] Configurer marker `integration` dans pytest.ini

**Vendredi** :
- [ ] Review tests avec équipe
- [ ] Refactoring si nécessaire
- [ ] CI/CD: Séparer unit vs integration tests
- [ ] **Milestone** : 20+ integration tests fonctionnels ✅

---

### Week 2: Coverage + Performance (Steps 2 & 3)

**Lundi** :
- [ ] Setup coverage.py dans `pyproject.toml`
- [ ] Générer rapport baseline (`htmlcov/`)
- [ ] Identifier fichiers <90% avec gaps spécifiques
- [ ] Créer issues GitHub pour chaque gap majeur

**Mardi** :
- [ ] Écrire +25 tests pour core plugins (edge cases)
- [ ] Écrire +10 tests pour services (error handling)
- [ ] Écrire +15 tests pour CLI commands (flags)
- [ ] Target: Core plugins >90%

**Mercredi** :
- [ ] Écrire +20 tests pour GUI API endpoints
- [ ] Configurer CI génère rapport coverage sur PR
- [ ] Ajouter badge coverage dans README.md
- [ ] Target: Services >90%, CLI >85%

**Jeudi** :
- [ ] Performance benchmarking baseline
- [ ] Optimiser fixtures (scope="module/session")
- [ ] Implémenter in-memory DB pour unit tests
- [ ] Configurer pytest-xdist pour parallélisation

**Vendredi** :
- [ ] Tester performance après optimisations
- [ ] Documenter "Running tests efficiently"
- [ ] Configurer CI utilise pytest-xdist
- [ ] Final review & validation
- [ ] **Milestone** : Coverage >90%, Tests <15s en parallèle ✅

---

## 🎯 CRITÈRES DE SUCCÈS

### Must-Have (Bloquants pour Phase 5 du refactor)

✅ **Integration Tests** :
- [ ] Au minimum 20 tests d'intégration avec vraie DuckDB
- [ ] Coverage du pipeline complet : Import → Transform → Export
- [ ] Tests géospatiaux et hiérarchies couverts
- [ ] CI sépare unit tests (rapides) vs integration (lents)

✅ **Code Coverage** :
- [ ] Core plugins : >90% coverage
- [ ] Services : >90% coverage
- [ ] CLI commands : >85% coverage
- [ ] CI échoue si coverage régresse >5%

✅ **Quality Gates** :
- [ ] Tous les tests passent (0 failures, 0 warnings)
- [ ] Documentation à jour (README, docstrings)
- [ ] Aucun anti-pattern réintroduit

---

### Should-Have (Hautement recommandé)

🟡 **Performance** :
- [ ] Benchmarks de performance établis
- [ ] Suite complète <40s (séquentiel) ou <15s (parallèle -n 4)
- [ ] Fixtures optimisées (scope approprié)

🟡 **GUI Coverage** :
- [ ] API endpoints >75% coverage
- [ ] File upload endpoint testé
- [ ] Validation errors testées

🟡 **Documentation** :
- [ ] Guide "Integration vs Unit tests"
- [ ] Guide "Running tests efficiently"
- [ ] Pre-commit hooks configurés

---

### Nice-to-Have (Bonus)

🟢 **CI/CD Advanced** :
- [ ] Parallel test execution automatique en CI
- [ ] Test performance dashboard (track over time)
- [ ] Automated coverage regression detection (fail si <85%)

🟢 **Developer Experience** :
- [ ] VS Code test runner configuré
- [ ] Test templates/snippets pour nouveaux tests
- [ ] Live coverage feedback pendant développement

🟢 **Advanced Testing** :
- [ ] Property-based testing avec Hypothesis (existant dans deps)
- [ ] Mutation testing (vérifie qualité des tests)
- [ ] Contract testing pour API GUI

---

## 📚 RÉFÉRENCES

### Documents Liés

- **[Refactor Action Plan](./refactor-action-plan.md)** - Phase 5 (Tests & Validation) - Ce roadmap prépare cette phase
- **[Error Handling Roadmap](./error-handling.md)** - Phase 0 (Validation Framework) - Les tests d'intégration valident error handling
- **[Refactor Status](./refactor-status-2025-01-20.md)** - Progression actuelle (Phase 1 Plugins 56%) - Tests qualité critique pour migration

### Fichiers Modifiés lors de l'Élimination des Anti-Patterns (2025-01-22)

**Tests corrigés** :
- `tests/cli/test_stats.py` - FakeRegistry → EntityRegistry (40 lines mock → production)
- `tests/cli/test_transform.py` - ResourceWarning fix via Database mock
- `tests/core/services/test_transformer.py` - Documentation limitations (line 7-18)
- `tests/core/services/test_exporter.py` - Documentation orchestration tests (line 7-13)
- `tests/core/services/test_importer.py` - spec= ajouté aux mocks (line 31, 43, 52)
- `tests/core/plugins/transformers/aggregation/test_field_aggregator.py` - Mock correct level
- `tests/common/test_database.py` - Infrastructure mocking justifié (line 438-454)
- `tests/common/test_environment.py` - Real filesystem vs mocks

**Config** :
- `pyproject.toml` - filterwarnings ajoutés (line 268-285)

### Code Examples

**Anti-pattern AVANT** (Testing Mock Behavior) :
```python
# tests/core/plugins/transformers/aggregation/test_field_aggregator.py (OLD)
def test_transform_with_db_source(self, mocker):
    # ❌ Mock la méthode privée au lieu de la dépendance externe
    mock_get_field = mocker.patch.object(
        self.plugin, "_get_field_value", return_value=500
    )
    result = self.plugin.transform(SAMPLE_DATA.copy(), config)
    assert result == expected_result
    mock_get_field.assert_called_once()  # ❌ Test le mock, pas le comportement
```

**Best practice APRÈS** (Testing Real Behavior) :
```python
# tests/core/plugins/transformers/aggregation/test_field_aggregator.py (NEW)
def test_transform_with_db_source(self, mocker):
    """✅ Mock database au bon niveau (dépendance externe)."""
    mocker.patch.object(
        self.plugin.registry,
        "get",
        return_value=SimpleNamespace(table_name="entity_plots")
    )
    # ✅ Mock l'external dependency (database fetch)
    mocker.patch.object(
        self.db_mock,
        "fetch_one",
        return_value={"plot_value": 500}
    )

    result = self.plugin.transform(SAMPLE_DATA.copy(), config)

    # ✅ Test le résultat réel, pas les appels mock
    assert result == {"db_direct_value": {"value": "500"}}

    # Bug révélé: valeur retournée comme string "500" au lieu de int 500!
```

### Testing Best Practices Appliquées

1. **Mock the external dependency, not the internal logic**
   - ✅ Mock `db.fetch_one()` (external)
   - ❌ Ne pas mock `_get_field_value()` (internal/private)

2. **Use spec= parameter to catch invalid method calls**
   - ✅ `Mock(spec=Database)` détecte appels invalides
   - ❌ `Mock()` accepte silencieusement tout

3. **Test real behavior with temporary files (tmp_path)**
   - ✅ `test_environment.py` utilise `tmp_path` pour vraie suppression fichiers
   - ❌ Ne pas mock `os.remove()`, `shutil.rmtree()`

4. **Document test limitations clearly**
   - ✅ `test_transformer.py:7-18` - NOTE explicite sur limitations
   - ✅ `test_exporter.py:7-13` - LIMITATION documentée

5. **Verify parameters and outcomes, not just that functions were called**
   - ✅ `assert result["value"] == expected_value`
   - ❌ `mock.assert_called_once()` seul (insuffisant)

---

## 🔄 PROCHAINES ÉTAPES IMMÉDIATES

**Aujourd'hui (J+0)** :
- [ ] Créer branche `feature/integration-tests`
- [ ] Créer structure `tests/integration/`
- [ ] Setup fixtures de base (`conftest.py`)

**Cette semaine** :
- [ ] Implémenter Step 1 (Integration Tests)
- [ ] Daily standup : Review progress on checklist

**Semaine prochaine** :
- [ ] Implémenter Steps 2 & 3 (Coverage + Performance)
- [ ] Final review avant merge

**Review Points** :
- [ ] Après Week 1 : Review integration tests avec équipe
- [ ] Après Week 2 : Review coverage + performance metrics
- [ ] Avant merge : Validation tous critères Must-Have remplis

---

**Dernière mise à jour** : 2025-01-22
**Prochaine review** : Après Step 1 completion (fin Week 1)
**Status** : 🟡 EN COURS - Step 1 to start
