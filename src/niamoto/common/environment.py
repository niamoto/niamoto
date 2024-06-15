import os
import shutil

from niamoto.core.models import Base
from niamoto.common.database import Database
from niamoto.common.config import Config


class Environment:
    """
    A class used to manage the environment for the Niamoto project.

    Attributes:
        config (Config): The configuration settings for the Niamoto project.
    """

    def __init__(self, config: Config):
        """
        Initializes the Environment with the provided configuration.

        Args:
            config (Config): The configuration settings for the Niamoto project.
        """
        self.config = config

    def initialize(self) -> None:
        """
        Initialize the environment based on the provided configuration.
        """
        # Ensure all necessary directories are created
        os.makedirs(os.path.dirname(self.config.database_path), exist_ok=True)
        os.makedirs(self.config.logs_path, exist_ok=True)

        # Create directories for each source
        for source in self.config.data_sources.values():
            if isinstance(source, dict):
                path = source.get("path")
                if path:
                    os.makedirs(os.path.dirname(path), exist_ok=True)

        # Create directories for each output
        for path in self.config.output_paths.values():
            os.makedirs(os.path.dirname(path), exist_ok=True)

        # Initialize the database
        db = Database(self.config.database_path)
        Base.metadata.create_all(db.engine)

    def reset(self) -> None:
        """
        Reset the environment by deleting the existing database, configuration,
        web and api static_files.
        """
        db_path = self.config.database_path
        if os.path.exists(db_path):
            os.remove(db_path)

        # static_pages_path = self.config.output_paths.get("static_site")
        # if static_pages_path and os.path.exists(static_pages_path):
        #     shutil.rmtree(static_pages_path)
        #
        # static_api_path = self.config.output_paths.get("static_api")
        # if static_api_path and os.path.exists(static_api_path):
        #     shutil.rmtree(static_api_path)

        self.initialize()
