"""Unit tests for suggestion_service helper resolution logic."""

import json
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pandas as pd

from niamoto.common.database import Database
from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.imports.registry import EntityKind, EntityRegistry
from niamoto.core.imports.widget_generator import WidgetSuggestion
from niamoto.gui.api.services.templates.suggestion_service import (
    _REFERENCE_FIELD_SUGGESTIONS_CACHE,
    _build_reference_field_cache_key,
    _get_first_dataset_name,
    _pick_identifier_column,
    _pick_name_column,
    _resolve_entity_table,
    _should_profile_reference_field,
    get_reference_enrichment_catalog,
    get_reference_enrichment_suggestions,
    get_reference_field_suggestions,
)


class _Kind(str, Enum):
    REFERENCE = "reference"
    DATASET = "dataset"


@dataclass
class _EntityMeta:
    name: str
    kind: _Kind
    table_name: str
    config: Dict[str, Any]


class _DummyRegistry:
    def __init__(
        self,
        metadata: Optional[Dict[str, _EntityMeta]] = None,
        datasets: Optional[List[_EntityMeta]] = None,
    ):
        self.metadata = metadata or {}
        self.datasets = datasets or []

    def get(self, name: str) -> _EntityMeta:
        if name not in self.metadata:
            raise KeyError(name)
        return self.metadata[name]

    def list_entities(self, kind: Optional[Any] = None) -> List[_EntityMeta]:
        return list(self.datasets)


class _DummyDb:
    def __init__(self, existing_tables: List[str]):
        self.existing_tables = set(existing_tables)

    def has_table(self, table_name: str) -> bool:
        return table_name in self.existing_tables


def test_resolve_entity_table_prefers_registry_mapping():
    db = _DummyDb(existing_tables=["custom_reference_table", "entity_taxons"])
    registry = _DummyRegistry(
        metadata={
            "taxons": _EntityMeta(
                name="taxons",
                kind=_Kind.REFERENCE,
                table_name="custom_reference_table",
                config={},
            )
        }
    )

    resolved = _resolve_entity_table(db, "taxons", registry=registry, kind="reference")

    assert resolved == "custom_reference_table"


def test_resolve_entity_table_fallback_conventions_for_reference():
    db = _DummyDb(existing_tables=["entity_plots"])

    resolved = _resolve_entity_table(db, "plots", registry=None, kind="reference")

    assert resolved == "entity_plots"


def test_pick_identifier_and_name_columns():
    columns = ["plot_uuid", "display_label", "description"]

    id_field = _pick_identifier_column(
        columns, entity_name="plots", preferred="plot_uuid"
    )
    name_field = _pick_name_column(columns, id_field, "plots")

    assert id_field == "plot_uuid"
    assert name_field == "display_label"


def test_get_first_dataset_name_prefers_registry():
    registry = _DummyRegistry(
        datasets=[
            _EntityMeta(
                name="observations",
                kind=_Kind.DATASET,
                table_name="dataset_observations",
                config={},
            )
        ]
    )
    import_config = {"entities": {"datasets": {"occurrences": {}}}}

    dataset = _get_first_dataset_name(import_config, registry=registry)

    assert dataset == "observations"


def test_should_profile_reference_field_skips_technical_columns():
    assert not _should_profile_reference_field("parent_id", pd.Series([1, 2, 3]))
    assert not _should_profile_reference_field("created_at", pd.Series(["a", "b"]))
    assert not _should_profile_reference_field(
        "geometry", pd.Series([b"\x00\x01", b"\x00\x02"])
    )


def test_should_profile_reference_field_keeps_useful_columns():
    assert _should_profile_reference_field(
        "full_name", pd.Series(["Araucaria columnaris", "Amborella trichopoda"])
    )


