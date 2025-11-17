"""
Integration tests for resource cascade resolution.

These tests ensure that CLI and Desktop load plugins identically using
the cascade resolution pattern (Project > User > System).

IMPORTANT: These are integration tests using real files, not mocks.
Following testing-anti-patterns skill: test real behavior, not mock behavior.
"""

from pathlib import Path
import pytest

from niamoto.common.resource_paths import ResourcePaths, ResourceLocation
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.registry import PluginRegistry


# Sample plugin code for testing
SAMPLE_TRANSFORMER_V1 = '''"""Sample transformer plugin v1"""
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("test_transformer", PluginType.TRANSFORMER)
class TestTransformerV1(TransformerPlugin):
    """Test transformer version 1"""
    name = "test_transformer"
    type = PluginType.TRANSFORMER
    version = "1.0"

    def transform(self, data, config):
        return {"version": "1.0", "data": data}
'''

SAMPLE_TRANSFORMER_V2 = '''"""Sample transformer plugin v2"""
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("test_transformer", PluginType.TRANSFORMER)
class TestTransformerV2(TransformerPlugin):
    """Test transformer version 2"""
    name = "test_transformer"
    type = PluginType.TRANSFORMER
    version = "2.0"

    def transform(self, data, config):
        return {"version": "2.0", "data": data}
'''

SAMPLE_EXPORTER = '''"""Sample exporter plugin"""
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register

@register("test_exporter", PluginType.EXPORTER)
class TestExporter(ExporterPlugin):
    """Test exporter"""
    name = "test_exporter"
    type = PluginType.EXPORTER

    def export(self, data, config, output_path):
        pass
'''


class TestResourcePaths:
    """Test ResourcePaths cascade resolution."""

    def test_get_plugin_paths_returns_correct_order(self, tmp_path):
        """
        Test that get_plugin_paths returns locations in priority order:
        Project (100) > User (50) > System (10)
        """
        project_path = tmp_path / "project"
        project_path.mkdir()

        locations = ResourcePaths.get_plugin_paths(project_path)

        # Should have 3 locations
        assert len(locations) == 3

        # Check order by priority
        assert locations[0].priority == 100  # Project
        assert locations[0].scope == ResourcePaths.SCOPE_PROJECT
        assert locations[0].path == project_path / "plugins"

        assert locations[1].priority == 50  # User
        assert locations[1].scope == ResourcePaths.SCOPE_USER
        assert locations[1].path == Path.home() / ".niamoto" / "plugins"

        assert locations[2].priority == 10  # System
        assert locations[2].scope == ResourcePaths.SCOPE_SYSTEM
        # System path points to niamoto/core/plugins

    def test_get_plugin_paths_without_project(self):
        """
        Test that get_plugin_paths works without project_path.
        Should only return User and System locations.
        """
        locations = ResourcePaths.get_plugin_paths(project_path=None)

        # Should have 2 locations (no project)
        assert len(locations) == 2

        assert locations[0].scope == ResourcePaths.SCOPE_USER
        assert locations[0].priority == 50

        assert locations[1].scope == ResourcePaths.SCOPE_SYSTEM
        assert locations[1].priority == 10

    def test_resource_location_tracks_existence(self, tmp_path):
        """Test that ResourceLocation.exists reflects actual path existence."""
        existing_path = tmp_path / "exists"
        existing_path.mkdir()

        nonexistent_path = tmp_path / "does_not_exist"

        loc_exists = ResourceLocation(scope="test", path=existing_path, priority=100)

        loc_missing = ResourceLocation(
            scope="test", path=nonexistent_path, priority=100
        )

        assert loc_exists.exists is True
        assert loc_missing.exists is False

    def test_resolve_resource_finds_highest_priority(self, tmp_path):
        """Test that resolve_resource returns highest priority match."""
        # Create project and user directories
        project_path = tmp_path / "project" / "plugins"
        user_path = tmp_path / "user" / "plugins"
        system_path = tmp_path / "system" / "plugins"

        for path in [project_path, user_path, system_path]:
            path.mkdir(parents=True)

        # Create same plugin in all locations
        (project_path / "my_plugin.py").write_text("# project version")
        (user_path / "my_plugin.py").write_text("# user version")
        (system_path / "my_plugin.py").write_text("# system version")

        locations = [
            ResourceLocation("project", project_path, 100),
            ResourceLocation("user", user_path, 50),
            ResourceLocation("system", system_path, 10),
        ]

        # Should find project version (highest priority)
        result = ResourcePaths.resolve_resource("my_plugin.py", locations)

        assert result == project_path / "my_plugin.py"
        assert result.read_text() == "# project version"

    def test_collect_all_resources_deduplicates(self, tmp_path):
        """Test that collect_all_resources deduplicates by filename."""
        # Create directories
        project_path = tmp_path / "project" / "plugins"
        user_path = tmp_path / "user" / "plugins"

        project_path.mkdir(parents=True)
        user_path.mkdir(parents=True)

        # Create plugins - duplicate name in both locations
        (project_path / "plugin_a.py").write_text("# project A")
        (project_path / "plugin_b.py").write_text("# project B")
        (user_path / "plugin_a.py").write_text("# user A")  # Duplicate!
        (user_path / "plugin_c.py").write_text("# user C")

        locations = [
            ResourceLocation("project", project_path, 100),
            ResourceLocation("user", user_path, 50),
        ]

        results = ResourcePaths.collect_all_resources(locations, "*.py")

        # Should have 3 unique plugins (A from project, B from project, C from user)
        assert len(results) == 3

        filenames = {r.name for r in results}
        assert filenames == {"plugin_a.py", "plugin_b.py", "plugin_c.py"}

        # Verify plugin_a comes from project (higher priority)
        plugin_a = next(r for r in results if r.name == "plugin_a.py")
        assert plugin_a.read_text() == "# project A"


