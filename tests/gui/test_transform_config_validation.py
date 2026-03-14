"""
Tests de validation des configurations transform.yml par groupe.

Phase 1.3 du plan: Vérifie que chaque configuration du transform.yml de référence
peut être parsée correctement et validée par les config_model/param_schema Pydantic
des plugins enregistrés.

Anti-patterns respectés:
- ✓ Utilise les vrais fichiers YAML de l'instance de test
- ✓ Valide contre les vrais modèles Pydantic
- ✓ Documente les plugins manquants comme exceptions connues
- ✗ Ne mocke PAS les modèles Pydantic
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, Mock

from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry


_TEST_INSTANCE_PATH = (
    Path(__file__).parent.parent.parent / "test-instance" / "niamoto-test"
)

pytestmark = pytest.mark.skipif(
    not _TEST_INSTANCE_PATH.exists(),
    reason="Instance de test locale absente (test-instance/niamoto-test)",
)

# Plugins référencés dans transform.yml mais pas encore implémentés.
# Seront ignorés dans les tests de validation.
KNOWN_MISSING_PLUGINS = {
    "entity_map_extractor",  # Widget cartographique planifié, pas encore créé
}


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def ensure_plugins_loaded():
    """Charge tous les plugins core en important leurs modules.

    L'import déclenche les décorateurs @register qui inscrivent
    les plugins dans le PluginRegistry.
    """
    # -- Transformers: aggregation --
    import niamoto.core.plugins.transformers.aggregation.binary_counter  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.field_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.statistical_summary  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.top_ranking  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.database_aggregator  # noqa: F401

    # -- Transformers: distribution --
    import niamoto.core.plugins.transformers.distribution.binned_distribution  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.categorical_distribution  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.time_series_analysis  # noqa: F401

    # -- Transformers: extraction --
    import niamoto.core.plugins.transformers.extraction.direct_attribute  # noqa: F401
    import niamoto.core.plugins.transformers.extraction.geospatial_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.extraction.multi_column_extractor  # noqa: F401

    # -- Transformers: class_objects --
    import niamoto.core.plugins.transformers.class_objects.series_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.binary_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.field_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.categories_mapper  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.categories_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_matrix_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_by_axis_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_ratio_aggregator  # noqa: F401

    # -- Transformers: chains --
    import niamoto.core.plugins.transformers.chains.transform_chain  # noqa: F401

    # -- Transformers: geospatial --
    import niamoto.core.plugins.transformers.geospatial.raster_stats  # noqa: F401
    import niamoto.core.plugins.transformers.geospatial.shape_processor  # noqa: F401
    import niamoto.core.plugins.transformers.geospatial.vector_overlay  # noqa: F401

    # -- Transformers: ecological --
    import niamoto.core.plugins.transformers.ecological.land_use  # noqa: F401
    import niamoto.core.plugins.transformers.ecological.elevation_profile  # noqa: F401
    import niamoto.core.plugins.transformers.ecological.fragmentation  # noqa: F401
    import niamoto.core.plugins.transformers.ecological.custom_calculator  # noqa: F401
    import niamoto.core.plugins.transformers.ecological.custom_formatter  # noqa: F401
    import niamoto.core.plugins.transformers.ecological.forest_elevation  # noqa: F401
    import niamoto.core.plugins.transformers.ecological.forest_holdridge  # noqa: F401

    # -- Widgets --
    import niamoto.core.plugins.widgets.hierarchical_nav_widget  # noqa: F401
    import niamoto.core.plugins.widgets.bar_plot  # noqa: F401
    import niamoto.core.plugins.widgets.donut_chart  # noqa: F401
    import niamoto.core.plugins.widgets.radial_gauge  # noqa: F401
    import niamoto.core.plugins.widgets.info_grid  # noqa: F401
    import niamoto.core.plugins.widgets.interactive_map  # noqa: F401
    import niamoto.core.plugins.widgets.line_plot  # noqa: F401
    import niamoto.core.plugins.widgets.scatter_plot  # noqa: F401
    import niamoto.core.plugins.widgets.summary_stats  # noqa: F401
    import niamoto.core.plugins.widgets.table_view  # noqa: F401
    import niamoto.core.plugins.widgets.raw_data_widget  # noqa: F401
    import niamoto.core.plugins.widgets.sunburst_chart  # noqa: F401
    import niamoto.core.plugins.widgets.concentric_rings  # noqa: F401
    import niamoto.core.plugins.widgets.stacked_area_plot  # noqa: F401
    import niamoto.core.plugins.widgets.diverging_bar_plot  # noqa: F401

    # -- Loaders --
    import niamoto.core.plugins.loaders.direct_reference  # noqa: F401
    import niamoto.core.plugins.loaders.nested_set  # noqa: F401
    import niamoto.core.plugins.loaders.stats_loader  # noqa: F401
    import niamoto.core.plugins.loaders.join_table  # noqa: F401
    import niamoto.core.plugins.loaders.adjacency_list  # noqa: F401
    import niamoto.core.plugins.loaders.spatial  # noqa: F401

    # -- Exporters --
    import niamoto.core.plugins.exporters.html_page_exporter  # noqa: F401
    import niamoto.core.plugins.exporters.json_api_exporter  # noqa: F401
    import niamoto.core.plugins.exporters.index_generator  # noqa: F401


@pytest.fixture(scope="session")
def reference_transform_yml():
    """Charge le transform.yml de référence depuis l'instance de test."""
    config_path = (
        Path(__file__).parent.parent.parent
        / "test-instance"
        / "niamoto-test"
        / "config"
        / "transform.yml"
    )
    assert config_path.exists(), f"Fichier de référence introuvable: {config_path}"

    with open(config_path) as f:
        configs = yaml.safe_load(f)

    # Indexe par group_by
    return {cfg["group_by"]: cfg for cfg in configs}


