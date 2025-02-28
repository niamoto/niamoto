# core/plugins/plugin_loader.py
import sys
import importlib
import importlib.util
import logging
import os
import inspect
from pathlib import Path
from typing import Set, Dict, Any, List
from .base import PluginType
from .exceptions import PluginLoadError
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


def is_plugin_class(obj):
    """
    Check if an object is a plugin class.

    Args:
        obj: Object to check

    Returns:
        True if the object is a plugin class, False otherwise
    """
    try:
        return hasattr(obj, "type") and isinstance(obj.type, PluginType)
    except Exception:
        return False


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
            project_path: Path to the project plugins directory

        Raises:
            PluginLoadError: If loading of project plugins fails
        """
        try:
            plugins_dir = Path(
                project_path
            )  # project_path is already the plugins directory

            if not plugins_dir.exists():
                logger.info(f"No plugins directory found at {plugins_dir}")
                return

            # Add project path to Python path for imports
            project_root = str(
                plugins_dir.parent
            )  # Go up one level from plugins directory to get project root
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            else:
                print(f"DEBUG: {project_root} already in sys.path")

            # Load plugins for each type
            for plugin_type in PluginType:
                type_dir = plugins_dir / (plugin_type.value + "s")
                if type_dir.exists():
                    self._load_plugins_from_dir(type_dir)

            # Also check top-level plugins
            for file in plugins_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue
                module_name = f"plugins.{file.stem}"
                try:
                    self._load_plugin_file(file, module_name)
                except Exception as e:
                    print(
                        f"DEBUG ERROR: Failed to load top-level plugin {file.name}: {str(e)}"
                    )

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load project plugins from {project_path}",
                details={"error": str(e)},
            )

    def _load_plugins_from_dir(self, directory: Path, is_core: bool = False) -> None:
        """
        Load all plugins from a directory recursively.

        Args:
            directory: Directory containing plugin files
            is_core: Whether these are core plugins

        Raises:
            PluginLoadError: If loading of plugins fails
        """
        try:
            # Recursively find all .py files
            for file in directory.rglob("*.py"):
                # Skip __init__.py and other files starting with _
                if file.name.startswith("_"):
                    continue

                module_name = self._get_module_name(file, is_core)
                if module_name in self.loaded_plugins:
                    continue

                try:
                    self._load_plugin_file(file, module_name)
                except Exception as e:
                    logger.error(f"Failed to load plugin {file.name}: {str(e)}")

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load plugins from {directory}", details={"error": str(e)}
            )

    def _load_plugin_file(self, file: Path, module_name: str) -> None:
        """
        Load a single plugin file and register it.

        Args:
            file: Plugin file path
            module_name: Module name for the plugin

        Raises:
            PluginLoadError: If loading fails
        """
        try:
            self._load_plugin_module(file, module_name)
            self.loaded_plugins.add(module_name)
            self.plugin_paths[module_name] = str(file)
        except Exception as e:
            raise PluginLoadError(
                f"Failed to load plugin file {file}",
                details={"error": str(e), "module": module_name},
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
            # Get path relative to plugins directory (2 levels up from file's parent)
            plugin_root = Path(__file__).parent
            relative_path = file.relative_to(plugin_root).with_suffix("")
            return f"niamoto.core.plugins.{'.'.join(relative_path.parts)}"
        else:
            # Project plugins use relative import path from plugins directory
            # Include all subdirectories in the module path
            relative_path = file.relative_to(file.parents[file.parts.index("plugins")])
            return f"plugins.{'.'.join(relative_path.with_suffix('').parts)}"

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

            # Find and unregister existing plugins from this module
            self._unregister_module_plugins(module_name)

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

    def _unregister_module_plugins(self, module_name: str) -> None:
        """
        Unregister all plugins from a specific module.

        Args:
            module_name: Name of the module
        """
        # Get all registered plugins
        all_plugins = PluginRegistry.list_plugins()

        # For each plugin type
        for plugin_type, plugins in all_plugins.items():
            # Convert string to PluginType enum
            plugin_type_enum = PluginType(plugin_type)

            # Get all plugins for this type
            plugins_by_type = PluginRegistry.get_plugins_by_type(plugin_type_enum)

            # Check each plugin to see if it belongs to this module
            for plugin_name, plugin_class in list(plugins_by_type.items()):
                if plugin_class.__module__ == module_name:
                    # Unregister this plugin
                    PluginRegistry.remove_plugin(plugin_name, plugin_type_enum)
                    logger.debug(
                        f"Unregistered plugin {plugin_name} of type {plugin_type}"
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

            # Find and unregister existing plugins from this module
            self._unregister_module_plugins(module_name)

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

    def discover_plugins(self, directory: Path) -> List[Dict[str, str]]:
        """
        Discover plugins in a directory without loading them.

        Args:
            directory: Directory to search for plugins

        Returns:
            List of discovered plugin information dictionaries
        """
        discovered = []

        try:
            if not directory.exists():
                logger.warning(f"Directory does not exist: {directory}")
                return []

            # Walk through the directory
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)

                # Skip directories starting with underscore
                dirs[:] = [d for d in dirs if not d.startswith("_")]

                # Process Python files
                for file in files:
                    if file.endswith(".py") and not file.startswith("_"):
                        file_path = root_path / file

                        # Determine plugin type from directory structure
                        rel_path = file_path.relative_to(directory)
                        parts = rel_path.parts

                        plugin_type = None
                        if len(parts) > 0:
                            # Check if the first directory indicates a plugin type
                            type_dir = parts[0]
                            if type_dir.endswith("s") and type_dir[:-1] in [
                                t.value for t in PluginType
                            ]:
                                plugin_type = type_dir[:-1]

                        # If type couldn't be determined from directory, try to load and check
                        if not plugin_type:
                            try:
                                # Get module name
                                is_core = "niamoto/core/plugins" in str(file_path)
                                module_name = self._get_module_name(file_path, is_core)

                                # Try to import the module to check for plugin classes
                                spec = importlib.util.spec_from_file_location(
                                    module_name, file_path
                                )
                                if spec and spec.loader:
                                    module = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(module)

                                    # Look for plugin classes
                                    for name, obj in inspect.getmembers(module):
                                        if inspect.isclass(obj) and is_plugin_class(
                                            obj
                                        ):
                                            plugin_type = obj.type.value
                                            break
                            except Exception as e:
                                logger.debug(
                                    f"Error inspecting plugin {file_path}: {str(e)}"
                                )
                                continue

                        if plugin_type:
                            # Add to discovered plugins
                            is_core = "niamoto/core/plugins" in str(file_path)
                            module_name = self._get_module_name(file_path, is_core)

                            discovered.append(
                                {
                                    "path": str(file_path),
                                    "module": module_name,
                                    "name": file_path.stem,
                                    "type": plugin_type,
                                }
                            )

        except Exception as e:
            logger.error(f"Error discovering plugins: {str(e)}")

        return discovered

    def register_plugin(
        self, module_name: str, class_name: str, plugin_type: str
    ) -> None:
        """
        Register a plugin without fully loading it.

        Args:
            module_name: Name of the module containing the plugin
            class_name: Name of the plugin class
            plugin_type: Type of the plugin

        Raises:
            PluginLoadError: If registration fails
        """
        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Get the plugin class
            plugin_class = getattr(module, class_name)

            # Register the plugin
            plugin_type_enum = PluginType(plugin_type)
            PluginRegistry.register_plugin(plugin_class, plugin_type_enum)

            # Add to loaded plugins
            self.loaded_plugins.add(module_name)

        except Exception as e:
            raise PluginLoadError(
                f"Failed to register plugin {module_name}.{class_name}",
                details={"error": str(e)},
            )

    def load_plugin(self, module_name: str, class_name: str):
        """
        Load a plugin class from a module.

        Args:
            module_name: Name of the module containing the plugin
            class_name: Name of the plugin class

        Returns:
            The plugin class

        Raises:
            PluginLoadError: If loading fails
        """
        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Get the plugin class
            plugin_class = getattr(module, class_name)

            return plugin_class

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load plugin {module_name}.{class_name}",
                details={"error": str(e)},
            )
