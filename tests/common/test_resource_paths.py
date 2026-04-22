from __future__ import annotations

from pathlib import Path

from niamoto.common.resource_paths import ResourceLocation, ResourcePaths


def test_resource_location_sets_exists_flag(tmp_path: Path) -> None:
    existing = tmp_path / "plugins"
    existing.mkdir()

    assert ResourceLocation("project", existing, 100).exists is True
    assert ResourceLocation("project", tmp_path / "missing", 100).exists is False


def test_get_plugin_paths_orders_project_user_and_system(
    monkeypatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr("niamoto.common.bundle.is_frozen", lambda: False)

    locations = ResourcePaths.get_plugin_paths(project_path=project)

    assert [location.scope for location in locations] == ["project", "user", "system"]
    assert locations[0].path == project / "plugins"
    assert locations[1].path == home / ".niamoto" / "plugins"
    assert (home / ".niamoto" / "plugins").exists()


def test_get_template_paths_uses_bundle_path_when_frozen(
    monkeypatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    bundle_templates = tmp_path / "bundle" / "niamoto" / "templates"
    bundle_templates.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr("niamoto.common.bundle.is_frozen", lambda: True)
    monkeypatch.setattr(
        "niamoto.common.bundle.get_resource_path",
        lambda relative_path: bundle_templates,
    )

    locations = ResourcePaths.get_template_paths(project_path=None)

    assert locations[-1].scope == "system"
    assert locations[-1].path == bundle_templates


def test_resolve_resource_prefers_first_existing_location(tmp_path: Path) -> None:
    project_plugins = tmp_path / "project" / "plugins"
    user_plugins = tmp_path / "user" / "plugins"
    project_plugins.mkdir(parents=True)
    user_plugins.mkdir(parents=True)
    (user_plugins / "bar_plot.py").write_text("user", encoding="utf-8")
    (project_plugins / "bar_plot.py").write_text("project", encoding="utf-8")

    locations = [
        ResourceLocation("project", project_plugins, 100),
        ResourceLocation("user", user_plugins, 50),
    ]

    assert (
        ResourcePaths.resolve_resource("bar_plot.py", locations)
        == project_plugins / "bar_plot.py"
    )


def test_collect_all_resources_shadows_lower_priority_duplicates(
    tmp_path: Path,
) -> None:
    project_plugins = tmp_path / "project" / "plugins"
    user_plugins = tmp_path / "user" / "plugins"
    project_plugins.mkdir(parents=True)
    user_plugins.mkdir(parents=True)
    (project_plugins / "bar_plot.py").write_text("project", encoding="utf-8")
    (user_plugins / "bar_plot.py").write_text("user", encoding="utf-8")
    (user_plugins / "line_plot.py").write_text("user", encoding="utf-8")

    locations = [
        ResourceLocation("project", project_plugins, 100),
        ResourceLocation("user", user_plugins, 50),
    ]

    resources = ResourcePaths.collect_all_resources(locations, "*.py")

    assert resources == [project_plugins / "bar_plot.py", user_plugins / "line_plot.py"]
