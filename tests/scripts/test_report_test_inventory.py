from __future__ import annotations

from pathlib import Path

from scripts.dev.report_test_inventory import build_inventory, main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_inventory_groups_domains_and_ignores_noise(tmp_path: Path) -> None:
    _write(
        tmp_path / "src/niamoto/common/config.py",
        "def load_config() -> str:\n    return 'ok'\n",
    )
    _write(
        tmp_path / "src/niamoto/core/imports/profiler.py",
        "def build_profile() -> str:\n    return 'profile'\n",
    )
    _write(
        tmp_path / "tests/common/test_config.py",
        "def test_config() -> None:\n    assert True\n",
    )
    _write(
        tmp_path / "tests/core/imports/test_profiler_io.py",
        "def test_profiler_io() -> None:\n    assert True\n",
    )
    _write(
        tmp_path / "tests/core/imports/test_profiler_ml.py",
        "def test_profiler_ml() -> None:\n    assert True\n",
    )
    _write(
        tmp_path / "src/niamoto/gui/ui/src/features/import/hooks/useImportJob.ts",
        "export function useImportJob() { return 'ok' }\n",
    )
    _write(
        tmp_path / "src/niamoto/gui/ui/src/features/import/hooks/useImportJob.test.ts",
        "import { describe, expect, it } from 'vitest'\n"
        "describe('useImportJob', () => { it('works', () => { expect(true).toBe(true) }) })\n",
    )
    _write(
        tmp_path
        / "src/niamoto/gui/ui/src/features/import/hooks/useCompatibilityCheck.ts",
        "export function useCompatibilityCheck() { return 'pending' }\n",
    )
    _write(
        tmp_path / "src/niamoto/gui/ui/src/shared/lib/api/client.ts",
        "export function apiClient() { return 'client' }\n",
    )
    _write(
        tmp_path / "src/niamoto/gui/ui/src/shared/lib/api/client.test.ts",
        "import { describe, expect, it } from 'vitest'\n"
        "describe('apiClient', () => { it('works', () => { expect(true).toBe(true) }) })\n",
    )
    _write(
        tmp_path
        / "src/niamoto/gui/ui/src/features/tools/content/aboutContent.generated.ts",
        "export const generated = true\n",
    )
    _write(
        tmp_path / "src/niamoto/gui/ui/node_modules/vendor.ts",
        "export const vendor = true\n",
    )

    report = build_inventory(
        repo_root=tmp_path,
        coverage_xml_path=tmp_path / "coverage.xml",
        frontend_coverage_path=tmp_path / "frontend-coverage-summary.json",
    )

    assert report.python_coverage.status == "missing"
    assert report.frontend_coverage.status == "missing"
    assert report.python_sources == (
        "src/niamoto/common/config.py",
        "src/niamoto/core/imports/profiler.py",
    )
    assert (
        "src/niamoto/gui/ui/src/features/tools/content/aboutContent.generated.ts"
        not in report.frontend_sources
    )
    assert "src/niamoto/gui/ui/node_modules/vendor.ts" not in report.frontend_sources
    assert "src/niamoto/core/imports/profiler.py" not in {
        gap.path for gap in report.top_python_gaps
    }
    assert "src/niamoto/gui/ui/src/features/import/hooks/useCompatibilityCheck.ts" in {
        gap.path for gap in report.top_frontend_gaps
    }

    python_domains = {summary.name: summary for summary in report.python_domains}
    assert python_domains["common"].direct_test_files == 1
    assert python_domains["core/imports"].direct_test_files == 1

    frontend_areas = {summary.name: summary for summary in report.frontend_areas}
    assert frontend_areas["import"].source_files == 2
    assert frontend_areas["import"].direct_test_files == 1
    assert frontend_areas["shared"].source_files == 1
    assert frontend_areas["shared"].direct_test_files == 1

    markdown = report.to_markdown()
    assert "## Highest-ROI Python Gaps" in markdown
    assert (
        "`src/niamoto/gui/ui/src/features/import/hooks/useCompatibilityCheck.ts`"
        in markdown
    )


def test_build_inventory_marks_stale_coverage_when_files_do_not_match(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "src/niamoto/common/config.py",
        "def load_config() -> str:\n    return 'ok'\n",
    )
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        """<?xml version="1.0" ?>
<coverage>
  <packages>
    <package name="src.niamoto.common">
      <classes>
        <class filename="src/niamoto/common/config.py" line-rate="1.0">
          <lines>
            <line number="1" hits="1" />
          </lines>
        </class>
        <class filename="src/niamoto/core/missing.py" line-rate="0.0">
          <lines>
            <line number="1" hits="0" />
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
""",
        encoding="utf-8",
    )

    report = build_inventory(
        repo_root=tmp_path,
        coverage_xml_path=coverage_xml,
        frontend_coverage_path=tmp_path / "frontend-coverage-summary.json",
    )

    assert report.python_coverage.status == "stale"
    assert report.python_coverage.matched_files == 1
    assert report.python_coverage.total_files == 2


def test_build_inventory_reads_available_frontend_coverage_summary(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "src/niamoto/gui/ui/src/shared/lib/api/client.ts",
        "export function apiClient() { return 'client' }\n",
    )
    summary_path = tmp_path / "coverage-summary.json"
    summary_path.write_text(
        '{"total": {"lines": {"pct": 64.5}}}',
        encoding="utf-8",
    )

    report = build_inventory(
        repo_root=tmp_path,
        coverage_xml_path=tmp_path / "coverage.xml",
        frontend_coverage_path=summary_path,
    )

    assert report.frontend_coverage.status == "available"
    assert report.frontend_coverage.line_rate == 0.645


def test_main_returns_non_zero_for_malformed_coverage(tmp_path: Path, capsys) -> None:
    bad_xml = tmp_path / "coverage.xml"
    bad_xml.write_text("<coverage>", encoding="utf-8")

    exit_code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--coverage-xml",
            str(bad_xml),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid coverage xml" in captured.err