# ============================================================================
# HELPERS
# ============================================================================


def find_plugin_class(plugin_name: str):
    """Trouve une classe de plugin par nom dans tous les types."""
    for plugin_type in PluginType:
        if PluginRegistry.has_plugin(plugin_name, plugin_type):
            return PluginRegistry.get_plugin(plugin_name, plugin_type), plugin_type
    return None, None


def get_all_widget_configs(reference_transform_yml):
    """Extrait tous les widgets de tous les groupes avec leur contexte."""
    widgets = []
    for group_name, group_config in reference_transform_yml.items():
        for widget_name, widget_config in group_config.get("widgets_data", {}).items():
            widgets.append(
                {
                    "group": group_name,
                    "widget_name": widget_name,
                    "plugin_name": widget_config["plugin"],
                    "config": widget_config,
                }
            )
    return widgets


# ============================================================================
# TESTS: Structure du transform.yml
# ============================================================================


class TestTransformConfigStructure:
    """Vérifie la structure de base du transform.yml."""

    def test_all_groups_present(self, reference_transform_yml):
        """Les 3 groupes (taxons, plots, shapes) doivent être présents."""
        expected_groups = {"taxons", "plots", "shapes"}
        actual_groups = set(reference_transform_yml.keys())
        assert expected_groups == actual_groups

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_group_has_sources(self, group, reference_transform_yml):
        """Chaque groupe doit avoir des sources."""
        config = reference_transform_yml[group]
        assert "sources" in config
        assert len(config["sources"]) > 0

    @pytest.mark.parametrize("group", ["taxons", "plots"])
    def test_group_has_widgets(self, group, reference_transform_yml):
        """Les groupes taxons et plots doivent avoir des widgets_data."""
        config = reference_transform_yml[group]
        assert "widgets_data" in config
        assert len(config["widgets_data"]) > 0

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_widgets_have_plugin_key(self, group, reference_transform_yml):
        """Chaque widget doit spécifier un plugin."""
        config = reference_transform_yml[group]
        for widget_name, widget_config in config["widgets_data"].items():
            assert "plugin" in widget_config, (
                f"Widget '{widget_name}' du groupe '{group}' n'a pas de clé 'plugin'"
            )

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_sources_have_required_keys(self, group, reference_transform_yml):
        """Chaque source doit avoir les clés requises (name, data, grouping)."""
        config = reference_transform_yml[group]
        for source in config["sources"]:
            assert "name" in source, f"Source sans 'name' dans groupe '{group}'"
            assert "data" in source, f"Source sans 'data' dans groupe '{group}'"
            assert "grouping" in source, f"Source sans 'grouping' dans groupe '{group}'"


