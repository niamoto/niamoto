"""
Resource path resolution with cascade pattern for plugins and templates.

This module provides a unified way to resolve resources (plugins, templates)
across three scopes with priority-based override:
  1. Project-local (highest priority)
  2. User-global (~/.niamoto/)
  3. System built-in (lowest priority)

This module is used by both CLI and Desktop to ensure identical plugin loading.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ResourceLocation:
    """Represents a location where resources can be found"""

    # Scope du chemin ("project", "user", "system")
    scope: str

    # Chemin absolu vers le répertoire de ressources
    path: Path

    # Priorité (plus élevé = prioritaire)
    priority: int

    # Est-ce que cette ressource existe réellement ?
    exists: bool = field(init=False)

    def __post_init__(self):
        """Check if the path exists after initialization"""
        self.exists = self.path.exists()


class ResourcePaths:
    """Gestionnaire de chemins de ressources avec résolution en cascade"""

    # Scope constants
    SCOPE_PROJECT = "project"
    SCOPE_USER = "user"
    SCOPE_SYSTEM = "system"

    @staticmethod
    def get_plugin_paths(project_path: Optional[Path] = None) -> List[ResourceLocation]:
        """
        Retourne tous les chemins de recherche de plugins, ordonnés par priorité.

        Args:
            project_path: Chemin du projet actuel (optionnel)

        Returns:
            Liste de ResourceLocation, ordre décroissant de priorité
        """
        locations = []

        # 1. Project-local (priorité 100)
        if project_path:
            project_plugins_path = project_path / "plugins"
            locations.append(
                ResourceLocation(
                    scope=ResourcePaths.SCOPE_PROJECT,
                    path=project_plugins_path,
                    priority=100,
                )
            )

        # 2. User-global (priorité 50)
        user_dir = Path.home() / ".niamoto"
        user_plugins_path = user_dir / "plugins"

        # Create user directory structure if it doesn't exist (lazy creation)
        try:
            user_plugins_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If we can't create it (permissions, etc.), continue anyway
            # The ResourceLocation.exists will be False and it will be skipped
            pass

        locations.append(
            ResourceLocation(
                scope=ResourcePaths.SCOPE_USER,
                path=user_plugins_path,
                priority=50,
            )
        )

        # 3. System built-in (priorité 10)
        try:
            from niamoto.common.bundle import get_resource_path, is_frozen

            if is_frozen():
                system_path = get_resource_path("niamoto/core/plugins")
            else:
                # Development mode: use relative path from this file
                system_path = Path(__file__).parent.parent / "core" / "plugins"
        except ImportError:
            # Fallback if bundle module doesn't exist yet
            system_path = Path(__file__).parent.parent / "core" / "plugins"

        locations.append(
            ResourceLocation(
                scope=ResourcePaths.SCOPE_SYSTEM,
                path=system_path,
                priority=10,
            )
        )

        return locations

    @staticmethod
    def get_template_paths(
        project_path: Optional[Path] = None,
    ) -> List[ResourceLocation]:
        """
        Retourne tous les chemins de recherche de templates, ordonnés par priorité.

        Args:
            project_path: Chemin du projet actuel (optionnel)

        Returns:
            Liste de ResourceLocation, ordre décroissant de priorité
        """
        locations = []

        # 1. Project-local (priorité 100)
        if project_path:
            project_templates_path = project_path / "templates"
            locations.append(
                ResourceLocation(
                    scope=ResourcePaths.SCOPE_PROJECT,
                    path=project_templates_path,
                    priority=100,
                )
            )

        # 2. User-global (priorité 50)
        user_dir = Path.home() / ".niamoto"
        user_templates_path = user_dir / "templates"

        # Create user directory structure if it doesn't exist (lazy creation)
        try:
            user_templates_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If we can't create it (permissions, etc.), continue anyway
            # The ResourceLocation.exists will be False and it will be skipped
            pass

        locations.append(
            ResourceLocation(
                scope=ResourcePaths.SCOPE_USER,
                path=user_templates_path,
                priority=50,
            )
        )

        # 3. System built-in (priorité 10)
        try:
            from niamoto.common.bundle import get_resource_path, is_frozen

            if is_frozen():
                system_path = get_resource_path("niamoto/templates")
            else:
                # Development mode: use relative path from this file
                system_path = Path(__file__).parent.parent / "templates"
        except ImportError:
            # Fallback if bundle module doesn't exist yet
            system_path = Path(__file__).parent.parent / "templates"

        locations.append(
            ResourceLocation(
                scope=ResourcePaths.SCOPE_SYSTEM,
                path=system_path,
                priority=10,
            )
        )

        return locations

    @staticmethod
    def resolve_resource(
        resource_name: str,
        locations: List[ResourceLocation],
        must_exist: bool = True,
    ) -> Optional[Path]:
        """
        Resolve a specific resource file across multiple locations.

        Args:
            resource_name: Name or relative path of the resource to find
            locations: List of ResourceLocation to search (should be ordered by priority)
            must_exist: If True, only return paths that exist

        Returns:
            Path to the resource with highest priority, or None if not found
        """
        # Search in priority order (already sorted by caller)
        for location in locations:
            resource_path = location.path / resource_name

            if must_exist:
                if resource_path.exists():
                    return resource_path
            else:
                # Return first matching scope even if file doesn't exist
                return resource_path

        return None

    @staticmethod
    def collect_all_resources(
        locations: List[ResourceLocation],
        pattern: str = "*",
    ) -> List[Path]:
        """
        Collect all resources matching a pattern from all locations.

        Resources with same name in higher-priority locations will
        shadow those in lower-priority locations (no duplicates).

        Args:
            locations: List of ResourceLocation to search
            pattern: Glob pattern to match files (e.g., "*.py", "transform_*")

        Returns:
            List of unique resource paths, deduplicated by filename
        """
        seen_names = set()
        results = []

        # Iterate in priority order
        for location in locations:
            if not location.exists:
                continue

            # Find all matching files in this location
            for resource_path in location.path.glob(pattern):
                if not resource_path.is_file():
                    continue

                resource_name = resource_path.name

                # Skip if we already found this resource in higher-priority location
                if resource_name in seen_names:
                    continue

                seen_names.add(resource_name)
                results.append(resource_path)

        return results
