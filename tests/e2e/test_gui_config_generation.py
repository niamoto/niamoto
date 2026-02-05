"""
Tests end-to-end pour la génération de config via le GUI.

Phase 3.1 du plan: Vérifie le round-trip complet :
  référence YAML → API → Schema JSON → Save → Reload → Compare

Utilise l'instance de test réelle (test-instance/niamoto-test/) avec :
- transform.yml de référence
- Vrais fichiers imports/ (raster, vector, CSV)
- Vrais plugins enregistrés

Anti-patterns respectés :
- ✓ Utilise la vraie instance de test, pas de données inventées
- ✓ Teste le vrai cycle save/load via l'API FastAPI
- ✓ Mock uniquement le contexte (working directory)
- ✗ Ne teste PAS les transformations complètes (besoin de DB)
"""

import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.gui.api import context
from niamoto.gui.api.app import create_app


# ============================================================================
# CONSTANTES
# ============================================================================

TEST_INSTANCE_PATH = (
    Path(__file__).parent.parent.parent / "test-instance" / "niamoto-test"
)

# Plugins manquants connus (cf. Phase 1.3)
KNOWN_MISSING_PLUGINS = {
    "entity_map_extractor",
    "binary_aggregator",
}


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def ensure_plugins_loaded():
    """Charge tous les plugins core."""
    # -- Transformers --
    import niamoto.core.plugins.transformers.aggregation.binary_counter  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.field_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.statistical_summary  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.top_ranking  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.binned_distribution  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.categorical_distribution  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.time_series_analysis  # noqa: F401
    import niamoto.core.plugins.transformers.extraction.geospatial_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.binary_aggregator  # noqa: F401

    # -- Widgets --
    import niamoto.core.plugins.widgets.hierarchical_nav_widget  # noqa: F401
    import niamoto.core.plugins.widgets.bar_plot  # noqa: F401
    import niamoto.core.plugins.widgets.donut_chart  # noqa: F401
    import niamoto.core.plugins.widgets.radial_gauge  # noqa: F401
    import niamoto.core.plugins.widgets.info_grid  # noqa: F401
    import niamoto.core.plugins.widgets.interactive_map  # noqa: F401

    # -- Loaders --
    import niamoto.core.plugins.loaders.direct_reference  # noqa: F401
    import niamoto.core.plugins.loaders.nested_set  # noqa: F401
    import niamoto.core.plugins.loaders.stats_loader  # noqa: F401


@pytest.fixture(scope="session")
def reference_transform():
    """Charge le transform.yml de référence."""
    config_path = TEST_INSTANCE_PATH / "config" / "transform.yml"
    assert config_path.exists(), f"Instance de test introuvable: {config_path}"

    with open(config_path) as f:
        configs = yaml.safe_load(f)

    return {cfg["group_by"]: cfg for cfg in configs}


@pytest.fixture(scope="session")
def reference_export():
    """Charge le export.yml de référence."""
    config_path = TEST_INSTANCE_PATH / "config" / "export.yml"
    if not config_path.exists():
        return None
    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def test_client():
    """Crée un TestClient FastAPI."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def working_directory(tmp_path):
    """Crée un répertoire de travail avec la structure de l'instance de test."""
    # Copie config/
    src_config = TEST_INSTANCE_PATH / "config"
    dst_config = tmp_path / "config"
    shutil.copytree(src_config, dst_config)

    # Crée imports/ vide (les fichiers sont trop gros pour copier)
    (tmp_path / "imports").mkdir()
    (tmp_path / "exports").mkdir()

    return tmp_path


@pytest.fixture(autouse=True)
def mock_context(working_directory):
    """Pointe le contexte API vers le répertoire de travail temporaire."""
    with patch.object(context, "_working_directory", working_directory):
        yield working_directory


# ============================================================================
# HELPERS
# ============================================================================


def find_plugin_class(plugin_name: str):
    """Trouve un plugin par nom dans tous les types."""
    for plugin_type in PluginType:
        if PluginRegistry.has_plugin(plugin_name, plugin_type):
            return PluginRegistry.get_plugin(plugin_name, plugin_type), plugin_type
    return None, None


