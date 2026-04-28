"""Product-level benchmark scenarios for AutoConfigService."""

from __future__ import annotations

import shutil
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from niamoto.core.imports.auto_config_service import AutoConfigService


FIXTURES_DIR = Path(__file__).parents[2] / "gui" / "api" / "routers" / "fixtures"


def _copy_import_fixtures(tmp_path: Path, filenames: list[str]) -> Path:
    """Create a temporary imports directory populated with selected fixtures."""
    imports_dir = tmp_path / "imports"
    imports_dir.mkdir()

    for filename in filenames:
        shutil.copy(FIXTURES_DIR / filename, imports_dir / filename)

    return tmp_path


@pytest.fixture
def benchmark_service(tmp_path: Path) -> AutoConfigService:
    """Create an AutoConfigService rooted in a temporary working directory."""
    return AutoConfigService(tmp_path)


class TestAutoConfigServiceBenchmark:
    """Lock the expected product behavior on representative CSV scenarios."""

    def test_nominal_taxonomy_scenario_builds_dataset_and_reference(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        _copy_import_fixtures(
            tmp_path,
            ["sample_occurrences.csv", "sample_taxonomy.csv"],
        )

        result = benchmark_service.auto_configure(
            [
                "imports/sample_occurrences.csv",
                "imports/sample_taxonomy.csv",
            ]
        )

        assert set(result["entities"]["datasets"]) == {"sample_occurrences"}
        assert "sample_taxonomy" in result["entities"]["references"]

        occurrences = result["decision_summary"]["sample_occurrences"]
        taxonomy = result["decision_summary"]["sample_taxonomy"]

        assert occurrences["final_entity_type"] == "dataset"
        assert taxonomy["final_entity_type"] == "hierarchical_reference"
        assert taxonomy["review_required"] is True

        assert any(
            ref["from"] == "sample_occurrences"
            and ref["field"] == "id_taxonref"
            and ref.get("target_field") == "id"
            and ref["confidence"] >= 0.9
            for ref in taxonomy["referenced_by"]
        )
        assert not any(
            warning == "No references detected. Add taxonomy or lookup tables."
            for warning in result["warnings"]
        )

    def test_spatial_lookup_scenario_promotes_reference_role(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        _copy_import_fixtures(tmp_path, ["sample_plots.csv"])

        result = benchmark_service.auto_configure(["imports/sample_plots.csv"])

        assert result["entities"]["datasets"] == {}
        assert set(result["entities"]["references"]) == {"sample_plots"}

        plots = result["decision_summary"]["sample_plots"]

        assert plots["final_entity_type"] == "reference"
        assert plots["ml_entity_type"] == "reference"
        assert plots["review_required"] is False
        assert (
            "No references detected. Add taxonomy or lookup tables."
            not in result["warnings"]
        )

    def test_class_object_stats_are_exposed_as_auxiliary_sources(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir(exist_ok=True)
        (imports_dir / "sample_occurrences.csv").write_text(
            "\n".join(
                [
                    "id,id_plot,measurement",
                    "1,1,10.5",
                    "2,2,11.2",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (imports_dir / "sample_plots.csv").write_text(
            "\n".join(
                [
                    "id_plot,plot,elevation",
                    "1,Plot A,150",
                    "2,Plot B,180",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "imports" / "plot_metrics.csv").write_text(
            "\n".join(
                [
                    "id,plot_id,class_object,class_name,class_value",
                    "1,1,dbh,0-10,4",
                    "2,2,dbh,10-20,7",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = benchmark_service.auto_configure(
            [
                "imports/sample_occurrences.csv",
                "imports/sample_plots.csv",
                "imports/plot_metrics.csv",
            ]
        )

        assert "plot_metrics" not in result["entities"]["datasets"]
        assert "plot_metrics" not in result["entities"]["references"]
        assert (
            result["decision_summary"]["plot_metrics"]["final_entity_type"]
            == "auxiliary_source"
        )
        assert result["decision_summary"]["plot_metrics"]["review_required"] is False
        assert any(
            source["name"] == "plot_metrics" and source["grouping"] == "sample_plots"
            for source in result["auxiliary_sources"]
        )
        assert any(
            source["name"] == "plot_metrics"
            and source["relation"]["ref_field"] == "id_plot"
            and source["relation"]["match_field"] == "plot_id"
            for source in result["auxiliary_sources"]
        )

    def test_rich_plot_reference_and_stats_sources_match_test_instance_shape(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir(exist_ok=True)

        occurrence_rows = [
            "id,id_table_liste_plots_n,idtax_individual_f,tax_fam,tax_gen,tax_sp_level,stem_diameter,height_m,observed_at,data_src,level_det,measurement,geo_pt",
        ]
        for index in range(1, 31):
            plot_id = 1 if index <= 15 else 2
            taxon_id = 4 if index <= 15 else 38
            occurrence_rows.append(
                f'{index},{plot_id},{taxon_id},Family {taxon_id},Genus {taxon_id},Species {taxon_id},{index * 2.0},{index / 10},2024-01-01,inventories,species,{index * 1.5},"POINT ({index} {index})"'
            )
        (imports_dir / "occurrences.csv").write_text(
            "\n".join(occurrence_rows) + "\n",
            encoding="utf-8",
        )
        (imports_dir / "plots.csv").write_text(
            "\n".join(
                [
                    "id_liste_plots,plot_name,locality_name,date_y,nbe_stem,geo_pt",
                    '1,Plot A,Locality A,2020,356,"POINT (1 1)"',
                    '2,Plot B,Locality B,2021,408,"POINT (2 2)"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (imports_dir / "raw_plot_stats.csv").write_text(
            "\n".join(
                [
                    "plot_id,class_object,class_value,class_name",
                    "1,nbe_stem,356,NA",
                    "2,nbe_stem,408,NA",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (imports_dir / "raw_taxa_stats.csv").write_text(
            "\n".join(
                [
                    "taxon_id,class_object,class_value,class_name",
                    "4,nbe_source_dataset,12,cafriplot network",
                    "38,nbe_source_dataset,18,cafriplot network",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = benchmark_service.auto_configure(
            [
                "imports/occurrences.csv",
                "imports/plots.csv",
                "imports/raw_plot_stats.csv",
                "imports/raw_taxa_stats.csv",
            ]
        )

        assert set(result["entities"]["datasets"]) == {"occurrences"}
        assert {"plots", "taxons"}.issubset(result["entities"]["references"])
        assert "raw_plot_stats" not in result["entities"]["references"]
        assert "raw_taxa_stats" not in result["entities"]["references"]
        assert result["decision_summary"]["plots"]["final_entity_type"] == "reference"
        assert (
            result["decision_summary"]["raw_plot_stats"]["final_entity_type"]
            == "auxiliary_source"
        )
        assert (
            result["decision_summary"]["raw_taxa_stats"]["final_entity_type"]
            == "auxiliary_source"
        )

        sources_by_name = {
            source["name"]: source for source in result["auxiliary_sources"]
        }
        assert sources_by_name["plot_stats"]["grouping"] == "plots"
        assert (
            sources_by_name["plot_stats"]["relation"]["ref_field"] == "id_liste_plots"
        )
        assert sources_by_name["plot_stats"]["relation"]["match_field"] == "plot_id"
        assert sources_by_name["taxa_stats"]["grouping"] == "taxons"
        assert sources_by_name["taxa_stats"]["relation"]["ref_field"] == "taxons_id"
        assert sources_by_name["taxa_stats"]["relation"]["match_field"] == "taxon_id"

    def test_reference_relation_prefers_dataset_over_auxiliary_source(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir(exist_ok=True)
        (imports_dir / "sample_occurrences.csv").write_text(
            "\n".join(
                [
                    "id,plot_name,measurement",
                    "1,Plot A,10.5",
                    "2,Plot B,11.2",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (imports_dir / "sample_plots.csv").write_text(
            "\n".join(
                [
                    "id_plot,plot,elevation",
                    "1,Plot A,150",
                    "2,Plot B,180",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (imports_dir / "plot_metrics.csv").write_text(
            "\n".join(
                [
                    "id,plot_id,class_object,class_name,class_value",
                    "1,1,dbh,0-10,4",
                    "2,2,dbh,10-20,7",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = benchmark_service.auto_configure(
            [
                "imports/sample_occurrences.csv",
                "imports/sample_plots.csv",
                "imports/plot_metrics.csv",
            ]
        )

        relation = result["entities"]["references"]["sample_plots"]["relation"]

        assert relation == {
            "dataset": "sample_occurrences",
            "foreign_key": "plot_name",
            "reference_key": "plot",
        }

    def test_reference_relation_prefers_plot_label_when_dataset_values_start_empty(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir(exist_ok=True)
        (imports_dir / "sample_occurrences.csv").write_text(
            "\n".join(
                [
                    "id,plot_name,measurement",
                    "1,,10.5",
                    "2,,11.2",
                    "3,,9.8",
                    "4,Plot A,12.1",
                    "5,Plot B,13.4",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (imports_dir / "sample_plots.csv").write_text(
            "\n".join(
                [
                    "id_plot,plot,elevation",
                    "1,Plot A,150",
                    "2,Plot B,180",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = benchmark_service.auto_configure(
            [
                "imports/sample_occurrences.csv",
                "imports/sample_plots.csv",
            ]
        )

        relation = result["entities"]["references"]["sample_plots"]["relation"]

        assert relation == {
            "dataset": "sample_occurrences",
            "foreign_key": "plot_name",
            "reference_key": "plot",
        }

    def test_shape_stats_attach_to_detected_shapes_reference(
        self, benchmark_service: AutoConfigService, tmp_path: Path
    ):
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir(exist_ok=True)

        (imports_dir / "raw_shape_stats.csv").write_text(
            "\n".join(
                [
                    "id,label,class_object,class_name,class_value",
                    "provinces_1,PROVINCE NORD,cover_forest,Forêt,0.34",
                    "provinces_2,PROVINCE SUD,cover_forest,Hors-forêt,0.66",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        gdf = gpd.GeoDataFrame(
            {
                "nom": ["PROVINCE NORD", "PROVINCE SUD"],
                "code_com": ["98827", "98828"],
            },
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
            ],
            crs="EPSG:4326",
        )
        gdf.to_file(imports_dir / "provinces.gpkg", driver="GPKG")

        result = benchmark_service.auto_configure(
            [
                "imports/raw_shape_stats.csv",
                "imports/provinces.gpkg",
            ]
        )

        assert "shapes" in result["entities"]["references"]
        assert "raw_shape_stats" not in result["entities"]["datasets"]
        assert "raw_shape_stats" not in result["entities"]["references"]
        assert (
            result["decision_summary"]["raw_shape_stats"]["final_entity_type"]
            == "auxiliary_source"
        )
        assert result["decision_summary"]["raw_shape_stats"]["review_level"] == "stable"
        assert any(
            source["name"] == "shape_stats" and source["grouping"] == "shapes"
            for source in result["auxiliary_sources"]
        )