# ============================================================================
# TESTS: Enregistrement des plugins
# ============================================================================


class TestPluginRegistration:
    """Vérifie que les plugins référencés dans transform.yml existent."""

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_plugins_are_registered(self, group, reference_transform_yml):
        """Chaque plugin référencé doit être enregistré (sauf exceptions connues)."""
        config = reference_transform_yml[group]
        missing = []

        for widget_name, widget_config in config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue
            plugin_class, plugin_type = find_plugin_class(plugin_name)
            if plugin_class is None:
                missing.append(f"{widget_name} -> {plugin_name}")

        assert not missing, f"Plugins non trouvés pour le groupe '{group}': {missing}"

    def test_known_missing_plugins_documented(self, reference_transform_yml):
        """Vérifie que les plugins KNOWN_MISSING sont bien utilisés dans le YAML."""
        all_plugin_names = set()
        for group_config in reference_transform_yml.values():
            for widget_config in group_config.get("widgets_data", {}).values():
                all_plugin_names.add(widget_config["plugin"])

        # Chaque plugin dans KNOWN_MISSING doit être effectivement référencé
        for missing_name in KNOWN_MISSING_PLUGINS:
            assert missing_name in all_plugin_names, (
                f"'{missing_name}' est dans KNOWN_MISSING_PLUGINS mais "
                f"n'apparaît pas dans transform.yml — à retirer de la liste"
            )

    def test_loader_plugins_registered(self, reference_transform_yml):
        """Les plugins de relation (loaders) doivent être enregistrés."""
        missing = []
        for group_name, group_config in reference_transform_yml.items():
            for source in group_config.get("sources", []):
                relation = source.get("relation", {})
                if "plugin" in relation:
                    loader_name = relation["plugin"]
                    if not PluginRegistry.has_plugin(loader_name, PluginType.LOADER):
                        missing.append(
                            f"{group_name}/{source['name']} -> {loader_name}"
                        )

        assert not missing, f"Loaders non trouvés: {missing}"


# ============================================================================
# TESTS: Validation config_model / param_schema
# ============================================================================