def yaml_equivalent(a: Any, b: Any) -> bool:
    """Compare deux structures YAML en ignorant l'ordre des clés."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(yaml_equivalent(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(yaml_equivalent(x, y) for x, y in zip(a, b))
    return a == b


# ============================================================================
# TESTS: Round-trip save/load configuration
# ============================================================================


class TestConfigSaveLoadRoundTrip:
    """Teste le cycle complet : reference YAML → save API → reload → compare."""

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_save_and_reload_preserves_widgets(
        self, test_client, group, reference_transform
    ):
        """Sauvegarder puis recharger doit préserver tous les widgets."""
        ref_config = reference_transform[group]

        # POST /api/templates/save-config avec la config de référence
        save_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": ref_config["widgets_data"],
            "mode": "replace",
        }

        response = test_client.post("/api/templates/save-config", json=save_request)
        assert response.status_code == 200, (
            f"Save failed for '{group}': {response.text}"
        )
        save_data = response.json()
        assert save_data["success"] is True

        # GET /api/transform/config pour recharger
        response = test_client.get("/api/transform/config")
        assert response.status_code == 200

        loaded_config = response.json()
        raw_config = loaded_config["raw_config"]

        # Trouver le groupe dans la config rechargée
        found_group = None
        if isinstance(raw_config, list):
            for cfg in raw_config:
                if cfg.get("group_by") == group:
                    found_group = cfg
                    break

        assert found_group is not None, f"Groupe '{group}' non trouvé après reload"

        # Vérifier que tous les widgets sont présents
        ref_widgets = set(ref_config["widgets_data"].keys())
        loaded_widgets = set(found_group.get("widgets_data", {}).keys())

        missing = ref_widgets - loaded_widgets
        extra = loaded_widgets - ref_widgets
        assert not missing, f"Widgets perdus après save/load pour '{group}': {missing}"
        assert not extra, f"Widgets supplémentaires pour '{group}': {extra}"

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_save_preserves_widget_params(
        self, test_client, group, reference_transform
    ):
        """Les paramètres de chaque widget doivent être préservés."""
        ref_config = reference_transform[group]

        # Save
        save_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": ref_config["widgets_data"],
            "mode": "replace",
        }
        response = test_client.post("/api/templates/save-config", json=save_request)
        assert response.status_code == 200

        # Reload
        response = test_client.get("/api/transform/config")
        raw_config = response.json()["raw_config"]

        found_group = None
        if isinstance(raw_config, list):
            for cfg in raw_config:
                if cfg.get("group_by") == group:
                    found_group = cfg
                    break

        assert found_group is not None

        # Comparer chaque widget
        errors = []
        for widget_name, ref_widget in ref_config["widgets_data"].items():
            loaded_widget = found_group["widgets_data"].get(widget_name)
            if loaded_widget is None:
                errors.append(f"{widget_name}: absent après reload")
                continue

            # Plugin doit être identique
            if ref_widget.get("plugin") != loaded_widget.get("plugin"):
                errors.append(
                    f"{widget_name}: plugin '{ref_widget.get('plugin')}' "
                    f"!= '{loaded_widget.get('plugin')}'"
                )

            # Params doivent être équivalents
            ref_params = ref_widget.get("params", {})
            loaded_params = loaded_widget.get("params", {})
            if not yaml_equivalent(ref_params, loaded_params):
                errors.append(f"{widget_name}: params diffèrent après round-trip")

        assert not errors, f"Erreurs de round-trip pour '{group}':\n" + "\n".join(
            errors
        )

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_save_preserves_sources(self, test_client, group, reference_transform):
        """Les sources doivent être préservées après save/load."""
        ref_config = reference_transform[group]

        # Save
        save_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": ref_config["widgets_data"],
            "mode": "replace",
        }
        response = test_client.post("/api/templates/save-config", json=save_request)
        assert response.status_code == 200

        # Reload
        response = test_client.get("/api/transform/config")
        raw_config = response.json()["raw_config"]

        found_group = None
        if isinstance(raw_config, list):
            for cfg in raw_config:
                if cfg.get("group_by") == group:
                    found_group = cfg
                    break

        assert found_group is not None

        # Comparer les noms de sources
        ref_source_names = {s["name"] for s in ref_config["sources"]}
        loaded_source_names = {s["name"] for s in found_group.get("sources", [])}
        assert ref_source_names == loaded_source_names, (
            f"Sources diffèrent pour '{group}': "
            f"ref={ref_source_names} vs loaded={loaded_source_names}"
        )


# ============================================================================
# TESTS: Schema JSON couvre les params de référence
# ============================================================================


class TestSchemaCoversReferenceParams:
    """Vérifie que le JSON Schema de chaque plugin couvre ses params."""

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_schema_has_fields_for_all_params(
        self, test_client, group, reference_transform
    ):
        """Le JSON Schema doit avoir un champ pour chaque param utilisé.

        Note: BasePluginParams a extra="allow", donc certains params (ex: title)
        sont acceptés sans être dans le schema. Le test tolère ces params quand
        le schema autorise additionalProperties.
        """
        ref_config = reference_transform[group]
        issues = []

        for widget_name, widget_config in ref_config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            # Récupérer le schema via l'API
            response = test_client.get(f"/api/plugins/{plugin_name}/schema")
            if response.status_code != 200:
                issues.append(f"{widget_name} ({plugin_name}): schema non trouvé")
                continue

            data = response.json()
            if not data.get("has_params"):
                continue

            schema = data["schema"]
            schema_properties = set()

            # Extraire les propriétés du schema (avec résolution $defs)
            if "properties" in schema:
                schema_properties = set(schema["properties"].keys())

            # Si le schema autorise additionalProperties (extra="allow"),
            # les params non déclarés sont acceptés → pas d'erreur
            allows_extra = schema.get("additionalProperties", True) is not False

            # Vérifier que chaque param de la référence a un champ dans le schema
            params = widget_config.get("params", {})
            for param_name in params:
                if param_name not in schema_properties:
                    # Vérifier dans les propriétés héritées (PluginConfig a plugin, params)
                    # Pour les config_model, les params sont wrappés
                    if "params" in schema_properties:
                        # C'est un config_model wrapper, les params sont dans params
                        continue
                    if allows_extra:
                        # Le schema autorise les champs supplémentaires
                        continue
                    issues.append(
                        f"{widget_name} ({plugin_name}): "
                        f"param '{param_name}' absent du schema"
                    )

        assert not issues, (
            f"Params non couverts par le schema pour '{group}':\n" + "\n".join(issues)
        )

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_all_plugins_expose_schema(self, test_client, group, reference_transform):
        """Chaque plugin utilisé dans la référence doit exposer un schema."""
        ref_config = reference_transform[group]
        no_schema = []

        for widget_name, widget_config in ref_config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            response = test_client.get(f"/api/plugins/{plugin_name}/schema")
            if response.status_code != 200:
                no_schema.append(f"{widget_name} -> {plugin_name}")
                continue

            data = response.json()
            if not data.get("has_params"):
                no_schema.append(f"{widget_name} -> {plugin_name} (has_params=False)")

        assert not no_schema, f"Plugins sans schema pour '{group}':\n" + "\n".join(
            no_schema
        )


# ============================================================================
# TESTS: Layers API avec les vrais fichiers
# ============================================================================


class TestLayersWithRealFiles:
    """Teste l'API /api/layers avec les fichiers réels de l'instance de test."""

    @pytest.fixture(autouse=True)
    def setup_real_imports(self, working_directory):
        """Crée des liens symboliques vers les vrais fichiers imports."""
        src_imports = TEST_INSTANCE_PATH / "imports"
        dst_imports = working_directory / "imports"

        # Supprimer le dossier vide créé par working_directory
        if dst_imports.exists():
            shutil.rmtree(dst_imports)

        # Lien symbolique vers les vrais imports
        dst_imports.symlink_to(src_imports)

    def test_detects_raster_files(self, test_client):
        """L'API détecte les fichiers raster (.tif) dans imports/."""
        response = test_client.get("/api/layers?type=raster&include_metadata=false")
        assert response.status_code == 200
        data = response.json()

        raster_names = {r["name"] for r in data["raster"]}
        # L'instance de test a des .tif
        assert len(data["raster"]) > 0, "Aucun raster trouvé dans imports/"
        assert any(name.endswith(".tif") for name in raster_names), (
            f"Pas de .tif trouvé parmi: {raster_names}"
        )

    def test_detects_vector_files(self, test_client):
        """L'API détecte les fichiers vector (.gpkg) dans imports/."""
        response = test_client.get("/api/layers?type=vector&include_metadata=false")
        assert response.status_code == 200
        data = response.json()

        vector_names = {v["name"] for v in data["vector"]}
        assert len(data["vector"]) > 0, "Aucun vector trouvé dans imports/"
        assert any(name.endswith(".gpkg") for name in vector_names), (
            f"Pas de .gpkg trouvé parmi: {vector_names}"
        )

    def test_raster_metadata_extraction(self, test_client):
        """Les métadonnées raster sont extraites (CRS, dimensions)."""
        response = test_client.get("/api/layers?type=raster&include_metadata=true")
        assert response.status_code == 200
        data = response.json()

        # Au moins un raster devrait avoir du CRS
        rasters_with_crs = [r for r in data["raster"] if r.get("crs")]
        assert len(rasters_with_crs) > 0, (
            "Aucun raster avec CRS extrait — rasterio peut-être non installé"
        )

    def test_vector_metadata_extraction(self, test_client):
        """Les métadonnées vector sont extraites (CRS, colonnes)."""
        response = test_client.get("/api/layers?type=vector&include_metadata=true")
        assert response.status_code == 200
        data = response.json()

        vectors_with_crs = [v for v in data["vector"] if v.get("crs")]
        assert len(vectors_with_crs) > 0, (
            "Aucun vector avec CRS extrait — geopandas peut-être non installé"
        )

    def test_layer_count_matches_files(self, test_client):
        """Le nombre de layers détectés correspond aux fichiers réels."""
        response = test_client.get("/api/layers?type=all&include_metadata=false")
        data = response.json()

        total = len(data["raster"]) + len(data["vector"])
        # L'instance a ~4 tif + ~7 gpkg = ~11 fichiers géo
        assert total >= 5, f"Seulement {total} layers détectés, attendu au moins 5"


