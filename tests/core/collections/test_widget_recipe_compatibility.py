"""Tests for widget recipe compatibility classification."""

from __future__ import annotations

from niamoto.core.collections.widget_recipe_compatibility import (
    IncomingColumnProfile,
    IncomingDataProfile,
    WidgetRecipeCompatibilityService,
)


TRANSFORM_CONFIG = [
    {
        "group_by": "taxons",
        "sources": [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": "taxons",
                "relation": {
                    "plugin": "direct_reference",
                    "key": "taxon_id",
                    "ref_key": "id",
                },
            }
        ],
        "widgets_data": {
            "family_chart": {
                "plugin": "categorical_distribution",
                "params": {"source": "occurrences", "field": "family"},
            },
            "dbh_chart": {
                "plugin": "binned_distribution",
                "params": {"source": "occurrences", "field": "dbh_cm"},
            },
            "missing_chart": {
                "plugin": "top_ranking",
                "params": {"source": "occurrences", "field": "status"},
            },
        },
    }
]

EXPORT_CONFIG = {
    "exports": [
        {
            "exporter": "html_page_exporter",
            "groups": [
                {
                    "group_by": "taxons",
                    "widgets": [
                        {"data_source": "family_chart", "plugin": "donut_chart"},
                        {"data_source": "dbh_chart", "plugin": "bar_plot"},
                        {"data_source": "missing_chart", "plugin": "bar_plot"},
                    ],
                }
            ],
        }
    ]
}


def test_widget_recipe_compatibility_classifies_valid_degraded_and_broken():
    profile = IncomingDataProfile(
        columns={
            "family": IncomingColumnProfile(
                name="family",
                type="string",
                cardinality=42,
                coverage=1.0,
                label_max_length=18,
            ),
            "dbh_cm": IncomingColumnProfile(
                name="dbh_cm",
                type="float",
                cardinality=10,
                coverage=1.0,
            ),
            "new_habitat": IncomingColumnProfile(
                name="new_habitat",
                type="string",
                cardinality=4,
                coverage=0.9,
            ),
        }
    )
    service = WidgetRecipeCompatibilityService(
        transform_config=TRANSFORM_CONFIG,
        export_config=EXPORT_CONFIG,
    )

    report = service.classify("occurrences", profile)
    by_widget = {impact.widget_id: impact for impact in report.impacts}

    assert by_widget["family_chart"].status == "degraded"
    assert "donut" in by_widget["family_chart"].detail
    assert by_widget["dbh_chart"].status == "still_valid"
    assert by_widget["missing_chart"].status == "broken"
    assert by_widget["new:occurrences:new_habitat"].collection == "taxons"
    assert report.summary["newly_available"] == 1


def test_widget_recipe_compatibility_returns_unknown_without_profile_evidence():
    service = WidgetRecipeCompatibilityService(
        transform_config=TRANSFORM_CONFIG,
        export_config=EXPORT_CONFIG,
    )

    report = service.classify("occurrences", IncomingDataProfile(columns={}))

    assert {impact.status for impact in report.impacts} == {"unknown"}
    assert report.summary["unknown"] == 3


