import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from niamoto.core.components.exports.api_generator import ApiGenerator


class TestAPIGenerator:
    """Test suite for the ApiGenerator class."""

    @pytest.fixture
    def generator(self, tmp_path: Path) -> ApiGenerator:
        """Fixture to create an ApiGenerator instance."""
        output_dir = tmp_path / "output"
        # The constructor expects a Config object, not db_path and output_dir
        # We need to mock the Config object for this test.
        mock_config = MagicMock()
        mock_config.get_export_config = {"api": str(output_dir)}
        return ApiGenerator(mock_config)

    def test_generate_all_shapes_json(self, generator: ApiGenerator, tmp_path: Path):
        """Test the generate_all_shapes_json method."""
        # Arrange
        mock_shape1 = MagicMock()
        mock_shape1.id = 1
        mock_shape1.label = "Shape 1"
        mock_shape1.type = "TypeA"

        mock_shape2 = MagicMock()
        mock_shape2.id = 2
        mock_shape2.label = "Shape 2"
        mock_shape2.type = "TypeB"

        shapes = [mock_shape1, mock_shape2]
        expected_output_path = tmp_path / "output" / "all_shapes.json"

        # Act
        output_path = generator.generate_all_shapes_json(shapes)

        # Assert
        assert output_path == str(expected_output_path)
        assert expected_output_path.exists()

        with open(expected_output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        expected_data = {
            "total": 2,
            "shapes": [
                {
                    "id": 1,
                    "name": "Shape 1",
                    "type": "TypeA",
                    "endpoint": "/api/shape/1.json",
                },
                {
                    "id": 2,
                    "name": "Shape 2",
                    "type": "TypeB",
                    "endpoint": "/api/shape/2.json",
                },
            ],
        }
        assert data == expected_data
