import pytest
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseWriteError,
    ConfigurationError,
    DatabaseConnectionError,
)


def test_file_read_error():
    """
    Test case for the FileReadError exception.
    """
    with pytest.raises(FileReadError) as e:
        raise FileReadError("/path/to/file")
    assert str(e.value) == "Error reading the file: /path/to/file"


def test_data_validation_error():
    """
    Test case for the DataValidationError exception.
    """
    with pytest.raises(DataValidationError) as e:
        raise DataValidationError("Invalid data")
    assert str(e.value) == "Data validation error: Invalid data"


def test_database_write_error():
    """
    Test case for the DatabaseWriteError exception.
    """
    with pytest.raises(DatabaseWriteError) as e:
        raise DatabaseWriteError("table_name")
    assert str(e.value) == "Failed to write data to the database: Table table_name"


def test_configuration_error():
    """
    Test case for the ConfigurationError exception.
    """
    with pytest.raises(ConfigurationError) as e:
        raise ConfigurationError("config_key")
    assert str(e.value) == "Configuration error: config_key is missing or invalid"


def test_database_connection_error():
    """
    Test case for the DatabaseConnectionError exception.
    """
    with pytest.raises(DatabaseConnectionError) as e:
        raise DatabaseConnectionError("db_url")
    assert (
        str(e.value) == "Failed to connect to the database: Unable to connect to db_url"
    )