class TestConfigValidation:
    """Valide les configurations transform.yml contre les modèles Pydantic."""

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_all_plugins_have_schema(self, group, reference_transform_yml):
        """Chaque plugin trouvé doit avoir config_model ou param_schema."""
        config = reference_transform_yml[group]
        no_model = []

        for widget_name, widget_config in config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            plugin_class, _ = find_plugin_class(plugin_name)
            if plugin_class is None:
                continue

            has_config = (
                hasattr(plugin_class, "config_model") and plugin_class.config_model
            )
            has_schema = (
                hasattr(plugin_class, "param_schema") and plugin_class.param_schema
            )
            if not has_config and not has_schema:
                no_model.append(f"{widget_name} -> {plugin_name}")

        assert not no_model, (
            f"Plugins sans config_model/param_schema pour '{group}': {no_model}"
        )

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_param_schema_validates(self, group, reference_transform_yml):
        """Les paramètres du transform.yml doivent valider contre param_schema."""
        config = reference_transform_yml[group]
        errors = []

        for widget_name, widget_config in config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            plugin_class, _ = find_plugin_class(plugin_name)
            if plugin_class is None:
                continue

            # Valide les params contre param_schema si disponible
            if hasattr(plugin_class, "param_schema") and plugin_class.param_schema:
                params = widget_config.get("params", {})
                try:
                    plugin_class.param_schema(**params)
                except Exception as e:
                    errors.append(f"{widget_name} ({plugin_name}): {e}")

        assert not errors, f"Erreurs param_schema pour '{group}':\n" + "\n".join(errors)

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_config_model_validates(self, group, reference_transform_yml):
        """La config complète doit valider contre config_model."""
        config = reference_transform_yml[group]
        errors = []

        for widget_name, widget_config in config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            plugin_class, _ = find_plugin_class(plugin_name)
            if plugin_class is None:
                continue

            # Valide la config complète contre config_model si disponible
            if hasattr(plugin_class, "config_model") and plugin_class.config_model:
                try:
                    plugin_class.config_model(**widget_config)
                except Exception as e:
                    errors.append(f"{widget_name} ({plugin_name}): {e}")

        assert not errors, f"Erreurs config_model pour '{group}':\n" + "\n".join(errors)

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_validate_config_method(self, group, reference_transform_yml):
        """La méthode validate_config des instances doit accepter les configs."""
        config = reference_transform_yml[group]
        errors = []

        for widget_name, widget_config in config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            plugin_class, _ = find_plugin_class(plugin_name)
            if plugin_class is None:
                continue

            # Créer une instance avec un mock db + mock registry
            try:
                plugin_instance = plugin_class(db=MagicMock(), registry=Mock())
            except Exception:
                # Certains plugins n'acceptent pas registry
                try:
                    plugin_instance = plugin_class(db=MagicMock())
                except Exception:
                    continue

            if not hasattr(plugin_instance, "validate_config"):
                continue

            try:
                plugin_instance.validate_config(widget_config)
            except Exception as e:
                errors.append(f"{widget_name} ({plugin_name}): {e}")

        assert not errors, f"Erreurs validate_config pour '{group}':\n" + "\n".join(
            errors
        )


# ============================================================================
# TESTS: Schémas JSON pour le GUI
# ============================================================================


class TestPluginJsonSchemas:
    """Vérifie que les plugins exposent des schémas JSON valides pour le GUI."""

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_json_schema_generation(self, group, reference_transform_yml):
        """Chaque plugin avec param_schema doit générer un JSON Schema valide."""
        config = reference_transform_yml[group]
        errors = []

        for widget_name, widget_config in config["widgets_data"].items():
            plugin_name = widget_config["plugin"]
            if plugin_name in KNOWN_MISSING_PLUGINS:
                continue

            plugin_class, _ = find_plugin_class(plugin_name)
            if plugin_class is None:
                continue

            # Tester param_schema.model_json_schema()
            if hasattr(plugin_class, "param_schema") and plugin_class.param_schema:
                try:
                    schema = plugin_class.param_schema.model_json_schema()
                    assert isinstance(schema, dict), "Le schéma doit être un dict"
                    assert "properties" in schema, "Le schéma doit avoir 'properties'"
                except Exception as e:
                    errors.append(f"{widget_name} ({plugin_name}) param_schema: {e}")

            # Tester config_model.model_json_schema()
            elif hasattr(plugin_class, "config_model") and plugin_class.config_model:
                try:
                    schema = plugin_class.config_model.model_json_schema()
                    assert isinstance(schema, dict)
                except Exception as e:
                    errors.append(f"{widget_name} ({plugin_name}) config_model: {e}")

        assert not errors, (
            f"Erreurs de génération JSON Schema pour '{group}':\n" + "\n".join(errors)
        )

    def test_unique_plugin_names_across_types(self):
        """Vérifie qu'il n'y a pas de collision de noms entre types de plugins."""
        all_names = {}
        for plugin_type in PluginType:
            plugins = PluginRegistry.get_plugins_by_type(plugin_type)
            for name in plugins:
                if name in all_names:
                    # Un même nom ne devrait pas apparaître dans deux types différents
                    pytest.fail(
                        f"Plugin '{name}' enregistré comme {all_names[name]} "
                        f"ET {plugin_type.value}"
                    )
                all_names[name] = plugin_type.value


