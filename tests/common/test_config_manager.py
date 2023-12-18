import os
import pytest
from unittest.mock import mock_open, patch
from niamoto.common.config_manager import ConfigManager


def test_load_config():
    mock_toml = {
        "section1": {"key1": "value1", "key2": "value2"},
        "section2": {"key3": "value3", "key4": "value4"},
    }

    with patch(
        "builtins.open", mock_open(read_data=str(mock_toml))
    ) as mock_file, patch("os.path.exists", return_value=True), patch(
        "toml.load", return_value=mock_toml
    ):
        config_manager = ConfigManager()
        assert config_manager.config == mock_toml
        mock_file.assert_called_once_with(
            os.path.join(os.getcwd(), "config", "niamoto_config.toml"), "r"
        )


def test_get():
    mock_toml = {
        "section1": {"key1": "value1", "key2": "value2"},
        "section2": {"key3": "value3", "key4": "value4"},
    }

    with patch("builtins.open", mock_open(read_data=str(mock_toml))), patch(
        "os.path.exists", return_value=True
    ), patch("toml.load", return_value=mock_toml):
        config_manager = ConfigManager()
        assert config_manager.get("section1", "key1") == "value1"
        assert config_manager.get("section1") == {"key1": "value1", "key2": "value2"}


def test_load_config_file_not_found():
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            ConfigManager()
