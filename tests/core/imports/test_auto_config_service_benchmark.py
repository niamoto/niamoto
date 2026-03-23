"""Product-level benchmark scenarios for AutoConfigService."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

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
