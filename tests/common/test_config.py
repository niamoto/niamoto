import os
import pytest
import tempfile
import yaml
from niamoto.common.config import Config


def test_default_config():
    """
    Test case for the default configuration of the application.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["NIAMOTO_HOME"] = temp_dir
        config = Config()
        assert config.get("database", "path") == "data/db/niamoto.db"
        assert config.get("sources", "taxonomy") == "data/sources/taxonomy.csv"
        assert config.get("sources", "plots") == "data/sources/plots.gpkg"
        assert config.get("sources", "occurrences") == "data/sources/occurrences.csv"
        assert (
            config.get("sources", "occurrence-plots")
            == "data/sources/occurrence-plots.csv"
        )
        assert config.get("sources", "raster") == "data/sources/raster"
        assert config.get("web", "static_pages") == "web/static_files"
        assert config.get("web", "api") == "web/api"
        assert config.get("logs", "path") == "logs"


def test_custom_config(tmp_path):
    """
    Test case for a custom configuration of the application.

    Args:
        tmp_path: A pytest fixture that provides a temporary directory unique to the test invocation.
    """
    custom_config = {
        "database": {"path": "custom/db/path.db"},
        "sources": {
            "taxonomy": "custom/taxonomy.csv",
            "plots": "custom/plots.gpkg",
            "occurrences": "custom/occurrences.csv",
            "occurrence-plots": "custom/occurrence-plots.csv",
            "raster": "custom/raster",
        },
        "web": {
            "static_pages": "custom/static_files",
            "api": "custom/api",
        },
        "logs": {"path": "custom/logs"},
    }
    config_path = tmp_path / "custom_config.yml"
    with open(config_path, "w") as f:
        yaml.dump(custom_config, f)

    config = Config(str(config_path))
    assert config.get("database", "path") == "custom/db/path.db"
    assert config.get("sources", "taxonomy") == "custom/taxonomy.csv"
    assert config.get("sources", "plots") == "custom/plots.gpkg"
    assert config.get("sources", "occurrences") == "custom/occurrences.csv"
    assert config.get("sources", "occurrence-plots") == "custom/occurrence-plots.csv"
    assert config.get("sources", "raster") == "custom/raster"
    assert config.get("web", "static_pages") == "custom/static_files"
    assert config.get("web", "api") == "custom/api"
    assert config.get("logs", "path") == "custom/logs"


def test_get_method():
    """
    Test case for the get method of the Config class.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["NIAMOTO_HOME"] = temp_dir
        config = Config()
        assert config.get("database") == {"path": "data/db/niamoto.db"}
        assert config.get("sources", "plots") == "data/sources/plots.gpkg"
        assert config.get("web") == {"static_pages": "web/static_files", "api": "web/api"}


def test_valid_config():
    """
    Test case for validating a correct configuration of the application.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["NIAMOTO_HOME"] = temp_dir
        config = Config()
        assert config.validate_config() is not None


def test_invalid_config(tmp_path):
    """
    Test case for validating an incorrect configuration of the application.

    Args:
        tmp_path: A pytest fixture that provides a temporary directory unique to the test invocation.
    """
    invalid_config = {
        "database": {"path": ""},
        "sources": {
            "taxonomy": "",
            "plots": "",
            "occurrences": "",
            "occurrence-plots": "",
            "raster": "",
        },
        "web": {
            "static_pages": "",
            "api": "",
        },
        "logs": {"path": ""},
    }
    config_path = tmp_path / "invalid_config.yml"
    with open(config_path, "w") as f:
        yaml.dump(invalid_config, f)

    config = Config(str(config_path))
    with pytest.raises(ValueError) as e:
        config.validate_config()
    assert "Error validating configuration file" in str(e.value)
