"""
Plugin loader module for Niamoto.

This module provides dynamic plugin loading capabilities for both core and project-specific
plugins. It handles:

- Dynamic loading and unloading of plugins
- Plugin discovery and registration
- Module path resolution and import management
- Hot reloading of plugins during development
- Plugin dependency management

The loader supports a hierarchical plugin structure and maintains plugin state
throughout the application lifecycle. It includes safeguards for handling import
errors and plugin conflicts.
"""

# core/plugins/plugin_loader.py
import sys
import importlib
import importlib.util
import logging
import os
import inspect
from pathlib import Path
from typing import Set, Dict, Any, List, Optional
from dataclasses import dataclass

from .base import PluginType
from .exceptions import PluginLoadError
from .registry import PluginRegistry
from niamoto.common.resource_paths import ResourcePaths, ResourceLocation

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Information about a loaded plugin including its scope and priority"""

    name: str
    plugin_class: type
    scope: str  # "project", "user", "system"
    path: Path
    priority: int
    module_name: str


# List of core plugin modules to load automatically
CORE_PLUGIN_MODULES = [
    "niamoto.core.plugins.transformers",
    "niamoto.core.plugins.exporters",
    "niamoto.core.plugins.widgets",
]


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

    Supports cascade resolution across three scopes:
    - Project-local (~/.niamoto/plugins) - priority 100
    - User-global (project/.niamoto/plugins) - priority 50
    - System built-in (niamoto/core/plugins) - priority 10
    """

    def __init__(self):
        self.loaded_plugins: Set[str] = set()
        self.plugin_paths: Dict[str, str] = {}
        self.plugin_info_by_name: Dict[str, PluginInfo] = {}  # Track plugin metadata

    def load_plugins_with_cascade(self, project_path: Optional[Path] = None) -> None:
        """
        Load plugins using cascade resolution (Project > User > System).

        This is the NEW UNIFIED method that replaces load_core_plugins() + load_project_plugins().
        It uses ResourcePaths to discover plugins across all scopes and handles conflicts.

        Args:
            project_path: Optional project path for project-local plugins

        Raises:
            PluginLoadError: If loading fails
        """
        try:
            # Get all plugin locations via ResourcePaths
            locations = ResourcePaths.get_plugin_paths(project_path)

            logger.info("=" * 60)
            logger.info("Loading plugins with cascade resolution")
            logger.info("=" * 60)

            # Log scanning paths
            for location in locations:
                status = "✓" if location.exists else "✗"
                logger.info(
                    f"{status} Scanning {location.scope} plugins: {location.path} (priority: {location.priority})"
                )

            # Collect all plugins from all locations (in priority order: high to low)
            # Process Project first, then User, then System
            # First plugin found wins - this ensures highest priority plugin is registered first
            # in the registry, and duplicates from lower-priority scopes are automatically rejected
            discovered_plugins: Dict[str, PluginInfo] = {}

            for location in locations:  # Process high priority first (already sorted)
                if not location.exists:
                    continue

                # Scan this location for plugins
                location_plugins = self._discover_plugins_in_location(location)

                for plugin_name, plugin_info in location_plugins.items():
                    if plugin_name in discovered_plugins:
                        # CONFLICT: This plugin was already found in a higher-priority scope
                        # Skip this lower-priority version
                        previous = discovered_plugins[plugin_name]
                        logger.warning(
                            f"⚠️  Skipping '{plugin_name}' from {location.scope} ({location.path}) "
                            f"- already loaded from {previous.scope} (priority {previous.priority})"
                        )
                        continue

                    # First occurrence of this plugin - add it
                    discovered_plugins[plugin_name] = plugin_info

            # Now load the discovered plugins
            logger.info("")
            logger.info(f"Loading {len(discovered_plugins)} unique plugins:")

            for plugin_name, plugin_info in discovered_plugins.items():
                try:
                    # Actually load and register the plugin
                    self._load_and_register_plugin(plugin_info)
                    logger.info(
                        f"  ✓ Loaded '{plugin_name}' from {plugin_info.scope} "
                        f"(priority: {plugin_info.priority})"
                    )
                except Exception as e:
                    logger.error(f"  ✗ Failed to load '{plugin_name}': {str(e)}")

            # Summary
            logger.info("")
            logger.info("Plugin loading summary:")
            scopes_count = {"project": 0, "user": 0, "system": 0}
            for plugin_info in discovered_plugins.values():
                scopes_count[plugin_info.scope] = (
                    scopes_count.get(plugin_info.scope, 0) + 1
                )

            logger.info(f"  Total plugins: {len(discovered_plugins)}")
            logger.info(f"    - Project: {scopes_count.get('project', 0)}")
            logger.info(f"    - User: {scopes_count.get('user', 0)}")
            logger.info(f"    - System: {scopes_count.get('system', 0)}")
            logger.info("=" * 60)

        except Exception as e:
            raise PluginLoadError(
                "Failed to load plugins with cascade", details={"error": str(e)}
            )

    def _discover_plugins_in_location(
        self, location: ResourceLocation
    ) -> Dict[str, PluginInfo]:
        """
        Discover all plugins in a specific location.

        Args:
            location: ResourceLocation to scan

        Returns:
            Dictionary mapping plugin names to PluginInfo
        """
        plugins = {}

        try:
            # Scan for .py files recursively
            for file in location.path.rglob("*.py"):
                if file.name.startswith("_"):
                    continue

                # Determine module name based on scope
                is_core = location.scope == ResourcePaths.SCOPE_SYSTEM
                module_name = self._get_module_name(file, is_core)

                # Try to extract plugin class
                try:
                    # Quick inspection to find plugin classes
                    spec = importlib.util.spec_from_file_location(module_name, file)
                    if not spec or not spec.loader:
                        continue

                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin classes in this module
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and is_plugin_class(obj):
                            plugin_name = getattr(obj, "name", file.stem)

                            plugins[plugin_name] = PluginInfo(
                                name=plugin_name,
                                plugin_class=obj,
                                scope=location.scope,
                                path=file,
                                priority=location.priority,
                                module_name=module_name,
                            )

                except Exception as e:
                    # Check if this is a registration conflict (plugin already registered)
                    from niamoto.core.plugins.exceptions import PluginRegistrationError

                    if isinstance(
                        e, PluginRegistrationError
                    ) and "already registered" in str(e):
                        logger.warning(
                            f"⚠️  Skipping '{file.stem}' from {location.scope} ({file}) "
                            f"- plugin name already registered from higher-priority scope"
                        )
                    else:
                        logger.debug(f"Skipping {file.name}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error discovering plugins in {location.path}: {str(e)}")

        return plugins

    def _load_and_register_plugin(self, plugin_info: PluginInfo) -> None:
        """
        Load and register a plugin from PluginInfo.

        Note: The plugin is already registered in PluginRegistry by the @register decorator
        when the module was executed during discovery. This method only tracks it locally.

        Args:
            plugin_info: Plugin information

        Raises:
            PluginLoadError: If loading fails
        """
        try:
            # Register in our tracking dictionaries
            self.loaded_plugins.add(plugin_info.module_name)
            self.plugin_paths[plugin_info.module_name] = str(plugin_info.path)
            self.plugin_info_by_name[plugin_info.name] = plugin_info

            # NOTE: We do NOT call PluginRegistry.register_plugin() here because
            # the @register decorator already registered the plugin when the module
            # was executed during _discover_plugins_in_location().

        except Exception as e:
            raise PluginLoadError(
                f"Failed to track plugin {plugin_info.name}",
                details={"error": str(e), "scope": plugin_info.scope},
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
        try:
            if is_core:
                # Approche adaptative pour les plugins de base
                # Extraire le nom de module à partir des composants du chemin
                path_str = str(file)

                # Méthode 1: Extraction basée sur les composants du chemin
                if (
                    "/niamoto/core/plugins/" in path_str
                    or "\\niamoto\\core\\plugins\\" in path_str
                ):
                    # Diviser le chemin et extraire la partie après "niamoto/core/plugins"
                    parts = (
                        path_str.split("niamoto/core/plugins/")
                        if "/" in path_str
                        else path_str.split("niamoto\\core\\plugins\\")
                    )
                    if len(parts) > 1:
                        # Prendre la partie après "niamoto/core/plugins/"
                        rel_path = parts[1].replace("/", ".").replace("\\", ".")
                        # Enlever l'extension .py
                        if rel_path.endswith(".py"):
                            rel_path = rel_path[:-3]
                        return f"niamoto.core.plugins.{rel_path}"

                # Méthode 2: Méthode originale (essayer avec le chemin relatif)
                try:
                    # Get plugin root - works in both source and frozen modes
                    plugin_root = Path(__file__).parent

                    relative_path = file.relative_to(plugin_root).with_suffix("")
                    return f"niamoto.core.plugins.{'.'.join(relative_path.parts)}"
                except ValueError:
                    # Méthode 3: si tous les autres échouent, construire le nom de module à partir du nom de fichier
                    # et de la structure des répertoires parents
                    file_stem = file.stem
                    parent_dir = file.parent.name
                    grandparent = (
                        file.parent.parent.name if len(file.parents) > 0 else ""
                    )

                    # Détecter plugin_type à partir des noms de répertoire
                    plugin_types = ["transformers", "exporters", "loaders", "widgets"]

                    if grandparent in plugin_types:
                        # Chemin de type .../transformers/subdir/file.py
                        return f"niamoto.core.plugins.{grandparent}.{parent_dir}.{file_stem}"
                    elif parent_dir in plugin_types:
                        # Chemin de type .../transformers/file.py
                        return f"niamoto.core.plugins.{parent_dir}.{file_stem}"
                    else:
                        # Dernier recours
                        return f"niamoto.core.plugins.{file_stem}"
            else:
                # Pour les plugins de projet - logique inchangée
                try:
                    relative_path = file.relative_to(
                        file.parents[file.parts.index("plugins")]
                    )
                    return f"plugins.{'.'.join(relative_path.with_suffix('').parts)}"
                except (ValueError, IndexError):
                    # Fallback si "plugins" n'est pas trouvé dans le chemin
                    return f"plugins.{file.stem}"
        except Exception as e:
            logger.debug(f"Error determining module name for {file}: {str(e)}")
            # Si tout échoue, juste utiliser le nom du fichier comme dernier recours
            return f"plugin_{file.stem}"

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

    def get_plugin_details(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all loaded plugins including scope and priority.

        This is used by the `niamoto plugins list` command.

        Returns:
            List of plugin details dictionaries
        """
        details = []

        for plugin_name, plugin_info in self.plugin_info_by_name.items():
            # Check if this plugin overrides another
            is_overriding = False
            overridden_scopes = []

            # Get all plugins from PluginRegistry to check for conflicts
            PluginRegistry.list_plugins()

            details.append(
                {
                    "name": plugin_name,
                    "scope": plugin_info.scope,
                    "path": str(plugin_info.path),
                    "priority": plugin_info.priority,
                    "module": plugin_info.module_name,
                    "type": plugin_info.plugin_class.type.value,
                    "is_overriding": is_overriding,
                    "overridden_scopes": overridden_scopes,
                }
            )

        # Sort by priority (high to low), then by name
        details.sort(key=lambda x: (-x["priority"], x["name"]))

        return details

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