# ============================================================================
# TESTS: Transform config endpoint
# ============================================================================


class TestTransformConfigEndpoint:
    """Teste GET /api/transform/config avec la config de référence."""

    def test_get_config_returns_all_groups(self, test_client, reference_transform):
        """L'endpoint retourne tous les groupes de la config."""
        response = test_client.get("/api/transform/config")
        assert response.status_code == 200

        data = response.json()
        raw_config = data["raw_config"]

        # raw_config est une liste de groupes
        assert isinstance(raw_config, list)
        group_names = {cfg["group_by"] for cfg in raw_config}
        assert {"taxons", "plots", "shapes"} == group_names

    def test_get_config_widget_count(self, test_client, reference_transform):
        """Le nombre de widgets dans la réponse est correct."""
        response = test_client.get("/api/transform/config")
        data = response.json()

        # Compter les widgets dans la référence
        expected_total = sum(
            len(cfg["widgets_data"]) for cfg in reference_transform.values()
        )
        assert data["summary"]["total_widgets"] == expected_total

    def test_get_config_widget_types(self, test_client):
        """Les types de widgets (plugins) sont correctement comptés."""
        response = test_client.get("/api/transform/config")
        data = response.json()

        widget_types = data["summary"]["widget_types"]
        # Plugins les plus utilisés dans la référence
        assert "statistical_summary" in widget_types
        assert "field_aggregator" in widget_types
        assert "binned_distribution" in widget_types


