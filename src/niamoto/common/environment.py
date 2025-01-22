import os
import shutil
from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.core.models import Base
from niamoto.common.exceptions import (
    EnvironmentSetupError,
    FileWriteError,
    DatabaseError,
)
from niamoto.common.utils import error_handler


class Environment:
    """A class used to manage the environment for the Niamoto project."""

    @error_handler(log=True, raise_error=True)
    def __init__(self, config_dir: str):
        """Initialize Environment with config directory."""
        try:
            self.config = Config(config_dir, create_default=True)
        except Exception as e:
            raise EnvironmentSetupError(
                message="Failed to initialize environment configuration",
                details={"config_dir": config_dir, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def initialize(self) -> None:
        """Initialize the environment based on configuration."""
        try:
            # Create database directory
            db_dir = os.path.dirname(self.config.database_path)
            os.makedirs(db_dir, exist_ok=True)

            # Create logs directory
            if self.config.logs_path:
                os.makedirs(self.config.logs_path, exist_ok=True)

            # Create output directories
            for output_type, out_path in self.config.get_export_config.items():
                if out_path:
                    try:
                        os.makedirs(out_path, exist_ok=True)
                    except OSError as e:
                        raise FileWriteError(
                            file_path=out_path,
                            message=f"Failed to create output directory for {output_type}",
                            details={"error": str(e)},
                        )

            # Create import directory
            imports_root = os.path.join(self.config.get_niamoto_home(), "imports")
            os.makedirs(imports_root, exist_ok=True)

            # Initialize database
            try:
                db = Database(self.config.database_path)
                Base.metadata.create_all(db.engine)
            except Exception as e:
                raise DatabaseError(
                    message="Failed to initialize database",
                    details={"path": self.config.database_path, "error": str(e)},
                )

        except Exception as e:
            raise EnvironmentSetupError(
                message="Failed to initialize environment", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def reset(self) -> None:
        """Reset environment by deleting DB, clearing exports (except 'files' directory) and logs."""
        try:
            # Remove database
            db_path = self.config.database_path
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError as e:
                    raise FileWriteError(
                        file_path=db_path,
                        message="Failed to remove database file",
                        details={"error": str(e)},
                    )

            # Clear exports directory while preserving 'files' directory
            exports_dir = self.config.get_export_config.get(
                "web"
            )  # Base exports directory
            if exports_dir and os.path.exists(exports_dir):
                try:
                    # Remove all files and directories in exports except 'files'
                    for item in os.listdir(exports_dir):
                        item_path = os.path.join(exports_dir, item)
                        if item != "files":
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                except OSError as e:
                    raise FileWriteError(
                        file_path=exports_dir,
                        message="Failed to clear exports directory",
                        details={"error": str(e)},
                    )

            # Clear API directory specifically
            api_dir = self.config.get_export_config.get("api")
            if api_dir and os.path.exists(api_dir):
                try:
                    shutil.rmtree(api_dir)
                except OSError as e:
                    raise FileWriteError(
                        file_path=api_dir,
                        message="Failed to clear API directory",
                        details={"error": str(e)},
                    )

            # Clear logs directory
            if self.config.logs_path and os.path.exists(self.config.logs_path):
                try:
                    shutil.rmtree(self.config.logs_path)
                except OSError as e:
                    raise FileWriteError(
                        file_path=self.config.logs_path,
                        message="Failed to clear logs directory",
                        details={"error": str(e)},
                    )

            # Reinitialize environment
            self.initialize()

        except Exception as e:
            raise EnvironmentSetupError(
                message="Failed to reset environment", details={"error": str(e)}
            )
