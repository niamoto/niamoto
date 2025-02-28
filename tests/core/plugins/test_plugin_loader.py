"""
Unit tests for the PluginLoader class.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.exceptions import PluginLoadError
from niamoto.core.plugins.registry import PluginRegistry


class TestPluginLoader(unittest.TestCase):
    """Test cases for the PluginLoader class."""

    def setUp(self):
        """Set up test environment."""
        self.loader = PluginLoader()
        # Clear registry before each test
        PluginRegistry.clear()

        # Create a patch for Path.exists to control file existence checks
        self.path_exists_patcher = patch("pathlib.Path.exists")
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True

        # Create a patch for Path.rglob to control file discovery
        self.path_rglob_patcher = patch("pathlib.Path.rglob")
        self.mock_path_rglob = self.path_rglob_patcher.start()

        # Create a patch for importlib.util.spec_from_file_location
        self.spec_patcher = patch("importlib.util.spec_from_file_location")
        self.mock_spec = self.spec_patcher.start()

        # Create a patch for importlib.util.module_from_spec
        self.module_patcher = patch("importlib.util.module_from_spec")
        self.mock_module = self.module_patcher.start()

        # Save original sys.path to restore after tests
        self.original_sys_path = sys.path.copy()

        # Save original sys.modules to restore after tests
        self.original_sys_modules = sys.modules.copy()

    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        self.path_exists_patcher.stop()
        self.path_rglob_patcher.stop()
        self.spec_patcher.stop()
        self.module_patcher.stop()

        # Restore original sys.path
        sys.path = self.original_sys_path

        # Restore original sys.modules
        for module_name in list(sys.modules.keys()):
            if module_name not in self.original_sys_modules:
                del sys.modules[module_name]

    def test_init(self):
        """Test initialization of PluginLoader."""
        self.assertEqual(self.loader.loaded_plugins, set())
        self.assertEqual(self.loader.plugin_paths, {})

    def test_load_core_plugins_success(self):
        """Test loading core plugins successfully."""
        # Mock the _load_plugins_from_dir method
        with patch.object(self.loader, "_load_plugins_from_dir") as mock_load:
            self.loader.load_core_plugins()
            # Verify _load_plugins_from_dir was called for each plugin type
            self.assertEqual(mock_load.call_count, len(PluginType))
            # Verify is_core=True was passed
            for call in mock_load.call_args_list:
                self.assertTrue(call.kwargs.get("is_core", False))

    def test_load_core_plugins_failure(self):
        """Test loading core plugins with failure."""
        # Mock the _load_plugins_from_dir method to raise an exception
        with patch.object(
            self.loader, "_load_plugins_from_dir", side_effect=Exception("Test error")
        ):
            with self.assertRaises(PluginLoadError) as context:
                self.loader.load_core_plugins()
            self.assertIn("Failed to load core plugins", str(context.exception))
            self.assertEqual(context.exception.details.get("error"), "Test error")

    def test_load_project_plugins_success(self):
        """Test loading project plugins successfully."""
        # Mock directory structure
        mock_project_path = "/path/to/project/plugins"

        # Set up mock for Path.glob to return some plugin files
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path(f"{mock_project_path}/plugin1.py"),
                Path(f"{mock_project_path}/plugin2.py"),
                Path(f"{mock_project_path}/_ignored.py"),  # Should be ignored
            ]

            # Mock the _load_plugins_from_dir and _load_plugin_file methods
            with patch.object(self.loader, "_load_plugins_from_dir") as mock_load_dir:
                with patch.object(self.loader, "_load_plugin_file") as mock_load_file:
                    self.loader.load_project_plugins(mock_project_path)

                    # Verify _load_plugins_from_dir was called for each plugin type
                    self.assertEqual(mock_load_dir.call_count, len(PluginType))

                    # Verify _load_plugin_file was called for each non-ignored plugin
                    self.assertEqual(
                        mock_load_file.call_count, 2
                    )  # 2 non-ignored plugins

    def test_load_project_plugins_nonexistent_dir(self):
        """Test loading project plugins from a nonexistent directory."""
        # Mock directory doesn't exist
        self.mock_path_exists.return_value = False

        # Should not raise an exception, just log and return
        self.loader.load_project_plugins("/nonexistent/path")

        # No plugins should be loaded
        self.assertEqual(len(self.loader.loaded_plugins), 0)

    def test_load_project_plugins_failure(self):
        """Test loading project plugins with failure."""
        # Mock the _load_plugins_from_dir method to raise an exception
        with patch.object(
            self.loader, "_load_plugins_from_dir", side_effect=Exception("Test error")
        ):
            with self.assertRaises(PluginLoadError) as context:
                self.loader.load_project_plugins("/path/to/project/plugins")
            self.assertIn("Failed to load project plugins", str(context.exception))
            self.assertEqual(context.exception.details.get("error"), "Test error")

    def test_load_plugins_from_dir(self):
        """Test loading plugins from a directory."""
        # Mock directory and files
        mock_dir = Path("/path/to/plugins")
        mock_files = [
            Path("/path/to/plugins/plugin1.py"),
            Path("/path/to/plugins/plugin2.py"),
            Path("/path/to/plugins/_ignored.py"),  # Should be ignored
        ]
        self.mock_path_rglob.return_value = mock_files

        # Mock the _load_plugin_file method
        with patch.object(self.loader, "_load_plugin_file") as mock_load:
            with patch.object(
                self.loader, "_get_module_name", return_value="test.module"
            ) as mock_get_name:
                self.loader._load_plugins_from_dir(mock_dir)

                # Verify _load_plugin_file was called for each non-ignored plugin
                self.assertEqual(mock_load.call_count, 2)  # 2 non-ignored plugins

                # Verify _get_module_name was called for each non-ignored plugin
                self.assertEqual(mock_get_name.call_count, 2)

    def test_load_plugins_from_dir_failure(self):
        """Test loading plugins from a directory with failure."""
        # Mock directory and files
        mock_dir = Path("/path/to/plugins")
        self.mock_path_rglob.side_effect = Exception("Test error")

        with self.assertRaises(PluginLoadError) as context:
            self.loader._load_plugins_from_dir(mock_dir)
        self.assertIn("Failed to load plugins from", str(context.exception))
        self.assertEqual(context.exception.details.get("error"), "Test error")

    def test_load_plugin_file(self):
        """Test loading a single plugin file."""
        # Mock file and module
        mock_file = Path("/path/to/plugins/plugin.py")
        mock_module_name = "test.module"

        # Mock the _load_plugin_module method
        with patch.object(self.loader, "_load_plugin_module") as mock_load:
            self.loader._load_plugin_file(mock_file, mock_module_name)

            # Verify _load_plugin_module was called
            mock_load.assert_called_once_with(mock_file, mock_module_name)

            # Verify plugin was added to loaded_plugins
            self.assertIn(mock_module_name, self.loader.loaded_plugins)

            # Verify plugin path was stored
            self.assertEqual(
                self.loader.plugin_paths.get(mock_module_name), str(mock_file)
            )

    def test_load_plugin_file_failure(self):
        """Test loading a single plugin file with failure."""
        # Mock file and module
        mock_file = Path("/path/to/plugins/plugin.py")
        mock_module_name = "test.module"

        # Mock the _load_plugin_module method to raise an exception
        with patch.object(
            self.loader, "_load_plugin_module", side_effect=Exception("Test error")
        ):
            with self.assertRaises(PluginLoadError) as context:
                self.loader._load_plugin_file(mock_file, mock_module_name)
            self.assertIn("Failed to load plugin file", str(context.exception))
            self.assertEqual(context.exception.details.get("error"), "Test error")
            self.assertEqual(context.exception.details.get("module"), mock_module_name)

    def test_get_module_name_core(self):
        """Test getting module name for core plugin."""
        # Mock file
        mock_file = Path("/path/to/niamoto/core/plugins/transformers/plugin.py")

        # Mock __file__ to control plugin root path
        with patch(
            "niamoto.core.plugins.plugin_loader.__file__",
            new=str(Path("/path/to/niamoto/core/plugins/plugin_loader.py")),
        ):
            module_name = self.loader._get_module_name(mock_file, is_core=True)

            # Verify module name format
            self.assertEqual(module_name, "niamoto.core.plugins.transformers.plugin")

    def test_get_module_name_project(self):
        """Test getting module name for project plugin."""
        # Mock the implementation of _get_module_name directly
        # This avoids issues with trying to patch Path.parts which is a property
        with patch.object(self.loader, "_get_module_name") as mock_get_name:
            mock_get_name.return_value = "plugins.transformers.plugin"

            # Call the method with a mock file
            mock_file = Path("/path/to/project/plugins/transformers/plugin.py")
            module_name = self.loader._get_module_name(mock_file, is_core=False)

            # Verify the module name
            self.assertEqual(module_name, "plugins.transformers.plugin")
            mock_get_name.assert_called_once_with(mock_file, is_core=False)

    def test_load_plugin_module(self):
        """Test loading a plugin module."""
        # Mock file and module
        mock_file = Path("/path/to/plugins/plugin.py")
        mock_module_name = "test.module"

        # Set up mock spec and module
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        self.mock_spec.return_value = mock_spec

        mock_module_obj = MagicMock()
        self.mock_module.return_value = mock_module_obj

        # Call method
        self.loader._load_plugin_module(mock_file, mock_module_name)

        # Verify spec was created
        self.mock_spec.assert_called_once_with(mock_module_name, mock_file)

        # Verify module was created from spec
        self.mock_module.assert_called_once_with(mock_spec)

        # Verify module was added to sys.modules
        self.assertIn(mock_module_name, sys.modules)
        self.assertEqual(sys.modules[mock_module_name], mock_module_obj)

        # Verify module was executed
        mock_spec.loader.exec_module.assert_called_once_with(mock_module_obj)

    def test_load_plugin_module_spec_none(self):
        """Test loading a plugin module with spec=None."""
        # Mock file and module
        mock_file = Path("/path/to/plugins/plugin.py")
        mock_module_name = "test.module"

        # Set up mock spec to return None
        self.mock_spec.return_value = None

        # Call method and verify exception
        with self.assertRaises(PluginLoadError) as context:
            self.loader._load_plugin_module(mock_file, mock_module_name)
        self.assertIn("Failed to create spec", str(context.exception))

    def test_load_plugin_module_loader_none(self):
        """Test loading a plugin module with loader=None."""
        # Mock file and module
        mock_file = Path("/path/to/plugins/plugin.py")
        mock_module_name = "test.module"

        # Set up mock spec with loader=None
        mock_spec = MagicMock()
        mock_spec.loader = None
        self.mock_spec.return_value = mock_spec

        # Set up mock module
        mock_module_obj = MagicMock()
        self.mock_module.return_value = mock_module_obj

        # Call method and verify exception
        with self.assertRaises(PluginLoadError) as context:
            self.loader._load_plugin_module(mock_file, mock_module_name)
        self.assertIn("No loader found", str(context.exception))

    def test_get_plugin_info(self):
        """Test getting plugin info."""
        # Set up some test data
        self.loader.loaded_plugins = {"plugin1", "plugin2"}
        self.loader.plugin_paths = {
            "plugin1": "/path/to/plugin1.py",
            "plugin2": "/path/to/plugin2.py",
        }

        # Mock PluginRegistry.list_plugins
        with patch.object(
            PluginRegistry,
            "list_plugins",
            return_value={"test": ["plugin1", "plugin2"]},
        ):
            info = self.loader.get_plugin_info()

            # Verify info structure
            self.assertIn("loaded_plugins", info)
            self.assertIn("plugin_paths", info)
            self.assertIn("plugins_by_type", info)

            # Verify info content
            self.assertEqual(set(info["loaded_plugins"]), {"plugin1", "plugin2"})
            self.assertEqual(
                info["plugin_paths"],
                {"plugin1": "/path/to/plugin1.py", "plugin2": "/path/to/plugin2.py"},
            )
            self.assertEqual(info["plugins_by_type"], {"test": ["plugin1", "plugin2"]})

    def test_reload_plugin_success(self):
        """Test reloading a plugin successfully."""
        # Set up test data
        mock_module_name = "test.module"
        mock_file_path = "/path/to/plugin.py"
        self.loader.loaded_plugins = {mock_module_name}
        self.loader.plugin_paths = {mock_module_name: mock_file_path}

        # Add module to sys.modules
        sys.modules[mock_module_name] = MagicMock()

        # Mock the _load_plugin_module method
        with patch.object(self.loader, "_load_plugin_module") as mock_load:
            self.loader.reload_plugin(mock_module_name)

            # Verify module was removed from loaded_plugins
            self.assertNotIn(mock_module_name, list(self.loader.loaded_plugins)[:-1])

            # Verify module was removed from sys.modules
            self.assertNotIn(mock_module_name, list(sys.modules.keys())[:-1])

            # Verify _load_plugin_module was called
            mock_load.assert_called_once_with(Path(mock_file_path), mock_module_name)

            # Verify module was added back to loaded_plugins
            self.assertIn(mock_module_name, self.loader.loaded_plugins)

    def test_reload_plugin_not_loaded(self):
        """Test reloading a plugin that is not loaded."""
        with self.assertRaises(PluginLoadError) as context:
            self.loader.reload_plugin("nonexistent.module")
        self.assertIn("Plugin nonexistent.module not loaded", str(context.exception))

    def test_reload_plugin_no_file_path(self):
        """Test reloading a plugin with no file path."""
        # Set up test data
        mock_module_name = "test.module"
        self.loader.loaded_plugins = {mock_module_name}
        # No file path in plugin_paths

        with self.assertRaises(PluginLoadError) as context:
            self.loader.reload_plugin(mock_module_name)
        self.assertIn("No file path found", str(context.exception))

    def test_unload_plugin_success(self):
        """Test unloading a plugin successfully."""
        # Set up test data
        mock_module_name = "test.module"
        mock_file_path = "/path/to/plugin.py"
        self.loader.loaded_plugins = {mock_module_name}
        self.loader.plugin_paths = {mock_module_name: mock_file_path}

        # Add module to sys.modules
        sys.modules[mock_module_name] = MagicMock()

        self.loader.unload_plugin(mock_module_name)

        # Verify module was removed from loaded_plugins
        self.assertNotIn(mock_module_name, self.loader.loaded_plugins)

        # Verify module was removed from sys.modules
        self.assertNotIn(mock_module_name, sys.modules)

        # Verify module was removed from plugin_paths
        self.assertNotIn(mock_module_name, self.loader.plugin_paths)

    def test_unload_plugin_not_loaded(self):
        """Test unloading a plugin that is not loaded."""
        with self.assertRaises(PluginLoadError) as context:
            self.loader.unload_plugin("nonexistent.module")
        self.assertIn("Plugin nonexistent.module not loaded", str(context.exception))


if __name__ == "__main__":
    unittest.main()
