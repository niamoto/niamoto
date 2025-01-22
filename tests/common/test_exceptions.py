from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseWriteError,
    ConfigurationError,
    DatabaseConnectionError,
    NiamotoError,
    TemplateError,
    OutputError,
    ProcessError,
    CalculationError,
    DataTransformError,
    ValidationError,
    CommandError,
    ArgumentError,
)


def test_base_niamoto_error():
    """Test the base NiamotoError class."""
    details = {"key": "value"}
    error = NiamotoError("Test error", details)

    assert str(error) == "Test error"
    assert error.details == details

    # Test with no details
    error = NiamotoError("Test error")
    assert error.details == {}


def test_file_read_error():
    """Test case for the FileReadError exception."""
    file_path = "/path/to/file"
    details = {"encoding": "utf-8"}

    error = FileReadError(file_path, "Test error", details)
    assert error.file_path == file_path
    assert error.details == details
    assert str(error) == "Test error"


def test_data_validation_error():
    """Test case for the DataValidationError exception."""
    validation_errors = [
        {"field": "name", "error": "required"},
        {"field": "age", "error": "must be positive"},
    ]
    error = DataValidationError("Invalid data", validation_errors)

    assert error.validation_errors == validation_errors
    assert "validation_errors" in error.details
    assert str(error) == "Invalid data"


def test_database_write_error():
    """Test case for the DatabaseWriteError exception."""
    table = "test_table"
    details = {"operation": "insert"}
    error = DatabaseWriteError(table, "Write failed", details)

    assert error.table_name == table
    assert error.details == details
    assert str(error) == "Write failed"


def test_configuration_error():
    """Test case for the ConfigurationError exception."""
    config_key = "database"
    details = {"file": "config.yml"}
    error = ConfigurationError(config_key, "Missing configuration", details)

    assert error.config_key == config_key
    assert error.details == details
    assert str(error) == "Missing configuration"


def test_database_connection_error():
    """Test case for the DatabaseConnectionError exception."""
    details = {"host": "localhost", "port": 5432}
    error = DatabaseConnectionError("Connection failed", details)

    assert error.details == details
    assert str(error) == "Connection failed"


def test_template_error():
    """Test case for the TemplateError exception."""
    template = "index.html"
    details = {"line": 42}
    error = TemplateError(template, "Template syntax error", details)

    assert error.template_name == template
    assert error.details == details
    assert str(error) == "Template syntax error"


def test_output_error():
    """Test case for the OutputError exception."""
    path = "/output/file.html"
    details = {"reason": "permission denied"}
    error = OutputError(path, "Failed to write output", details)

    assert error.output_path == path
    assert error.details == details
    assert str(error) == "Failed to write output"


def test_process_error():
    """Test case for ProcessError and its subclasses."""
    # Test ProcessError
    error = ProcessError("Process failed")
    assert str(error) == "Process failed"

    # Test CalculationError
    error = CalculationError("Division by zero", {"operation": "divide"})
    assert str(error) == "Division by zero"
    assert error.details == {"operation": "divide"}

    # Test DataTransformError
    error = DataTransformError("Invalid data format", {"format": "CSV"})
    assert str(error) == "Invalid data format"
    assert error.details == {"format": "CSV"}


def test_cli_errors():
    """Test case for CLI related errors."""
    # Test CommandError
    cmd = "niamoto generate"
    details = {"exit_code": 1}
    error = CommandError(cmd, "Command failed", details)

    assert error.command == cmd
    assert error.details == details
    assert str(error) == "Command failed"

    # Test ArgumentError
    arg = "--group"
    details = {"allowed": ["taxon", "plot"]}
    error = ArgumentError(arg, "Invalid argument", details)

    assert error.argument == arg
    assert error.details == details
    assert str(error) == "Invalid argument"


def test_validation_error():
    """Test case for ValidationError."""
    field = "email"
    details = {"value": "invalid", "pattern": r".*@.*"}
    error = ValidationError(field, "Invalid email format", details)

    assert error.field == field
    assert error.details == details
    assert str(error) == "Invalid email format"