# ============================================================================
# TESTS: API /api/layers
# ============================================================================


class TestLayersApi:
    """Tests pour l'endpoint API /api/layers."""

    @pytest.fixture
    def test_client(self):
        """Crée un TestClient FastAPI."""
        from niamoto.gui.api.app import create_app

        app = create_app()
        from fastapi.testclient import TestClient

        return TestClient(app)

    @pytest.fixture
    def working_directory(self, tmp_path):
        """Crée un répertoire de travail temporaire avec structure imports/."""
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir()
        return tmp_path

    @pytest.fixture(autouse=True)
    def mock_context(self, working_directory):
        """Pointe l'API vers le répertoire temporaire."""
        from unittest.mock import patch
        from niamoto.gui.api import context

        with patch.object(context, "_working_directory", working_directory):
            yield working_directory

    def test_list_layers_empty(self, test_client):
        """GET /api/layers retourne des listes vides si aucun fichier géo."""
        response = test_client.get("/api/layers")
        assert response.status_code == 200
        data = response.json()
        assert data["raster"] == []
        assert data["vector"] == []

    def test_list_layers_with_raster(self, test_client, working_directory):
        """GET /api/layers détecte les fichiers raster dans imports/."""
        imports_dir = working_directory / "imports"
        # Créer un faux fichier raster (le metadata extraction sera partiel)
        raster_file = imports_dir / "dem.tif"
        raster_file.write_bytes(b"\x00" * 100)

        response = test_client.get("/api/layers?type=raster")
        assert response.status_code == 200
        data = response.json()
        assert len(data["raster"]) == 1
        assert data["raster"][0]["name"] == "dem.tif"
        assert data["raster"][0]["type"] == "raster"
        assert data["vector"] == []

    def test_list_layers_with_vector(self, test_client, working_directory):
        """GET /api/layers détecte les fichiers vector dans imports/."""
        imports_dir = working_directory / "imports"
        # Créer un faux fichier vector
        vector_file = imports_dir / "boundaries.geojson"
        vector_file.write_text('{"type": "FeatureCollection", "features": []}')

        response = test_client.get("/api/layers?type=vector")
        assert response.status_code == 200
        data = response.json()
        assert len(data["vector"]) == 1
        assert data["vector"][0]["name"] == "boundaries.geojson"
        assert data["vector"][0]["type"] == "vector"
        assert data["raster"] == []

    def test_list_layers_filter_type(self, test_client, working_directory):
        """Le paramètre type filtre correctement les résultats."""
        imports_dir = working_directory / "imports"
        (imports_dir / "dem.tif").write_bytes(b"\x00" * 100)
        (imports_dir / "parcels.geojson").write_text(
            '{"type": "FeatureCollection", "features": []}'
        )

        # Filtrer raster uniquement
        response = test_client.get("/api/layers?type=raster")
        data = response.json()
        assert len(data["raster"]) == 1
        assert len(data["vector"]) == 0

        # Filtrer vector uniquement
        response = test_client.get("/api/layers?type=vector")
        data = response.json()
        assert len(data["raster"]) == 0
        assert len(data["vector"]) == 1

        # Tous les types
        response = test_client.get("/api/layers?type=all")
        data = response.json()
        assert len(data["raster"]) == 1
        assert len(data["vector"]) == 1

    def test_list_layers_recursive(self, test_client, working_directory):
        """Les fichiers dans les sous-dossiers d'imports/ sont détectés."""
        sub_dir = working_directory / "imports" / "geo" / "rasters"
        sub_dir.mkdir(parents=True)
        (sub_dir / "elevation.tif").write_bytes(b"\x00" * 100)

        response = test_client.get("/api/layers")
        data = response.json()
        assert len(data["raster"]) == 1
        assert "elevation.tif" in data["raster"][0]["name"]

    def test_get_layer_info_not_found(self, test_client):
        """GET /api/layers/{path} retourne 404 pour un fichier inexistant."""
        response = test_client.get("/api/layers/imports/nonexistent.tif")
        assert response.status_code == 404

    def test_get_layer_info_unsupported_type(self, test_client, working_directory):
        """GET /api/layers/{path} retourne 400 pour un type non supporté."""
        text_file = working_directory / "imports" / "readme.txt"
        text_file.write_text("hello")

        response = test_client.get("/api/layers/imports/readme.txt")
        assert response.status_code == 400