def test_build_reference_field_cache_key_tracks_project_state(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir()

    db_path = db_dir / "niamoto.duckdb"
    import_path = config_dir / "import.yml"
    db_path.write_text("", encoding="utf-8")
    import_path.write_text("entities: {}", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_working_directory",
        lambda: work_dir,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_database_path",
        lambda: db_path,
    )

    key1 = _build_reference_field_cache_key("taxons")
    import_path.write_text("entities: {references: {taxons: {}}}", encoding="utf-8")
    key2 = _build_reference_field_cache_key("taxons")

    assert key1 is not None
    assert key2 is not None
    assert key1 != key2


def _prepare_reference_project(
    tmp_path,
    *,
    frame: pd.DataFrame,
    entity_name: str = "plots",
    table_name: str = "entity_plots",
    entity_config: Optional[Dict[str, Any]] = None,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        "version: '1.0'\nentities:\n  references: {}\n",
        encoding="utf-8",
    )

    db_path = project_dir / "niamoto.db"
    db = Database(str(db_path), optimize=False)
    frame.to_sql(table_name, db.engine, if_exists="replace", index=False)

    registry = EntityRegistry(db)
    registry.register_entity(
        name=entity_name,
        kind=EntityKind.REFERENCE,
        table_name=table_name,
        config=entity_config
        or {
            "schema": {
                "id_field": "id_plot",
                "fields": [{"name": "geo_pt", "type": "geometry"}],
            }
        },
    )
    db.close_db_session()
    return project_dir, db_path


def test_reference_field_suggestions_use_fast_path_without_ml(monkeypatch, tmp_path):
    _REFERENCE_FIELD_SUGGESTIONS_CACHE.clear()
    project_dir, db_path = _prepare_reference_project(
        tmp_path,
        frame=pd.DataFrame(
            {
                "id_plot": [1, 2, 3],
                "plot": ["Plot A", "Plot B", "Plot C"],
                "geo_pt": ["POINT(1 1)", "POINT(2 2)", "POINT(3 3)"],
                "elevation": [100.0, 120.0, 140.0],
                "holdridge": ["humid", "dry", "humid"],
                "in_um": [1, 0, 1],
            }
        ),
    )

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_working_directory",
        lambda: project_dir,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_database_path",
        lambda: db_path,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service._build_reference_field_cache_key",
        lambda reference_name: ("cache-test", reference_name, "db", 1, 1),
    )

    def _fail_profile(*args, **kwargs):
        raise AssertionError(
            "ML profiling should not run for clear internal references"
        )

    monkeypatch.setattr(
        "niamoto.core.imports.profiler.DataProfiler.profile_dataframe",
        _fail_profile,
    )

    suggestions = get_reference_field_suggestions("plots")

    matched_columns = {suggestion["matched_column"] for suggestion in suggestions}
    assert matched_columns == {"elevation", "holdridge", "in_um"}
    assert all(suggestion["source"] == "reference" for suggestion in suggestions)
    assert all(suggestion["source_name"] == "plots" for suggestion in suggestions)


