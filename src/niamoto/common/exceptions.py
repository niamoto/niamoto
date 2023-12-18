# exceptions.py


class FileReadError(Exception):
    """Exception raised when there is an error reading the file."""

    def __init__(self, file_path: str, message: str = "Error reading the file"):
        self.file_path = file_path
        super().__init__(f"{message}: {file_path}")


class DataValidationError(Exception):
    """Exception raised for data validation errors."""

    def __init__(self, errors: str):
        self.errors = errors
        super().__init__(f"Data validation error: {errors}")


class DatabaseWriteError(Exception):
    """Exception raised when writing to the database fails."""

    def __init__(
        self, table_name: str, message: str = "Failed to write data to the database"
    ):
        self.table_name = table_name
        super().__init__(f"{message}: Table {table_name}")


class ConfigurationError(Exception):
    """
    Exception raised for configuration errors.
    """

    def __init__(self, config_key: str, message: str = "Configuration error"):
        self.config_key = config_key
        super().__init__(f"{message}: {config_key} is missing or invalid")


class DatabaseConnectionError(Exception):
    """
    Exception raised when connection to the database fails.
    """

    def __init__(self, db_url: str, message: str = "Failed to connect to the database"):
        self.db_url = db_url
        super().__init__(f"{message}: Unable to connect to {db_url}")
