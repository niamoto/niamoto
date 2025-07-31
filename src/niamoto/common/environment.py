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
    def __init__(self, config_dir: str, project_name: str = None):
        """Initialize Environment with config directory.

        Args:
            config_dir: Path to the configuration directory
            project_name: Optional name for the project
        """
        try:
            self.config = Config(config_dir, create_default=True)
            self.project_name = project_name
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

            # Create plugins directory if configured
            if (
                "plugins" in self.config.config
                and "path" in self.config.config["plugins"]
            ):
                plugins_path = self.config.config["plugins"]["path"]
                if not os.path.isabs(plugins_path):
                    plugins_path = os.path.join(
                        self.config.get_niamoto_home(), plugins_path
                    )
                os.makedirs(plugins_path, exist_ok=True)

            # Create templates directory if configured
            if (
                "templates" in self.config.config
                and "path" in self.config.config["templates"]
            ):
                templates_path = self.config.config["templates"]["path"]
                if not os.path.isabs(templates_path):
                    templates_path = os.path.join(
                        self.config.get_niamoto_home(), templates_path
                    )
                os.makedirs(templates_path, exist_ok=True)
                # Also create assets subdirectory
                assets_path = os.path.join(templates_path, "assets")
                os.makedirs(assets_path, exist_ok=True)

            # Update project name in config if provided
            if self.project_name:
                config_file_path = os.path.join(self.config.config_dir, "config.yml")
                import yaml

                # Read existing config
                with open(config_file_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

                # Update project name
                if "project" not in config_data:
                    config_data["project"] = {}
                config_data["project"]["name"] = self.project_name

                # Also ensure we have the current date and version
                from datetime import datetime

                try:
                    from niamoto.__version__ import __version__
                except ImportError:
                    __version__ = "unknown"

                config_data["project"]["created_at"] = datetime.now().isoformat()
                config_data["project"]["niamoto_version"] = __version__

                # Write back to file
                with open(config_file_path, "w", encoding="utf-8") as f:
                    yaml.dump(
                        config_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )

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

            # Clear web exports directory
            web_dir = self.config.get_export_config.get("web")
            if web_dir and os.path.exists(web_dir):
                try:
                    shutil.rmtree(web_dir)
                except OSError as e:
                    raise FileWriteError(
                        file_path=web_dir,
                        message="Failed to clear web exports directory",
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
