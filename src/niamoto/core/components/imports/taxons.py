"""
This module contains the TaxonomyImporter class used to
import taxonomy data from a CSV file or occurrences into the database.
"""

from pathlib import Path
from typing import Tuple, Optional, Any, Dict, List

import pandas as pd
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)
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
    def import_from_csv(
        self,
        file_path: str,
        ranks: Tuple[str, ...],
        api_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Import taxonomy from a CSV file.

        Args:
            file_path (str): Path to the CSV file.
            ranks (Tuple[str, ...]): Taxonomy ranks to process.
            api_config (Optional[Dict[str, Any]]): API configuration for enrichment.

        Returns:
            str: Success message.

        Raises:
            FileReadError: If file cannot be read.
            ValidationError: If data is invalid.
            ProcessError: If processing fails.
        """
        try:
            # Validate file exists
            file_path = str(Path(file_path).resolve())
            if not Path(file_path).exists():
                raise FileReadError(file_path, "Taxonomy file not found")

            # Read and validate CSV
            try:
                df = pd.read_csv(file_path)
            except Exception as e:
                raise FileReadError(file_path, f"Failed to read CSV: {str(e)}") from e

            # Prepare and process data
            df = self._prepare_dataframe(df, ranks)

            # Process the data with optional API enrichment
            count = self._process_dataframe(df, ranks, api_config)

            # Return success message with just the filename, not the full path
            return f"{count} taxons imported from {Path(file_path).name}."
        except Exception as e:
            if isinstance(e, (FileReadError, DataValidationError)):
                raise
            raise TaxonomyImportError(
                f"Failed to import taxonomy data: {str(e)}",
                details={"file": file_path, "error": str(e)},
            ) from e

    @error_handler(log=True, raise_error=True)
    def import_from_occurrences(
        self,
        occurrences_file: str,
        ranks: Tuple[str, ...],
        column_mapping: Dict[str, str],
        api_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extract and import taxonomy data from occurrences.

        Args:
            occurrences_file (str): Path to occurrences CSV file.
            ranks (Tuple[str, ...]): Taxonomy ranks to import.
            column_mapping (Dict[str, str]): Mapping between taxonomy fields and occurrence columns.
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

            # Validate column mapping
            required_columns = ["taxon_id", "family", "genus", "species"]
            missing_columns = [
                col for col in required_columns if col not in column_mapping
            ]
            if missing_columns:
                raise DataValidationError(
                    "Missing required column mappings",
                    [{"field": col} for col in missing_columns],
                )

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

        # Create dictionaries to store relationships
        family_ids = {}  # family_name -> id
        genus_ids = {}  # genus_name -> id

        # Use the ranks from configuration if provided
        rank_names = list(ranks) if ranks else []

        try:
            with self.db.session() as session:
                # First pass: insert all taxa into database to get auto-generated IDs
                # Variable to store the current enrichment message
                current_enrichment_message = "[green]Importing taxonomy data[/green]"
                if api_enricher:
                    current_enrichment_message = (
                        "[green]Enriching taxonomy data[/green]"
                    )

                with Progress(
                    SpinnerColumn(),
                    TextColumn("{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                    refresh_per_second=10,
                ) as progress:
                    task_insert = progress.add_task(
                        current_enrichment_message, total=len(df)
                    )

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
                                                "✓" in last_message
                                                or "✗" in last_message
                                            ):
                                                # Update the task description with the current message
                                                # Preserve the message formatting
                                                current_enrichment_message = (
                                                    last_message
                                                )
                                                progress.update(
                                                    task_insert,
                                                    description=current_enrichment_message,
                                                )
                                except Exception as e:
                                    error_msg = f"API enrichment failed for {row_dict.get('full_name')}: {str(e)}"
                                    # Update the task description with the error message
                                    # Preserve the bold red formatting for the error
                                    current_enrichment_message = (
                                        f"[bold red]{error_msg}[/]"
                                    )
                                    progress.update(
                                        task_insert,
                                        description=current_enrichment_message,
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
                            if rank_name == rank_names[0]:  # First rank (family)
                                family_ids[row["full_name"]] = taxon.id
                            elif rank_name == rank_names[1]:  # Second rank (genus)
                                genus_ids[row["full_name"]] = taxon.id

                                # Link genus to its family
                                if "parent_family_name" in row and pd.notna(
                                    row["parent_family_name"]
                                ):
                                    family_name = row["parent_family_name"]
                                    if family_name in family_ids:
                                        taxon.parent_id = family_ids[family_name]

                            elif (
                                rank_name in rank_names[2:]
                            ):  # Subsequent ranks (species, infra)
                                # Link species to its genus
                                if "parent_genus_name" in row and pd.notna(
                                    row["parent_genus_name"]
                                ):
                                    genus_name = row["parent_genus_name"]
                                    if genus_name in genus_ids:
                                        taxon.parent_id = genus_ids[genus_name]

                            # Count imported taxa
                            imported_count += 1

                            # Update progress
                            progress.update(task_insert, advance=1)

                            # Periodic commit
                            if imported_count % 10 == 0:
                                session.commit()

                    # Final commit for all records
                    session.commit()

                # Second pass: update nested set values
                progress.console.print("[yellow]Updating nested set model...")
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

        # Select relevant columns for taxonomy
        taxon_cols = []
        for key in ["taxon_id", "family", "genus", "species", "infra"]:
            if key in column_mapping and column_mapping[key] in df.columns:
                taxon_cols.append(column_mapping[key])

        # Include additional columns that might be useful
        for col in ["taxaname", "taxonref", "id_rank"]:
            if col in df.columns and col not in taxon_cols:
                taxon_cols.append(col)

        # Create a DataFrame with only taxonomy related columns
        occurrences_taxa = df[taxon_cols].drop_duplicates()

        # Initialize structures to track unique taxa
        unique_families = set()
        unique_genera = {}  # genus -> family
        species_data = []  # list to store species level data

        # Extract unique taxonomic data
        for _, row in occurrences_taxa.iterrows():
            # Extract taxonomy information
            family = (
                row[column_mapping["family"]]
                if "family" in column_mapping and column_mapping["family"] in row
                else None
            )
            genus = (
                row[column_mapping["genus"]]
                if "genus" in column_mapping and column_mapping["genus"] in row
                else None
            )
            species = (
                row[column_mapping["species"]]
                if "species" in column_mapping and column_mapping["species"] in row
                else None
            )
            infra = (
                row[column_mapping["infra"]]
                if "infra" in column_mapping and column_mapping["infra"] in row
                else None
            )

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
            if not family and not genus:
                continue

            # Determine rank from data and process accordingly
            if species and pd.notna(species):
                # This is a species or infra-species level entry
                if infra and pd.notna(infra):
                    # Use the 4th rank if it exists, otherwise "infra"
                    rank_name = rank_names[3] if len(rank_names) > 3 else "infra"
                else:
                    # Use the 3rd rank if it exists, otherwise "species"
                    rank_name = rank_names[2] if len(rank_names) > 2 else "species"

                # Add family to unique set
                if family and pd.notna(family):
                    unique_families.add(family)

                # Add genus to dict with its family
                if genus and pd.notna(genus) and family and pd.notna(family):
                    unique_genera[genus] = family

                # Store all relevant data for species level entries
                species_data.append(
                    {
                        "taxon_id": taxon_id,
                        "family": family,
                        "genus": genus,
                        "species": species,
                        "infra": infra,
                        "rank_name": rank_name,
                        "full_name": self._build_full_name(row, column_mapping),
                        "authors": self._extract_authors(row, column_mapping),
                        "taxonref": (
                            row["taxonref"]
                            if "taxonref" in row and pd.notna(row["taxonref"])
                            else None
                        ),
                    }
                )
            elif genus and pd.notna(genus):
                # This is a genus-only entry with taxon_id
                genus_rank = rank_names[1] if len(rank_names) > 1 else "genus"
                if taxon_id is not None:
                    # Store genus data with taxon_id for later processing
                    species_data.append(
                        {
                            "taxon_id": taxon_id,
                            "family": family,
                            "genus": genus,
                            "species": None,
                            "infra": None,
                            "rank_name": genus_rank,
                            "full_name": genus,
                            "authors": self._extract_authors(row, column_mapping),
                            "taxonref": (
                                row["taxonref"]
                                if "taxonref" in row and pd.notna(row["taxonref"])
                                else None
                            ),
                        }
                    )
                # Also add to unique genera for hierarchy building
                if family and pd.notna(family):
                    unique_genera[genus] = family
            elif family and pd.notna(family):
                # This is a family-only entry with taxon_id
                family_rank = rank_names[0] if rank_names else "family"
                if taxon_id is not None:
                    # Store family data with taxon_id for later processing
                    species_data.append(
                        {
                            "taxon_id": taxon_id,
                            "family": family,
                            "genus": None,
                            "species": None,
                            "infra": None,
                            "rank_name": family_rank,
                            "full_name": family,
                            "authors": self._extract_authors(row, column_mapping),
                            "taxonref": (
                                row["taxonref"]
                                if "taxonref" in row and pd.notna(row["taxonref"])
                                else None
                            ),
                        }
                    )
                # Always add to unique families
                unique_families.add(family)

        # Create the taxonomy entries in the correct order
        taxonomy_entries = []

        # Track which families and genera have explicit taxon_ids
        families_with_ids = {
            data["family"]: data
            for data in species_data
            if data["rank_name"] == (rank_names[0] if rank_names else "family")
            and data["taxon_id"] is not None
        }
        genera_with_ids = {
            data["genus"]: data
            for data in species_data
            if data["rank_name"] == (rank_names[1] if len(rank_names) > 1 else "genus")
            and data["taxon_id"] is not None
        }

        # 1. Add families (highest level)
        family_rank = rank_names[0] if rank_names else "family"

        for family in unique_families:
            # Check if this family has an explicit taxon_id
            if family in families_with_ids:
                # Use the data from species_data with taxon_id
                data = families_with_ids[family]
                taxonomy_entries.append(
                    {
                        "full_name": data["full_name"],
                        "rank_name": data["rank_name"],
                        "authors": data["authors"],
                        "parent_id": None,  # Families are top-level
                        "taxon_id": data["taxon_id"],
                        "extra_data": {
                            "auto_generated": False,
                            "taxon_type": family_rank,
                            "original_id": data["taxon_id"],
                        },
                    }
                )
            else:
                # Auto-generate family entry
                taxonomy_entries.append(
                    {
                        "full_name": family,
                        "rank_name": family_rank,
                        "authors": "",
                        "parent_id": None,  # Families are top-level
                        "taxon_id": None,  # No external ID for automatically generated families
                        "extra_data": {
                            "auto_generated": True,
                            "taxon_type": family_rank,
                            "original_id": None,
                        },
                    }
                )

        # 2. Add genera
        genus_rank = rank_names[1] if len(rank_names) > 1 else "genus"

        for genus, family in unique_genera.items():
            # Check if this genus has an explicit taxon_id
            if genus in genera_with_ids:
                # Use the data from species_data with taxon_id
                data = genera_with_ids[genus]
                taxonomy_entries.append(
                    {
                        "full_name": data["full_name"],
                        "rank_name": data["rank_name"],
                        "authors": data["authors"],
                        "parent_family_name": family,
                        "taxon_id": data["taxon_id"],
                        "extra_data": {
                            "auto_generated": False,
                            "taxon_type": genus_rank,
                            "parent_family": family,
                            "original_id": data["taxon_id"],
                        },
                    }
                )
            else:
                # Auto-generate genus entry
                taxonomy_entries.append(
                    {
                        "full_name": genus,
                        "rank_name": genus_rank,
                        "authors": "",
                        "parent_family_name": family,
                        "taxon_id": None,
                        "extra_data": {
                            "auto_generated": True,
                            "taxon_type": genus_rank,
                            "parent_family": family,
                            "original_id": None,
                        },
                    }
                )

        # 3. Add species and subspecies
        for data in species_data:
            # Skip if this entry was already processed as a family or genus
            if (
                data["rank_name"] == family_rank and data["family"] in families_with_ids
            ) or (data["rank_name"] == genus_rank and data["genus"] in genera_with_ids):
                continue

            # Get the external ID of the taxon
            external_id = data["taxon_id"]

            entry = {
                "full_name": data["full_name"],
                "rank_name": data["rank_name"],
                "authors": data["authors"],
                "parent_genus_name": data[
                    "genus"
                ],  # Use this to create relationship after DB insertion
                "taxon_id": external_id,  # Store the external ID in the new field
                "extra_data": {
                    "auto_generated": False,
                    "taxon_type": data["rank_name"],
                    "parent_family": data["family"],
                    "parent_genus": data["genus"],
                },
            }

            # Add external ID in extra_data with the name corresponding to the key in column_mapping
            if external_id is not None and "taxon_id" in column_mapping:
                # Use the column name as key in extra_data
                entry["extra_data"][column_mapping["taxon_id"]] = external_id

            # Add taxonref to extra_data if available
            if data["taxonref"]:
                entry["extra_data"]["taxonref"] = data["taxonref"]

            taxonomy_entries.append(entry)

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

    @error_handler(log=True, raise_error=True)
    def _prepare_dataframe(
        self, df: pd.DataFrame, ranks: Tuple[str, ...]
    ) -> pd.DataFrame:
        """
        Prepare dataframe for processing.

        Args:
            df: Input dataframe
            ranks: Taxonomy ranks

        Returns:
            Prepared dataframe

        Raises:
            DataValidationError: If preparation fails
        """
        try:
            # Make sure we have all required columns
            required_fields = {"id_taxon", "full_name", "rank_name"}
            for field in required_fields:
                if field not in df.columns:
                    if field == "rank_name" and "rank" in ranks:
                        # Handle special case for rank_name
                        df["rank_name"] = df.apply(
                            lambda row: self._get_rank_name_from_rank_id(
                                self._get_rank(row, ranks)
                            ),
                            axis=1,
                        )
                    else:
                        raise DataValidationError(
                            f"Required field '{field}' missing in taxonomy data",
                            [{"field": field}],
                        )

            # Ensure authors column exists
            if "authors" not in df.columns:
                df["authors"] = None

            # Identify the rank of each row if not already present
            if "rank" not in df.columns:
                df["rank"] = df.apply(lambda row: self._get_rank(row, ranks), axis=1)

            # Get parent ID for each row if not already present
            if "parent_id" not in df.columns:
                df["parent_id"] = df.apply(
                    lambda row: self._get_parent_id(row, ranks), axis=1
                )

            # Sort for processing
            df.sort_values(by=["rank", "full_name"], inplace=True)

            return df
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise
            raise DataValidationError(
                "Failed to prepare taxonomy data", [{"error": str(e)}]
            ) from e

    @staticmethod
    def _get_rank(row: Any, ranks: Tuple[str, ...]) -> Optional[str]:
        """
        Get the rank of a row.

        Args:
            row (Any): The row to get the rank from.
            ranks (Tuple[str, ...]): The ranks to get.

        Returns:
            Optional[str]: The rank of the row.
        """
        for rank in reversed(ranks):
            if rank in row and pd.notna(row[rank]) and row["id_taxon"] == row[rank]:
                return rank
        return None

    @staticmethod
    def _get_parent_id(row: Any, ranks: Tuple[str, ...]) -> Optional[int]:
        """
        Get the parent id of a row.

        Args:
            row (Any): The row to get the parent id from.
            ranks (Tuple[str, ...]): The ranks to get.

        Returns:
            Optional[int]: The parent id of the row.
        """
        for rank in reversed(ranks):
            if rank in row and pd.notna(row[rank]) and row["id_taxon"] != row[rank]:
                parent_id = row[rank]
                if not pd.isna(parent_id):
                    try:
                        return int(parent_id)
                    except (ValueError, TypeError):
                        return None
        return None

    @staticmethod
    def _get_rank_name_from_rank_id(rank_id: Optional[str]) -> str:
        """
        Convert a rank ID to a rank name.

        Args:
            rank_id: The rank ID to convert

        Returns:
            str: The rank name.
        """
        mapping = {
            "id_famille": "family",
            "id_genre": "genus",
            "id_espèce": "species",
            "id_sous-espèce": "infra",
        }
        return mapping.get(rank_id, "unknown")

    @error_handler(log=True, raise_error=True)
    def _process_dataframe(self, df: pd.DataFrame, ranks: Tuple[str, ...]) -> int:
        """
        Process dataframe and import data.

        Args:
            df: Dataframe to process
            ranks: Taxonomy ranks

        Returns:
            Number of imported records

        Raises:
            TaxonomyImportError: If processing fails
            DatabaseError: If database operations fail
        """
        imported_count = 0

        try:
            with self.db.session() as session:
                # Calculate the total number of taxons to process
                total_taxons = sum(len(df[df["rank"] == rank]) for rank in ranks)

                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                    refresh_per_second=10,  # Refresh more often
                )

                with progress:
                    task = progress.add_task(
                        "[green]Importing taxons", total=total_taxons
                    )

                    for _, row in df.iterrows():
                        try:
                            taxon = self._create_or_update_taxon(row, session, ranks)
                            if taxon is not None:
                                imported_count += 1
                        except SQLAlchemyError as e:
                            raise DatabaseError(
                                f"Database error while processing taxon: {str(e)}",
                            ) from e

                        # Update the progress bar
                        progress.update(task, advance=1)

                        # Commit and update nested set values after each rank
                        if imported_count > 0 and imported_count % 1000 == 0:
                            session.commit()
                            self._update_nested_set_values(session)

                    # Commit final and update nested set values
                    session.commit()
                    self._update_nested_set_values(session)

            return imported_count

        except Exception as e:
            if isinstance(e, DatabaseError):
                raise
            raise TaxonomyImportError(
                "Failed to process taxonomy data", details={"error": str(e)}
            ) from e

    @error_handler(log=True, raise_error=True)
    def _create_or_update_taxon(
        self, row: Any, session: Any, ranks: Tuple[str, ...]
    ) -> Optional[TaxonRef]:
        """
        Create or update a taxon record.

        Args:
            row: Data row
            session: Database session
            ranks: Taxonomy ranks

        Returns:
            Created or updated taxon

        Raises:
            DatabaseError: If database operation fails
        """
        taxon_id = int(row["id_taxon"])
        try:
            # Get or create taxon
            taxon: Optional[TaxonRef] = (
                session.query(TaxonRef).filter_by(id=taxon_id).one_or_none()
            )

            if taxon is None:
                taxon = TaxonRef(id=taxon_id)
                session.add(taxon)

            # Update fields
            taxon.full_name = row["full_name"]
            taxon.authors = row["authors"] if pd.notna(row["authors"]) else None
            taxon.rank_name = row["rank_name"]

            # Set parent ID
            parent_id = row["parent_id"]
            if not pd.isna(parent_id):
                taxon.parent_id = int(parent_id)

            # Store extra data
            standard_fields = ["id_taxon", "full_name", "authors", "rank", "parent_id"]
            all_ignored_fields = set(standard_fields).union(ranks)
            extra_data = {
                key: None if pd.isna(value) else self._convert_to_correct_type(value)
                for key, value in row.items()
                if key not in all_ignored_fields
            }
            taxon.extra_data = extra_data

            session.flush()
            return taxon

        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                f"Failed to create/update taxon {taxon_id}", details={"error": str(e)}
            ) from e

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
