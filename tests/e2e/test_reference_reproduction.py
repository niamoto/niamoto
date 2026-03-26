"""E2E checks for reproducing a reference project via GUI APIs.

These tests validate the workflow:
- apply reference widgets/sources with /api/templates/save-config
- verify transform.yml parity after reload
- verify export.yml widgets are regenerated for shapes
- smoke-test preview rendering for shapes widgets
"""

import shutil
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import duckdb
import pytest
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api import context
from niamoto.gui.api.app import create_app

REFERENCE_INSTANCE_PATH = (
    Path(__file__).parent.parent.parent / "test-instance" / "niamoto-nc"
)
TARGET_INSTANCE_PATH = (
    Path(__file__).parent.parent.parent / "test-instance" / "niamoto-test"
)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not REFERENCE_INSTANCE_PATH.exists() or not TARGET_INSTANCE_PATH.exists(),
        reason="Instances de test locales absentes (test-instance/niamoto-nc et niamoto-test)",
    ),
]


@pytest.fixture(scope="session", autouse=True)
def ensure_plugins_loaded():
    """Load transformer/widget plugins required by reference shapes previews."""
    # Transformers
    import niamoto.core.plugins.transformers.aggregation.binary_counter  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.field_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.statistical_summary  # noqa: F401
    import niamoto.core.plugins.transformers.aggregation.top_ranking  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.binned_distribution  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.categorical_distribution  # noqa: F401
    import niamoto.core.plugins.transformers.distribution.time_series_analysis  # noqa: F401
    import niamoto.core.plugins.transformers.extraction.geospatial_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.geospatial.shape_processor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.binary_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.categories_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.categories_mapper  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.field_aggregator  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_by_axis_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_matrix_extractor  # noqa: F401
    import niamoto.core.plugins.transformers.class_objects.series_ratio_aggregator  # noqa: F401

    # Widgets
    import niamoto.core.plugins.widgets.bar_plot  # noqa: F401
    import niamoto.core.plugins.widgets.donut_chart  # noqa: F401
    import niamoto.core.plugins.widgets.hierarchical_nav_widget  # noqa: F401
    import niamoto.core.plugins.widgets.info_grid  # noqa: F401
    import niamoto.core.plugins.widgets.interactive_map  # noqa: F401
    import niamoto.core.plugins.widgets.radial_gauge  # noqa: F401

    # Loaders
    import niamoto.core.plugins.loaders.stats_loader  # noqa: F401


@pytest.fixture(scope="session")
def reference_transform() -> dict[str, dict[str, Any]]:
    """Load transform reference config from niamoto-nc."""
    transform_path = REFERENCE_INSTANCE_PATH / "config" / "transform.yml"
    assert transform_path.exists(), f"Missing reference transform.yml: {transform_path}"
    with open(transform_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or []
    assert isinstance(config, list), (
        "Reference transform.yml should be a list of groups"
    )
    return {group["group_by"]: group for group in config if isinstance(group, dict)}


@pytest.fixture
def test_client(mock_context: Path) -> TestClient:
    """Create API client after context is patched to temporary workspace."""
    return TestClient(create_app())


@pytest.fixture
def working_directory(tmp_path: Path) -> Path:
    """Create an isolated project workspace for API tests."""
    src_config = TARGET_INSTANCE_PATH / "config"
    dst_config = tmp_path / "config"
    shutil.copytree(src_config, dst_config)

    (tmp_path / "imports").symlink_to(TARGET_INSTANCE_PATH / "imports")
    (tmp_path / "db").symlink_to(TARGET_INSTANCE_PATH / "db")
    (tmp_path / "exports").mkdir(exist_ok=True)
    (tmp_path / "exports" / "web").mkdir(parents=True, exist_ok=True)

    return tmp_path


@pytest.fixture(autouse=True)
def mock_context(working_directory: Path):
    """Point GUI API context to temporary workspace."""
    with patch.object(context, "_working_directory", working_directory):
        yield working_directory


def _get_group(raw_config: Any, group_name: str) -> dict[str, Any]:
    """Find a group config inside transform raw_config."""
    if isinstance(raw_config, list):
        for group in raw_config:
            if isinstance(group, dict) and group.get("group_by") == group_name:
                return group
    raise AssertionError(f"Group '{group_name}' not found in transform config")


def _normalize(value: Any) -> Any:
    """Recursively sort dict keys for robust comparisons."""
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _shrink_group_table_for_publication_test(
    working_directory: Path, group: str, max_items: int = 5
) -> None:
    """Keep only a small subset of rows in the group table for fast smoke exports."""
    db_path = working_directory / "db" / "niamoto.duckdb"
    id_column = f"{group}_id"

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            f'CREATE TEMP TABLE __keep_ids AS SELECT "{id_column}" FROM "{group}" '
            f'ORDER BY "{id_column}" LIMIT {max_items}'
        )
        conn.execute(
            f'DELETE FROM "{group}" WHERE "{id_column}" NOT IN '
            f'(SELECT "{id_column}" FROM __keep_ids)'
        )
    finally:
        conn.close()


