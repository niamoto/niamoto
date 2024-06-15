from typing import Dict, Any, Optional
from niamoto.common.database import Database
from niamoto.core.components.mappers.mapping_manager import MappingManager


class MapperService:
    """
    The MapperService class provides methods to manage mappings.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initializes a new instance of the MapperService with a given database path.

        Args:
            db_path (str): The path to the database file.
        """
        self.db = Database(db_path)
        self.mapping_manager = MappingManager(self.db)

    def generate_mapping(
        self,
        csvfile: str,
        group_by: str,
        reference_table_name: Optional[str],
        reference_data_path: Optional[str],
    ) -> None:
        """
        Generates a mapping.

        Args:
            csvfile (str): The path to the CSV file to be used for the mapping.
            group_by (str): The field to group by.
            reference_table_name (str, optional): The name of the reference table.
            reference_data_path (str, optional): The path to the reference data.
        """
        self.mapping_manager.generate_mapping(
            csvfile, group_by, reference_table_name, reference_data_path
        )

    def add_mapping(self, field: str) -> None:
        """
        Adds a mapping.

        Args:
            field (str): The field to add to the mapping.
        """
        self.mapping_manager.add_mapping(field)

    def get_mapping(self) -> list[dict[str, Any]]:
        """
        Retrieves the mapping.

        Returns:
            list[dict[str, Any]]: The mapping.
        """
        return self.mapping_manager.get_mapping()

    def get_group_config(self, group_by: str) -> Dict[str, Any]:
        """
        Retrieves the group configuration.

        Args:
            group_by (str): The field to group by.

        Returns:
            Dict[str, Any]: The group configuration.
        """
        return self.mapping_manager.get_group_config(group_by)

    def get_source_path(self, source_name: str) -> str:
        """
        Retrieves the path for a given source.

        Args:
            source_name (str): The name of the source.

        Returns:
            str: The path to the source.
        """
        sources = self.mapping_manager.get_sources()
        return sources.get(source_name, {}).get("path", "")

    def get_source_identifier(self, source_name: str) -> str:
        """
        Retrieves the identifier for a given source.

        Args:
            source_name (str): The name of the source.

        Returns:
            str: The identifier for the source.
        """
        sources = self.mapping_manager.get_sources()
        return sources.get(source_name, {}).get("identifier", "id")

    def get_fields(self, group_by: str) -> Dict[str, Any]:
        """
        Retrieves the fields for a given group.

        Args:
            group_by (str): The field to group by.

        Returns:
            Dict[str, Any]: The fields for the given group.
        """
        return self.mapping_manager.get_fields(group_by)
