import os
import shutil
from typing import Dict, Any

from niamoto.core.models import Base
from niamoto.common.database import Database


class Environment:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def initialize(self) -> None:
        """
        Initialize the environment based on the provided configuration.
        """
        raster_path = self.config["sources"]["raster"]
        os.makedirs(os.path.join(os.getcwd(), raster_path), exist_ok=True)

        for key in ["web", "logs"]:
            for path in self.config[key].values():
                os.makedirs(os.path.join(os.getcwd(), path), exist_ok=True)

        db_path = self.config["database"]["path"]
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db = Database(db_path)
        Base.metadata.create_all(db.engine)

    def reset(self) -> None:
        """
        Reset the environment by deleting the existing database, configuration,
        and web static pages.
        """
        db_path = self.config["database"]["path"]
        if os.path.exists(db_path):
            os.remove(db_path)

        static_pages_path = os.path.join(
            os.getcwd(), self.config["web"]["static_pages"]
        )
        if os.path.exists(static_pages_path):
            shutil.rmtree(static_pages_path)

        self.initialize()
