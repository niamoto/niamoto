from pathlib import Path

import yaml

from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.gui.api.services.templates.utils import widget_utils


def test_parse_dynamic_template_id_supports_regular_transformers():
    widget_utils._transformer_names = None
    widget_utils._widget_names = None
    PluginLoader().load_plugins_with_cascade()

    assert "binned_distribution" in widget_utils._get_transformer_names()
    assert widget_utils.parse_dynamic_template_id(
        "basal_area_binned_distribution_bar_plot"
    ) == {
        "column": "basal_area",
        "transformer": "binned_distribution",
        "widget": "bar_plot",
    }


def test_map_transformer_to_widget_supports_reference_enrichment_profile():
    assert (
        widget_utils.map_transformer_to_widget(
            "reference_enrichment_profile",
            "taxons_gbif_reference_enrichment_profile_enrichment_panel",
        )
        == "enrichment_panel"
    )


def test_generate_widget_title_applies_transformer_conventions():
    assert (
        widget_utils.generate_widget_title(
            "basal_area_top_ranking_bar_plot",
            "top_ranking",
            {"field": "basal_area", "count": 5},
        )
        == "Top 5 - Basal Area"
    )
    assert (
        widget_utils.generate_widget_title(
            "dbh_binned_distribution_bar_plot",
            "binned_distribution",
            {"field": "dbh"},
        )
        == "Dbh distribution"
    )
    assert (
        widget_utils.generate_widget_title(
            "tree_nav",
            "hierarchical_nav_widget",
            {"referential_data": "taxons"},
        )
        == "Navigation - Taxons"
    )


def test_generate_widget_params_for_binned_distribution_uses_transform_labels():
    params = widget_utils.generate_widget_params(
        "bar_plot",
        "binned_distribution",
        {"x_label": "DBH class", "y_label": "Trees"},
    )

    assert params["transform"] == "bins_to_df"
    assert params["transform_params"]["percentage_field"] == "percentages"
    assert params["x_axis"] == "bin"
    assert params["y_axis"] == "count"
    assert params["labels"] == {"bin": "DBH class", "count": "Trees"}


def test_generate_widget_params_for_series_extractor_respects_overrides():
    params = widget_utils.generate_widget_params(
        "bar_plot",
        "class_object_series_extractor",
        {
            "size_field": {"output": "classes"},
            "value_field": {"output": "values"},
            "orientation": "v",
            "x_axis": "classes",
            "y_axis": "values",
            "sort_order": "ascending",
            "auto_color": False,
            "gradient_color": "#0f766e",
            "gradient_mode": "saturation",
            "show_legend": True,
        },
    )

    assert params == {
        "orientation": "v",
        "x_axis": "classes",
        "y_axis": "values",
        "sort_order": "ascending",
        "gradient_color": "#0f766e",
        "gradient_mode": "saturation",
        "show_legend": True,
    }


def test_generate_widget_params_handles_gauge_and_navigation_defaults():
    assert widget_utils.generate_widget_params(
        "radial_gauge",
        "statistical_summary",
        {},
    ) == {
        "stat_to_display": "mean",
        "show_range": True,
        "auto_range": True,
    }

    assert widget_utils.generate_widget_params(
        "hierarchical_nav_widget",
        "hierarchical_nav_widget",
        {
            "referential_data": "taxons",
            "id_field": "id_taxon",
            "name_field": "full_name",
            "base_url": "/taxons",
            "show_search": False,
            "lft_field": "lft",
            "rght_field": "rght",
            "level_field": "rank_name",
            "parent_id_field": "parent_id",
        },
    ) == {
        "referential_data": "taxons",
        "id_field": "id_taxon",
        "name_field": "full_name",
        "base_url": "/taxons",
        "show_search": False,
        "lft_field": "lft",
        "rght_field": "rght",
        "level_field": "rank_name",
        "parent_id_field": "parent_id",
    }


def test_is_class_object_template_and_invalid_dynamic_ids():
    assert widget_utils.is_class_object_template("series_extractor") is True
    assert widget_utils.is_class_object_template("top_ranking") is False
    assert widget_utils.parse_dynamic_template_id("bar_plot") is None
    assert widget_utils.parse_dynamic_template_id("missing_widget_suffix") is None


def test_find_widget_group_supports_list_and_dict_formats(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "plots",
                    "widgets_data": {"plot_widget": {"plugin": "field_aggregator"}},
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(widget_utils, "get_working_directory", lambda: tmp_path)
    assert widget_utils.find_widget_group("plot_widget") == "plots"

    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            {
                "groups": {
                    "taxons": {
                        "widgets_data": {
                            "taxon_widget": {"plugin": "categorical_distribution"}
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    assert widget_utils.find_widget_group("taxon_widget") == "taxons"
    assert widget_utils.find_widget_group("missing_widget") is None


def test_load_configured_widget_reads_nested_transform_and_export_override(
    tmp_path, monkeypatch
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            {
                "groups": {
                    "plots": {
                        "widgets_data": {
                            "gauge_1": {
                                "plugin": "field_aggregator",
                                "params": {
                                    "transformer": {
                                        "plugin": "class_object_field_aggregator",
                                        "params": {
                                            "source": "plot_stats",
                                            "field": "biomass",
                                        },
                                    },
                                    "widget": {
                                        "plugin": "radial_gauge",
                                        "params": {"max_value": 100},
                                    },
                                    "title": "Transform Biomass",
                                },
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "groups": [
                            {
                                "group_by": "plots",
                                "widgets": [
                                    {
                                        "data_source": "gauge_1",
                                        "plugin": "radial_gauge",
                                        "title": "Export Biomass",
                                        "params": {"min_value": 0},
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(widget_utils, "get_working_directory", lambda: tmp_path)

    result = widget_utils.load_configured_widget("gauge_1", "plots")

    assert result == {
        "transformer_plugin": "class_object_field_aggregator",
        "transformer_params": {"source": "plot_stats", "field": "biomass"},
        "widget_plugin": "radial_gauge",
        "widget_params": {"min_value": 0},
        "widget_title": "Export Biomass",
        "widget_id": "gauge_1",
    }


def test_load_widget_params_from_export_supports_legacy_group_lists(
    tmp_path, monkeypatch
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "groups": [
                    {
                        "group_by": "plots",
                        "widgets": [
                            {
                                "data_source": "geo_pt_geospatial_extractor_interactive_map",
                                "params": {"custom_tiles_url": "https://tiles.example"},
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(widget_utils, "get_working_directory", lambda: Path(tmp_path))

    assert widget_utils.load_widget_params_from_export(
        "geo_pt_geospatial_extractor_interactive_map", "plots"
    ) == {"custom_tiles_url": "https://tiles.example"}
