"""
This module contains the TaxonomyImporter class used to
import taxonomy data from a CSV file or occurrences into the database.
"""

from pathlib import Path
from typing import Tuple, Optional, Any, Dict, List

import pandas as pd
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from niamoto.common.database import Database
from niamoto.core.models import TaxonRef
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    TaxonomyImportError,
    FileReadError,
    DataValidationError,
    DatabaseError,
)
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.common.config import Config
from niamoto.common.progress import get_progress_tracker


class TaxonomyImporter:
    """
    A class used to import taxonomy data from a CSV file or occurrences into the database.

    Attributes:
        db (Database): The database connection.
        db_path (str): The path to the database.
    """

    def __init__(self, db: Database):
        """
        Initializes the TaxonomyImporter with the database connection.

        Args:
            db (Database): The database connection.
        """
        self.db = db
        self.db_path = db.db_path

        # Initialiser le chargeur de plugins et charger les plugins
        config = Config()
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_core_plugins()

        # Charger les plugins du projet s'ils existent
        self.plugin_loader.load_project_plugins(config.plugins_dir)

    @error_handler(log=True, raise_error=True)
    def import_taxonomy(
        self,
        occurrences_file: str,
        hierarchy_config: Dict[str, Any],
        api_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extract and import taxonomy data from occurrences.

        Args:
            occurrences_file (str): Path to occurrences CSV file.
            hierarchy_config (Dict[str, Any]): Hierarchical configuration with levels.
            api_config (Optional[Dict[str, Any]]): API configuration for enrichment.

        Returns:
            str: Success message.

        Raises:
            FileReadError: If file cannot be read.
            DataValidationError: If data is invalid.
            TaxonomyImportError: If import operation fails.
        """
        try:
            # Validate file exists
            occurrences_file = str(Path(occurrences_file).resolve())
            if not Path(occurrences_file).exists():
                raise FileReadError(occurrences_file, "Occurrences file not found")

            # Validate hierarchy config
            if not hierarchy_config:
                raise DataValidationError(
                    "Hierarchy configuration is required",
                    [{"field": "hierarchy"}],
                )

            if "levels" not in hierarchy_config:
                raise DataValidationError(
                    "Missing 'levels' in hierarchy configuration",
                    [{"field": "hierarchy.levels"}],
                )

            # Extract ranks and column mapping from hierarchy config
            rank_list = []
            new_column_mapping = {}

            for level in hierarchy_config["levels"]:
                if "name" not in level or "column" not in level:
                    raise DataValidationError(
                        "Each level must have 'name' and 'column'",
                        [{"level": level}],
                    )
                rank_list.append(level["name"])
                new_column_mapping[level["name"]] = level["column"]

            # Add taxon_id and authors if specified
            if "taxon_id_column" in hierarchy_config:
                new_column_mapping["taxon_id"] = hierarchy_config["taxon_id_column"]
            if "authors_column" in hierarchy_config:
                new_column_mapping["authors"] = hierarchy_config["authors_column"]

            # Override ranks and column_mapping with hierarchy config
            ranks = tuple(rank_list)
            column_mapping = new_column_mapping

            # Read the occurrences file
            try:
                df = pd.read_csv(occurrences_file, low_memory=False)
            except Exception as e:
                raise FileReadError(
                    occurrences_file, f"Failed to read CSV: {str(e)}"
                ) from e

            # Check if mapped columns exist in the file
            file_columns = set(df.columns)
            mapped_columns = set(column_mapping.values())
            missing_in_file = mapped_columns - file_columns
            if missing_in_file:
                raise DataValidationError(
                    f"Columns missing in occurrence file: {', '.join(missing_in_file)}",
                    [{"field": col} for col in missing_in_file],
                )

            # Extract taxonomy data
            taxonomy_df = self._extract_taxonomy_from_occurrences(
                df, column_mapping, ranks
            )

            # Process the taxonomy data and build the hierarchy
            count = self._process_taxonomy_with_relations(
                taxonomy_df, ranks, api_config
            )

            return f"{count} taxons extracted and imported from {Path(occurrences_file).name}."

        except Exception as e:
            if isinstance(e, (FileReadError, DataValidationError)):
                raise
            raise TaxonomyImportError(
                f"Failed to extract and import taxonomy from occurrences: {str(e)}",
                details={"file": occurrences_file, "error": str(e)},
            ) from e

    @error_handler(log=True, raise_error=True)
    def _process_taxonomy_with_relations(
        self,
        df: pd.DataFrame,
        ranks: Tuple[str, ...] = None,
        api_config: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Process taxonomy data and build parent-child relationships.
        This version uses database auto-increment for IDs
        and establishes relationships after insertion.

        Args:
            df: DataFrame containing taxonomy data
            ranks: Taxonomy ranks from configuration (optional)
            api_config: API configuration for enrichment (optional)

        Returns:
            Number of imported records
        """
        imported_count = 0
        # Check if API enrichment is enabled
        api_enricher = None
        if api_config and api_config.get("enabled", False):
            from niamoto.core.plugins.registry import PluginRegistry
            from niamoto.core.plugins.base import PluginType

            # Get the configured plugin
            plugin_name = api_config.get("plugin", "api_taxonomy_enricher")
            try:
                plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.LOADER)
                api_enricher = plugin_class(self.db)
                print(f"API enrichment enabled using plugin: {plugin_name}")
            except Exception as e:
                print(f"Failed to load API enrichment plugin: {str(e)}")
                api_enricher = None

        # Create dictionary to store relationships by rank
        taxa_by_rank = {rank: {} for rank in ranks if ranks}

        # Use the ranks from configuration if provided
        rank_names = list(ranks) if ranks else []

        try:
            # Import taxonomy data

            with self.db.session() as session:
                # First pass: insert all taxa into database to get auto-generated IDs
                # Variable to store the current enrichment message
                current_enrichment_message = "[green]Importing taxonomy...[/green]"
                if api_enricher:
                    current_enrichment_message = (
                        "[green]Enriching taxonomy data[/green]"
                    )

                progress_tracker = get_progress_tracker()
                with progress_tracker.track(
                    current_enrichment_message, total=len(df)
                ) as update:
                    # Process in hierarchical order based on ranks from configuration
                    # If ranks are not provided, use those present in the DataFrame
                    if not rank_names:
                        rank_names = df["rank_name"].unique().tolist()

                    for rank_name in rank_names:
                        rank_df = df[df["rank_name"] == rank_name]

                        for _, row in rank_df.iterrows():
                            # Convert data to dictionary for processing
                            row_dict = row.to_dict()

                            # Apply API enrichment if configured
                            if api_enricher:
                                try:
                                    # Save the current length of log messages
                                    prev_log_length = (
                                        len(api_enricher.log_messages)
                                        if hasattr(api_enricher, "log_messages")
                                        else 0
                                    )

                                    # Apply enrichment
                                    enriched_row_dict = api_enricher.load_data(
                                        row_dict, api_config
                                    )

                                    # Update row_dict with the enrichment result
                                    row_dict = enriched_row_dict
                                    # Update the status message with new messages
                                    if (
                                        hasattr(api_enricher, "log_messages")
                                        and len(api_enricher.log_messages)
                                        > prev_log_length
                                    ):
                                        new_messages = api_enricher.log_messages[
                                            prev_log_length:
                                        ]
                                        if new_messages:
                                            # Retrieve the last message
                                            last_message = new_messages[-1]

                                            # Display only if it's a success/error message
                                            if (
                                                "[✓]" in last_message
                                                or "✗" in last_message
                                            ):
                                                # Update the task description with the current message
                                                # Preserve the message formatting
                                                current_enrichment_message = (
                                                    last_message
                                                )
                                except Exception as e:
                                    error_msg = f"API enrichment failed for {row_dict.get('full_name')}: {str(e)}"
                                    # Log the error
                                    current_enrichment_message = (
                                        f"[bold red]{error_msg}[/]"
                                    )

                            # Convert taxon_id to integer if it's a number
                            taxon_id_value = None
                            if "taxon_id" in row and pd.notna(row["taxon_id"]):
                                try:
                                    if isinstance(row["taxon_id"], (int, float)):
                                        taxon_id_value = int(row["taxon_id"])
                                    else:
                                        taxon_id_value = int(float(row["taxon_id"]))
                                except (ValueError, TypeError):
                                    # If conversion fails, keep None
                                    pass

                            extra_data = {}
                            if "extra_data" in row_dict and isinstance(
                                row_dict["extra_data"], dict
                            ):
                                extra_data = row_dict["extra_data"].copy()

                            # Add API enrichment data if available
                            if "api_enrichment" in row_dict and isinstance(
                                row_dict["api_enrichment"], dict
                            ):
                                # Merge enrichment data with extra_data
                                extra_data.update(row_dict["api_enrichment"])
                            # Create taxon instance without explicit ID
                            taxon = TaxonRef(
                                full_name=row["full_name"],
                                authors=(
                                    row["authors"] if pd.notna(row["authors"]) else None
                                ),
                                rank_name=row[
                                    "rank_name"
                                ],  # Use directly the rank name from configuration
                                taxon_id=taxon_id_value,
                                extra_data=extra_data,
                            )

                            # Add to session
                            session.add(taxon)
                            session.flush()  # Flush to get the generated ID

                            # Store ID for establishing relationships later
                            if rank_name in taxa_by_rank:
                                taxa_by_rank[rank_name][row["full_name"]] = taxon.id

                            # Link to parent using parent_info
                            if "parent_info" in row and pd.notna(row["parent_info"]):
                                parent_info = row["parent_info"]
                                if parent_info and isinstance(parent_info, dict):
                                    parent_rank = parent_info.get("rank")
                                    parent_value = parent_info.get("value")

                                    if (
                                        parent_rank
                                        and parent_value
                                        and parent_rank in taxa_by_rank
                                    ):
                                        if parent_value in taxa_by_rank[parent_rank]:
                                            taxon.parent_id = taxa_by_rank[parent_rank][
                                                parent_value
                                            ]

                            # Count imported taxa
                            imported_count += 1

                            # Update progress with real-time duration
                            update(1)

                            # Periodic commit
                            if imported_count % 10 == 0:
                                session.commit()

                    # Final commit for all records
                    session.commit()

                    # Task completed

                # Second pass: update nested set values
                self._update_nested_set_values(session)
                session.commit()

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Database error: {str(e)}", details={"error": str(e)}
            ) from e
        except Exception as e:
            raise TaxonomyImportError(
                f"Failed to process taxonomy: {str(e)}", details={"error": str(e)}
            ) from e

        return imported_count

    def _extract_taxonomy_from_occurrences(
        self, df: pd.DataFrame, column_mapping: Dict[str, str], ranks: Tuple[str, ...]
    ) -> pd.DataFrame:
        """
        Extract unique taxonomy entries from occurrences and build complete taxonomy hierarchy,
        using database auto-increment for IDs.

        Args:
            df (pd.DataFrame): DataFrame containing occurrences.
            column_mapping (Dict[str, str]): Mapping between taxonomy fields and occurrence columns.
            ranks (Tuple[str, ...]): Taxonomy ranks to extract.

        Returns:
            pd.DataFrame: DataFrame containing extracted taxonomy data with complete hierarchy.
        """
        # Use directly the ranks from configuration
        rank_names = list(ranks)

        # Select relevant columns for taxonomy based on configuration
        taxon_cols = []

        # Add taxon_id column if present
        if "taxon_id" in column_mapping and column_mapping["taxon_id"] in df.columns:
            taxon_cols.append(column_mapping["taxon_id"])

        # Add all rank columns from configuration
        for rank in rank_names:
            if rank in column_mapping and column_mapping[rank] in df.columns:
                taxon_cols.append(column_mapping[rank])

        # Add authors column if present
        if "authors" in column_mapping and column_mapping["authors"] in df.columns:
            taxon_cols.append(column_mapping["authors"])

        # Include additional columns that might be useful
        for col in ["taxaname", "taxonref", "id_rank"]:
            if col in df.columns and col not in taxon_cols:
                taxon_cols.append(col)

        # Create a DataFrame with only taxonomy related columns
        occurrences_taxa = df[taxon_cols].drop_duplicates()

        # Initialize structures to track unique taxa by rank
        unique_taxa_by_rank = {rank: {} for rank in rank_names}
        taxa_data = []  # list to store all taxa data

        # Extract unique taxonomic data
        for _, row in occurrences_taxa.iterrows():
            # Extract taxonomy information for each rank
            rank_values = {}
            for rank in rank_names:
                if rank in column_mapping and column_mapping[rank] in row:
                    value = row[column_mapping[rank]]
                    if pd.notna(value):
                        rank_values[rank] = value
                    else:
                        rank_values[rank] = None
                else:
                    rank_values[rank] = None

            # Convert taxon_id to integer if possible
            taxon_id = None
            if "taxon_id" in column_mapping and column_mapping["taxon_id"] in row:
                raw_id = row[column_mapping["taxon_id"]]
                if pd.notna(raw_id):
                    try:
                        # Convert to integer if it's a number (even with decimal)
                        if isinstance(raw_id, (int, float)):
                            taxon_id = int(raw_id)
                        else:
                            # Try to convert a string to integer
                            taxon_id = int(float(raw_id))
                    except (ValueError, TypeError):
                        # If conversion fails, keep the original value
                        taxon_id = raw_id

            # Skip entries without any taxonomic information
            if not any(rank_values.values()):
                continue

            # Determine the lowest rank present for this row
            lowest_rank = None
            lowest_rank_idx = -1
            for idx, rank in enumerate(rank_names):
                if rank_values[rank] is not None:
                    lowest_rank = rank
                    lowest_rank_idx = idx

            # Skip if no rank values found
            if lowest_rank is None:
                continue

            # Build the hierarchy for this entry
            for rank_idx, rank in enumerate(rank_names[: lowest_rank_idx + 1]):
                rank_value = rank_values[rank]
                if rank_value is None:
                    continue

                # Store parent values for linking
                parent_rank = rank_names[rank_idx - 1] if rank_idx > 0 else None
                parent_value = rank_values[parent_rank] if parent_rank else None

                # Track unique taxa at each rank with their parent
                if rank_value not in unique_taxa_by_rank[rank]:
                    unique_taxa_by_rank[rank][rank_value] = {
                        "parent_rank": parent_rank,
                        "parent_value": parent_value,
                        "has_explicit_id": False,
                    }

            # Store the complete data for this taxon at its lowest rank
            if lowest_rank is not None:
                full_name = self._build_full_name_generic(
                    row, column_mapping, rank_values, rank_names
                )

                taxa_data.append(
                    {
                        "taxon_id": taxon_id,
                        "rank_name": lowest_rank,
                        "full_name": full_name,
                        "authors": self._extract_authors(row, column_mapping),
                        "rank_values": rank_values.copy(),
                        "taxonref": (
                            row["taxonref"]
                            if "taxonref" in row and pd.notna(row["taxonref"])
                            else None
                        ),
                    }
                )

                # Mark this taxon as having an explicit ID if applicable
                if taxon_id is not None and lowest_rank in unique_taxa_by_rank:
                    if rank_values[lowest_rank] in unique_taxa_by_rank[lowest_rank]:
                        unique_taxa_by_rank[lowest_rank][rank_values[lowest_rank]][
                            "has_explicit_id"
                        ] = True

        # Create the taxonomy entries in the correct order
        taxonomy_entries = []

        # Track which taxa have explicit taxon_ids by rank
        taxa_with_ids = {}
        for rank in rank_names:
            taxa_with_ids[rank] = {
                data["rank_values"][rank]: data
                for data in taxa_data
                if data["rank_name"] == rank
                and data["taxon_id"] is not None
                and data["rank_values"][rank] is not None
            }

        # Process each rank level in hierarchical order
        for rank_idx, rank in enumerate(rank_names):
            # Get all unique values at this rank
            for taxon_name, taxon_info in unique_taxa_by_rank[rank].items():
                # Check if this taxon has an explicit taxon_id
                taxon_data = None
                if rank in taxa_with_ids and taxon_name in taxa_with_ids[rank]:
                    taxon_data = taxa_with_ids[rank][taxon_name]

                # Prepare parent information
                parent_info = None
                if rank_idx > 0 and taxon_info["parent_value"]:
                    parent_info = {
                        "rank": taxon_info["parent_rank"],
                        "value": taxon_info["parent_value"],
                    }

                # Create the taxonomy entry
                if taxon_data:
                    # Use the data with explicit taxon_id
                    taxonomy_entries.append(
                        {
                            "full_name": taxon_data["full_name"],
                            "rank_name": rank,
                            "authors": taxon_data["authors"],
                            "taxon_id": taxon_data["taxon_id"],
                            "extra_data": {
                                "auto_generated": False,
                                "taxon_type": rank,
                                "original_id": taxon_data["taxon_id"],
                                "parent_info": parent_info,
                            },
                        }
                    )
                else:
                    # Auto-generate entry
                    taxonomy_entries.append(
                        {
                            "full_name": taxon_name,
                            "rank_name": rank,
                            "authors": "",
                            "taxon_id": None,
                            "extra_data": {
                                "auto_generated": True,
                                "taxon_type": rank,
                                "original_id": None,
                                "parent_info": parent_info,
                            },
                        }
                    )

        # Convert to DataFrame
        if not taxonomy_entries:
            # Create an empty DataFrame with required columns
            required_cols = [
                "full_name",
                "rank_name",
                "authors",
                "parent_id",
                "taxon_id",
                "extra_data",
            ]
            return pd.DataFrame(columns=required_cols)

        taxonomy_df = pd.DataFrame(taxonomy_entries)

        # Sort the taxonomy to ensure correct processing order (hierarchical)
        # Create a dictionary of order based on the ranks from configuration
        rank_order = {rank: i for i, rank in enumerate(rank_names)}

        taxonomy_df["sort_key"] = taxonomy_df["rank_name"].map(
            lambda x: rank_order.get(x, 99)
        )
        taxonomy_df.sort_values(by=["sort_key", "full_name"], inplace=True)
        taxonomy_df.drop(columns=["sort_key"], inplace=True)

        return taxonomy_df

    def _build_full_name_generic(
        self,
        row: pd.Series,
        column_mapping: Dict[str, str],
        rank_values: Dict[str, Any],
        rank_names: List[str],
    ) -> str:
        """
        Build a complete taxonomy name from the data of an occurrence row for any hierarchy.

        Args:
            row (pd.Series): Occurrence row.
            column_mapping (Dict[str, str]): Mapping between taxonomy fields and occurrence columns.
            rank_values (Dict[str, Any]): Values for each rank.
            rank_names (List[str]): List of rank names in hierarchical order.

        Returns:
            str: Complete taxonomy name.
        """
        # Find the lowest rank with a value
        lowest_rank = None
        lowest_rank_idx = -1
        for idx, rank in enumerate(rank_names):
            if rank_values.get(rank):
                lowest_rank = rank
                lowest_rank_idx = idx

        if lowest_rank is None:
            return "Unknown taxon"

        # For the lowest two ranks, build binomial/trinomial name
        if lowest_rank_idx >= 1:
            # Get the second to last rank (genus equivalent)
            parent_rank = rank_names[lowest_rank_idx - 1]
            parent_value = rank_values.get(parent_rank, "")

            # Get the lowest rank value
            current_value = str(rank_values[lowest_rank]).strip()

            if parent_value:
                parent_value = str(parent_value).split(",", maxsplit=1)[0].strip()
                # Remove parent name if it's already included in current value
                if current_value.startswith(parent_value):
                    current_value = current_value[len(parent_value) :].strip()
                return (
                    f"{parent_value} {current_value}" if current_value else parent_value
                )
            else:
                return current_value
        else:
            # For top-level ranks, just return the name
            return str(rank_values[lowest_rank]).strip()

    def _build_full_name(self, row: pd.Series, column_mapping: Dict[str, str]) -> str:
        """
        Build a complete taxonomy name from the data of an occurrence row.

        Args:
            row (pd.Series): Occurrence row.
            column_mapping (Dict[str, str]): Mapping between taxonomy fields
            and occurrence columns.

        Returns:
            str: Complete taxonomy name.
        """
        # Check if "infra" is present and not null
        if "infra" in column_mapping and column_mapping["infra"] in row:
            infra = row[column_mapping["infra"]]
            if pd.notna(infra):
                return str(infra).strip()

        # Otherwise, build from "genus" and "species"
        genus = None
        if "genus" in column_mapping and column_mapping["genus"] in row:
            genus = row[column_mapping["genus"]]
            if pd.notna(genus):
                genus = str(genus).split(",", maxsplit=1)[0].strip()

        species = None
        if "species" in column_mapping and column_mapping["species"] in row:
            species = row[column_mapping["species"]]
            if pd.notna(species):
                species = str(species).split(",", maxsplit=1)[0].strip()
                if genus and species.startswith(genus):
                    species = species[len(genus) :].strip()

        if genus and species:
            return f"{genus} {species}"
        elif genus:
            return genus
        elif "family" in column_mapping and column_mapping["family"] in row:
            family = row[column_mapping["family"]]
            if pd.notna(family):
                return str(family).split(",", maxsplit=1)[0].strip()

        return "Unknown taxon"

    def _extract_authors(self, row: pd.Series, column_mapping: Dict[str, str]) -> str:
        """
        Extract author information by comparing the species/infra name with the full name including authors.

        Args:
            row: Occurrence row
            column_mapping: Mapping between taxonomy fields and occurrence columns

        Returns:
            Extracted author information
        """
        # Get the authors column if directly specified in mapping
        if "authors" in column_mapping and column_mapping["authors"] in row:
            authors_value = row[column_mapping["authors"]]
            if pd.notna(authors_value):
                # If the authors field contains the full taxon name with authors
                # Try to extract just the author part by comparing with species or infra name

                # First check if we have species or infra name for comparison
                species_name = None
                if "species" in column_mapping and column_mapping["species"] in row:
                    species_name = row[column_mapping["species"]]

                infra_name = None
                if "infra" in column_mapping and column_mapping["infra"] in row:
                    infra_name = row[column_mapping["infra"]]

                # Use the most specific name available for comparison
                base_name = infra_name if pd.notna(infra_name) else species_name

                if pd.notna(base_name) and str(authors_value).startswith(
                    str(base_name)
                ):
                    # Extract the part after the base name
                    author_part = str(authors_value)[len(str(base_name)) :].strip()
                    if author_part:  # Check that the author part is not empty
                        return author_part
                elif pd.notna(authors_value):
                    # If we can't extract using comparison, return the whole field
                    # This assumes the field contains only the author information
                    return str(authors_value)

        return ""

    @staticmethod
    def _convert_to_correct_type(value: Any) -> Any:
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    @error_handler(log=True, raise_error=True)
    def _update_nested_set_values(self, session: Any) -> None:
        """
        Update nested set values for the taxonomy tree.

        Args:
            session: Database session

        Raises:
            DatabaseError: If update fails
        """
        try:
            # Get all taxons
            taxons = (
                session.query(TaxonRef)
                .order_by(TaxonRef.rank_name, TaxonRef.full_name)
                .all()
            )
            taxon_dict = {taxon.id: taxon for taxon in taxons}

            def traverse(taxon_id: int, _left: int, level: int) -> int:
                """Traverse tree and update nested set values."""
                taxon = taxon_dict[taxon_id]
                taxon.lft = _left
                taxon.level = level

                right = _left + 1
                child_ids = (
                    session.query(TaxonRef.id)
                    .filter(TaxonRef.parent_id == taxon_id)
                    .order_by(TaxonRef.rank_name, TaxonRef.full_name)
                    .all()
                )
                for (child_id,) in child_ids:
                    right = traverse(child_id, right, level + 1)

                taxon.rght = right
                return right + 1

            # Process root nodes
            left = 1
            root_taxons = (
                session.query(TaxonRef)
                .filter(func.coalesce(TaxonRef.parent_id, 0) == 0)
                .order_by(TaxonRef.rank_name, TaxonRef.full_name)
                .all()
            )
            for taxon in root_taxons:
                left = traverse(taxon.id, left, 0)

            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                "Failed to update nested set values", details={"error": str(e)}
            ) from e

    def _get_rank_names_from_config(self, ranks: Tuple[str, ...]) -> List[str]:
        """
        Get the rank names directly from the configuration.

        Args:
            ranks: Tuple of rank names from the configuration

        Returns:
            List of rank names as they are in the configuration
        """
        # Simply return the ranks as they are
        rank_names = []
        for rank in ranks:
            # If the rank starts with "id_", extract the part after "id_"
            if rank.startswith("id_"):
                rank_name = rank[3:]
                rank_names.append(rank_name)
            else:
                # Otherwise, use the name as it is
                rank_names.append(rank)

        return rank_names