def test_field_aggregator_uses_per_field_sources_for_recipe_compatibility():
    transform_config = [
        {
            "group_by": "plots",
            "widgets_data": {
                "metrics": {
                    "plugin": "field_aggregator",
                    "params": {
                        "fields": [
                            {
                                "source": "plot_stats",
                                "field": "dbh_cm",
                                "target": "dbh",
                            },
                            {
                                "source": "shape_stats",
                                "field": "area_ha",
                                "target": "area",
                            },
                        ]
                    },
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "dbh_cm": IncomingColumnProfile(name="dbh_cm", type="float"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify("plot_stats", profile)

    assert [impact.widget_id for impact in report.impacts] == ["metrics"]
    assert report.impacts[0].status == "still_valid"


def test_class_object_recipe_requires_structural_columns_and_extractor_inputs():
    transform_config = [
        {
            "group_by": "plots",
            "widgets_data": {
                "elevation": {
                    "plugin": "class_object_series_extractor",
                    "params": {
                        "source": "shape_stats",
                        "class_object": "elevation",
                        "size_field": {"input": "class_name", "output": "tops"},
                        "value_field": {"input": "class_value", "output": "counts"},
                    },
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "class_object": IncomingColumnProfile(name="class_object", type="string"),
            "class_name": IncomingColumnProfile(name="class_name", type="string"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify("shape_stats", profile)

    assert report.impacts[0].status == "broken"
    assert report.impacts[0].affected_columns == ["class_value"]


def test_newly_available_ignores_columns_already_present_in_old_schema():
    profile = IncomingDataProfile(
        columns={
            "family": IncomingColumnProfile(
                name="family",
                type="string",
                cardinality=3,
                coverage=1.0,
            )
        }
    )
    service = WidgetRecipeCompatibilityService(
        transform_config=[],
        export_config={},
    )

    report = service.classify(
        "occurrences",
        profile,
        old_column_names={"family"},
    )

    assert report.summary["newly_available"] == 0


def test_widget_recipe_compatibility_tracks_direct_attribute_dependencies():
    transform_config = [
        {
            "group_by": "plots",
            "widgets_data": {
                "plot_area": {
                    "plugin": "direct_attribute",
                    "params": {"source": "plots", "field": "area_ha"},
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "name": IncomingColumnProfile(name="name", type="string"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify("plots", profile)

    assert report.impacts[0].status == "broken"
    assert report.impacts[0].affected_columns == ["area_ha"]


def test_widget_recipe_compatibility_tracks_time_series_dependencies():
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "phenology": {
                    "plugin": "time_series_analysis",
                    "params": {
                        "source": "occurrences",
                        "time_field": "month_obs",
                        "fields": {"flower": "has_flower"},
                        "value_fields": ["fruit_count"],
                    },
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "month_obs": IncomingColumnProfile(name="month_obs", type="integer"),
            "has_flower": IncomingColumnProfile(name="has_flower", type="integer"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify("occurrences", profile)

    assert report.impacts[0].status == "broken"
    assert report.impacts[0].affected_columns == ["fruit_count"]


def test_widget_recipe_compatibility_descends_into_transform_chain_steps():
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "phenology": {
                    "plugin": "transform_chain",
                    "params": {
                        "steps": [
                            {
                                "plugin": "time_series_analysis",
                                "params": {
                                    "source": "occurrences",
                                    "time_field": "month_obs",
                                    "fields": {"flower": "has_flower"},
                                    "value_fields": ["fruit_count"],
                                },
                                "output_key": "phenology_raw",
                            },
                            {
                                "plugin": "threshold_analysis",
                                "params": {
                                    "time_series": "@phenology_raw.month_data",
                                },
                                "output_key": "phenology_peaks",
                            },
                        ]
                    },
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "month_obs": IncomingColumnProfile(name="month_obs", type="integer"),
            "has_flower": IncomingColumnProfile(name="has_flower", type="integer"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify(
        "occurrences",
        profile,
        old_column_names={"month_obs", "has_flower"},
    )

    assert report.impacts[0].widget_id == "phenology"
    assert report.impacts[0].status == "broken"
    assert report.impacts[0].affected_columns == ["fruit_count"]


def test_widget_recipe_compatibility_uses_chain_source_for_steps_without_source():
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "phenology": {
                    "plugin": "transform_chain",
                    "params": {
                        "source": "occurrences",
                        "steps": [
                            {
                                "plugin": "time_series_analysis",
                                "params": {
                                    "time_field": "month_obs",
                                    "fields": {"flower": "has_flower"},
                                    "value_fields": ["fruit_count"],
                                },
                                "output_key": "phenology_raw",
                            },
                        ],
                    },
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "month_obs": IncomingColumnProfile(name="month_obs", type="integer"),
            "has_flower": IncomingColumnProfile(name="has_flower", type="integer"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify(
        "occurrences",
        profile,
        old_column_names={"month_obs", "has_flower"},
    )

    assert report.impacts[0].widget_id == "phenology"
    assert report.impacts[0].status == "broken"
    assert report.impacts[0].affected_columns == ["fruit_count"]


def test_top_ranking_readability_uses_ranked_field_not_aggregate_field():
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "top_species": {
                    "plugin": "top_ranking",
                    "params": {
                        "source": "occurrences",
                        "field": "z_species",
                        "aggregate_field": "a_count",
                    },
                }
            },
        }
    ]
    export_config = {
        "exports": [
            {
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [
                            {"data_source": "top_species", "plugin": "bar_plot"}
                        ],
                    }
                ]
            }
        ]
    }
    profile = IncomingDataProfile(
        columns={
            "a_count": IncomingColumnProfile(
                name="a_count",
                type="integer",
                cardinality=1,
                coverage=1.0,
            ),
            "z_species": IncomingColumnProfile(
                name="z_species",
                type="string",
                cardinality=80,
                coverage=1.0,
            ),
        }
    )
    service = WidgetRecipeCompatibilityService(
        transform_config=transform_config,
        export_config=export_config,
    )

    report = service.classify("occurrences", profile)

    assert report.impacts[0].status == "degraded"
    assert "cardinality is high" in report.impacts[0].detail


def test_widget_recipe_compatibility_reads_export_widgets_from_params_groups():
    export_config = {
        "exports": [
            {
                "exporter": "html_page_exporter",
                "params": {
                    "groups": [
                        {
                            "group_by": "taxons",
                            "widgets": [
                                {
                                    "data_source": "family_chart",
                                    "plugin": "donut_chart",
                                }
                            ],
                        }
                    ]
                },
            }
        ]
    }
    profile = IncomingDataProfile(
        columns={
            "family": IncomingColumnProfile(
                name="family",
                type="string",
                cardinality=42,
                coverage=1.0,
                label_max_length=18,
            )
        }
    )
    service = WidgetRecipeCompatibilityService(
        transform_config=TRANSFORM_CONFIG,
        export_config=export_config,
    )

    report = service.classify("occurrences", profile)
    by_widget = {impact.widget_id: impact for impact in report.impacts}

    assert by_widget["family_chart"].widget_plugin == "donut_chart"
    assert by_widget["family_chart"].status == "degraded"


def test_widget_recipe_compatibility_reads_top_level_simple_widget_fields():
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "top_families": {
                    "plugin": "top_ranking",
                    "source": "occurrences",
                    "field": "family",
                }
            },
        }
    ]
    profile = IncomingDataProfile(
        columns={
            "new_family": IncomingColumnProfile(name="new_family", type="string"),
        }
    )
    service = WidgetRecipeCompatibilityService(transform_config=transform_config)

    report = service.classify(
        "occurrences",
        profile,
        old_column_names={"family"},
    )

    assert report.impacts[0].widget_id == "top_families"
    assert report.impacts[0].status == "broken"
    assert report.impacts[0].affected_columns == ["family"]
    assert "new:occurrences:family" not in {
        impact.widget_id for impact in report.impacts
    }


def test_widget_recipe_compatibility_keys_export_widgets_by_collection():
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "summary": {
                    "plugin": "categorical_distribution",
                    "params": {"source": "occurrences", "field": "family"},
                }
            },
        },
        {
            "group_by": "plots",
            "widgets_data": {
                "summary": {
                    "plugin": "categorical_distribution",
                    "params": {"source": "occurrences", "field": "plot_type"},
                }
            },
        },
    ]
    export_config = {
        "exports": [
            {
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [
                            {"data_source": "summary", "plugin": "donut_chart"}
                        ],
                    },
                    {
                        "group_by": "plots",
                        "widgets": [{"data_source": "summary", "plugin": "bar_plot"}],
                    },
                ]
            }
        ]
    }
    profile = IncomingDataProfile(
        columns={
            "family": IncomingColumnProfile(
                name="family",
                type="string",
                cardinality=80,
                coverage=1.0,
                label_max_length=12,
            ),
            "plot_type": IncomingColumnProfile(
                name="plot_type",
                type="string",
                cardinality=20,
                coverage=1.0,
                label_max_length=12,
            ),
        }
    )
    service = WidgetRecipeCompatibilityService(
        transform_config=transform_config,
        export_config=export_config,
    )

    report = service.classify("occurrences", profile)
    by_collection = {impact.collection: impact for impact in report.impacts}

    assert by_collection["taxons"].widget_plugin == "donut_chart"
    assert by_collection["taxons"].status == "degraded"
    assert "too high for a readable donut chart" in by_collection["taxons"].detail
    assert by_collection["plots"].widget_plugin == "bar_plot"
    assert by_collection["plots"].status == "still_valid"
