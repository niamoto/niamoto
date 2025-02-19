# core/plugins/plugin_loader.py
import sys
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Set, Dict, Any
from .base import PluginType
from .exceptions import PluginLoadError
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Loader for Niamoto plugins, handling both core and third-party plugins.
    """

    def __init__(self):
        self.loaded_plugins: Set[str] = set()
        self.plugin_paths: Dict[str, str] = {}

    def load_core_plugins(self) -> None:
        """
        Load core plugins bundled with Niamoto.

        Raises:
            PluginLoadError: If loading of core plugins fails
        """
        try:
            core_plugins_path = Path(__file__).parent

            # Load plugins for each type
            for plugin_type in PluginType:
                plugin_dir = core_plugins_path.joinpath(f"{plugin_type.value}s")
                if plugin_dir.exists():
                    self._load_plugins_from_dir(plugin_dir, is_core=True)

        except Exception as e:
            raise PluginLoadError(
                "Failed to load core plugins", details={"error": str(e)}
            )

    def load_project_plugins(self, project_path: str) -> None:
        """
        Load plugins from a project directory.

        Args:
            project_path: Path to the project root

        Raises:
            PluginLoadError: If loading of project plugins fails
        """
        try:
            plugins_dir = Path(project_path) / "plugins"
            if not plugins_dir.exists():
                logger.info(f"No plugins directory found at {plugins_dir}")
                return

            # Add project path to Python path for imports
            if str(project_path) not in sys.path:
                sys.path.insert(0, str(project_path))

            # Load plugins for each type
            for plugin_type in PluginType:
                type_dir = plugins_dir / (plugin_type.value + "s")
                if type_dir.exists():
                    self._load_plugins_from_dir(type_dir)

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load project plugins from {project_path}",
                details={"error": str(e)},
            )

    def _load_plugins_from_dir(self, directory: Path, is_core: bool = False) -> None:
        """
        Load all plugins from a directory.

        Args:
            directory: Directory containing plugin files
            is_core: Whether these are core plugins

        Raises:
            PluginLoadError: If loading of plugins fails
        """
        try:
            for file in directory.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                module_name = self._get_module_name(file, is_core)
                if module_name in self.loaded_plugins:
                    continue

                try:
                    self._load_plugin_module(file, module_name)
                    self.loaded_plugins.add(module_name)
                    self.plugin_paths[module_name] = str(file)
                except Exception as e:
                    logger.error(f"Failed to load plugin {file.name}: {str(e)}")

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load plugins from {directory}", details={"error": str(e)}
            )

    def _get_module_name(self, file: Path, is_core: bool) -> str:
        """
        Generate module name for a plugin file.

        Args:
            file: Plugin file path
            is_core: Whether this is a core plugin

        Returns:
            Module name for import
        """
        if is_core:
            # Core plugins use absolute import path
            parts = file.relative_to(Path(__file__).parent).with_suffix("").parts
            return f"niamoto.core.plugins.{'.'.join(parts)}"
        else:
            # Project plugins use relative import path
            return f"plugins.{file.parent.name}.{file.stem}"

    def _load_plugin_module(self, file: Path, module_name: str) -> None:
        """
        Load a single plugin module.

        Args:
            file: Plugin file path
            module_name: Name for the module

        Raises:
            PluginLoadError: If loading of module fails
        """
        try:
            spec = importlib.util.spec_from_file_location(module_name, file)
            if spec is None:
                raise PluginLoadError(
                    f"Failed to create spec for {module_name}",
                    details={"file": str(file)},
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module

            if spec.loader is None:
                raise PluginLoadError(
                    f"No loader found for {module_name}", details={"file": str(file)}
                )

            spec.loader.exec_module(module)

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load module {module_name}",
                details={"file": str(file), "error": str(e)},
            )

    def get_plugin_info(self) -> Dict[str, Any]:
        """
        Get information about loaded plugins.

        Returns:
            Dictionary containing plugin information
        """
        return {
            "loaded_plugins": list(self.loaded_plugins),
            "plugin_paths": self.plugin_paths,
            "plugins_by_type": PluginRegistry.list_plugins(),
        }

    def reload_plugin(self, module_name: str) -> None:
        """
        Reload a specific plugin module.

        Args:
            module_name: Name of module to reload

        Raises:
            PluginLoadError: If reload fails
        """
        try:
            if module_name not in self.loaded_plugins:
                raise PluginLoadError(
                    f"Plugin {module_name} not loaded",
                    details={"loaded_plugins": list(self.loaded_plugins)},
                )

            file_path = self.plugin_paths.get(module_name)
            if not file_path:
                raise PluginLoadError(
                    f"No file path found for {module_name}",
                    details={"module": module_name},
                )

            # Remove from loaded plugins
            self.loaded_plugins.remove(module_name)

            # Remove from sys.modules to force reload
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Reload module
            self._load_plugin_module(Path(file_path), module_name)
            self.loaded_plugins.add(module_name)

        except Exception as e:
            raise PluginLoadError(
                f"Failed to reload plugin {module_name}", details={"error": str(e)}
            )

    def unload_plugin(self, module_name: str) -> None:
        """
        Unload a specific plugin module.

        Args:
            module_name: Name of module to unload

        Raises:
            PluginLoadError: If unload fails
        """
        try:
            if module_name not in self.loaded_plugins:
                raise PluginLoadError(
                    f"Plugin {module_name} not loaded",
                    details={"loaded_plugins": list(self.loaded_plugins)},
                )

            # Remove from loaded plugins
            self.loaded_plugins.remove(module_name)

            # Remove from sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Remove from plugin paths
            self.plugin_paths.pop(module_name, None)

            # Remove from registry
            # Note: This requires knowing the plugin type and name
            # You might want to store this information when loading

        except Exception as e:
            raise PluginLoadError(
                f"Failed to unload plugin {module_name}", details={"error": str(e)}
            )
