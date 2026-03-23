"""Security-focused tests for AutoConfigService path handling."""

from pathlib import Path

import pytest

from niamoto.core.imports.auto_config_service import AutoConfigService


@pytest.fixture
def secured_service(tmp_path: Path) -> AutoConfigService:
    """Create a service bound to an isolated working directory."""
    imports_dir = tmp_path / "imports"
    imports_dir.mkdir()
    return AutoConfigService(tmp_path)


def test_analyze_file_rejects_paths_outside_project(
    secured_service: AutoConfigService,
):
    with pytest.raises(ValueError, match="outside project"):
        secured_service.analyze_file("../secret.csv")


def test_detect_relationships_rejects_target_paths_outside_project(
    secured_service: AutoConfigService, tmp_path: Path
):
    source = tmp_path / "imports" / "source.csv"
    source.write_text("id,name\n1,test\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside project"):
        secured_service.detect_relationships(
            "imports/source.csv",
            ["../secret.csv"],
        )


def test_auto_configure_rejects_absolute_paths_outside_project(
    secured_service: AutoConfigService, tmp_path: Path
):
    outside_path = tmp_path.parent / "outside.csv"
    outside_path.write_text("id,name\n1,test\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside project"):
        secured_service.auto_configure([str(outside_path)])


def test_analyze_file_does_not_expose_internal_sample_rows(
    secured_service: AutoConfigService, tmp_path: Path
):
    sample_file = tmp_path / "imports" / "sample.csv"
    sample_file.write_text("id,name\n1,test\n2,demo\n", encoding="utf-8")

    analysis = secured_service.analyze_file("imports/sample.csv")

    assert "_sample_rows" not in analysis


def test_read_csv_can_skip_full_row_count_when_not_needed(
    secured_service: AutoConfigService, tmp_path: Path
):
    sample_file = tmp_path / "imports" / "sample.csv"
    sample_file.write_text(
        "id,name\n1,a\n2,b\n3,c\n4,d\n5,e\n",
        encoding="utf-8",
    )

    columns, rows, row_count = secured_service._read_csv_columns_and_rows(
        sample_file,
        max_rows=2,
        count_all_rows=False,
    )

    assert columns == ["id", "name"]
    assert len(rows) == 2
    assert row_count == 2
