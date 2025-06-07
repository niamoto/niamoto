"""
Plugin registry module for Niamoto.

This module implements a centralized registry system for managing all Niamoto plugins.
It provides functionality for:

- Plugin registration and management
- Type-safe plugin retrieval
- Plugin metadata storage and access
- Plugin type categorization

The registry is implemented as a singleton class that maintains separate
registries for different plugin types, ensuring type safety and proper
organization of the plugin ecosystem.
"""

from typing import Dict, Type, Optional, Any
from .base import Plugin, PluginType
from .exceptions import PluginRegistrationError, PluginNotFoundError


class PluginRegistry:
    """
    Central registry for all Niamoto plugins.
    Handles registration and retrieval of plugins by type.
    """

    # Store plugins by type and name
    _plugins: Dict[PluginType, Dict[str, Type[Plugin]]] = {
        plugin_type: {} for plugin_type in PluginType
    }

    # Store plugin metadata
    _metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_plugin(
        cls,
        name: str,
        plugin_class: Type[Plugin],
        plugin_type: Optional[PluginType] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a plugin with the system.
        Args:
            name: Unique identifier for the plugin
            plugin_class: The plugin class to register
            plugin_type: Type of plugin, inferred from class if not provided
            metadata: Optional metadata about the plugin
        Raises:
            PluginRegistrationError: If registration fails
        """
        try:
            # Get plugin type from class if not provided
            actual_type = plugin_type or plugin_class.type

            # Validate plugin type
            if not isinstance(actual_type, PluginType):
                raise PluginRegistrationError(
                    f"Invalid plugin type: {actual_type}",
                    details={"plugin": name, "type": str(actual_type)},
                )

            # Check if plugin already registered
            if name in cls._plugins[actual_type]:
                # Check if it's the same plugin class - if so, allow it (for pipeline re-runs)
                existing_plugin = cls._plugins[actual_type][name]

                # Compare by class name and module path since reloaded modules create new class objects
                existing_id = f"{existing_plugin.__module__}.{existing_plugin.__name__}"
                new_id = f"{plugin_class.__module__}.{plugin_class.__name__}"

                if existing_id == new_id:
                    # Same plugin class (by module and name), skip registration
                    return
                else:
                    # Different plugin class with same name - this is an error
                    raise PluginRegistrationError(
                        f"Plugin {name} already registered for type {actual_type.value} with different class",
                        details={
                            "plugin": name,
                            "type": actual_type.value,
                            "existing_class": existing_id,
                            "new_class": new_id,
                        },
                    )

            # Register plugin
            cls._plugins[actual_type][name] = plugin_class

            # Store metadata if provided
            if metadata:
                cls._metadata[name] = metadata

        except Exception as e:
            if isinstance(e, PluginRegistrationError):
                raise
            raise PluginRegistrationError(
                f"Failed to register plugin {name}",
                details={
                    "plugin": name,
                    "type": actual_type.value if actual_type else None,
                    "error": str(e),
                },
            )

    @classmethod
    def get_plugin(cls, name: str, plugin_type: PluginType) -> Type[Plugin]:
        """
        Retrieve a plugin by name and type.
        Args:
            name: Plugin identifier
            plugin_type: Type of plugin to retrieve
        Returns:
            The plugin class
        Raises:
            PluginNotFoundError: If plugin not found
        """
        try:
            return cls._plugins[plugin_type][name]
        except KeyError:
            raise PluginNotFoundError(
                f"Plugin {name} not found for type {plugin_type.value}",
                details={
                    "plugin": name,
                    "type": plugin_type.value,
                    "available": list(cls._plugins[plugin_type].keys()),
                },
            )

    @classmethod
    def get_plugins_by_type(cls, plugin_type: PluginType) -> Dict[str, Type[Plugin]]:
        """
        Get all plugins of a specific type.
        Args:
            plugin_type: Type of plugins to retrieve
        Returns:
            Dictionary of plugin name to plugin class
        """
        return cls._plugins[plugin_type].copy()

    @classmethod
    def get_plugin_metadata(cls, name: str) -> Dict[str, Any]:
        """
        Get metadata for a plugin.
        Args:
            name: Plugin identifier
        Returns:
            Plugin metadata or empty dict if none registered
        """
        return cls._metadata.get(name, {})

    @classmethod
    def list_plugins(cls) -> Dict[PluginType, list[str]]:
        """
        List all registered plugins by type.
        Returns:
            Dictionary of plugin types to list of plugin names
        """
        return {
            plugin_type: list(plugins.keys())
            for plugin_type, plugins in cls._plugins.items()
        }

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered plugins.
        Mainly used for testing.
        """
        for plugin_type in PluginType:
            cls._plugins[plugin_type].clear()
        cls._metadata.clear()

    @classmethod
    def has_plugin(cls, name: str, plugin_type: PluginType) -> bool:
        """
        Check if a plugin is registered.
        Args:
            name: Plugin identifier
            plugin_type: Type of plugin to retrieve
        Returns:
            True if plugin is registered
        """
        return name in cls._plugins[plugin_type]

    @classmethod
    def remove_plugin(cls, name: str, plugin_type: PluginType) -> None:
        """
        Remove a plugin from the registry.
        Args:
            name: Plugin identifier
            plugin_type: Type of plugin to retrieve
        Raises:
            PluginNotFoundError: If plugin not found
        """
        try:
            del cls._plugins[plugin_type][name]
            cls._metadata.pop(name, None)
        except KeyError:
            raise PluginNotFoundError(
                f"Cannot remove plugin {name}: not found",
                details={"plugin": name, "type": plugin_type.value},
            )