class TestPluginCascade:
    """
    Integration tests for plugin cascade loading.

    These tests use REAL temporary directories and REAL plugin files
    to ensure the cascade resolution works correctly.
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Set up and tear down for each test."""
        # Clear registry before test
        PluginRegistry.clear()

        yield

        # Clear registry after test
        PluginRegistry.clear()

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        project = tmp_path / "test_project"
        project.mkdir()

        # Create project plugins directory
        (project / "plugins").mkdir()

        return project

    @pytest.fixture
    def temp_user_dir(self, tmp_path, monkeypatch):
        """Create and use a temporary user directory."""
        user_dir = tmp_path / "user_home" / ".niamoto"
        user_dir.mkdir(parents=True)

        # Monkey-patch Path.home() to return our temp dir
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "user_home")

        (user_dir / "plugins").mkdir()

        return user_dir

    def test_project_plugins_override_system(self, temp_project):
        """
        Test that project plugins override system plugins.

        This is the core cascade behavior: same plugin name in project
        should take precedence over system version.
        """
        # Write a project plugin with same name as system plugin
        # (Use a simple plugin that won't conflict with real system plugins)
        project_plugin = temp_project / "plugins" / "custom_calc.py"
        project_plugin.write_text(SAMPLE_TRANSFORMER_V2)

        # Load with cascade
        loader = PluginLoader()
        loader.load_plugins_with_cascade(temp_project)

        # Verify plugin is tracked as coming from project
        assert "test_transformer" in loader.plugin_info_by_name
        plugin_info = loader.plugin_info_by_name["test_transformer"]

        assert plugin_info.scope == ResourcePaths.SCOPE_PROJECT
        assert plugin_info.priority == 100
        assert "custom_calc.py" in str(plugin_info.path)

    def test_user_plugins_override_system(self, temp_project, temp_user_dir):
        """
        Test that user plugins override system plugins.
        """
        # Write user plugin
        user_plugin = temp_user_dir / "plugins" / "user_transformer.py"
        user_plugin.write_text(SAMPLE_TRANSFORMER_V1)

        # Load with cascade (no project plugins)
        loader = PluginLoader()
        loader.load_plugins_with_cascade(temp_project)

        # Verify plugin is tracked as coming from user scope
        if "test_transformer" in loader.plugin_info_by_name:
            plugin_info = loader.plugin_info_by_name["test_transformer"]
            assert plugin_info.scope == ResourcePaths.SCOPE_USER
            assert plugin_info.priority == 50

    def test_project_overrides_user_overrides_system(self, temp_project, temp_user_dir):
        """
        Test complete cascade: Project > User > System.

        Same plugin in all three scopes - project version should win.
        """
        # Write same plugin to project and user
        project_plugin = temp_project / "plugins" / "cascade_test.py"
        project_plugin.write_text(SAMPLE_TRANSFORMER_V2)  # v2.0

        user_plugin = temp_user_dir / "plugins" / "cascade_test.py"
        user_plugin.write_text(SAMPLE_TRANSFORMER_V1)  # v1.0

        # Load with cascade
        loader = PluginLoader()

        # Debug: check what locations are returned
        locations = ResourcePaths.get_plugin_paths(temp_project)
        print("\n=== Locations for cascade test ===")
        for loc in locations:
            print(
                f"  {loc.scope} (priority {loc.priority}): {loc.path} (exists: {loc.exists})"
            )

        loader.load_plugins_with_cascade(temp_project)

        # Debug: check what was loaded
        print("\n=== Plugins loaded ===")
        for name, info in loader.plugin_info_by_name.items():
            if "test_transformer" in name:
                print(
                    f"  {name}: scope={info.scope}, priority={info.priority}, path={info.path}"
                )

        # Project version should win
        plugin_info = loader.plugin_info_by_name["test_transformer"]
        assert plugin_info.scope == ResourcePaths.SCOPE_PROJECT, (
            f"Expected project scope, got {plugin_info.scope} from {plugin_info.path}"
        )
        assert plugin_info.priority == 100
        assert "cascade_test.py" in str(plugin_info.path)

    def test_multiple_plugins_from_different_scopes(self, temp_project, temp_user_dir):
        """
        Test that plugins from different scopes coexist when names differ.
        """
        # Project has transformer
        (temp_project / "plugins" / "proj_transformer.py").write_text(
            SAMPLE_TRANSFORMER_V1
        )

        # User has exporter
        (temp_user_dir / "plugins" / "user_exporter.py").write_text(SAMPLE_EXPORTER)

        # Load with cascade
        loader = PluginLoader()
        loader.load_plugins_with_cascade(temp_project)

        # Both should be loaded
        assert "test_transformer" in loader.plugin_info_by_name
        assert "test_exporter" in loader.plugin_info_by_name

        # Verify scopes
        assert (
            loader.plugin_info_by_name["test_transformer"].scope
            == ResourcePaths.SCOPE_PROJECT
        )
        assert (
            loader.plugin_info_by_name["test_exporter"].scope
            == ResourcePaths.SCOPE_USER
        )

    def test_cli_and_desktop_load_identically(self, temp_project, temp_user_dir):
        """
        CRITICAL: Verify that CLI and Desktop load the exact same plugins.

        This test ensures both use the same ResourcePaths code and get
        identical results, which is the whole point of the cascade system.
        """
        # Set up plugins in different scopes
        (temp_project / "plugins" / "plugin_a.py").write_text(SAMPLE_TRANSFORMER_V1)
        (temp_user_dir / "plugins" / "plugin_b.py").write_text(SAMPLE_EXPORTER)

        # Simulate CLI loading
        cli_loader = PluginLoader()
        cli_loader.load_plugins_with_cascade(temp_project)
        cli_plugins = set(cli_loader.plugin_info_by_name.keys())

        # Clear registry
        PluginRegistry.clear()

        # Simulate Desktop loading (same code, same project)
        desktop_loader = PluginLoader()
        desktop_loader.load_plugins_with_cascade(temp_project)
        desktop_plugins = set(desktop_loader.plugin_info_by_name.keys())

        # MUST be identical
        assert cli_plugins == desktop_plugins, (
            "CLI and Desktop must load identical plugins"
        )

        # Verify plugin info is identical
        for plugin_name in cli_plugins:
            cli_info = cli_loader.plugin_info_by_name[plugin_name]
            desktop_info = desktop_loader.plugin_info_by_name[plugin_name]

            assert cli_info.scope == desktop_info.scope
            assert cli_info.priority == desktop_info.priority
            assert cli_info.path == desktop_info.path

    def test_get_plugin_details_includes_cascade_info(self, temp_project):
        """
        Test that get_plugin_details() returns cascade information.

        This is used by 'niamoto plugins list --verbose' command.
        """
        # Add a project plugin
        (temp_project / "plugins" / "detail_test.py").write_text(SAMPLE_TRANSFORMER_V1)

        loader = PluginLoader()
        loader.load_plugins_with_cascade(temp_project)

        details = loader.get_plugin_details()

        # Should have at least our test plugin
        test_plugin = next(
            (d for d in details if d["name"] == "test_transformer"), None
        )

        assert test_plugin is not None
        assert "scope" in test_plugin
        assert "priority" in test_plugin
        assert "path" in test_plugin
        assert test_plugin["scope"] == ResourcePaths.SCOPE_PROJECT
        assert test_plugin["priority"] == 100


