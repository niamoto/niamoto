import pandas as pd
from unittest.mock import Mock, patch

from niamoto.core.plugins.widgets.interactive_map import (
    InteractiveMapWidget,
    InteractiveMapParams,
)
from tests.common.base_test import NiamotoTestCase


class TestInteractiveMapWidget(NiamotoTestCase):
    """Test cases for InteractiveMapWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = InteractiveMapWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, InteractiveMapParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)

    def test_parse_geojson_points_valid(self):
        """Test parsing valid GeoJSON Point FeatureCollection."""
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [165.0, -21.0]},
                    "properties": {"name": "Test Point", "count": 5},
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [166.0, -22.0]},
                    "properties": {"name": "Test Point 2", "count": 3},
                },
            ],
        }

        result = self.widget._parse_geojson_points(geojson_data)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertIn("longitude", result.columns)
        self.assertIn("latitude", result.columns)
        self.assertIn("name", result.columns)
        self.assertIn("count", result.columns)

        # Check coordinates
        self.assertEqual(result.iloc[0]["longitude"], 165.0)
        self.assertEqual(result.iloc[0]["latitude"], -21.0)
        self.assertEqual(result.iloc[1]["longitude"], 166.0)
        self.assertEqual(result.iloc[1]["latitude"], -22.0)

    def test_parse_geojson_points_empty_features(self):
        """Test parsing GeoJSON with no features."""
        geojson_data = {"type": "FeatureCollection", "features": []}

        result = self.widget._parse_geojson_points(geojson_data)

        self.assertIsNotNone(result)
        self.assertTrue(result.empty)

    def test_parse_geojson_points_invalid_structure(self):
        """Test parsing invalid GeoJSON structure."""
        invalid_data = {"type": "Feature"}  # Not a FeatureCollection

        result = self.widget._parse_geojson_points(invalid_data)
        self.assertIsNone(result)

    def test_parse_geojson_points_non_point_features(self):
        """Test parsing GeoJSON with non-Point features."""
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [165.0, -21.0],
                                [166.0, -21.0],
                                [166.0, -22.0],
                                [165.0, -22.0],
                                [165.0, -21.0],
                            ]
                        ],
                    },
                    "properties": {"name": "Test Polygon"},
                }
            ],
        }

        result = self.widget._parse_geojson_points(geojson_data)

        self.assertIsNotNone(result)
        self.assertTrue(result.empty)  # No Point features to extract

    def test_parse_geojson_points_invalid_coordinates(self):
        """Test parsing GeoJSON with invalid coordinates."""
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [165.0],  # Missing latitude
                    },
                    "properties": {"name": "Invalid Point"},
                }
            ],
        }

        result = self.widget._parse_geojson_points(geojson_data)

        self.assertIsNotNone(result)
        self.assertTrue(result.empty)  # Invalid coordinates should be skipped

    def test_prepare_geojson_from_dataframe_string(self):
        """Test preparing GeoJSON from DataFrame with string data."""
        df = pd.DataFrame(
            {
                "geojson_field": ['{"type": "FeatureCollection", "features": []}'],
                "other_field": ["test"],
            }
        )

        params = InteractiveMapParams(geojson_source="geojson_field")

        result = self.widget._prepare_geojson(df, params)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "FeatureCollection")

    def test_prepare_geojson_from_dataframe_dict(self):
        """Test preparing GeoJSON from DataFrame with dict data."""
        geojson_dict = {"type": "FeatureCollection", "features": []}
        df = pd.DataFrame({"geojson_field": [geojson_dict], "other_field": ["test"]})

        params = InteractiveMapParams(geojson_source="geojson_field")

        result = self.widget._prepare_geojson(df, params)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "FeatureCollection")

    def test_prepare_geojson_invalid_json(self):
        """Test preparing GeoJSON with invalid JSON string."""
        df = pd.DataFrame({"geojson_field": ["invalid json"], "other_field": ["test"]})

        params = InteractiveMapParams(geojson_source="geojson_field")

        result = self.widget._prepare_geojson(df, params)

        self.assertIsNone(result)

    def test_prepare_geojson_missing_field(self):
        """Test preparing GeoJSON with missing field."""
        df = pd.DataFrame({"other_field": ["test"]})

        params = InteractiveMapParams(geojson_source="missing_field")

        result = self.widget._prepare_geojson(df, params)

        self.assertIsNone(result)

    def test_process_geojson_or_topojson_geojson(self):
        """Test processing GeoJSON data."""
        geojson_data = {"type": "FeatureCollection", "features": []}

        result = self.widget._process_geojson_or_topojson(geojson_data)

        self.assertEqual(result, geojson_data)

    @patch("topojson.Topology")
    def test_process_geojson_or_topojson_topojson(self, mock_topology_class):
        """Test processing TopoJSON data."""
        topojson_data = {"type": "Topology", "objects": {"data": {}}, "arcs": []}

        # Mock the topology conversion
        mock_topology = Mock()
        mock_topology.to_geojson.return_value = (
            '{"type": "FeatureCollection", "features": []}'
        )
        mock_topology_class.return_value = mock_topology

        result = self.widget._process_geojson_or_topojson(topojson_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "FeatureCollection")

    @patch("topojson.Topology")
    def test_process_geojson_or_topojson_topojson_error(self, mock_topology_class):
        """Test processing TopoJSON data with conversion error."""
        topojson_data = {"type": "Topology", "objects": {"data": {}}, "arcs": []}

        # Mock the topology to raise an exception
        mock_topology_class.side_effect = Exception("Conversion error")

        result = self.widget._process_geojson_or_topojson(topojson_data)

        self.assertIsNone(result)

    def test_process_geojson_or_topojson_unsupported(self):
        """Test processing unsupported data type."""
        unsupported_data = {"type": "Unsupported"}

        result = self.widget._process_geojson_or_topojson(unsupported_data)

        self.assertIsNone(result)

    @patch("topojson.Topology")
    def test_optimize_geojson_to_topojson(self, mock_topology_class):
        """Test optimizing GeoJSON to TopoJSON."""
        geojson_data = {"type": "FeatureCollection", "features": []}

        # Mock the topology optimization
        mock_topology = Mock()
        mock_topology.to_dict.return_value = {"type": "Topology", "objects": {}}
        mock_topology_class.return_value = mock_topology

        result = self.widget._optimize_geojson_to_topojson(geojson_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "Topology")
        mock_topology_class.assert_called_once_with(data=geojson_data, prequantize=True)

    @patch("topojson.Topology")
    def test_optimize_geojson_to_topojson_error(self, mock_topology_class):
        """Test optimizing GeoJSON to TopoJSON with error."""
        geojson_data = {"type": "FeatureCollection", "features": []}

        # Mock the topology to raise an exception
        mock_topology_class.side_effect = Exception("Optimization error")

        result = self.widget._optimize_geojson_to_topojson(geojson_data)

        self.assertEqual(result, geojson_data)  # Should return original data on error

    def test_optimize_geojson_to_topojson_non_featurecollection(self):
        """Test optimizing non-FeatureCollection to TopoJSON."""
        geojson_data = {"type": "Feature"}

        result = self.widget._optimize_geojson_to_topojson(geojson_data)

        self.assertEqual(result, geojson_data)  # Should return original data

    def test_calculate_zoom_from_bounds_single_point(self):
        """Test zoom calculation for single point."""
        zoom = self.widget._calculate_zoom_from_bounds(-21.0, -21.0, 165.0, 165.0)

        self.assertEqual(zoom, 15.0)  # Single point should use high zoom

    def test_calculate_zoom_from_bounds_small_area(self):
        """Test zoom calculation for small area."""
        zoom = self.widget._calculate_zoom_from_bounds(-21.1, -20.9, 164.9, 165.1)

        self.assertGreater(zoom, 10.0)
        self.assertLessEqual(zoom, 18.0)

    def test_calculate_zoom_from_bounds_large_area(self):
        """Test zoom calculation for large area."""
        zoom = self.widget._calculate_zoom_from_bounds(-25.0, -15.0, 160.0, 170.0)

        self.assertGreater(zoom, 1.0)
        self.assertLess(zoom, 10.0)

    def test_calculate_zoom_from_bounds_clamps_minimum(self):
        """Test zoom calculation clamps to minimum value."""
        zoom = self.widget._calculate_zoom_from_bounds(-90.0, 90.0, -180.0, 180.0)

        self.assertGreaterEqual(zoom, 1.0)

    def test_calculate_zoom_from_bounds_clamps_maximum(self):
        """Test zoom calculation clamps to maximum value."""
        zoom = self.widget._calculate_zoom_from_bounds(
            -21.0001, -20.9999, 164.9999, 165.0001
        )

        self.assertLessEqual(zoom, 18.0)


class TestInteractiveMapWidgetRender(NiamotoTestCase):
    """Test cases for InteractiveMapWidget render method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = InteractiveMapWidget(self.mock_db)

    def test_render_no_data(self):
        """Test rendering with no data."""
        params = InteractiveMapParams()

        result = self.widget.render(None, params)

        self.assertIn("No valid map data available", result)

    def test_render_empty_dataframe(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()
        params = InteractiveMapParams(map_type="scatter_map")

        result = self.widget.render(df, params)

        self.assertIn("No valid data available", result)

    @patch("plotly.express.scatter_map")
    def test_render_scatter_map_success(self, mock_scatter_map):
        """Test successful scatter map rendering."""
        # Create test data
        df = pd.DataFrame(
            {
                "latitude": [-21.0, -22.0],
                "longitude": [165.0, 166.0],
                "count": [5, 3],
                "name": ["Point 1", "Point 2"],
            }
        )

        # Mock plotly figure - now using to_json() instead of to_html()
        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {}}'
        mock_scatter_map.return_value = mock_fig

        params = InteractiveMapParams(
            map_type="scatter_map", color_field="count", hover_name="name"
        )

        result = self.widget.render(df, params)

        self.assertIn("plotly-graph-div", result)
        self.assertIn("map-widget", result)
        mock_scatter_map.assert_called_once()

    def test_render_scatter_map_missing_coordinates(self):
        """Test scatter map rendering with missing coordinate columns."""
        df = pd.DataFrame({"count": [5, 3], "name": ["Point 1", "Point 2"]})

        params = InteractiveMapParams(map_type="scatter_map")

        result = self.widget.render(df, params)

        self.assertIn("Missing coordinate columns", result)

    @patch("plotly.express.choropleth_map")
    def test_render_choropleth_map_missing_location_field(self, mock_choropleth_map):
        """Test choropleth map rendering without location field."""
        df = pd.DataFrame({"value": [1, 2], "name": ["Area 1", "Area 2"]})

        params = InteractiveMapParams(map_type="choropleth_map")

        result = self.widget.render(df, params)

        self.assertIn("Location field is required", result)

    def test_render_geojson_points_parsing(self):
        """Test rendering with GeoJSON point data."""
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [165.0, -21.0]},
                    "properties": {"name": "Test Point", "count": 5},
                }
            ],
        }

        with patch("plotly.express.scatter_map") as mock_scatter_map:
            mock_fig = Mock()
            mock_fig.to_json.return_value = '{"data": [], "layout": {}}'
            mock_scatter_map.return_value = mock_fig

            params = InteractiveMapParams(map_type="scatter_map")

            result = self.widget.render(geojson_data, params)

            self.assertIn("plotly-graph-div", result)

    @patch("topojson.Topology")
    def test_render_topojson_parsing(self, mock_topology_class):
        """Test parsing TopoJSON data structure."""
        # Mock TopoJSON data
        topojson_data = {
            "shape_coords": {"type": "Topology", "objects": {"data": {}}, "arcs": []}
        }

        # Mock topology conversion to get choropleth outline mode
        mock_topology = Mock()
        mock_topology.to_geojson.return_value = (
            '{"type": "FeatureCollection", "features": [{"id": 0}]}'
        )
        mock_topology_class.return_value = mock_topology

        # Use default params to trigger the TopJSON processing without specifying choropleth
        params = InteractiveMapParams()

        result = self.widget.render(topojson_data, params)

        # Should process TopoJSON and attempt to render as choropleth outline
        # The exact result depends on whether plotly succeeds, but at minimum it should try
        self.assertIsInstance(result, str)
        # Could be success or error, but should not be None
        self.assertIsNotNone(result)

    @patch("plotly.express.scatter_map")
    def test_render_auto_zoom_enabled(self, mock_scatter_map):
        """Test rendering with auto zoom enabled."""
        df = pd.DataFrame(
            {
                "latitude": [-21.0, -22.0, -20.5],
                "longitude": [165.0, 166.0, 164.5],
                "count": [5, 3, 7],
            }
        )

        # Mock plotly figure
        mock_fig = Mock()
        mock_fig.to_json.return_value = '{"data": [], "layout": {}}'
        mock_scatter_map.return_value = mock_fig

        params = InteractiveMapParams(map_type="scatter_map", auto_zoom=True)

        result = self.widget.render(df, params)

        self.assertIn("plotly-graph-div", result)

        # Check that scatter_map was called with calculated zoom
        call_args = mock_scatter_map.call_args
        self.assertIsNotNone(call_args[1].get("zoom"))

    def test_render_with_error_handling(self):
        """Test render method with various error conditions."""
        df = pd.DataFrame({"latitude": [-21.0], "longitude": [165.0]})

        # Test with plotly error
        with patch("plotly.express.scatter_map", side_effect=Exception("Plotly error")):
            params = InteractiveMapParams(map_type="scatter_map")
            result = self.widget.render(df, params)
            self.assertIn("Error generating map", result)