def test_reference_field_suggestions_fallback_ml_only_on_ambiguous_columns(
    monkeypatch, tmp_path
):
    _REFERENCE_FIELD_SUGGESTIONS_CACHE.clear()
    project_dir, db_path = _prepare_reference_project(
        tmp_path,
        frame=pd.DataFrame(
            {
                "id_plot": [1, 2, 3],
                "plot": ["Plot A", "Plot B", "Plot C"],
                "elevation": [100.0, 120.0, 140.0],
                "odd_mix": ["10", "unknown", "30"],
            }
        ),
    )

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_working_directory",
        lambda: project_dir,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_database_path",
        lambda: db_path,
    )

    captured_columns: List[str] = []

    def _fake_profile(self, profile_df, path):
        captured_columns.extend(profile_df.columns.tolist())
        return SimpleNamespace(
            columns=[
                SimpleNamespace(
                    name="odd_mix",
                    dtype="object",
                    semantic_type=None,
                    unique_ratio=0.66,
                    null_ratio=0.0,
                    sample_values=["10", "unknown", "30"],
                    confidence=0.6,
                )
            ]
        )

    def _fake_enrich(self, col_profile, series):
        return EnrichedColumnProfile(
            name=col_profile.name,
            dtype="object",
            semantic_type=None,
            unique_ratio=0.66,
            null_ratio=0.0,
            sample_values=["10", "unknown", "30"],
            confidence=0.7,
            data_category=DataCategory.CATEGORICAL_HIGH_CARD,
            field_purpose=FieldPurpose.CLASSIFICATION,
            cardinality=3,
        )

    def _fake_generate(self, profiles, source_table="occurrences"):
        assert [profile.name for profile in profiles] == ["odd_mix"]
        return [
            WidgetSuggestion(
                id="odd_mix_top_ranking_bar_plot",
                name="Top Odd Mix",
                description="Most frequent values of odd_mix",
                transformer_plugin="top_ranking",
                widget_plugin="bar_plot",
                widget_type="chart",
                category="chart",
                icon="BarChart3",
                column="odd_mix",
                confidence=0.7,
                transformer_config={
                    "source": source_table,
                    "field": "odd_mix",
                    "mode": "direct",
                    "count": 10,
                },
                widget_params={"x_axis": "counts", "y_axis": "tops"},
                source_name=source_table,
            )
        ]

    monkeypatch.setattr(
        "niamoto.core.imports.profiler.DataProfiler.profile_dataframe",
        _fake_profile,
    )
    monkeypatch.setattr(
        "niamoto.core.imports.data_analyzer.DataAnalyzer.enrich_profile",
        _fake_enrich,
    )
    monkeypatch.setattr(
        "niamoto.core.imports.widget_generator.WidgetGenerator.generate_for_columns",
        _fake_generate,
    )

    suggestions = get_reference_field_suggestions("plots")

    assert captured_columns == ["odd_mix"]
    assert any(
        suggestion["matched_column"] == "elevation" for suggestion in suggestions
    )
    assert any(suggestion["matched_column"] == "odd_mix" for suggestion in suggestions)


def test_reference_field_suggestions_cache_skips_second_ml_pass(monkeypatch, tmp_path):
    _REFERENCE_FIELD_SUGGESTIONS_CACHE.clear()
    project_dir, db_path = _prepare_reference_project(
        tmp_path,
        frame=pd.DataFrame(
            {
                "id_plot": [1, 2, 3],
                "plot": ["Plot A", "Plot B", "Plot C"],
                "odd_mix": ["10", "unknown", "30"],
            }
        ),
    )

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_working_directory",
        lambda: project_dir,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_database_path",
        lambda: db_path,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service._build_reference_field_cache_key",
        lambda reference_name: ("cache-test", reference_name, "db", 1, 1),
    )

    calls = {"profile": 0}

    def _fake_profile(self, profile_df, path):
        calls["profile"] += 1
        return SimpleNamespace(
            columns=[
                SimpleNamespace(
                    name="odd_mix",
                    dtype="object",
                    semantic_type=None,
                    unique_ratio=0.66,
                    null_ratio=0.0,
                    sample_values=["10", "unknown", "30"],
                    confidence=0.6,
                )
            ]
        )

    def _fake_enrich(self, col_profile, series):
        return EnrichedColumnProfile(
            name=col_profile.name,
            dtype="object",
            semantic_type=None,
            unique_ratio=0.66,
            null_ratio=0.0,
            sample_values=["10", "unknown", "30"],
            confidence=0.7,
            data_category=DataCategory.CATEGORICAL_HIGH_CARD,
            field_purpose=FieldPurpose.CLASSIFICATION,
            cardinality=3,
        )

    def _fake_generate(self, profiles, source_table="occurrences"):
        return [
            WidgetSuggestion(
                id="odd_mix_top_ranking_bar_plot",
                name="Top Odd Mix",
                description="Most frequent values of odd_mix",
                transformer_plugin="top_ranking",
                widget_plugin="bar_plot",
                widget_type="chart",
                category="chart",
                icon="BarChart3",
                column="odd_mix",
                confidence=0.7,
                transformer_config={
                    "source": source_table,
                    "field": "odd_mix",
                    "mode": "direct",
                    "count": 10,
                },
                widget_params={"x_axis": "counts", "y_axis": "tops"},
                source_name=source_table,
            )
        ]

    monkeypatch.setattr(
        "niamoto.core.imports.profiler.DataProfiler.profile_dataframe",
        _fake_profile,
    )
    monkeypatch.setattr(
        "niamoto.core.imports.data_analyzer.DataAnalyzer.enrich_profile",
        _fake_enrich,
    )
    monkeypatch.setattr(
        "niamoto.core.imports.widget_generator.WidgetGenerator.generate_for_columns",
        _fake_generate,
    )

    get_reference_field_suggestions("plots")
    get_reference_field_suggestions("plots")

    assert calls["profile"] == 1


