import os

from niamoto.common.config import Config


class Environment:
    """
    A class used to manage the environment for the Niamoto project.
    """

    def __init__(self, config_dir: str):
        """
        Initializes the Environment with the provided config directory.
        """
        self.config = Config(config_dir, create_default=True)

    def initialize(self) -> None:
        """
        Initialize the environment based on the provided configuration.
        """
        # 1) Create DB, logs, outputs from config.yml
        db_dir = os.path.dirname(self.config.database_path)
        os.makedirs(db_dir, exist_ok=True)

        if self.config.logs_path:
            os.makedirs(self.config.logs_path, exist_ok=True)

        for _, out_path in self.config.output_paths.items():
            if out_path:
                os.makedirs(out_path, exist_ok=True)

        # 2) Create the top-level directory for sources
        sources_root = os.path.join(self.config.get_niamoto_home(), "data", "sources")
        os.makedirs(sources_root, exist_ok=True)

        # 3) Initialize DB
        from niamoto.common.database import Database
        from niamoto.core.models import Base

        db = Database(self.config.database_path)
        Base.metadata.create_all(db.engine)

    def reset(self) -> None:
        """
        Reset environment by deleting DB & clearing outputs.
        """
        import shutil

        db_path = self.config.database_path
        if os.path.exists(db_path):
            os.remove(db_path)

        for _, out_path in self.config.output_paths.items():
            if out_path and os.path.exists(out_path):
                shutil.rmtree(out_path)

        self.initialize()