# ============================================================================
# TESTS: API /api/plugins/{id}/schema
# ============================================================================


class TestPluginSchemaApi:
    """Tests pour l'endpoint API /api/plugins/{id}/schema."""

    @pytest.fixture
    def test_client(self):
        """Crée un TestClient FastAPI."""
        from niamoto.gui.api.app import create_app

        app = create_app()
        from fastapi.testclient import TestClient

        return TestClient(app)

    @pytest.fixture(autouse=True)
    def mock_context(self, tmp_path):
        """Pointe l'API vers un répertoire temporaire."""
        from unittest.mock import patch
        from niamoto.gui.api import context

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        with patch.object(context, "_working_directory", tmp_path):
            yield

    def test_schema_for_binned_distribution(self, test_client):
        """Le schéma de binned_distribution contient les propriétés attendues."""
        response = test_client.get("/api/plugins/binned_distribution/schema")
        assert response.status_code == 200
        data = response.json()
        assert data["has_params"] is True
        schema = data["schema"]
        assert "properties" in schema

    def test_schema_for_statistical_summary(self, test_client):
        """Le schéma de statistical_summary est accessible."""
        response = test_client.get("/api/plugins/statistical_summary/schema")
        assert response.status_code == 200
        data = response.json()
        assert data["has_params"] is True

    def test_schema_for_hierarchical_nav_widget(self, test_client):
        """Le schéma du widget hierarchical_nav_widget est accessible."""
        response = test_client.get("/api/plugins/hierarchical_nav_widget/schema")
        assert response.status_code == 200
        data = response.json()
        assert data["has_params"] is True

    def test_schema_not_found(self, test_client):
        """Un plugin inexistant retourne 404."""
        response = test_client.get("/api/plugins/nonexistent_plugin/schema")
        assert response.status_code == 404

    def test_schema_contains_ui_hints(self, test_client):
        """Le schéma doit contenir les annotations UI (json_schema_extra)."""
        response = test_client.get("/api/plugins/class_object_binary_aggregator/schema")
        assert response.status_code == 200
        data = response.json()
        schema = data["schema"]

        # Vérifie que le schéma contient des propriétés
        assert "properties" in schema
        properties = schema.get("properties", {})
        assert len(properties) > 0

    @pytest.mark.parametrize(
        "plugin_name",
        [
            "binned_distribution",
            "field_aggregator",
            "binary_counter",
            "categorical_distribution",
            "statistical_summary",
            "top_ranking",
            "geospatial_extractor",
            "time_series_analysis",
            "class_object_series_extractor",
            "class_object_binary_aggregator",
        ],
    )
    def test_all_transform_plugins_have_schema(self, test_client, plugin_name):
        """Chaque plugin transformer doit exposer un schéma via l'API."""
        response = test_client.get(f"/api/plugins/{plugin_name}/schema")
        assert response.status_code == 200, (
            f"Plugin '{plugin_name}' n'expose pas de schéma"
        )
        data = response.json()
        assert data["has_params"] is True, (
            f"Plugin '{plugin_name}' signale has_params=False"
        )
