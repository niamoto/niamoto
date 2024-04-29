from typing import Dict, Any, Optional
from niamoto.common.database import Database
from niamoto.core.components.mappers.mapping_manager import MappingManager


class MapperService:
    def __init__(self, db_path: str) -> None:
        self.db = Database(db_path)
        self.mapping_manager = MappingManager(self.db)

    def generate_mapping(
        self,
        csvfile: str,
        group_by: str,
        reference_table_name: Optional[str],
        reference_data_path: Optional[str],
    ) -> None:
        self.mapping_manager.generate_mapping(
            csvfile, group_by, reference_table_name, reference_data_path
        )

    def add_mapping(self, field: str) -> None:
        self.mapping_manager.add_mapping(field)

    def get_mapping(self) -> list[dict[str, Any]]:
        return self.mapping_manager.get_mapping()

    def get_group_config(self, group_by: str) -> Dict[str, Any]:
        return self.mapping_manager.get_group_config(group_by)

    def get_fields(self, group_by: str) -> Dict[str, Any]:
        return self.mapping_manager.get_fields(group_by)
