import os
import yaml
from typing import Any, Dict, Optional, List
from niamoto.common.exceptions import (
    ConfigurationError,
    FileReadError,
    FileWriteError,
    FileFormatError,
    EnvironmentSetupError,
)
from niamoto.common.utils import error_handler


class Config:
    """
    Class to manage all Niamoto configuration files:
     - config.yml (global env settings: database, logs, outputs, etc.)
     - import.yml (data sources)
     - transform.yml (transformations)
     - export.yml (widgets)
    """

    @error_handler(log=True, raise_error=True)
    def __init__(
        self, config_dir: Optional[str] = None, create_default: bool = True
    ) -> None:
        """
        Initialize the Config manager by loading multiple YAML files from config_dir.

        Args:
            config_dir (str): Path to the directory containing the 4 config files.
            create_default (bool): If True, create default configs if not found.
        """
        try:
            if not config_dir:
                config_dir = os.path.join(self.get_niamoto_home(), "config")
            self.config_dir = config_dir
            self.config: Dict[str, Any] = {}
            self.imports: Dict[str, Any] = {}
            self.transforms: Any = {}
            self.exports: Any = {}

            self._load_files(create_default)
        except Exception as e:
            raise ConfigurationError(
                config_key="initialization",
                message="Failed to initialize configuration",
                details={"config_dir": config_dir, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def _load_files(self, create_default: bool) -> None:
        """Load or create the config files."""
        config_files = {
            "config.yml": (self._default_config, "config"),
            "import.yml": (self._default_imports, "imports"),
            "transform.yml": (self._default_transforms, "transforms"),
            "export.yml": (self._default_exports, "exports"),
        }

        for filename, (default_func, attr_name) in config_files.items():
            file_path = os.path.join(self.config_dir, filename)
            try:
                file_path = os.path.join(self.config_dir, filename)
                config_data = self._load_yaml_with_defaults(
                    file_path, default_func(), create_default
                )
                setattr(self, attr_name, config_data)
            except Exception as e:
                raise ConfigurationError(
                    config_key=filename,
                    message="Failed to load configuration file",
                    details={"file": file_path, "error": str(e)},
                )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def get_niamoto_home() -> str:
        """
        Return the Niamoto home directory.

        This method checks if the 'NIAMOTO_HOME' environment variable is set.
        If it is, returns that path; otherwise, falls back to the current working directory.
        """
        niamoto_home = os.environ.get("NIAMOTO_HOME")
        if not niamoto_home:
            niamoto_home = os.getcwd()
        if not os.path.exists(niamoto_home):
            raise EnvironmentSetupError(
                message="NIAMOTO_HOME directory not found",
                details={"path": niamoto_home},
            )
        return niamoto_home

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def _load_yaml_with_defaults(
        file_path: str, default_data: Dict[str, Any], create_if_missing: bool
    ) -> Dict[str, Any]:
        """
        Loads a YAML file or creates it from defaults if not found.
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        raise FileFormatError(
                            file_path=file_path,
                            message="Invalid YAML format",
                            details={"error": str(e)},
                        )
                    return data or {}
            elif create_if_missing:
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as f:
                        yaml.dump(
                            default_data, f, default_flow_style=False, sort_keys=False
                        )
                    return default_data
                except Exception as e:
                    raise FileWriteError(
                        file_path=file_path,
                        message="Failed to create config file",
                        details={"error": str(e)},
                    )
            return {}
        except OSError as e:
            raise FileReadError(
                file_path=file_path,
                message="Failed to access config file",
                details={"error": str(e)},
            )

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """
        Default content for config.yml (database, logs, outputs).
        """
        return {
            "database": {"path": "db/niamoto.db"},
            "logs": {"path": "logs"},
            "exports": {
                "web": "exports",
                "api": "exports/api",
                "files": "exports/files",
            },
        }

    @staticmethod
    def _default_imports() -> Dict[str, Any]:
        """
        Default content for import.yml (taxonomy, occurrences, etc.).
        """
        return {
            "taxonomy": {"type": "csv", "path": "imports/taxonomy.csv"},
            "occurrences": {"type": "csv", "path": "imports/occurrences.csv"},
            "plots": {"type": "vector", "path": "imports/plots.gpkg"},
            "occurrence_plots": {"type": "csv", "path": "imports/occurrence-plots.csv"},
        }

    @staticmethod
    def _default_transforms() -> Dict[str, Any]:
        """
        Default transformations. Possibly an empty dict or minimal.
        """
        return {}

    @staticmethod
    def _default_exports() -> Dict[str, Any]:
        """
        Default export config. Possibly an empty dict or minimal.
        """
        return {}

    # ===============================
    # PROPERTIES / GETTERS
    # ===============================

    @property
    @error_handler(log=True, raise_error=True)
    def database_path(self) -> str:
        """
        Get the database path from config.yml.
        Returns:
            str: database path
        """
        path = self.config.get("database", {}).get("path")
        if not path:
            raise ConfigurationError(
                config_key="database.path",
                message="Database path not configured",
                details={"config": self.config.get("database", {})},
            )
        return path

    @property
    @error_handler(log=True, raise_error=True)
    def logs_path(self) -> str:
        """
        Get the logs path from config.yml.
        Returns:
            str: logs path

        """
        path = self.config.get("logs", {}).get("path")
        if not path:
            raise ConfigurationError(
                config_key="logs.path",
                message="Logs path not configured",
                details={"config": self.config.get("logs", {})},
            )
        return path

    @property
    @error_handler(log=True, raise_error=True)
    def get_export_config(self) -> Dict[str, str]:
        """
        Get the output paths from config.yml.
        Returns:
            Dict[str, str]: output paths
        """
        exports = self.config.get("exports", {})
        if not exports:
            raise ConfigurationError(
                config_key="exports",
                message="No export paths configured",
                details={"config": self.config},
            )
        return exports

    @property
    @error_handler(log=True, raise_error=True)
    def get_imports_config(self) -> Dict[str, Any]:
        """
        Get the data sources from import.yml.
        Returns:
            Dict[str, Any]: data sources

        """
        if not self.imports:
            raise ConfigurationError(
                config_key="imports",
                message="No import sources configured",
                details={"imports_file": "import.yml"},
            )
        return self.imports

    @error_handler(log=True, raise_error=True)
    def get_transforms_config(self) -> List[Dict[str, Any]]:
        """
        Get the transformations config from transform.yml.
        Returns:
            List[Dict[str, Any]]: transformations config
        """

        if not self.transforms:
            raise ConfigurationError(
                config_key="transforms",
                message="No transforms configuration found",
                details={"transforms_file": "transform.yml"},
            )
        return self.transforms

    @error_handler(log=True, raise_error=True)
    def get_exports_config(self) -> List[Dict[str, Any]]:
        """
        Get the transforms config from export.yml.
        Returns:
            List[Dict[str, Any]]: transforms config
        """
        if not self.exports:
            raise ConfigurationError(
                config_key="exports",
                message="No exports configuration found",
                details={"exports": "export.yml"},
            )
        return self.exports