class TestReferenceParity:
    """Ensure GUI save/reload can reproduce the reference transform config."""

    @pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
    def test_replace_matches_reference_config(
        self,
        test_client: TestClient,
        reference_transform: dict[str, dict[str, Any]],
        group: str,
    ):
        ref_group = reference_transform[group]

        save_request = {
            "group_by": group,
            "sources": ref_group["sources"],
            "widgets_data": ref_group["widgets_data"],
            "mode": "replace",
        }
        save_response = test_client.post(
            "/api/templates/save-config", json=save_request
        )
        assert save_response.status_code == 200, save_response.text
        assert save_response.json().get("success") is True

        reload_response = test_client.get("/api/transform/config")
        assert reload_response.status_code == 200, reload_response.text
        loaded_group = _get_group(reload_response.json()["raw_config"], group)

        assert _normalize(loaded_group.get("sources", [])) == _normalize(
            ref_group["sources"]
        )
        assert _normalize(loaded_group.get("widgets_data", {})) == _normalize(
            ref_group["widgets_data"]
        )


class TestShapesExportGeneration:
    """Ensure export config for shapes is regenerated from reference widgets."""

    def test_shapes_replace_regenerates_export_group(
        self,
        test_client: TestClient,
        working_directory: Path,
        reference_transform: dict[str, dict[str, Any]],
    ):
        ref_shapes = reference_transform["shapes"]

        save_request = {
            "group_by": "shapes",
            "sources": ref_shapes["sources"],
            "widgets_data": ref_shapes["widgets_data"],
            "mode": "replace",
        }
        save_response = test_client.post(
            "/api/templates/save-config", json=save_request
        )
        assert save_response.status_code == 200, save_response.text

        export_path = working_directory / "config" / "export.yml"
        assert export_path.exists(), "export.yml was not generated"

        with open(export_path, encoding="utf-8") as f:
            export_config = yaml.safe_load(f) or {}

        html_exporter = None
        for export in export_config.get("exports", []):
            if (
                isinstance(export, dict)
                and export.get("exporter") == "html_page_exporter"
            ):
                html_exporter = export
                break
        assert html_exporter is not None, "html_page_exporter is missing in export.yml"

        shapes_group = None
        for group_cfg in html_exporter.get("groups", []):
            if isinstance(group_cfg, dict) and group_cfg.get("group_by") == "shapes":
                shapes_group = group_cfg
                break
        assert shapes_group is not None, "shapes group is missing in export.yml"

        widgets = shapes_group.get("widgets", [])
        data_sources = {w.get("data_source") for w in widgets if isinstance(w, dict)}
        expected_sources = set(ref_shapes["widgets_data"].keys())

        assert len(widgets) == len(expected_sources)
        assert data_sources == expected_sources


class TestShapesPreviewSmoke:
    """Smoke test configured widget previews for reference shapes widgets."""

    @pytest.fixture
    def configured_shapes_widget_ids(
        self,
        test_client: TestClient,
        reference_transform: dict[str, dict[str, Any]],
    ) -> list[str]:
        ref_shapes = reference_transform["shapes"]
        save_request = {
            "group_by": "shapes",
            "sources": ref_shapes["sources"],
            "widgets_data": ref_shapes["widgets_data"],
            "mode": "replace",
        }
        save_response = test_client.post(
            "/api/templates/save-config", json=save_request
        )
        assert save_response.status_code == 200, save_response.text
        return list(ref_shapes["widgets_data"].keys())

    def test_shapes_previews_render_without_errors(
        self,
        test_client: TestClient,
        configured_shapes_widget_ids: list[str],
    ):
        error_markers = (
            "<p class='error'>",
            "traceback",
            "erreur lors de la preview",
            "widget render error",
        )
        issues: list[str] = []

        for widget_id in configured_shapes_widget_ids:
            response = test_client.get(
                f"/api/templates/preview/{widget_id}",
                params={"group_by": "shapes"},
            )
            body = response.text.lower()
            if response.status_code != 200:
                issues.append(
                    f"{widget_id}: HTTP {response.status_code} from preview endpoint"
                )
            if "<html" not in body:
                issues.append(f"{widget_id}: preview response is not HTML")

            present_markers = [marker for marker in error_markers if marker in body]
            if present_markers:
                issues.append(
                    f"{widget_id}: preview contains error markers {present_markers}"
                )

        assert not issues, "Shapes preview smoke test failed:\n" + "\n".join(issues)