def test_reference_enrichment_suggestions_build_one_panel_per_source(
    monkeypatch, tmp_path
):
    project_dir, db_path = _prepare_reference_project(
        tmp_path,
        frame=pd.DataFrame(
            {
                "id_plot": [1, 2],
                "plot": ["Plot A", "Plot B"],
                "extra_data": [
                    json.dumps(
                        {
                            "api_enrichment": {
                                "sources": {
                                    "gbif": {
                                        "label": "GBIF",
                                        "status": "completed",
                                        "data": {
                                            "match": {
                                                "canonical_name": "Araucaria columnaris",
                                                "rank": "SPECIES",
                                                "status": "ACCEPTED",
                                            },
                                            "occurrence_summary": {
                                                "occurrence_count": 42,
                                                "datasets_count": 4,
                                            },
                                            "links": {
                                                "species": "https://www.gbif.org/species/2685484"
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    ),
                    json.dumps(
                        {
                            "api_enrichment": {
                                "sources": {
                                    "gbif": {
                                        "label": "GBIF",
                                        "status": "completed",
                                        "data": {
                                            "match": {
                                                "canonical_name": "Agathis ovata",
                                                "rank": "SPECIES",
                                                "status": "ACCEPTED",
                                            },
                                            "occurrence_summary": {
                                                "occurrence_count": 12,
                                                "datasets_count": 2,
                                            },
                                        },
                                    },
                                    "custom-source": {
                                        "label": "Custom source",
                                        "status": "completed",
                                        "data": {
                                            "status": "verified",
                                            "reference_url": "https://example.org/resource",
                                        },
                                    },
                                }
                            }
                        }
                    ),
                ],
            }
        ),
    )

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_working_directory",
        lambda: project_dir,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_database_path",
        lambda: db_path,
    )

    suggestions = get_reference_enrichment_suggestions("plots")

    assert [suggestion["name"] for suggestion in suggestions] == [
        "Profil GBIF",
        "Profil Custom source",
    ]
    assert all(
        suggestion["plugin"] == "reference_enrichment_profile"
        for suggestion in suggestions
    )
    assert all(
        suggestion["widget_plugin"] == "enrichment_panel" for suggestion in suggestions
    )
    assert suggestions[1]["template_id"] == (
        "plots_custom_source_reference_enrichment_profile_enrichment_panel"
    )
    assert suggestions[0]["config"]["source"] == "plots"
    assert suggestions[0]["widget_params"]["summary_columns"] == 3
    assert suggestions[0]["config"]["summary_items"]
    assert suggestions[0]["config"]["sections"]


def test_reference_enrichment_catalog_returns_structured_fields(monkeypatch, tmp_path):
    project_dir, db_path = _prepare_reference_project(
        tmp_path,
        frame=pd.DataFrame(
            {
                "id_plot": [1],
                "plot": ["Plot A"],
                "extra_data": [
                    json.dumps(
                        {
                            "api_enrichment": {
                                "sources": {
                                    "gbif": {
                                        "label": "GBIF",
                                        "status": "completed",
                                        "data": {
                                            "match": {
                                                "canonical_name": "Araucaria columnaris",
                                                "status": "ACCEPTED",
                                            },
                                            "links": {
                                                "species": "https://www.gbif.org/species/2685484"
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    )
                ],
            }
        ),
    )

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_working_directory",
        lambda: project_dir,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.get_database_path",
        lambda: db_path,
    )

    catalogs = get_reference_enrichment_catalog("plots")

    assert [catalog["label"] for catalog in catalogs] == ["GBIF"]
    assert catalogs[0]["field_count"] >= 2
    assert any(
        field["path"] == "match.canonical_name" for field in catalogs[0]["fields"]
    )
    assert any(field["format"] == "link" for field in catalogs[0]["fields"])
