# Scripts

Scripts utilitaires pour le développement et la maintenance de Niamoto.

## Structure

```
scripts/
├── build/    # Build et release
├── dev/      # Développement quotidien
├── data/     # Manipulation de données
├── debug/    # Tests manuels et debugging
├── ml/       # Machine Learning
└── utils/    # Utilitaires divers
```

## build/

Scripts de build, release et génération.

| Script | Description |
|--------|-------------|
| `build_gui.sh` | Build de l'interface GUI React |
| `build_tailwind_standalone.py` | Build Tailwind CSS (sans npm) |
| `publish.sh` | Publication sur PyPI |
| `generate_changelog.py` | Génération du changelog |
| `generate_requirements.py` | Génération des requirements.txt |

## dev/

Scripts pour le développement quotidien.

| Script | Description |
|--------|-------------|
| `dev_web.sh` | Lance l'environnement de dev web (API + frontend Vite) |
| `dev_api.py` | Lance uniquement l'API FastAPI en mode dev |
| `dev_desktop.sh` | Lance l'application desktop (Tauri) |
| `smart_commit.sh` | Commit automatisé avec pre-commit hooks |

**Usage courant :**
```bash
# Lancer l'environnement de développement web
./scripts/dev/dev_web.sh test-instance/niamoto-nc
```

## data/

Scripts de manipulation et requêtage de données.

| Script | Description |
|--------|-------------|
| `query_db.py` | Requêtes SQL sur la base DuckDB |
| `create_shapefile.py` | Création de shapefiles |
| `shp_to_gpkg.py` | Conversion Shapefile → GeoPackage |
| `create_test_subset.py` | Création de sous-ensembles de test |

**Usage courant :**
```bash
# Requête SQL
uv run python scripts/data/query_db.py "SELECT * FROM taxon LIMIT 5"

# Mode interactif
uv run python scripts/data/query_db.py --interactive
```

## debug/

Scripts de test manuel et debugging (hors pytest).

| Script | Description |
|--------|-------------|
| `test_auto_detection.py` | Test de l'auto-détection de colonnes |
| `test_auto_suggestions.py` | Test des suggestions automatiques |
| `test_bootstrap.py` | Test du bootstrap |
| `test_pattern_matching.py` | Test du pattern matching |
| `trace_flow.py` | Traçage du flux d'exécution (pipeline transformer → widget) |

## ml/

Scripts liés au Machine Learning.

| Script | Description |
|--------|-------------|
| `collect_training_data.py` | Collecte de données d'entraînement |
| `train_column_detector.py` | Entraînement du détecteur de colonnes |

## utils/

Utilitaires divers.

| Script | Description |
|--------|-------------|
| `clean_magicmocks.py` | Nettoyage des MagicMocks dans les tests |
| `document_structure.py` | Documentation de la structure du projet |
| `run_tests_optimized.py` | Exécution optimisée des tests |