class TestPublicationPipeline:
    """End-to-end publication flow: save config -> export -> UI preview."""

    @pytest.mark.parametrize("group", ["shapes", "taxons", "plots"])
    def test_publish_to_ui_preview(
        self,
        test_client: TestClient,
        working_directory: Path,
        reference_transform: dict[str, dict[str, Any]],
        group: str,
    ):
        # Use reference DB/imports for full publication checks: niamoto-test DB
        # does not contain all materialized reference tables required by exporter.
        # Copy DB to keep each test isolated and avoid DuckDB file lock conflicts.
        db_link = working_directory / "db"
        if db_link.is_symlink() or db_link.is_file():
            db_link.unlink()
        elif db_link.exists():
            shutil.rmtree(db_link)
        shutil.copytree(REFERENCE_INSTANCE_PATH / "db", db_link)

        imports_link = working_directory / "imports"
        if imports_link.exists() or imports_link.is_symlink():
            imports_link.unlink()
        imports_link.symlink_to(REFERENCE_INSTANCE_PATH / "imports")
        _shrink_group_table_for_publication_test(working_directory, group)

        # Keep publication e2e fast and deterministic by exporting only the target group.
        ref_group = reference_transform[group]
        save_request = {
            "group_by": group,
            "sources": ref_group["sources"],
            "widgets_data": ref_group["widgets_data"],
            "mode": "replace",
        }
        save_response = test_client.post(
            "/api/templates/save-config", json=save_request
        )
        assert save_response.status_code == 200, (
            f"save-config failed for {group}: {save_response.text}"
        )
        assert save_response.json().get("success") is True

        # Reduce export scope to a single group and no static pages.
        export_path = working_directory / "config" / "export.yml"
        with open(export_path, encoding="utf-8") as f:
            export_config = yaml.safe_load(f) or {}

        for export in export_config.get("exports", []):
            if (
                isinstance(export, dict)
                and export.get("exporter") == "html_page_exporter"
            ):
                export.setdefault("params", {})
                export["params"]["output_dir"] = str(
                    working_directory / "exports" / "web"
                )
                export["params"].setdefault("template_dir", "templates/")
                export["static_pages"] = []
                export["groups"] = [
                    group_cfg
                    for group_cfg in export.get("groups", [])
                    if isinstance(group_cfg, dict)
                    and group_cfg.get("group_by") == group
                ]

        with open(export_path, "w", encoding="utf-8") as f:
            yaml.dump(
                export_config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120,
            )

        execute_response = test_client.post(
            "/api/export/execute",
            json={"config_path": "config/export.yml", "export_types": ["web_pages"]},
        )
        assert execute_response.status_code == 200, execute_response.text
        job_id = execute_response.json()["job_id"]

        final_status = None
        final_payload: dict[str, Any] = {}
        deadline = time.time() + 180
        while time.time() < deadline:
            status_response = test_client.get(f"/api/export/status/{job_id}")
            assert status_response.status_code == 200, status_response.text
            final_payload = status_response.json()
            final_status = final_payload.get("status")
            if final_status in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.5)

        assert final_status == "completed", (
            f"Export job {job_id} ended with status={final_status}: {final_payload}"
        )
        assert final_payload.get("result"), f"Export job {job_id} has no result payload"
        web_export = final_payload["result"]["exports"].get("web_pages", {})
        assert web_export.get("status") == "success", (
            f"web_pages export failed: {final_payload}"
        )
        web_export_data = web_export.get("data", {}).get("web_pages", {})
        assert web_export_data.get("status") == "success", (
            f"web_pages inner export failed: {final_payload}"
        )
        assert web_export_data.get("files_generated", 0) > 0, (
            f"web_pages generated no files: {final_payload}"
        )

        web_output = Path(
            web_export_data.get(
                "output_path", str(working_directory / "exports" / "web")
            )
        )
        assert web_output.exists(), "exports/web was not generated"
        generated_html = list(web_output.rglob("*.html"))
        assert generated_html, f"No published HTML files found in {web_output}"
        group_pages = [
            path
            for path in generated_html
            if f"/{group}/" in path.as_posix()
            or path.as_posix().endswith(f"/{group}/index.html")
        ]
        assert group_pages, f"No {group} pages generated in {web_output}"

        preview_target = group_pages[0].relative_to(web_output).as_posix()
        preview_response = test_client.get(f"/preview/{preview_target}")
        assert preview_response.status_code == 200, preview_response.text
        assert "<html" in preview_response.text.lower()