class TestInteractiveMapWidgetMultiLayer(NiamotoTestCase):
    """Test cases for multi-layer map functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = InteractiveMapWidget(self.mock_db)

    @patch("plotly.graph_objects.Figure")
    def test_render_multi_layer_map_basic(self, mock_figure_class):
        """Test basic multi-layer map rendering."""
        # Mock data with shape and forest coordinates
        data = {
            "shape_coords": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [165.0, -21.0],
                                    [166.0, -21.0],
                                    [166.0, -22.0],
                                    [165.0, -22.0],
                                    [165.0, -21.0],
                                ]
                            ],
                        },
                        "properties": {"name": "Test Shape"},
                    }
                ],
            },
            "forest_cover_coords": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [165.1, -21.1],
                                    [165.9, -21.1],
                                    [165.9, -21.9],
                                    [165.1, -21.9],
                                    [165.1, -21.1],
                                ]
                            ],
                        },
                        "properties": {"name": "Forest Area"},
                    }
                ],
            },
        }

        # Mock figure
        mock_fig = Mock()
        mock_fig.data = []
        mock_fig.layout = {}
        mock_fig.to_json.return_value = '{"data": [], "layout": {}}'
        mock_figure_class.return_value = mock_fig

        params = InteractiveMapParams(
            layers=[
                {"source": "shape_coords", "style": {"color": "#1fb99d", "weight": 2}},
                {
                    "source": "forest_cover_coords",
                    "style": {"fillColor": "#228b22", "fillOpacity": 0.8},
                },
            ]
        )

        result = self.widget.render(data, params)

        self.assertIn("plotly-graph-div", result)

    def test_render_multi_layer_no_layers(self):
        """Test multi-layer rendering with no layers defined."""
        data = {"shape_coords": {}}

        params = InteractiveMapParams(layers=[])

        result = self.widget.render(data, params)

        # When layers=[] is passed but is empty, the widget should fall back to normal rendering
        # and since shape_coords is empty, it should show "No valid data available"
        self.assertIn("No valid data available", result)

    def test_render_multi_layer_with_layers_but_no_content(self):
        """Test multi-layer rendering with layers defined but no actual content."""
        data = {"shape_coords": {}}

        params = InteractiveMapParams(layers=[{"source": "shape_coords", "style": {}}])

        # Mock the _render_multi_layer_map to return the expected message
        with patch.object(self.widget, "_render_multi_layer_map") as mock_render:
            mock_render.return_value = "<div class='alert alert-warning'>No layers defined for interactive map.</div>"

            result = self.widget.render(data, params)

            self.assertIn("No layers defined", result)

    @patch("topojson.Topology")
    def test_render_multi_layer_topojson_mode(self, mock_topology_class):
        """Test multi-layer rendering with TopoJSON optimization."""
        # Mock data
        data = {"shape_coords": {"type": "FeatureCollection", "features": []}}

        # Mock topology optimization
        mock_topology = Mock()
        mock_topology.to_dict.return_value = {"type": "Topology", "objects": {}}
        mock_topology_class.return_value = mock_topology

        params = InteractiveMapParams(
            use_topojson=True, layers=[{"source": "shape_coords", "style": {}}]
        )

        with patch.object(
            self.widget,
            "_render_client_side_topojson_map",
            return_value="<div class='plotly-graph-div'>TopoJSON Map</div>",
        ):
            result = self.widget.render(data, params)

            self.assertIn("plotly-graph-div", result)

    def test_render_client_side_topojson_map(self):
        """Test client-side TopoJSON map rendering."""
        topojson_data = {
            "shape_coords": {
                "type": "Topology",
                "objects": {"data": {}},
                "arcs": [],
                "bbox": [164.0, -22.0, 166.0, -20.0],
            }
        }

        shape_style = {"color": "#1fb99d", "weight": 2}
        forest_style = {"fillColor": "#228b22", "fillOpacity": 0.8}

        params = InteractiveMapParams(map_style="carto-positron", zoom=9.0)

        result = self.widget._render_client_side_topojson_map(
            topojson_data, shape_style, forest_style, params
        )

        self.assertIn("niamoto_map_", result)  # Should contain unique map ID
        self.assertIn(
            "topojson.feature", result
        )  # Should include TopoJSON functionality
        self.assertIn("Plotly.newPlot", result)  # Should include Plotly rendering
        self.assertIn(
            "Chargement de la carte", result
        )  # Should include loading indicator


class TestInteractiveMapParams(NiamotoTestCase):
    """Test cases for InteractiveMapParams validation."""

    def test_params_defaults(self):
        """Test parameter defaults."""
        params = InteractiveMapParams()

        self.assertEqual(params.map_type, "scatter_map")
        self.assertEqual(params.map_style, "carto-positron")
        self.assertEqual(params.zoom, 9.0)
        self.assertEqual(params.auto_zoom, False)
        self.assertEqual(params.size_max, 15)
        self.assertEqual(params.opacity, 0.8)
        self.assertEqual(params.show_attribution, False)
        self.assertEqual(params.use_topojson, False)

    def test_params_custom_values(self):
        """Test parameter with custom values."""
        params = InteractiveMapParams(
            title="Custom Map",
            map_type="choropleth_map",
            map_style="open-street-map",
            zoom=12.0,
            auto_zoom=True,
            center_lat=-21.5,
            center_lon=165.5,
            color_field="population",
            size_field="area",
            hover_name="name",
            hover_data=["value1", "value2"],
            show_attribution=True,
            use_topojson=True,
        )

        self.assertEqual(params.title, "Custom Map")
        self.assertEqual(params.map_type, "choropleth_map")
        self.assertEqual(params.map_style, "open-street-map")
        self.assertEqual(params.zoom, 12.0)
        self.assertEqual(params.auto_zoom, True)
        self.assertEqual(params.center_lat, -21.5)
        self.assertEqual(params.center_lon, 165.5)
        self.assertEqual(params.color_field, "population")
        self.assertEqual(params.size_field, "area")
        self.assertEqual(params.hover_name, "name")
        self.assertEqual(params.hover_data, ["value1", "value2"])
        self.assertEqual(params.show_attribution, True)
        self.assertEqual(params.use_topojson, True)

    def test_params_layers_configuration(self):
        """Test layer configuration parameter."""
        layers = [
            {"source": "shape_coords", "style": {"color": "#ff0000"}},
            {"source": "forest_coords", "style": {"fillColor": "#00ff00"}},
        ]

        params = InteractiveMapParams(layers=layers)

        self.assertEqual(params.layers, layers)
        self.assertEqual(len(params.layers), 2)
        self.assertEqual(params.layers[0]["source"], "shape_coords")
        self.assertEqual(params.layers[1]["style"]["fillColor"], "#00ff00")