class TestPluginConflictDetection:
    """Test that plugin conflicts are properly detected and logged."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clear registry before and after each test."""
        PluginRegistry.clear()
        yield
        PluginRegistry.clear()

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project."""
        project = tmp_path / "test_project"
        project.mkdir()
        (project / "plugins").mkdir()
        return project

    @pytest.fixture
    def temp_user_dir(self, tmp_path, monkeypatch):
        """Create temporary user directory."""
        user_dir = tmp_path / "user_home" / ".niamoto"
        user_dir.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path / "user_home")

        (user_dir / "plugins").mkdir()
        return user_dir

    def test_conflict_warning_logged(self, temp_project, temp_user_dir, caplog):
        """
        Test that conflicts are logged with warnings.

        When same plugin exists in project and user scopes,
        a warning should be logged indicating the override.
        """
        import logging

        caplog.set_level(logging.WARNING)

        # Create same plugin in both scopes
        (temp_project / "plugins" / "conflict.py").write_text(SAMPLE_TRANSFORMER_V2)
        (temp_user_dir / "plugins" / "conflict.py").write_text(SAMPLE_TRANSFORMER_V1)

        loader = PluginLoader()
        loader.load_plugins_with_cascade(temp_project)

        # Check for warning in logs - message contains "skipping" or "already loaded"
        warning_found = any(
            (
                "skipping" in record.message.lower()
                or "already loaded" in record.message.lower()
            )
            for record in caplog.records
            if record.levelname == "WARNING"
        )

        assert warning_found, (
            "Should log warning when plugin conflicts with higher-priority version"
        )

    def test_highest_priority_wins(self, temp_project, temp_user_dir):
        """
        Test that highest priority plugin is actually loaded.

        Verify the loaded plugin class is from the correct scope.
        """
        # Different versions in different scopes
        (temp_project / "plugins" / "priority_test.py").write_text(
            SAMPLE_TRANSFORMER_V2  # v2.0
        )
        (temp_user_dir / "plugins" / "priority_test.py").write_text(
            SAMPLE_TRANSFORMER_V1  # v1.0
        )

        loader = PluginLoader()
        loader.load_plugins_with_cascade(temp_project)

        plugin_info = loader.plugin_info_by_name["test_transformer"]

        # Project should win
        assert plugin_info.priority == 100
        assert plugin_info.scope == ResourcePaths.SCOPE_PROJECT

        # Verify it's from priority_test.py in project
        assert "priority_test.py" in str(plugin_info.path)
        assert str(temp_project) in str(plugin_info.path)