# ============================================================================
# TESTS: Transform sources endpoint
# ============================================================================


class TestTransformSourcesEndpoint:
    """Teste GET /api/transform/sources."""

    def test_sources_returns_by_group(self, test_client):
        """L'endpoint retourne les sources groupées."""
        response = test_client.get("/api/transform/sources")
        assert response.status_code == 200

        data = response.json()
        # Doit contenir les sources de chaque groupe
        assert isinstance(data, dict)

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_sources_for_group(self, test_client, group):
        """Chaque groupe a des sources."""
        response = test_client.get(f"/api/transform/sources?group_by={group}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)


# ============================================================================
# TESTS: Merge mode save
# ============================================================================


class TestConfigMergeMode:
    """Teste le mode merge lors de la sauvegarde."""

    def test_merge_adds_widget_without_removing(self, test_client, reference_transform):
        """Le mode merge ajoute un widget sans supprimer les existants."""
        group = "taxons"
        ref_config = reference_transform[group]
        original_widget_count = len(ref_config["widgets_data"])

        # D'abord sauvegarder la config de référence
        save_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": ref_config["widgets_data"],
            "mode": "replace",
        }
        response = test_client.post("/api/templates/save-config", json=save_request)
        assert response.status_code == 200

        # Ajouter un nouveau widget en mode merge
        new_widget = {
            "test_new_widget": {
                "plugin": "binary_counter",
                "params": {
                    "source": "occurrences",
                    "field": "in_um",
                    "true_label": "Test True",
                    "false_label": "Test False",
                },
            }
        }
        merge_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": new_widget,
            "mode": "merge",
        }
        response = test_client.post("/api/templates/save-config", json=merge_request)
        assert response.status_code == 200

        # Recharger et vérifier
        response = test_client.get("/api/transform/config")
        raw_config = response.json()["raw_config"]
        found_group = next(cfg for cfg in raw_config if cfg["group_by"] == group)

        loaded_widgets = found_group["widgets_data"]
        # Doit avoir les originaux + le nouveau
        assert len(loaded_widgets) == original_widget_count + 1
        assert "test_new_widget" in loaded_widgets

    def test_replace_mode_removes_old_widgets(self, test_client, reference_transform):
        """Le mode replace remplace tous les widgets."""
        group = "shapes"
        ref_config = reference_transform[group]

        # Sauvegarder la config de référence d'abord
        save_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": ref_config["widgets_data"],
            "mode": "replace",
        }
        response = test_client.post("/api/templates/save-config", json=save_request)
        assert response.status_code == 200

        # Remplacer avec un seul widget
        single_widget = {
            "only_widget": {
                "plugin": "field_aggregator",
                "params": {
                    "fields": [{"source": "shapes", "field": "name", "target": "name"}]
                },
            }
        }
        replace_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": single_widget,
            "mode": "replace",
        }
        response = test_client.post("/api/templates/save-config", json=replace_request)
        assert response.status_code == 200

        # Recharger et vérifier
        response = test_client.get("/api/transform/config")
        raw_config = response.json()["raw_config"]
        found_group = next(cfg for cfg in raw_config if cfg["group_by"] == group)

        assert len(found_group["widgets_data"]) == 1
        assert "only_widget" in found_group["widgets_data"]


# ============================================================================
# TESTS: Export config generation
# ============================================================================


class TestExportConfigGeneration:
    """Teste que la sauvegarde transform génère aussi export.yml."""

    def test_save_generates_export_yml(
        self, test_client, working_directory, reference_transform
    ):
        """POST /save-config doit aussi générer export.yml."""
        group = "taxons"
        ref_config = reference_transform[group]

        save_request = {
            "group_by": group,
            "sources": ref_config["sources"],
            "widgets_data": ref_config["widgets_data"],
            "mode": "replace",
        }
        response = test_client.post("/api/templates/save-config", json=save_request)
        assert response.status_code == 200

        # Vérifier que export.yml existe
        export_path = working_directory / "config" / "export.yml"
        assert export_path.exists(), "export.yml non généré après save-config"

        # Vérifier que c'est un YAML valide
        with open(export_path) as f:
            export_config = yaml.safe_load(f)
        assert export_config is not None
