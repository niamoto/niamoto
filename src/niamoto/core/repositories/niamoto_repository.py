from typing import Optional, Union, Callable, Any

from niamoto.common.exceptions import DatabaseError, ValidationError, DataTransformError
from niamoto.common.utils import error_handler
from niamoto.core.models import Base
from niamoto.common.database import Database


class NiamotoRepository:
    """
    The NiamotoRepository provides a data access layer to interact with the database.
    It allows fetching of entity objects defined by the SQLAlchemy ORM.
    """

    @error_handler(log=True, raise_error=True)
    def __init__(self, db_path: str) -> None:
        """
        Initializes a new instance of the NiamotoRepository with a given database path.

        Args:
            db_path (str): The path to the database file.
        """
        try:
            self.db = Database(db_path)
            self.session = self.db.session
        except Exception as e:
            raise DatabaseError(
                message="Failed to initialize repository",
                details={"db_path": db_path, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def get_entities(
        self,
        entity_class: Any,
        order_by: Optional[Union[Callable[[Any], Any], Any]] = None,
    ) -> Any:
        """
        Retrieves all entities of a given class from the database.

        Args:
            entity_class (class): The class representing the entity to retrieve.
            order_by (function, optional): A function that takes an instance of entity_class and returns a value to sort by.

        Returns:
            list: A list of entities retrieved from the database.
        """
        if not issubclass(entity_class, Base):
            raise ValidationError(
                field="entity_class",
                message="Invalid entity class",
                details={
                    "provided": str(entity_class),
                    "expected": "SQLAlchemy ORM class",
                },
            )

        try:
            query = self.session.query(entity_class)
            if order_by is not None:
                query = query.order_by(order_by)
            return query.all()
        except Exception as e:
            raise DatabaseError(
                message="Failed to retrieve entities",
                details={"entity_class": entity_class.__name__, "error": str(e)},
            )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def build_taxonomy_tree(taxons: Any) -> Any:
        """
        Builds a taxonomy tree from a list of taxons.

        Args:
            taxons (list): The list of taxons to build the tree from.

        Returns:
            list: A list of root nodes of the taxonomy tree.
        """
        if taxons is None:
            raise DataTransformError(
                message="Failed to build taxonomy tree",
                details={"error": "Input taxons cannot be None"},
            )

        try:
            rank_order = {"Famille": 1, "Genus": 2, "Species": 3, "Variety": 4}
            sorted_taxons = sorted(taxons, key=lambda x: rank_order.get(x.rank_name, 5))

            tree = {}
            for taxon in sorted_taxons:
                tree[taxon.id] = {
                    "name": taxon.full_name,
                    "parent_id": taxon.parent_id,
                    "children": [],
                }

            for id, node in tree.items():
                parent_id = node["parent_id"]
                if parent_id and parent_id in tree:  # Vérifie que le parent existe
                    tree[parent_id]["children"].append(node)

            root_nodes = [node for node in tree.values() if node["parent_id"] is None]

            if not root_nodes:
                raise DataTransformError(
                    message="No root nodes found in taxonomy tree",
                    details={"taxon_count": len(taxons)},
                )

            return root_nodes

        except Exception as e:
            raise DataTransformError(
                message="Failed to build taxonomy tree",
                details={
                    "taxon_count": len(taxons) if taxons is not None else 0,
                    "error": str(e),
                },
            )

    @error_handler(log=True, raise_error=True)
    def close_session(self) -> None:
        """
        Closes the database session.
        """
        try:
            self.db.close_db_session()
        except Exception as e:
            raise DatabaseError(
                message="Failed to close database session", details={"error": str(e)}
            )

    def __enter__(self) -> "NiamotoRepository":
        """
        Enters the context manager and opens the database session.

        Returns:
            NiamotoRepository: The current instance of the NiamotoRepository.
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exits the context manager and closes the database session.

        Args:
            exc_type (Any): The type of the exception.
            exc_val (Any): The value of the exception.
            exc_tb (Any): The traceback of the exception.
        """
        self.close_session()
