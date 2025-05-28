from unittest.mock import MagicMock, patch
import pandas as pd
import os
import tempfile

from niamoto.core.plugins.loaders.stats_loader import StatsLoader, StatsLoaderConfig
from niamoto.common.exceptions import DataLoadError
from tests.common.base_test import NiamotoTestCase


class TestStatsLoader(NiamotoTestCase):
    """Test case for the StatsLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Create a temporary directory for config to avoid creating at project root
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")

        # Mock the database connection (as expected by Plugin.__init__)
        self.mock_db = MagicMock()
        self.mock_db.engine = MagicMock()

        # Mock Config to prevent creating config directory at project root
        with patch("niamoto.core.plugins.loaders.stats_loader.Config") as mock_config:
            mock_config.return_value.get_imports_config = {}
            mock_config.return_value.config_dir = self.config_dir
            self.loader = StatsLoader(db=self.mock_db)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        # Clean up temporary directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        super().tearDown()

    # --- Tests for validate_config ---

    def test_validate_config_success(self):
        """Test successful validation of a minimal configuration."""
        config = {
            "plugin": "stats_loader",
            "query": "SELECT value FROM some_table WHERE group_id = :id",
        }
        validated_config = self.loader.validate_config(config)
        self.assertIsInstance(validated_config, StatsLoaderConfig)
        self.assertEqual(validated_config.plugin, "stats_loader")

    def test_validate_config_full_success(self):
        """Test successful validation of a full configuration."""
        config = {
            "plugin": "stats_loader",
            "data": "some_data_source",
            "statistic": "mean",
            "default_value": 0.0,
            "column": "target_col",
        }
        validated_config = self.loader.validate_config(config)
        self.assertIsInstance(validated_config, StatsLoaderConfig)
        self.assertEqual(validated_config.plugin, "stats_loader")

    # --- Tests for load_data ---

    @patch("pandas.read_sql")
    def test_load_data_db_success(self, mock_read_sql):
        """Test successful data loading from the database."""
        # --- Arrange ---
        group_id = 123
        config = {
            "plugin": "stats_loader",
            "data": "main_table",  # Corresponds to DB table name here
            "grouping": "ref_table",
            "key": "foreign_key",
        }
        # Mock imports_config to indicate non-CSV source (implicitly DB)
        self.loader.imports_config = {
            "main_table": {"type": "database"}
        }  # Or any type != 'csv'
        expected_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        mock_read_sql.return_value = expected_df

        # --- Act ---
        result_df = self.loader.load_data(group_id, config)

        # --- Assert ---
        pd.testing.assert_frame_equal(result_df, expected_df)
        mock_read_sql.assert_called_once()
        # Verify the constructed query (optional but good)
        args, kwargs = mock_read_sql.call_args
        query_string = str(args[0]).strip()  # Get the query text
        expected_query = """
                SELECT m.*
                FROM main_table m
                JOIN ref_table ref ON m.foreign_key = ref.id
                WHERE ref.id = :group_id
            """.strip()
        # Normalize whitespace for comparison
        self.assertEqual(
            " ".join(query_string.split()), " ".join(expected_query.split())
        )
        self.assertEqual(kwargs["params"], {"group_id": group_id})
        self.assertEqual(
            args[1], self.mock_db.engine.connect().__enter__()
        )  # Check connection used

    @patch("pandas.read_sql")
    def test_load_data_db_read_error(self, mock_read_sql):
        """Test DataLoadError when pd.read_sql fails."""
        # --- Arrange ---
        group_id = 456
        config = {
            "plugin": "stats_loader",
            "data": "another_table",
            "grouping": "refs",
            "key": "fk",
        }
        self.loader.imports_config = {"another_table": {"type": "db"}}
        mock_read_sql.side_effect = Exception("Database connection failed")

        # --- Act & Assert ---
        with self.assertRaises(DataLoadError) as cm:
            self.loader.load_data(group_id, config)

        # Check the final exception message and the original cause
        self.assertIn("Failed to load statistics data", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, Exception)
        self.assertEqual("Database connection failed", cm.exception.__cause__.args[0])

    @patch("os.path.exists", return_value=True)
    @patch("pandas.read_csv")
    def test_load_data_csv_success_comma(self, mock_read_csv, mock_exists):
        """Test successful data loading from a comma-separated CSV."""
        # --- Arrange ---
        group_id = 789
        source_key = "csv_stats"
        csv_rel_path = "data/stats.csv"
        config_dir = "/fake/config/dir"
        base_dir = os.path.dirname(config_dir)
        full_csv_path = os.path.join(base_dir, csv_rel_path)

        config = {
            "plugin": "stats_loader",
            "data": source_key,
        }  # Grouping/key not needed for CSV
        source_config = {"type": "csv", "path": csv_rel_path, "identifier": "record_id"}
        self.loader.imports_config = {source_key: source_config}
        # Mock config_dir used in _load_from_csv
        self.loader.config.config_dir = config_dir

        # Simulate pd.read_csv succeeding with comma, returning filtered data
        df_full = pd.DataFrame({"record_id": [789, 790], "value": [10, 20]})
        mock_read_csv.return_value = df_full
        expected_df = pd.DataFrame({"record_id": [789], "value": [10]})

        # --- Act ---
        result_df = self.loader.load_data(group_id, config)

        # --- Assert ---
        mock_exists.assert_called_once_with(full_csv_path)
        # Called once with default comma separator
        mock_read_csv.assert_called_once_with(full_csv_path, encoding="utf-8")
        pd.testing.assert_frame_equal(result_df, expected_df)

    @patch("os.path.exists", return_value=True)
    @patch("pandas.read_csv")
    def test_load_data_csv_success_semicolon(self, mock_read_csv, mock_exists):
        """Test successful data loading from a semicolon-separated CSV (fallback)."""
        # --- Arrange ---
        group_id = 101
        source_key = "csv_stats_semi"
        csv_rel_path = "data/stats_semi.csv"
        config_dir = "/other/config/dir"
        base_dir = os.path.dirname(config_dir)
        full_csv_path = os.path.join(base_dir, csv_rel_path)

        config = {"plugin": "stats_loader", "data": source_key}
        source_config = {"type": "csv", "path": csv_rel_path}  # Default identifier 'id'
        self.loader.imports_config = {source_key: source_config}
        self.loader.config.config_dir = config_dir

        # Simulate read_csv failing with comma, then succeeding with semicolon
        df_full = pd.DataFrame({"id": [101, 102], "metric": [1.5, 2.5]})
        mock_read_csv.side_effect = [
            pd.errors.ParserError("Failed with comma"),  # First call fails
            df_full,  # Second call succeeds
        ]
        expected_df = pd.DataFrame({"id": [101], "metric": [1.5]})

        # --- Act ---
        result_df = self.loader.load_data(group_id, config)

        # --- Assert ---
        mock_exists.assert_called_once_with(full_csv_path)
        self.assertEqual(mock_read_csv.call_count, 2)
        # Check calls
        call_args_list = mock_read_csv.call_args_list
        self.assertEqual(call_args_list[0][0], (full_csv_path,))
        self.assertEqual(
            call_args_list[0][1], {"encoding": "utf-8"}
        )  # First call args/kwargs
        self.assertEqual(call_args_list[1][0], (full_csv_path,))
        self.assertEqual(
            call_args_list[1][1], {"sep": ";", "decimal": ".", "encoding": "utf-8"}
        )  # Second call
        pd.testing.assert_frame_equal(result_df, expected_df)

    def test_load_data_source_not_found(self):
        """Test DataLoadError when the source key is not in imports_config."""
        # --- Arrange ---
        group_id = 1
        config = {"plugin": "stats_loader", "data": "non_existent_source"}
        self.loader.imports_config = {
            "real_source": {"type": "csv", "path": "..."}
        }  # No match

        # --- Act & Assert ---
        with self.assertRaises(DataLoadError) as cm:
            self.loader.load_data(group_id, config)

        # Check the final exception message and the original cause
        self.assertIn("Failed to load statistics data", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, DataLoadError)
        self.assertIn(
            "Source non_existent_source not found", str(cm.exception.__cause__)
        )

    @patch("os.path.exists", return_value=False)  # Mock os.path.exists to return False
    def test_load_data_csv_file_not_found(self, mock_exists):
        """Test DataLoadError when the CSV file does not exist."""
        # --- Arrange ---
        group_id = 2
        source_key = "missing_csv"
        csv_rel_path = "data/nonexistent.csv"
        config_dir = "/config"
        base_dir = os.path.dirname(config_dir)
        full_csv_path = os.path.join(base_dir, csv_rel_path)

        config = {"plugin": "stats_loader", "data": source_key}
        source_config = {"type": "csv", "path": csv_rel_path}
        self.loader.imports_config = {source_key: source_config}
        self.loader.config.config_dir = config_dir

        # --- Act & Assert ---
        with self.assertRaises(DataLoadError) as cm:
            self.loader.load_data(group_id, config)

        mock_exists.assert_called_once_with(full_csv_path)
        # Check the final exception message and the original cause
        self.assertIn("Failed to load statistics data", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, DataLoadError)
        self.assertEqual("CSV file not found", cm.exception.__cause__.args[0])
        self.assertEqual(cm.exception.details.get("path"), full_csv_path)

    @patch("os.path.exists", return_value=True)
    @patch("pandas.read_csv")
    def test_load_data_csv_parse_error(self, mock_read_csv, mock_exists):
        """Test DataLoadError when pd.read_csv fails for both separators."""
        # --- Arrange ---
        group_id = 3
        source_key = "bad_csv"
        csv_rel_path = "data/unreadable.csv"
        config_dir = "/another/config"
        base_dir = os.path.dirname(config_dir)
        full_csv_path = os.path.join(base_dir, csv_rel_path)

        config = {"plugin": "stats_loader", "data": source_key}
        source_config = {"type": "csv", "path": csv_rel_path}
        self.loader.imports_config = {source_key: source_config}
        self.loader.config.config_dir = config_dir

        # Simulate pd.read_csv failing on both attempts
        mock_read_csv.side_effect = [
            pd.errors.ParserError("Comma fail"),
            pd.errors.ParserError("Semicolon fail"),
        ]

        # --- Act & Assert ---
        with self.assertRaises(DataLoadError) as cm:
            self.loader.load_data(group_id, config)

        mock_exists.assert_called_once_with(full_csv_path)
        self.assertEqual(mock_read_csv.call_count, 2)  # Both attempts made
        # Check the final exception message and the original cause
        self.assertIn("Failed to load statistics data", str(cm.exception))
        # The cause should be the original ParserError from pandas
        self.assertIsInstance(cm.exception.__cause__, pd.errors.ParserError)
        # Check details passed from the original exception if necessary (example)
        # self.assertIn("Semicolon fail", str(cm.exception.__cause__))
        # Assuming details from the original parser error are not explicitly needed here
