import os
import toml

from typing import Any, Dict, Optional


class ConfigManager:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        config_path: str = os.path.join(os.getcwd(), "config", "niamoto_config.toml")
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                return toml.load(config_file)
        else:
            raise FileNotFoundError("Configuration file not found.")

    def get(self, section: str, key: Optional[str] = None) -> Any:
        if key:
            # Returns a specific value in the section
            return self.config[section].get(key)
        else:
            # Returns the entire section if no specific key is provided
            return self.config.get(section)
