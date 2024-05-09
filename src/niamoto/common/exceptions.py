# exceptions.py


class FileReadError(Exception):
    """
    Exception raised when there is an error reading the file.

    Attributes:
        file_path (str): The path of the file that could not be read.
    """

    def __init__(self, file_path: str, message: str = "Error reading the file"):
        """
        Initializes the FileReadError with the file path and an optional message.

        Args:
            file_path (str): The path of the file that could not be read.
            message (str, optional): The error message. Defaults to "Error reading the file".
        """
        self.file_path = file_path
        super().__init__(f"{message}: {file_path}")


class DataValidationError(Exception):
    """
    Exception raised for data validation errors.

    Attributes:
        errors (str): The validation errors.
    """

    def __init__(self, errors: str):
        """
        Initializes the DataValidationError with the validation errors.

        Args:
            errors (str): The validation errors.
        """
        self.errors = errors
        super().__init__(f"Data validation error: {errors}")


class DatabaseWriteError(Exception):
    """
    Exception raised when writing to the database fails.

    Attributes:
        table_name (str): The name of the table where the write operation failed.
    """

    def __init__(
        self, table_name: str, message: str = "Failed to write data to the database"
    ):
        """
        Initializes the DatabaseWriteError with the table name and an optional message.

        Args:
            table_name (str): The name of the table where the write operation failed.
            message (str, optional): The error message. Defaults to "Failed to write data to the database".
        """
        self.table_name = table_name
        super().__init__(f"{message}: Table {table_name}")


class ConfigurationError(Exception):
    """
    Exception raised for configuration errors.

    Attributes:
        config_key (str): The configuration key that caused the error.
    """

    def __init__(self, config_key: str, message: str = "Configuration error"):
        """
        Initializes the ConfigurationError with the configuration key and an optional message.

        Args:
            config_key (str): The configuration key that caused the error.
            message (str, optional): The error message. Defaults to "Configuration error".
        """
        self.config_key = config_key
        super().__init__(f"{message}: {config_key} is missing or invalid")


class DatabaseConnectionError(Exception):
    """
    Exception raised when connection to the database fails.

    Attributes:
        db_url (str): The URL of the database that could not be connected to.
    """

    def __init__(self, db_url: str, message: str = "Failed to connect to the database"):
        """
        Initializes the DatabaseConnectionError with the database URL and an optional message.

        Args:
            db_url (str): The URL of the database that could not be connected to.
            message (str, optional): The error message. Defaults to "Failed to connect to the database".
        """
        self.db_url = db_url
        super().__init__(f"{message}: Unable to connect to {db_url}")
