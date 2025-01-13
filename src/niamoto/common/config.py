import os
import yaml
from typing import Any, Dict, Optional, List


class Config:
    """
    Class to manage all Niamoto configuration files:
     - config.yml (global env settings: database, logs, outputs, etc.)
     - sources.yml (data sources)
     - stats.yml (transformations)
     - presentation.yml (widgets)
    """

    def __init__(
        self, config_dir: Optional[str] = None, create_default: bool = True
    ) -> None:
        """
        Initialize the Config manager by loading multiple YAML files from config_dir.

        Args:
            config_dir (str): Path to the directory containing the 4 config files.
            create_default (bool): If True, create default configs if not found.
        """
        if not config_dir:
            # default to <NIAMOTO_HOME>/config
            config_dir = os.path.join(self.get_niamoto_home(), "config")
        self.config_dir = config_dir
        self.config: Dict[str, Any] = {}  # For global environment config (config.yml)
        self.sources: Dict[str, Any] = {}  # For sources.yml
        self.stats_config: Any = {}  # For stats.yml
        self.presentation_config: Any = {}  # For presentation.yml

        # Possibly load each file
        self._load_files(create_default)

    def _load_files(self, create_default: bool) -> None:
        """
        Internal method to load (or create) the config files.
        """
        # 1) Load global environment config (config.yml)
        config_path = os.path.join(self.config_dir, "config.yml")
        self.config = self._load_yaml_with_defaults(
            config_path, self._default_config(), create_default
        )

        # 2) Load sources.yml
        sources_path = os.path.join(self.config_dir, "sources.yml")
        self.sources = self._load_yaml_with_defaults(
            sources_path, self._default_sources(), create_default
        )

        # 3) Load stats.yml
        stats_path = os.path.join(self.config_dir, "stats.yml")
        self.stats_config = self._load_yaml_with_defaults(
            stats_path, self._default_stats(), create_default
        )

        # 4) Load presentation.yml
        presentation_path = os.path.join(self.config_dir, "presentation.yml")
        self.presentation_config = self._load_yaml_with_defaults(
            presentation_path, self._default_presentation(), create_default
        )

    @staticmethod
    def get_niamoto_home() -> str:
        """
        Return the Niamoto home directory.

        This method checks if the 'NIAMOTO_HOME' environment variable is set.
        If it is, returns that path; otherwise, falls back to the current working directory.
        """
        niamoto_home = os.environ.get("NIAMOTO_HOME")
        if niamoto_home:
            return niamoto_home
        else:
            return os.getcwd()

    @staticmethod
    def _load_yaml_with_defaults(
        file_path: str, default_data: Dict[str, Any], create_if_missing: bool
    ) -> Dict[str, Any]:
        """
        Loads a YAML file or creates it from defaults if not found.
        """
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return yaml.safe_load(f) or {}
        else:
            if create_if_missing:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    yaml.dump(
                        default_data, f, default_flow_style=False, sort_keys=False
                    )
                return default_data
            else:
                return {}

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """
        Default content for config.yml (database, logs, outputs).
        """
        return {
            "database": {"path": "data/db/niamoto.db"},
            "logs": {"path": "logs"},
            "outputs": {"static_site": "outputs", "static_api": "outputs/api"},
        }

    @staticmethod
    def _default_sources() -> Dict[str, Any]:
        """
        Default content for sources.yml (taxonomy, occurrences, etc.).
        """
        return {
            "taxonomy": {"type": "csv", "path": "data/sources/taxonomy.csv"},
            "occurrences": {"type": "csv", "path": "data/sources/occurrences.csv"},
        }

    @staticmethod
    def _default_stats() -> Dict[str, Any]:
        """
        Default stats transformations. Possibly an empty dict or minimal.
        """
        return {}

    @staticmethod
    def _default_presentation() -> Dict[str, Any]:
        """
        Default presentation config. Possibly an empty dict or minimal.
        """
        return {}

    # ===============================
    # PROPERTIES / GETTERS
    # ===============================

    @property
    def database_path(self) -> str:
        return self.config.get("database", {}).get("path", "data/db/niamoto.db")

    @property
    def logs_path(self) -> str:
        return self.config.get("logs", {}).get("path", "logs")

    @property
    def output_paths(self) -> Dict[str, str]:
        return self.config.get("outputs", {})

    # Example: sources are directly in self.sources
    @property
    def data_sources(self) -> Dict[str, Any]:
        """
        If you're calling self.sources 'data_sources', you can rename
        or adapt as needed.
        """
        return self.sources

    # Provide getters for stats/presentation if needed
    def get_stats_config(self) -> List[Dict[str, Any]]:
        return self.stats_config

    def get_presentation_config(self) -> List[Dict[str, Any]]:
        return self.presentation_config
