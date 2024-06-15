import os
from typing import Any, Dict, Optional
import yaml


class Config:
    """
    Class to manage the configuration settings for Niamoto application.

    Attributes:
        config (Dict[str, Any]): Configuration dictionary loaded from YAML file.
    """

    def __init__(
        self, config_path: Optional[str] = None, create_default: bool = True
    ) -> None:
        """
        Initializes the ConfigManager and loads the configuration file.

        Args:
            config_path (Optional[str]): Custom path to the configuration file.
                                         If None, default path is used.
            create_default (bool): If True, creates a default configuration file if none exists.
        """
        niamoto_home = self.get_niamoto_home()
        self.config_path = config_path or os.path.join(niamoto_home, "config.yml")
        self.config: Dict[str, Any] = self.load_config(create_default)

    @property
    def database_path(self) -> Any:
        """
        Retrieves the database path from the configuration.

        Returns:
            Any: The database path.
        """
        return self.get("database", "path")

    @property
    def logs_path(self) -> Any:
        """
        Retrieves the logs path from the configuration.

        Returns:
            Any: The logs path.
        """
        return self.get("logs", "path")

    @property
    def data_sources(self) -> Dict[str, Any]:
        """
        Retrieves the data sources section from the configuration.

        Returns:
            Dict[str, Any]: The data sources section.
        """
        return self.get_section("sources")

    @property
    def output_paths(self) -> Dict[str, Any]:
        """
        Retrieves the output paths section from the configuration.

        Returns:
            Dict[str, Any]: The output paths section.
        """
        return self.get_section("outputs")

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Retrieves a specific section from the configuration.

        Args:
            section (str): The configuration section to retrieve.

        Returns:
            Dict[str, Any]: The configuration section.
        """
        return self.config.get(section, {}) or {}

    def get(self, section: str, key: Optional[str] = None) -> Any:
        """
        Retrieves a specific configuration value or a whole section.

        Args:
            section (str): The configuration section to retrieve.
            key (Optional[str]): The specific key in the section to retrieve.
                                 If None, returns the whole section.

        Returns:
            Any: The configuration value or section.
        """
        section_data = self.get_section(section)
        if key:
            return section_data.get(key)
        return section_data

    @staticmethod
    def create_default_config() -> Dict[str, Any]:
        """
        Create a default configuration dictionary.

        Returns:
            Dict[str, Any]: The default configuration dictionary.
        """
        return {
            "database": {"path": "data/db/niamoto.db"},
            "logs": {"path": "logs"},
            "sources": {
                "taxonomy": {
                    "path": "data/sources/taxonomy.csv",
                    "ranks": "id_family,id_genus,id_species,id_infra",
                },
                "plots": {
                    "path": "data/sources/plots.gpkg",
                    "identifier": "id_locality",
                },
                "occurrences": {
                    "path": "data/sources/occurrences.csv",
                    "identifier": "id_taxonref",
                },
                "occurrence-plots": {"path": "data/sources/occurrence-plots.csv"},
                "shapes": {"path": "data/sources/shapes.csv"},
                "rasters": {"path": "data/sources/rasters"},
            },
            "outputs": {
                "static_site": "outputs",
                "static_api": "outputs/api",
            },
            "aggregations": [],
        }

    def create_config_file(self, config: Dict[str, Any]) -> None:
        """
        Create or overwrite the YAML configuration file with the provided configuration.

        Args:
            config (Dict[str, Any]): Configuration to write to the file.
        """
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as config_file:
            yaml.dump(config, config_file, default_flow_style=False, sort_keys=False)

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Sets a specific configuration value.

        Args:
            section (str): The configuration section to modify.
            key (str): The specific key in the section to modify.
            value (Any): The new value to set.
        """
        if section in self.config:
            self.config[section][key] = value
        else:
            raise ValueError(
                f"Section '{section}' does not exist in the configuration."
            )

    def save(self) -> None:
        """
        Saves the current configuration to the YAML file.
        """
        with open(self.config_path, "w") as config_file:
            yaml.dump(
                self.config, config_file, default_flow_style=False, sort_keys=False
            )

    def validate_config(self) -> Optional[Dict[Any, Any]]:
        """
        Validate the currently loaded configuration.

        Returns:
            Optional[Dict[Any, Any]]: The validated configuration dictionary if the configuration is valid, None otherwise.
        """
        expected_keys = {
            "database": ["path"],
            "logs": ["path"],
            "sources": [
                "taxonomy",
                "plots",
                "occurrences",
                "occurrence-plots",
                "shapes",
                "rasters",
            ],
            "outputs": ["static_site", "static_api"],
            "aggregations": [],
        }

        try:
            with open(self.config_path, "r") as config_file:
                config: Dict[Any, Any] = yaml.safe_load(config_file)

            for section, keys in expected_keys.items():
                if section not in config:
                    raise ValueError(f"Missing section: {section}")

                for key in keys:
                    if key not in config[section] or not config[section][key]:
                        raise ValueError(
                            f"Missing or empty key '{key}' in section '{section}'"
                        )

            return config

        except Exception as e:
            raise ValueError(f"Error validating configuration file: {e}")

    def load_config(self, create_default: bool = True) -> Any:
        """
        Loads the configuration from the YAML file. If the file does not exist,
        creates a default configuration file.

        Args:
            create_default (bool): If True, creates a default configuration file if none exists.

        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as config_file:
                return yaml.safe_load(config_file)
        else:
            if create_default:
                config = self.create_default_config()
                self.create_config_file(config)
                return config
            else:
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}"
                )

    @staticmethod
    def get_niamoto_home() -> str:
        """
        Get the Niamoto home directory.

        Returns:
            str: The Niamoto home directory.
        """
        niamoto_home = os.environ.get("NIAMOTO_HOME")
        if niamoto_home:
            return niamoto_home
        else:
            return os.getcwd()
