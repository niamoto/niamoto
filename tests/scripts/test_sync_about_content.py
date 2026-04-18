from pathlib import Path

from scripts.build.sync_about_content import (
    README_END,
    README_START,
    default_content_path,
    default_fragment_path,
    default_readme_path,
    default_ui_output_path,
    sync_about_content,
)


def _extract_about_block(readme_text: str) -> str:
    start = readme_text.index(README_START) + len(README_START)
    end = readme_text.index(README_END)
    return readme_text[start:end].strip()


def test_sync_about_content_matches_tracked_outputs(tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    fragment_path = tmp_path / "README-about.en.md"
    ui_output_path = tmp_path / "aboutContent.generated.ts"

    readme_path.write_text(
        default_readme_path().read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    sync_about_content(
        content_path=default_content_path(),
        readme_path=readme_path,
        fragment_path=fragment_path,
        ui_output_path=ui_output_path,
    )

    expected_fragment = default_fragment_path().read_text(encoding="utf-8")
    expected_ui_output = default_ui_output_path().read_text(encoding="utf-8")

    assert fragment_path.read_text(encoding="utf-8") == expected_fragment
    assert ui_output_path.read_text(encoding="utf-8") == expected_ui_output
    assert (
        _extract_about_block(readme_path.read_text(encoding="utf-8"))
        == expected_fragment.strip()
    )


def test_readme_fragment_keeps_clickable_organization_names() -> None:
    fragment = default_fragment_path().read_text(encoding="utf-8")

    assert '<a href="https://www.province-nord.nc/">Province Nord</a>' in fragment
    assert '<a href="https://cirad.fr/">Cirad</a>' in fragment
    assert "**Julien Barbe** — Developer" in fragment
