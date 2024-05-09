import os
import re
import time
from typing import Any, Callable, Dict, List, Union

import pandas as pd
import rasterio  # type: ignore
from loguru import logger
from pyproj import Transformer, ProjError  # type: ignore
from rasterio.errors import RasterioError  # type: ignore
from rich.console import Console
from rich.progress import track
from shapely import wkt  # type: ignore

from niamoto.core.models import TaxonRef
from niamoto.common.config import Config
from niamoto.common.database import Database


class TaxonDataProcessor:
    """
    Processor for handling taxon data operations, including reading from a DataFrame,
    processing data, and writing to a database.
    """

    def __init__(self, db_path: str):
        """
        Initialize the processor with a database name.

        Args:
            db_path (str): The path to the database file.
        """
        self.db = Database(db_path)
        self.console = Console()
        self.config = Config()

    def process_and_write_taxon_data(self, data: Any) -> None:
        """
        Process the provided taxon data and write it to the database.
        """
        start_time = time.time()
        # Sort the DataFrame for easier processing

        taxonomy_config = {
            "Family": {"field": "id_family", "parent": ""},
            "Genus": {"field": "id_genus", "parent": "Family"},
            "Species": {"field": "id_species", "parent": "Genus"},
            "Hybrid": {"field": "id_species", "parent": "Genus"},
            "Subspecies": {"field": "id_infra", "parent": "Species"},
            "Variety": {"field": "id_infra", "parent": "Species"},
            "Forma": {"field": "id_infra", "parent": "Species"},
        }

        # Step 1: Create or update all taxons from the data
        # Iterate through each row of the sorted DataFrame
        self.console.print("Generating taxonomic hierarchy", style="italic blue")
        self.generate_taxonomy_from_occurrences(data, TaxonRef, taxonomy_config)

        # Commit the changes to ensure all taxons have been saved
        self.db.commit_session()

        # Step 2: Execute necessary calculations on the data
        self.console.print("Performing calculations", style="italic blue")
        self.perform_calculations(data, taxonomy_config)

        # Commit any additional changes
        self.db.commit_session()

        # Close the database session
        self.db.close_db_session()

        end_time = time.time()
        total_time = end_time - start_time

        self.console.print(
            f"Total processing time: {total_time:.2f} seconds", style="italic blue"
        )

    def generate_taxonomy_from_occurrences(
        self, data: Any, model: Any, config: Dict[str, Any]
    ) -> None:
        """
        Generate the taxonomy hierarchy from occurrence data.

        Args:
            data: DataFrame containing the occurrence data.
            model: The SQLAlchemy model to use for the taxon hierarchy.
            config: Configuration defining the taxonomic ranks and their hierarchy.
        """
        sorted_df = data.sort_values(
            by=["id_family", "id_genus", "id_species", "id_infra"]
        )

        self.create_taxonomic_hierarchy(sorted_df, self.db.session, model, config)

    def create_taxonomic_hierarchy(
        self, data: Any, session: Any, model: Any, taxonomy_config: Dict[str, Any]
    ) -> None:
        """
        Creates a taxonomic hierarchy based on a given configuration.

        Args:
            data: DataFrame containing the taxonomic data.
            session: Database session.
            model: The SQLAlchemy model to use for the taxonomic hierarchy.
            taxonomy_config: Configuration defining the taxonomic ranks and their hierarchy.
        """

        for rank in taxonomy_config:
            self.create_taxons_for_rank(
                data, session, model, rank, taxonomy_config[rank], taxonomy_config
            )

    def create_taxons_for_rank(
        self,
        data: Any,
        session: Any,
        model: Any,
        rank_name: str,
        rank_config: Dict[str, Any],
        taxonomy_config: Dict[str, Any],
    ) -> None:
        """
        Creates taxons for a specific rank based on the configuration.

        Args:
            data: DataFrame containing the taxonomic data.
            session: Database session.
            model: The SQLAlchemy model to use for the taxonomic hierarchy.
            rank_name: The name of the taxonomic rank.
            rank_config: Configuration for the taxonomic rank.
            taxonomy_config: Configuration defining the taxonomic ranks and their hierarchy.
        """
        ids = data[rank_config["field"]].dropna().unique()
        for id_ in track(ids, description=f"{rank_name}"):
            id_native = int(id_) if pd.notna(id_) else None
            taxon = session.query(TaxonRef).filter(TaxonRef.id == id_native).first()
            # query = session.query(model).filter(model.id_taxonref == id_native)
            # taxon_list = db.execute_query(query)
            # taxon = taxon_list[0] if taxon_list else None
            if not taxon:
                row = data[data[rank_config["field"]] == id_].iloc[0]
                # Extract and verify the identifiers for the different taxonomic ranks
                taxon_ids = {
                    "id_family": int(row.get("id_family"))
                    if pd.notna(row.get("id_family"))
                    else None,
                    "id_genus": int(row.get("id_genus"))
                    if pd.notna(row.get("id_genus"))
                    else None,
                    "id_species": int(row.get("id_species"))
                    if pd.notna(row.get("id_species"))
                    else None,
                    "id_infra": int(row.get("id_infra"))
                    if pd.notna(row.get("id_infra"))
                    else None,
                }
                parent_id_field = (
                    taxonomy_config[rank_config["parent"]]["field"]
                    if rank_config["parent"]
                    else None
                )
                parent_id = (
                    int(row[parent_id_field])
                    if parent_id_field and pd.notna(row[parent_id_field])
                    else None
                )
                if parent_id:
                    parent_taxon = (
                        session.query(TaxonRef).filter(TaxonRef.id == parent_id).first()
                    )
                    parent_id = parent_taxon.id if parent_taxon else None

                full_name = self.determine_full_name(row, rank_name)
                taxon = model(
                    id_taxonref=id_native,
                    id_family=int(taxon_ids["id_family"])
                    if pd.notna(taxon_ids["id_family"])
                    else None,
                    id_genus=int(taxon_ids["id_genus"])
                    if pd.notna(taxon_ids["id_genus"])
                    else None,
                    id_species=int(taxon_ids["id_species"])
                    if pd.notna(taxon_ids["id_species"])
                    else None,
                    id_infra=int(taxon_ids["id_infra"])
                    if pd.notna(taxon_ids["id_infra"])
                    else None,
                    rank_name=row.get("rank"),
                    full_name=full_name,
                    parent_id=parent_id,
                )

                session.add(taxon)
        session.commit()

    @staticmethod
    def determine_full_name(row: Any, rank_name: str) -> Any:
        """
        Determine the full name for a given taxon rank.

        Args:
            row (pd.Series): Data row containing taxon information.
            rank_name (str): The rank name of the taxon.

        Returns:
            str: The full name of the taxon.
        """
        if rank_name == "Family":
            return row.get("family", "")
        elif rank_name == "Genus":
            return row["taxaname"].split()[0] if "taxaname" in row else ""
        return row.get("taxaname", "")

    def perform_calculations(self, data: Any, taxonomy_config: Dict[str, Any]) -> None:
        """
        Perform calculations for each taxonomic level and update the Taxon objects in the database.

        Args:
            data (pd.DataFrame): The DataFrame containing occurrence data.
            taxonomy_config (dict): The configuration defining the taxonomic ranks and their hierarchy.
        """

        processed_ranks = set()

        # Perform calculations for each taxonomic level
        for rank_name, taxon_config in taxonomy_config.items():
            rank = taxon_config.get("field")
            if rank and rank not in processed_ranks:
                self.process_group(data, rank, rank_name)
                processed_ranks.add(rank)

        # Commit the changes to the database in one transaction
        self.db.commit_session()

    def process_group(self, data: Any, group_by_rank: str, rank_name: str) -> None:
        """
        Process a group of data for a given taxonomic level and update the database.

        Args:
            data (pd.DataFrame): The DataFrame containing the data to process.
            group_by_rank (str): The field to group the data by.
            rank_name (str): The name of the taxonomic rank to process.
        """
        # Define the calculations to perform for each field
        calculations: Dict[
            str,
            Union[List[Union[str, Callable[..., Any]]], str, Callable[..., Any]],
        ] = {
            "dbh": ["mean", "max", "median"],
            "height": ["max"],
            "wood_density": ["mean", "min", "max"],
            "bark_thickness": ["mean", "min", "max"],
            "leaf_thickness": ["mean", "min", "max"],
            "leaf_area": ["mean", "min", "max"],
            "leaf_sla": ["mean", "min", "max"],
            "leaf_ldmc": ["mean", "min", "max"],
            "occ": ["size"],
            "freq": ["max"],
        }

        # Total number of unique plots
        total_unique_plots = data["plot"].nunique()

        # Define a mapping from Pandas aggregation names to your Taxon model attribute names
        attr_mapping = {
            "mean": "avg",
            "size": "count",
        }

        ids = self.get_unique_ids(group_by_rank)
        for id_ in track(ids, description=f"{rank_name}"):
            # Filter the data for the current id
            filtered_data = data[data[group_by_rank] == id_].copy()
            filtered_data["occ"] = len(filtered_data)
            # Calculate the number of unique plots in the group
            unique_plots_in_group = filtered_data["plot"].nunique()

            # Calculate the frequency percentage for the group
            freq_percentage = (unique_plots_in_group / total_unique_plots) * 100
            filtered_data["freq"] = freq_percentage

            # Group the filtered data and perform all calculations
            grouped_data = filtered_data.groupby(group_by_rank).agg(calculations)

            # Rename the columns using the attribute mapping
            grouped_data.rename(
                columns=lambda x: self.map_attributes(x, attr_mapping), inplace=True
            )
            # Flatten the MultiIndex created by `agg`
            grouped_data.columns = [
                "_".join(col).strip() for col in grouped_data.columns.values
            ]

            grouped_data["occ_um_count"] = filtered_data.groupby(group_by_rank)[
                "in_um"
            ].apply(lambda x: (x.astype(str).str.lower() == "true").sum())

            # Process and update Taxon objects with the calculated metrics
            for taxon_id, metrics in grouped_data.iterrows():
                self.update_taxon(taxon_id, metrics)

            # Extract the coordinates from the filtered data
            # coordinates = self.extract_coordinates(filtered_data)

            # geo_json = {"type": "MultiPoint", "coordinates": coordinates}

    def calculate_frequencies(
        self, taxon_id: int, group_data: Any
    ) -> dict[str, dict[str, float]]:
        """
        Calculate the frequencies for various measurements for a given taxon.

        Args:
            taxon_id (int): The identifier of the Taxon to be updated.
            group_data (Any): The dataset containing the group data.

        Returns:
            dict[str, dict[str, float]]: A dictionary containing the frequencies of the field data categories as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        frequencies = {}

        dbh_bins = [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500]
        elevation_bins = [
            100,
            200,
            300,
            400,
            500,
            600,
            700,
            800,
            900,
            1000,
            1100,
            1200,
            1700,
        ]
        rainfall_bins = [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]
        holdridge_bins = [1, 2, 3]
        strate_bins = [1, 2, 3, 4]

        frequencies["dbh"] = self.process_field_data(group_data["dbh"], dbh_bins)

        """ frequencies["elevation"] = self.process_field_data(
            group_data["elevation"], elevation_bins
        ) """

        frequencies["holdridge"] = self.process_field_data(
            group_data["holdridge"], holdridge_bins
        )
        frequencies["strate"] = self.process_field_data(
            group_data["strate"], strate_bins
        )

        pheno_flower, pheno_fruit = self.calculate_phenology(group_data)

        frequencies["Pheno_flower"] = pheno_flower
        frequencies["pheno_fruit"] = pheno_fruit

        raster_dir = self.config.get("sources", "raster")

        # Define the path to the elevation raster file
        elevation_raster_path = os.path.join(raster_dir, "elevation.tif")

        # If the elevation raster file exists, calculate the distribution using the raster data
        if os.path.exists(elevation_raster_path):
            frequencies["elevation"] = self.calculate_raster_distribution(
                group_data["geo_pt"], elevation_bins, elevation_raster_path
            )
        # If the elevation raster file does not exist, calculate the distribution directly from the elevation data
        else:
            frequencies["elevation"] = self.calculate_direct_distribution(
                group_data["elevation"], elevation_bins
            )

        # Define the path to the rainfall raster file
        rainfall_raster_path = os.path.join(raster_dir, "rainfall.tif")

        # If the rainfall raster file exists, calculate the distribution using the raster data
        if os.path.exists(elevation_raster_path):
            frequencies["rainfall"] = self.calculate_raster_distribution(
                group_data["geo_pt"], rainfall_bins, rainfall_raster_path
            )
        # If the rainfall raster file does not exist, calculate the distribution directly from the rainfall data
        else:
            frequencies["rainfall"] = self.calculate_direct_distribution(
                group_data["rainfall"], rainfall_bins
            )

        return frequencies

    def update_taxon(self, taxon_id: int, update_data: Dict[str, Any]) -> None:
        """
        Update a Taxon object in the database with provided data.

        Args:
            taxon_id (int): The identifier of the Taxon to be updated.
            update_data (dict): The data to update the Taxon with.
        """
        # Fetch the Taxon object from the database
        taxon = self.db.session.query(TaxonRef).filter_by(id_taxonref=taxon_id).first()

        if taxon:
            # Update the Taxon object with the provided data
            for attr, value in update_data.items():
                setattr(taxon, attr, round(value, 2))

            # Commit the changes to the database
            self.db.commit_session()
        else:
            logger.error(f"Taxon with id {taxon_id} not found in the database.")

    @staticmethod
    def extract_coordinates(filtered_data: Any) -> List[List[float]]:
        """
        Extract geographic coordinates from the filtered data.

        Args:
            filtered_data (pd.DataFrame): The DataFrame containing the filtered data.

        Returns:
            list: A list of coordinates.
        """

        # This code returns a list of coordinates. For each point in the 'geo_pt' column of the filtered_data DataFrame,
        # it removes the "POINT (" and ")" strings, splits the remaining string into a list of strings,
        # converts each string to a float, and adds the list of floats to the outer list.
        # It only does this if the point is not NaN.
        return [
            list(map(float, str(point).replace("POINT (", "").replace(")", "").split()))
            for point in filtered_data["geo_pt"]
            if pd.notna(point)  # Check that the point is not NaN
        ]

    def get_unique_ids(self, field_name: str) -> List[int]:
        """
        Retrieve unique identifiers for a specified field from the database.

        Args:
            field_name (str): The field name to retrieve unique identifiers for.

        Returns:
            List[int]: A list of unique identifiers.
        """
        query = self.db.session.query(getattr(TaxonRef, field_name)).distinct()
        unique_ids = [record[0] for record in query.all() if record[0] is not None]
        return unique_ids

    @staticmethod
    def map_attributes(column_name: str, attr_mapping: Any) -> Any:
        """
        Maps the attributes of a column name based on a given attribute mapping.

        Args:
            column_name (str): The name of the column to map the attributes of.
            attr_mapping (dict): A dictionary containing the old attribute names as keys and the new attribute names as values.

        Returns:
            str: The column name with the attributes mapped according to the attribute mapping.
        """
        for old_attr, new_attr in attr_mapping.items():
            column_name = column_name.replace(old_attr, new_attr)
        return column_name

    @staticmethod
    def process_field_data(data: Any, bins: List[int]) -> dict[Any, Any]:
        """
        Categorizes the field data into specified bins and calculates the frequencies for each category.
        The frequencies are then converted to percentages and returned as a dictionary.

        Args:
            data (Any): The dataset containing the field data.
            bins (List[int]): The list of bins to categorize the data.

        Returns:
            dict[Any, Any]: A dictionary containing the frequencies of the field data categories as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        # Distribute the data into categories
        binned_data = pd.cut(data.dropna(), bins=bins, right=False)

        # Calculate the frequencies for each category
        data_counts = binned_data.value_counts(sort=False, normalize=True)

        # Convert to percentages
        data_percentages = data_counts.apply(
            lambda x: round(x * 100, 2) if not pd.isna(x) else 0.0
        )

        # Convert to dictionary
        return {
            str(interval.left): percentage
            for interval, percentage in data_percentages.items()
            if isinstance(interval, pd.Interval)
        }

    def calculate_phenology(
        self, group_data: Any
    ) -> tuple[dict[int, int], dict[int, int]]:
        """
        Calculate the frequency of flower and fruit occurrences for each month based on the input data.

        Args:
            group_data (Any): A pandas DataFrame containing the data for a specific taxon group. It should have columns `month_obs`, `flower`, and `fruit`.

        Returns:
            tuple[dict[int, int], dict[int, int]]: A tuple containing two dictionaries:
                - `flower_freq`: A dictionary where the keys represent the months (1 to 12) and the values represent the frequency of flower occurrences for each month.
                - `fruit_freq`: A dictionary where the keys represent the months (1 to 12) and the values represent the frequency of fruit occurrences for each month.
        """
        # Initialiser les dictionnaires pour les fréquences avec des clés numériques pour les mois
        pheno_flower = {month: 0 for month in range(1, 13)}
        pheno_fruit = {month: 0 for month in range(1, 13)}

        # Compter les occurrences pour chaque mois
        for month in range(1, 13):
            monthly_data = group_data[group_data["month_obs"] == month]

            if not monthly_data.empty:
                flower_count = monthly_data["flower"].sum()
                fruit_count = monthly_data["fruit"].sum()
                total_count = len(monthly_data)

                pheno_flower[month] = round(flower_count / total_count * 100)
                pheno_fruit[month] = round(fruit_count / total_count * 100)

        return pheno_flower, pheno_fruit

    def calculate_direct_distribution(
        self, data: Any, value_bins: List[int]
    ) -> dict[str, float]:
        """
        Calculate the distribution of values directly from the data.

        Args:
            data (Any): The dataset containing the data.
            value_bins (List[int]): The list of bins to categorize the data.

        Returns:
            dict[str, float]: A dictionary containing the distribution of values as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        filtered_values = data.dropna().tolist()

        return self.calculate_distribution(filtered_values, value_bins)

    def calculate_raster_distribution(
        self, geo_points: Any, value_bins: List[int], raster_path: str
    ) -> dict[str, float]:
        """
        Calculate the distribution of values from a raster file.

        Args:
            geo_points (Any): The geographic points to extract the values from.
            value_bins (List[int]): The list of bins to categorize the data.
            raster_path (str): The path to the raster file.

        Returns:
            dict[str, float]: A dictionary containing the distribution of values as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        raster_values = self.extract_raster_values(geo_points, raster_path)
        filtered_values = [value for value in raster_values if value is not None]

        return self.calculate_distribution(filtered_values, value_bins)

    def calculate_distribution(
        self, values: List[float], value_bins: List[int]
    ) -> dict[str, float]:
        """
        Calculate the distribution of values.

        Args:
            values (List[float]): The list of values.
            value_bins (List[int]): The list of bins to categorize the values.

        Returns:
            dict[str, float]: A dictionary containing the distribution of values as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        total_count = len(values)
        percentages_per_interval = {}

        previous_bin_edge = 0
        for bin_edge in value_bins:
            count_in_interval = sum(
                previous_bin_edge < value <= bin_edge for value in values
            )
            percentage = (
                round((count_in_interval / total_count) * 100, 2)
                if total_count > 0
                else 0.0
            )
            interval_label = f"{previous_bin_edge}-{bin_edge}"
            percentages_per_interval[interval_label] = percentage

            previous_bin_edge = bin_edge

        return percentages_per_interval

    @staticmethod
    def extract_raster_values(geo_points: Any, raster_path: str) -> Any:
        """
        Extract values for given geo points from a raster file.

        Args:
            geo_points (Any): The geographic points to extract the values from.
            raster_path (str): The path to the raster file.

        Returns:
            pd.Series: A pandas Series containing the extracted raster values.
        """
        raster_values = pd.Series([None] * len(geo_points))

        try:
            with rasterio.open(raster_path) as raster:
                transformer = Transformer.from_crs(
                    "epsg:4326", raster.crs, always_xy=True
                )
                point_pattern = re.compile(
                    r"POINT \(\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*\)"
                )
                raster_array = raster.read(1)

                for i, point_str in enumerate(geo_points):
                    if pd.notna(point_str) and point_pattern.match(point_str):
                        try:
                            point = wkt.loads(point_str)
                            x_transformed, y_transformed = transformer.transform(
                                point.x, point.y
                            )
                            row, col = raster.index(x_transformed, y_transformed)

                            if 0 <= col < raster.width and 0 <= row < raster.height:
                                raster_values[i] = raster_array[row, col]
                        except (RasterioError, ValueError, TypeError) as e:
                            logger.exception(
                                f"Erreur lors de l'extraction de la valeur raster: {e}"
                            )

        except ProjError as e:
            logger.error(f"Erreur de projection: {e}")

        return raster_values
