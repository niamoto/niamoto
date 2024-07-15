from typing import Dict, Any, Optional, List
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

    def add_aggregation(self, field: str) -> None:
        """
        Adds a mapping.

        Args:
            field (str): The field to add to the mapping.
        """
        self.mapping_manager.add_aggregation(field)

    def get_aggregations(self) -> list[dict[str, Any]]:
        """
        Retrieves the mapping.

        Returns:
            list[dict[str, Any]]: The mapping.
        """
        return self.mapping_manager.get_aggregations()

    def get_group_config(self, group_by: Optional[str]) -> Dict[str, Any]:
        """
        Retrieves the group configuration.

        Args:
            group_by (str): The field to group by.

        Returns:
            Dict[str, Any]: The group configuration.
        """
        return self.mapping_manager.get_group_config(str(group_by))

    def get_source_path(self, source_name: str) -> Any:
        """
        Retrieves the path for a given source.

        Args:
            source_name (str): The name of the source.

        Returns:
            Any: The path to the source.
        """
        sources = self.mapping_manager.get_sources()
        return sources.get(source_name, {}).get("path", "")

    def get_source_identifier(self, source_name: str) -> Any:
        """
        Retrieves the identifier for a given source.

        Args:
            source_name (str): The name of the source.

        Returns:
            Any: The identifier for the source.
        """
        sources = self.mapping_manager.get_sources()
        return sources.get(source_name, {}).get("identifier", "id")

    def get_group_filter(self, group: str) -> Any:
        """
        Get the filter configuration for a specific group.

        Args:
            group (str): The group name.

        Returns:
            Any: The filter configuration.
        """
        group_config = self.get_group_config(group)
        return group_config.get("filter", {})

    def get_fields(self, group_by: str) -> Dict[str, Any]:
        """
        Retrieves the fields for a given group.

        Args:
            group_by (str): The field to group by.

        Returns:
            Dict[str, Any]: The fields for the given group.
        """
        return self.mapping_manager.get_fields(group_by)

    def get_layers(self) -> List[Dict[str, Any]]:
        """
        Retrieves the layers configuration.

        Returns:
            List[Dict[str, Any]]: A list of layer configurations.
        """
        return self.mapping_manager.get_layers()

    def get_layer(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a layer configuration by name.

        Args:
            layer_name (str): The name of the layer.

        Returns:
            Optional[Dict[str, Any]]: The layer configuration if found, None otherwise.

        """
        return self.mapping_manager.get_layer(layer_name)

    def get_layer_path(self, layer_name: str) -> Optional[str]:
        """
        Retrieves the path for a given layer.

        Args:
            layer_name (str): The name of the layer.

        Returns:
            Optional[str]: The path to the layer if found, None otherwise.
        """
        layer = self.get_layer(layer_name)
        return layer.get("path") if layer else None

    def get_layer_type(self, layer_name: str) -> Optional[str]:
        """
        Retrieves the type of a given layer.

        Args:
            layer_name (str): The name of the layer.

        Returns:
            Optional[str]: The type of the layer if found, None otherwise.
        """
        layer = self.get_layer(layer_name)
        return layer.get("type") if layer else None

    def add_layer(self, layer_config: Dict[str, Any]) -> None:
        """
        Adds a new layer configuration.

        Args:
            layer_config (Dict[str, Any]): The layer configuration to add.

        Returns:
            None

        """
        self.mapping_manager.add_layer(layer_config)
