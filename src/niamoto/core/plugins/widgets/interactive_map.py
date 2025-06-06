import json
import logging
from typing import Any, List, Optional, Set
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import topojson
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.widgets.plotly_utils import (
    get_plotly_dependencies,
    render_plotly_figure,
    get_plotly_config,
)


logger = logging.getLogger(__name__)


class InteractiveMapParams(BaseModel):
    """Parameters for the interactive map widget."""

    title: Optional[str] = Field(None, description="Title to display above the map")
    description: Optional[str] = Field(
        None, description="Description to display below the title"
    )
    geojson_source: Optional[str] = Field(
        None, description="Field containing GeoJSON geometry or reference."
    )
    latitude_field: Optional[str] = Field(
        None, description="Field name for latitude (used if no GeoJSON)."
    )
    longitude_field: Optional[str] = Field(
        None, description="Field name for longitude (used if no GeoJSON)."
    )
    location_field: Optional[str] = Field(
        None,
        description="Field for identifying locations (used in choropleth/scatter hover).",
    )
    color_field: Optional[str] = Field(
        None, description="Field to determine color (for choropleth or scatter points)."
    )
    size_field: Optional[str] = Field(
        None, description="Field to determine size (for scatter points)."
    )
    hover_name: Optional[str] = Field(
        None, description="Field for primary hover label."
    )
    hover_data: Optional[List[str]] = Field(
        None, description="Additional fields for hover tooltip."
    )
    map_type: str = Field(
        default="scatter_map", description="'scatter_map' or 'choropleth_map'."
    )
    map_style: str = Field(
        default="carto-positron",
        description="Map base style (e.g., 'open-street-map', 'carto-positron', 'stamen-terrain').",
    )
    zoom: float = Field(default=9.0, description="Initial zoom level of the map")
    auto_zoom: bool = Field(
        default=False, description="Automatically calculate zoom to fit all data points"
    )
    center_lat: Optional[float] = Field(
        None, description="Initial map center latitude."
    )
    center_lon: Optional[float] = Field(
        None, description="Initial map center longitude."
    )
    color_continuous_scale: Optional[str] = Field(
        None, description="Plotly color scale name (e.g., 'Viridis', 'Plasma')."
    )
    color_discrete_map: Optional[Any] = Field(
        None, description="Mapping for discrete colors."
    )
    range_color: Optional[List[float]] = Field(
        None, description="Min/max for color scale."
    )
    size_max: Optional[int] = Field(
        default=15, description="Maximum marker size for scatter_map."
    )
    opacity: Optional[float] = Field(
        default=0.8, description="Marker/feature opacity (0 to 1)."
    )
    featureidkey: Optional[str] = Field(
        None,
        description="Key in GeoJSON features to link with location_field (e.g., 'properties.id').",
    )
    layers: Optional[List[dict]] = Field(
        None, description="List of layer configurations for multi-layer maps."
    )
    # Deprecated field for backward compatibility
    mapbox_style: Optional[str] = Field(
        None, description="Deprecated: Use map_style instead."
    )
    show_attribution: bool = Field(
        default=False, description="Whether to show map attribution"
    )
    use_topojson: bool = Field(
        default=False,
        description="Whether to optimize GeoJSON to TopoJSON format for reduced file size. Note: data already in TopoJSON format (from shape_processor) will not be re-optimized.",
    )


@register("interactive_map", PluginType.WIDGET)
class InteractiveMapWidget(WidgetPlugin):
    """Widget to display an interactive map using Plotly Express."""

    param_schema = InteractiveMapParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies."""
        # Get Plotly from centralized dependency
        deps = get_plotly_dependencies()
        # Add topojson-client; it is ~7 kB minified and cached.
        deps.add("/assets/js/vendor/topojson/3.1.0_topojson.js")
        return deps

    def _parse_geojson_points(self, geojson_data: dict) -> Optional[pd.DataFrame]:
        """Parses a GeoJSON FeatureCollection of Points into a DataFrame."""
        if (
            not isinstance(geojson_data, dict)
            or geojson_data.get("type") != "FeatureCollection"
        ):
            logger.error(
                "Invalid GeoJSON structure: Expected FeatureCollection dictionary."
            )
            return None

        features = geojson_data.get("features", [])
        if not features:
            """ logger.warning("GeoJSON FeatureCollection is empty.") """
            return pd.DataFrame()  # Return empty DataFrame

        records = []
        for feature in features:
            if (
                feature.get("type") == "Feature"
                and feature.get("geometry", {}).get("type") == "Point"
            ):
                coords = feature["geometry"].get("coordinates")
                props = feature.get("properties", {})
                if coords and len(coords) == 2:
                    record = {
                        "longitude": coords[0],
                        "latitude": coords[1],
                    }
                    record.update(props)  # Add properties like 'count'
                    records.append(record)
                else:
                    logger.warning(f"Skipping invalid Point feature: {feature}")
            else:
                logger.warning(f"Skipping non-Point feature: {feature}")

        if not records:
            logger.warning("No valid Point features found in GeoJSON.")
            return pd.DataFrame()

        return pd.DataFrame(records)

    def _prepare_geojson(
        self, data_frame: pd.DataFrame, params: InteractiveMapParams
    ) -> Optional[Any]:
        """Loads or prepares GeoJSON data for choropleth maps from DataFrame column."""
        if not params.geojson_source:
            return None
        if params.geojson_source in data_frame.columns and isinstance(
            data_frame[params.geojson_source].iloc[0], (dict, str)
        ):
            try:
                geojson_data = data_frame[params.geojson_source].iloc[0]
                if isinstance(geojson_data, str):
                    return json.loads(geojson_data)
                return geojson_data
            except Exception as e:
                logger.error(
                    f"Error parsing GeoJSON from field '{params.geojson_source}': {e}"
                )
                return None
        logger.warning(
            f"GeoJSON source '{params.geojson_source}' handling not fully implemented or data not found."
        )
        return None

    def _process_geojson_or_topojson(self, data: dict) -> Optional[dict]:
        """Process GeoJSON or TopoJSON data for rendering."""
        if data.get("type") == "Topology":
            try:
                # Identify object name from TopoJSON
                objects_keys = list(data.get("objects", {}).keys())
                if objects_keys:
                    object_name = objects_keys[0]
                    logger.debug(
                        f"Using object name '{object_name}' for TopoJSON conversion"
                    )

                    # Convert to GeoJSON
                    topology = topojson.Topology(data, object_name=object_name)
                    geojson_str = topology.to_geojson()
                    logger.debug(
                        "Successfully converted shape_coords TopoJSON to GeoJSON"
                    )
                    geojson_data = json.loads(geojson_str)  # Parse string to dict
                    logger.debug(
                        f"GeoJSON structure: {list(geojson_data.keys()) if isinstance(geojson_data, dict) else 'Not a dict'}"
                    )
                    return geojson_data
            except Exception as e:
                logger.error(
                    f"Error converting TopoJSON to GeoJSON: {e}", exc_info=True
                )
        elif data.get("type") == "FeatureCollection":
            return data
        else:
            logger.warning(f"Unsupported data type: {data.get('type')}")
        return None

    def _optimize_geojson_to_topojson(self, geojson_data: dict) -> Optional[dict]:
        """Convert GeoJSON to optimized TopoJSON using same parameters as shape_processor."""
        try:
            if geojson_data.get("type") != "FeatureCollection":
                logger.warning("Can only convert FeatureCollection to TopoJSON")
                return geojson_data

            # Use same optimization as shape_processor.py (line 240-241)
            # topology = tp.Topology(geojson, prequantize=True)
            # return topology.to_dict()
            topology = topojson.Topology(
                data=geojson_data,
                prequantize=True,  # Same as shape_processor
            )

            result = topology.to_dict()
            logger.debug(
                "Successfully optimized GeoJSON to TopoJSON using shape_processor parameters"
            )
            return result

        except Exception as e:
            logger.error(f"Error optimizing to TopoJSON: {e}", exc_info=True)
            return geojson_data  # Return original data on failure

    def _render_client_side_topojson_map(
        self,
        topojson_data: dict,
        shape_style: dict,
        forest_style: dict,
        params: InteractiveMapParams,
    ) -> str:
        """Render a map using client-side TopoJSON to GeoJSON conversion."""

        # Calculate bounds for centering and zoom from TopoJSON data
        center_lat = (
            params.center_lat if params.center_lat is not None else -21.0
        )  # Default to New Caledonia
        center_lon = params.center_lon if params.center_lon is not None else 165.0
        zoom_level = params.zoom if params.zoom is not None else 9.0

        # Generate a unique ID for this map
        map_id = (
            f"niamoto_map_{hash(json.dumps(topojson_data, sort_keys=True)) % 10000}"
        )

        # Create the HTML with embedded TopoJSON and JavaScript conversion
        html_content = f"""
        <div id="{map_id}" style="width: 100%; height: 500px; position: relative;">
            <div id="{map_id}_loader" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1000;">
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <div class="spinner" style="width: 50px; height: 50px; border: 5px solid #f3f3f3; border-top: 5px solid #2d5016; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <p style="margin-top: 10px; color: #666;">Chargement de la carte...</p>
                </div>
            </div>
            <style>
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </div>

        <script>
        // Defer map initialization until DOM is ready and page is loaded
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initializeMap{map_id});
        }} else {{
            // DOM is already loaded, initialize after a small delay to ensure other content loads first
            setTimeout(initializeMap{map_id}, 100);
        }}

        function initializeMap{map_id}() {{
            // Check if topojson is available, if not, wait for it to load
            if (typeof topojson === 'undefined') {{
                // Wait for topojson to load, but with a maximum retry count
                if (!initializeMap{map_id}.retryCount) {{
                    initializeMap{map_id}.retryCount = 0;
                }}
                initializeMap{map_id}.retryCount++;

                if (initializeMap{map_id}.retryCount < 50) {{ // Max 5 seconds (50 * 100ms)
                    setTimeout(initializeMap{map_id}, 100);
                    return;
                }} else {{
                    console.error('TopoJSON library failed to load after 5 seconds');
                    document.getElementById('{map_id}_loader').innerHTML = '<p style="color: red;">Erreur: Impossible de charger la bibliothèque TopoJSON</p>';
                    return;
                }}
            }}

            // Use requestAnimationFrame to ensure smooth loading
            requestAnimationFrame(function() {{
                // Embedded TopoJSON data
                const niamotoTopoData = {json.dumps(topojson_data)};

                // Style configurations
                const shapeStyle = {json.dumps(shape_style)};
                const forestStyle = {json.dumps(forest_style)};

                // Create Plotly figure
                const traces = [];

                // Process forest cover data if available
                if (niamotoTopoData.forest_cover_coords) {{
                    try {{
                    const forestTopology = niamotoTopoData.forest_cover_coords;
                    const objectKeys = Object.keys(forestTopology.objects || {{}});

                    if (objectKeys.length > 0) {{
                        const objectName = objectKeys[0];
                        const forestGeoJSON = topojson.feature(forestTopology, forestTopology.objects[objectName]);

                        // Ensure we have features
                        if (forestGeoJSON.features && forestGeoJSON.features.length > 0) {{
                            // Assign IDs to features if they don\'t have them
                            forestGeoJSON.features.forEach((feature, index) => {{
                                if (!feature.id) {{
                                    feature.id = index.toString();
                                }}
                                if (!feature.properties) {{
                                    feature.properties = {{}};
                                }}
                                feature.properties.name = `Forest ${{index}}`;
                            }});

                            // Create choroplethmap trace
                            const forestTrace = {{
                                type: \'choroplethmap\',
                                geojson: forestGeoJSON,
                                locations: forestGeoJSON.features.map(f => f.id),
                                z: forestGeoJSON.features.map(() => 1),
                                featureidkey: \'id\',
                                colorscale: [[0, forestStyle.fillColor || \'#228b22\'], [1, forestStyle.fillColor || \'#228b22\']],
                                showscale: false,
                                marker: {{
                                    opacity: forestStyle.fillOpacity || 0.6,
                                    line: {{width: 0}}
                                }},
                                name: \'Forest Cover\',
                                hovertemplate: \'%{{properties.name}}<extra></extra>\'
                            }};
                            traces.push(forestTrace);
                        }} else {{
                            console.warn(\'No features in forest GeoJSON\');
                        }}
                    }} else {{
                        console.warn(\'No objects found in forest TopoJSON\');
                    }}
                }} catch (e) {{
                    console.error(\'Error processing forest cover TopoJSON:\', e);
                    }}
                }}

                // Process shape boundary data if available
                if (niamotoTopoData.shape_coords) {{
                    try {{
                        const shapeTopology = niamotoTopoData.shape_coords;
                        const objectKeys = Object.keys(shapeTopology.objects || {{}});

                        if (objectKeys.length > 0) {{
                            const objectName = objectKeys[0];
                            const shapeGeoJSON = topojson.feature(shapeTopology, shapeTopology.objects[objectName]);

                        // Process each feature to extract boundary lines
                        if (shapeGeoJSON.features && shapeGeoJSON.features.length > 0) {{
                            shapeGeoJSON.features.forEach((feature, featureIndex) => {{
                                const geometry = feature.geometry;
                                if (!geometry || !geometry.coordinates) return;

                                const processCoordinates = (coords, geomType) => {{
                                    if (geomType === 'Polygon') {{
                                        coords.forEach((ring, ringIndex) => {{
                                            if (ring.length > 0) {{
                                                const lons = ring.map(p => p[0]);
                                                const lats = ring.map(p => p[1]);

                                                traces.push({{
                                                    type: 'scattermap',
                                                    lon: lons,
                                                    lat: lats,
                                                    mode: 'lines',
                                                    line: {{
                                                        width: shapeStyle.weight || 2,
                                                        color: shapeStyle.color || '#2d5016'
                                                    }},
                                                    showlegend: false,
                                                    hoverinfo: 'skip'
                                                }});
                                            }}
                                        }});
                                    }} else if (geomType === 'MultiPolygon') {{
                                        coords.forEach((polygon, polyIndex) => {{
                                            polygon.forEach((ring, ringIndex) => {{
                                                if (ring.length > 0) {{
                                                    const lons = ring.map(p => p[0]);
                                                    const lats = ring.map(p => p[1]);

                                                    traces.push({{
                                                        type: 'scattermap',
                                                        lon: lons,
                                                        lat: lats,
                                                        mode: 'lines',
                                                        line: {{
                                                            width: shapeStyle.weight || 2,
                                                            color: shapeStyle.color || '#2d5016'
                                                        }},
                                                        showlegend: false,
                                                        hoverinfo: 'skip'
                                                    }});
                                                }}
                                            }});
                                        }});
                                    }}
                                }};

                                processCoordinates(geometry.coordinates, geometry.type);
                            }});

                            // Add a single legend entry for shape boundary
                            traces.push({{
                                type: 'scattermap',
                                lon: [],
                                lat: [],
                                mode: 'lines',
                                line: {{
                                    width: shapeStyle.weight || 2,
                                    color: shapeStyle.color || '#2d5016'
                                }},
                                name: 'Shape Boundary',
                                showlegend: true
                            }});

                        }} else {{
                            console.warn(\'No features in shape GeoJSON\');
                        }}
                    }} else {{
                        console.warn(\'No objects found in shape TopoJSON\');
                    }}
                }} catch (e) {{
                    console.error(\'Error processing shape coords TopoJSON:\', e);
                }}
            }}

            // Calculate bounds from TopoJSON data
            let bounds = null;
            let zoom = {zoom_level};

            // Try to calculate bounds from the TopoJSON bbox
            if (niamotoTopoData.shape_coords && niamotoTopoData.shape_coords.bbox) {{
                const bbox = niamotoTopoData.shape_coords.bbox;
                bounds = {{
                    center: {{
                        lat: (bbox[1] + bbox[3]) / 2,
                        lon: (bbox[0] + bbox[2]) / 2
                    }}
                }};
                // Calculate zoom based on bbox
                const latDiff = bbox[3] - bbox[1];
                const lonDiff = bbox[2] - bbox[0];
                // Simple zoom calculation - adjust as needed
                if (latDiff < 0.5 && lonDiff < 0.5) {{
                    zoom = 10;
                }} else if (latDiff < 1 && lonDiff < 1) {{
                    zoom = 9;
                }} else {{
                    zoom = 8;
                }}
            }} else if (niamotoTopoData.forest_cover_coords && niamotoTopoData.forest_cover_coords.bbox) {{
                const bbox = niamotoTopoData.forest_cover_coords.bbox;
                bounds = {{
                    center: {{
                        lat: (bbox[1] + bbox[3]) / 2,
                        lon: (bbox[0] + bbox[2]) / 2
                    }}
                }};
            }}

            // Fallback to calculating from traces if needed
            if (!bounds && traces.length > 0) {{
                let minLat = Infinity, maxLat = -Infinity;
                let minLon = Infinity, maxLon = -Infinity;

                traces.forEach(trace => {{
                    if (trace.type === 'scattermap' && trace.lon && trace.lat) {{
                        trace.lon.forEach(lon => {{
                            if (lon < minLon) minLon = lon;
                            if (lon > maxLon) maxLon = lon;
                        }});
                        trace.lat.forEach(lat => {{
                            if (lat < minLat) minLat = lat;
                            if (lat > maxLat) maxLat = lat;
                        }});
                    }} else if (trace.type === 'choroplethmap' && trace.geojson) {{
                        // Try to extract bounds from GeoJSON if available
                        if (trace.geojson.bbox) {{
                            const bbox = trace.geojson.bbox;
                            if (bbox[0] < minLon) minLon = bbox[0];
                            if (bbox[2] > maxLon) maxLon = bbox[2];
                            if (bbox[1] < minLat) minLat = bbox[1];
                            if (bbox[3] > maxLat) maxLat = bbox[3];
                        }}
                    }}
                }});

                if (minLat !== Infinity) {{
                    bounds = {{
                        center: {{
                            lat: (minLat + maxLat) / 2,
                            lon: (minLon + maxLon) / 2
                        }}
                    }};
                }}
            }}

            // Create layout
            const layout = {{
                map: {{
                    style: "{params.map_style or "carto-positron"}",
                    center: bounds ? bounds.center : {{lat: {center_lat}, lon: {center_lon}}},
                    zoom: zoom
                }},
                margin: {{r: 0, t: 0, l: 0, b: 0}},
                height: 500,
                showlegend: true,
                legend: {{
                    x: 0.02,
                    y: 0.98,
                    bgcolor: 'rgba(255,255,255,0.8)',
                    bordercolor: 'black',
                    borderwidth: 1
                }},
                annotations: []
            }};

            // Create config
            const config = {{
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
                toImageButtonOptions: {{
                    format: 'png',
                    filename: 'niamoto_map',
                    height: 500,
                    width: 700
                }}
            }};

                // Render the map
                Plotly.newPlot('{map_id}', traces, layout, config).then(() => {{
                    // Hide loader once map is rendered
                    const loader = document.getElementById('{map_id}_loader');
                    if (loader) {{
                        loader.style.display = 'none';
                    }}
                }}).catch(error => {{
                    console.error('Error rendering map:', error);
                    // Hide loader even on error and show error message
                    const loader = document.getElementById('{map_id}_loader');
                    if (loader) {{
                        loader.innerHTML = '<p style="color: #e74c3c;">Erreur lors du chargement de la carte</p>';
                    }}
                }});
            }});
        }}
        </script>
        """

        attribution_class = " hide-attribution" if not params.show_attribution else ""

        return f"""<div class="map-widget{attribution_class}">
            <div class="map-container">{html_content}</div>
        </div>"""

    def _calculate_zoom_from_bounds(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        map_height: int = 500,
        map_width: int = 700,
    ) -> float:
        """Calculate appropriate zoom level based on geographic bounds.

        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            map_height: Map height in pixels (default 500)
            map_width: Map width in pixels (default 700)

        Returns:
            Optimal zoom level
        """
        import math

        # Calculate the extent
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon

        # Handle edge cases
        if lat_diff == 0 and lon_diff == 0:
            return 15.0  # Single point, use high zoom

        # World extent in degrees
        WORLD_DIM = {"height": 180, "width": 360}

        # Calculate zoom based on both dimensions
        # Using a simplified formula based on the Mercator projection
        zoom_lat = (
            math.log2(WORLD_DIM["height"] * map_height / (lat_diff * 256))
            if lat_diff > 0
            else 20
        )
        zoom_lon = (
            math.log2(WORLD_DIM["width"] * map_width / (lon_diff * 256))
            if lon_diff > 0
            else 20
        )

        # Take the minimum zoom to ensure all points are visible
        # Subtract a small buffer to ensure padding around points
        zoom = min(zoom_lat, zoom_lon) - 0.5

        # Clamp zoom between reasonable bounds
        return max(1.0, min(18.0, zoom))

    def render(self, data: Optional[Any], params: InteractiveMapParams) -> str:
        """Generate the HTML for the interactive map. Accepts DataFrame or parsed GeoJSON dict."""

        # Early return if no data
        if data is None:
            return "<div class='alert alert-warning'>No valid map data available.</div>"

        # If multi-layer map configuration is provided AND we have shape_coords in data (shape group)
        if params.layers and isinstance(data, dict) and "shape_coords" in data:
            try:
                result = self._render_multi_layer_map(data, params)
                return result
            except Exception as e:
                return (
                    "<div class='alert alert-danger'>Failed to render multi-layer map: %s</div>"
                    % str(e)
                )

        # For other groups (taxon, plot, etc.), use the original rendering approach

        # Handle DataFrame input
        df_plot = None
        geojson_plot_data = None  # Store GeoJSON for choropleth
        map_mode = "scatter"  # Default to scatter

        if isinstance(data, pd.DataFrame):
            if not data.empty:
                df_plot = data.copy()
        elif isinstance(data, dict):
            # Check for TopoJSON structure first (e.g., from 'shape' table 'geography')
            if (
                "shape_coords" in data
                and isinstance(data["shape_coords"], dict)
                and data["shape_coords"].get("type") == "Topology"
            ):
                try:
                    topo_data = data["shape_coords"]
                    # Convert TopoJSON to GeoJSON FeatureCollection. Requires object name ('data' in this case).
                    # This assumes the TopoJSON has an object named 'data'.
                    geojson_str = topojson.Topology(
                        topo_data, object_name="data"
                    ).to_geojson()
                    geojson_plot_data = json.loads(geojson_str)  # Parse string to dict
                    map_mode = "choropleth_outline"
                    # Create a dummy DataFrame needed by choropleth_map
                    # Add an 'id' property to the first feature for matching
                    if geojson_plot_data and geojson_plot_data.get("features"):
                        geojson_plot_data["features"][0]["id"] = (
                            0  # Add id for matching
                        )
                        df_plot = pd.DataFrame(
                            {"shape_id": [0], "value": [1]}
                        )  # Dummy df
                        # Also handle forest_cover_coords if present
                        if (
                            "forest_cover_coords" in data
                            and isinstance(data["forest_cover_coords"], dict)
                            and data["forest_cover_coords"].get("type") == "Topology"
                        ):
                            try:
                                forest_topo_data = data["forest_cover_coords"]
                                forest_geojson_str = topojson.Topology(
                                    forest_topo_data, object_name="data"
                                ).to_geojson()
                                forest_geojson_data = json.loads(forest_geojson_str)
                                # Add forest data as an additional feature with distinct ID
                                if forest_geojson_data and forest_geojson_data.get(
                                    "features"
                                ):
                                    # Assign a different ID for the forest layer
                                    for feature in forest_geojson_data.get(
                                        "features", []
                                    ):
                                        feature["id"] = 1  # Different ID than the shape
                                    # Add forest features to the main GeoJSON
                                    geojson_plot_data["features"].extend(
                                        forest_geojson_data["features"]
                                    )
                                    # Update DataFrame to include forest layer
                                    df_plot = pd.DataFrame(
                                        {
                                            "shape_id": [0, 1],
                                            "value": [1, 2],
                                            "layer": ["shape", "forest"],
                                        }
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Error converting forest TopoJSON to GeoJSON: {e}",
                                    exc_info=True,
                                )
                    else:
                        logger.warning(
                            "Failed to extract features from converted TopoJSON."
                        )
                        geojson_plot_data = None  # Reset on failure
                        map_mode = "scatter"  # Revert mode
                except Exception as e:
                    logger.error(
                        f"Error converting TopoJSON to GeoJSON: {e}", exc_info=True
                    )
                    geojson_plot_data = None
                    map_mode = "scatter"
            # If not TopoJSON, attempt to parse as GeoJSON Point FeatureCollection
            elif map_mode == "scatter":  # Only try if not already handled as TopoJSON
                df_plot = self._parse_geojson_points(data)
                if df_plot is None:  # Parsing failed
                    logger.warning("Failed to parse dict data as GeoJSON points.")
                # map_mode remains 'scatter'

        # If after processing, we don't have a valid DataFrame for plotting, exit
        # Exception: for choropleth_outline, df_plot is dummy, but geojson_plot_data must exist
        if (df_plot is None or df_plot.empty) and map_mode != "choropleth_outline":
            """ logger.warning(
                "No data or invalid data type provided to InteractiveMapWidget (expected non-empty DataFrame or parseable GeoJSON/TopoJSON dict)."
            ) """
            return "<p class='info'>No valid data available for the map.</p>"
        elif map_mode == "choropleth_outline" and not geojson_plot_data:
            logger.warning("Failed to generate GeoJSON for choropleth outline map.")
            return "<p class='info'>No valid map outline data available.</p>"

        required_cols = set()
        # Determine the effective map type
        effective_map_type = params.map_type

        # Handle backward compatibility for deprecated map types
        if effective_map_type == "scatter_mapbox":
            effective_map_type = "scatter_map"
        elif effective_map_type == "choropleth_mapbox":
            effective_map_type = "choropleth_map"

        if not effective_map_type:  # If not specified in params, infer from data
            if map_mode == "choropleth_outline":
                effective_map_type = (
                    "choropleth_map"  # Treat outline as choropleth for later logic
                )
            else:
                effective_map_type = "scatter_map"  # Default inferred type

        # --- Check requirements based on effective_map_type and map_mode ---

        if effective_map_type == "scatter_map":
            # Ensure the DataFrame (original or parsed) has lat/lon fields
            # If parsed from GeoJSON, these are standard 'latitude', 'longitude'
            latitude_field = params.latitude_field or "latitude"
            longitude_field = params.longitude_field or "longitude"

            # Only check lat/lon columns if we actually have point data (not dummy df)
            if map_mode == "scatter" and (
                latitude_field not in df_plot.columns
                or longitude_field not in df_plot.columns
            ):
                logger.error(
                    f"DataFrame missing required coordinate columns ('{latitude_field}', '{longitude_field}') for scatter_map."
                )
                return f"<p class='error'>Data Error: Missing coordinate columns ('{latitude_field}', '{longitude_field}').</p>"
            # Add required columns if they exist (even if check skipped for dummy df)
            if latitude_field in df_plot.columns:
                required_cols.add(latitude_field)
            if longitude_field in df_plot.columns:
                required_cols.add(longitude_field)
            # Allow color_field to be optional (e.g., 'count' from GeoJSON properties)
            color_field = params.color_field or (
                "count" if "count" in df_plot.columns else None
            )
            hover_name_field = params.hover_name  # Use configured or None
            hover_data_fields = params.hover_data
            size_field = params.size_field or (
                "count"
                if params.size_field is None and "count" in df_plot.columns
                else None
            )
            # Add fields used implicitly or explicitly to required_cols check
            if color_field:
                required_cols.add(color_field)
            if hover_name_field:
                required_cols.add(hover_name_field)
            if hover_data_fields:
                required_cols.update(hover_data_fields)
            if params.size_field:
                required_cols.add(params.size_field)

        elif effective_map_type == "choropleth_map":
            # Check for location field only if it's an explicitly configured choropleth
            # (not the implicit choropleth_outline which uses a dummy df)
            if map_mode != "choropleth_outline":
                if not params.location_field:
                    return "<p class='error'>Configuration Error: Location field is required for choropleth_map.</p>"
                required_cols.add(params.location_field)

        # Check for missing columns *in the DataFrame used for plotting*
        # For choropleth_outline, df_plot is dummy, so skip this check
        if map_mode != "choropleth_outline" and df_plot is not None:
            # Ensure required_cols actually exist in the df before checking difference
            valid_required_cols = {
                col for col in required_cols if col in df_plot.columns
            }
            missing_cols = required_cols - valid_required_cols
            if missing_cols:
                logger.error(
                    f"Missing required columns for InteractiveMapWidget ({params.map_type or map_mode}): {missing_cols}"
                )
                return f"<p class='error'>Configuration Error: Missing columns {missing_cols}.</p>"

        # Calculate center and zoom from data only for scatter plots with valid data
        calculated_zoom = params.zoom  # Default to params zoom
        if (
            effective_map_type == "scatter_map"
            and map_mode == "scatter"
            and df_plot is not None
            and not df_plot.empty
        ):
            center_lat = df_plot[latitude_field].mean()
            center_lon = df_plot[longitude_field].mean()

            # Calculate optimal zoom if auto_zoom is enabled
            if params.auto_zoom:
                min_lat = df_plot[latitude_field].min()
                max_lat = df_plot[latitude_field].max()
                min_lon = df_plot[longitude_field].min()
                max_lon = df_plot[longitude_field].max()
                calculated_zoom = self._calculate_zoom_from_bounds(
                    min_lat, max_lat, min_lon, max_lon
                )
                logger.debug(
                    f"Auto-calculated zoom level: {calculated_zoom} for bounds: lat[{min_lat}, {max_lat}], lon[{min_lon}, {max_lon}]"
                )

        try:
            fig = None
            if (
                effective_map_type == "scatter_map"
                and map_mode == "scatter"
                and df_plot is not None
                and not df_plot.empty
            ):
                fig = px.scatter_map(
                    df_plot,
                    lat=latitude_field,
                    lon=longitude_field,
                    color=color_field,
                    size=size_field,
                    hover_name=hover_name_field,
                    hover_data=hover_data_fields,
                    color_continuous_scale=params.color_continuous_scale,
                    color_discrete_map=params.color_discrete_map,
                    range_color=params.range_color,
                    size_max=params.size_max,
                    opacity=params.opacity,
                    zoom=calculated_zoom,
                    center={"lat": center_lat, "lon": center_lon},
                    map_style=params.map_style
                    if params.map_style
                    else params.mapbox_style,
                    title=None,
                )
            elif effective_map_type == "choropleth_map":
                # Note: Choropleth expects the original DataFrame, not the potentially
                # parsed GeoJSON points DataFrame (df_plot) if data was dict.
                # For now, assuming choropleth always gets a DataFrame directly.
                logger.debug("Creating choropleth with DataFrame: %s", df_plot)
                logger.debug(
                    "GeoJSON for plotting: %s with %s features",
                    type(geojson_plot_data),
                    len(geojson_plot_data.get("features", [])),
                )
                try:
                    fig = px.choropleth_map(
                        df_plot,  # Use df_plot (original, or dummy for outline)
                        geojson=geojson_plot_data,
                        # For outline, use dummy df location, else use configured
                        locations=params.location_field
                        if map_mode != "choropleth_outline"
                        else "shape_id",
                        featureidkey=params.featureidkey or "id",
                        # For outline, use dummy value, else use configured field
                        color=params.color_field
                        if map_mode != "choropleth_outline"
                        else "layer"
                        if "layer" in df_plot.columns
                        else "value",
                        color_discrete_map={"shape": "#2d5016", "forest": "#228b22"}
                        if "layer" in df_plot.columns
                        else params.color_discrete_map,
                        hover_name=params.hover_name,
                        hover_data=params.hover_data,
                        opacity=params.opacity,
                        zoom=params.zoom,
                        center={"lat": center_lat, "lon": center_lon},
                        map_style=params.map_style
                        if params.map_style
                        else params.mapbox_style,
                        title=None,
                    )
                    logger.debug(
                        "Successfully created choropleth figure with %s traces",
                        len(fig.data),
                    )
                    logger.debug(
                        "Figure data summary: %s", [trace.type for trace in fig.data]
                    )

                    # Make outline visible for choropleth outline
                    # Calculate center and zoom based on the bounds from GeoJSON
                    zoom_level = (
                        calculated_zoom if calculated_zoom is not None else params.zoom
                    )

                    if geojson_plot_data and "bbox" in geojson_plot_data:
                        center_lon = (
                            geojson_plot_data["bbox"][0] + geojson_plot_data["bbox"][2]
                        ) / 2
                        center_lat = (
                            geojson_plot_data["bbox"][1] + geojson_plot_data["bbox"][3]
                        ) / 2

                        # Calculate optimal zoom if auto_zoom is enabled
                        if params.auto_zoom:
                            bbox = geojson_plot_data["bbox"]
                            zoom_level = self._calculate_zoom_from_bounds(
                                bbox[1], bbox[3], bbox[0], bbox[2]
                            )
                            logger.debug(
                                "Auto-calculated zoom from bbox: %s for bounds: %s",
                                zoom_level,
                                bbox,
                            )
                        else:
                            zoom_level = params.zoom if params.zoom is not None else 9.0

                        logger.debug(
                            "Using center and zoom from GeoJSON bbox: center=(%s, %s), zoom=%s",
                            center_lat,
                            center_lon,
                            zoom_level,
                        )
                    else:
                        zoom_level = zoom_level if zoom_level is not None else 9.0
                        logger.debug(
                            "No bbox in GeoJSON, using zoom: %s",
                            zoom_level,
                        )

                    fig.update_layout(
                        map_zoom=zoom_level,
                        map_center={"lat": center_lat, "lon": center_lon},
                    )
                    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
                    # No need for access token with new map types
                    logger.debug("Successfully updated layout for choropleth_outline")
                except Exception as e:
                    logger.error(
                        "CRITICAL ERROR: Failed to create choropleth figure: %s",
                        str(e),
                        exc_info=True,
                    )
                    return (
                        "<div class='alert alert-danger'>Failed to create choropleth map figure: %s</div>"
                        % str(e)
                    )
            if fig:
                fig.update_layout(
                    margin={"r": 0, "t": 0, "l": 0, "b": 0},
                    annotations=[],  # Remove any annotations including attribution
                )
                # Disable attribution for map layers
                if hasattr(fig, "update_mapboxes"):
                    fig.update_mapboxes(
                        accesstoken=None,
                        style=params.map_style
                        if params.map_style
                        else "carto-positron",
                    )
                # Use centralized render function
                custom_config = get_plotly_config()
                custom_config["toImageButtonOptions"]["filename"] = "niamoto_map"
                html_content = render_plotly_figure(fig, custom_config)
                attribution_class = (
                    " hide-attribution" if not params.show_attribution else ""
                )

                return (
                    """<div class="map-widget%s"><div class="map-container">%s</div></div>"""
                    % (attribution_class, html_content)
                )
            else:
                return "<p class='error'>Failed to create map figure.</p>"

        except Exception as e:
            logger.exception("Error rendering InteractiveMapWidget: %s", e)
            return "<p class='error'>Error generating map: %s</p>" % e

    def _render_multi_layer_map(self, data: dict, params: InteractiveMapParams) -> str:
        """Render a multi-layer map based on the configuration in params.layers."""

        # Si aucune couche n'est définie, on ne peut pas rendre la carte
        if not params.layers:
            return "<div class='alert alert-warning'>No layers defined for interactive map.</div>"

        # Store data for TopoJSON embedding (if use_topojson is enabled)
        topojson_data = {}

        # Extract shape and forest coordinates from data dictionary if present
        shape_geojson = None
        forest_geojson = None
        shape_style = {}
        forest_style = {}

        # Process each layer based on its type and source data.
        for layer_config in params.layers:
            source_key = layer_config.get("source", "")
            layer_style = layer_config.get("style", {})

            # Skip if no source key
            if not source_key:
                continue

            # Extract source data
            source_data = data.get(source_key) if isinstance(data, dict) else None
            if source_data is None:
                continue

            # Store relevant GeoJSON and styles for shape and forest
            if source_key == "shape_coords":
                try:
                    processed_data = self._process_geojson_or_topojson(source_data)

                    if params.use_topojson:
                        # For TopoJSON mode: optimize if needed and store for client-side conversion
                        if processed_data and processed_data.get("type") == "Topology":
                            topojson_data[source_key] = processed_data
                            shape_geojson = processed_data  # Keep TopoJSON for client-side conversion
                        elif processed_data:
                            # Convert to TopoJSON for optimization
                            optimized_data = self._optimize_geojson_to_topojson(
                                processed_data
                            )
                            topojson_data[source_key] = optimized_data
                            shape_geojson = optimized_data  # Keep TopoJSON for client-side conversion
                    else:
                        # Regular mode: use GeoJSON directly
                        shape_geojson = processed_data

                except Exception as e:
                    logger.error("Error processing shape_coords: %s", str(e))
                shape_style = layer_style

            elif source_key == "forest_cover_coords":
                try:
                    processed_data = self._process_geojson_or_topojson(source_data)

                    if params.use_topojson:
                        # For TopoJSON mode: optimize if needed and store for client-side conversion
                        if processed_data and processed_data.get("type") == "Topology":
                            topojson_data[source_key] = processed_data
                            forest_geojson = processed_data  # Keep TopoJSON for client-side conversion
                        elif processed_data:
                            # Convert to TopoJSON for optimization
                            optimized_data = self._optimize_geojson_to_topojson(
                                processed_data
                            )
                            topojson_data[source_key] = optimized_data
                            forest_geojson = optimized_data  # Keep TopoJSON for client-side conversion
                    else:
                        # Regular mode: use GeoJSON directly
                        forest_geojson = processed_data

                except Exception as e:
                    logger.error("Error processing forest_cover_coords: %s", str(e))
                forest_style = layer_style

        # Handle TopoJSON mode with client-side rendering
        if params.use_topojson and topojson_data:
            return self._render_client_side_topojson_map(
                topojson_data, shape_style, forest_style, params
            )

        # Create base figure for regular GeoJSON mode
        fig = go.Figure()

        # Add forest cover layer if available
        if forest_geojson:
            try:
                # Handle both GeoJSON and TopoJSON formats
                if forest_geojson.get("type") == "Topology":
                    # For TopoJSON, we'll need to handle this in JavaScript
                    # For now, convert back to GeoJSON for Plotly
                    objects_keys = list(forest_geojson.get("objects", {}).keys())
                    if objects_keys:
                        object_name = objects_keys[0]
                        topology = topojson.Topology(
                            forest_geojson, object_name=object_name
                        )
                        geojson_str = topology.to_geojson()
                        forest_geojson_for_plotly = json.loads(geojson_str)
                    else:
                        forest_geojson_for_plotly = forest_geojson
                else:
                    forest_geojson_for_plotly = forest_geojson

                # Create matching DataFrame for feature IDs
                forest_ids = [
                    feature.get("id")
                    for feature in forest_geojson_for_plotly.get("features", [])
                ]
                forest_df = pd.DataFrame(
                    {"id": forest_ids, "value": [1] * len(forest_ids)}
                )

                # Get style parameters from configuration
                forest_color = forest_style.get(
                    "fillColor", "#228b22"
                )  # Default to forest green
                forest_opacity = forest_style.get("fillOpacity", 0.8)

                # Add forest layer (using GeoJSON for Plotly)
                fig.add_choroplethmap(
                    geojson=forest_geojson_for_plotly,
                    locations=forest_df["id"],
                    z=forest_df["value"],
                    featureidkey="id",
                    colorscale=[[0, forest_color], [1, forest_color]],
                    showscale=False,
                    marker_opacity=forest_opacity,
                    marker_line_width=0,
                    marker_line_color=forest_color,
                    name="Forest Cover",
                )
            except Exception as e:
                logger.error("Error adding forest layer: %s", str(e), exc_info=True)

        # Add shape boundary layer (without fill) - AFTER the forest layer to ensure it's on top
        if shape_geojson:
            # Handle both GeoJSON and TopoJSON formats
            if shape_geojson.get("type") == "Topology":
                # Convert TopoJSON to GeoJSON for Plotly rendering
                objects_keys = list(shape_geojson.get("objects", {}).keys())
                if objects_keys:
                    object_name = objects_keys[0]
                    topology = topojson.Topology(shape_geojson, object_name=object_name)
                    geojson_str = topology.to_geojson()
                    shape_geojson_for_plotly = json.loads(geojson_str)
                else:
                    shape_geojson_for_plotly = shape_geojson
            else:
                shape_geojson_for_plotly = shape_geojson

            # Use style from configuration instead of hardcoded values
            shape_color = shape_style.get("color", "#2d5016")
            shape_width = shape_style.get("weight", 2)

            logger.debug(
                "Adding shape layer with color %s and line width %s",
                shape_color,
                shape_width,
            )

            # Extract coordinates from GeoJSON to create line traces
            try:
                for feature in shape_geojson_for_plotly.get("features", []):
                    # Process geometry based on its type
                    geometry_type = feature.get("geometry", {}).get("type", "")
                    coordinates = feature.get("geometry", {}).get("coordinates", [])

                    logger.debug(
                        "Processing feature with geometry_type=%s, coordinates length=%s",
                        geometry_type,
                        len(coordinates) if coordinates else 0,
                    )

                    if not coordinates:
                        continue

                    # Extract lat/lon for different geometry types
                    if geometry_type == "Polygon":
                        # For each polygon ring
                        for ring in coordinates:
                            lons = [point[0] for point in ring]
                            lats = [point[1] for point in ring]

                            # Create a line trace
                            fig.add_trace(
                                go.Scattermap(
                                    lon=lons,
                                    lat=lats,
                                    mode="lines",
                                    line=dict(width=shape_width, color=shape_color),
                                    name="Shape Boundary",
                                    showlegend=False,  # Hide from legend
                                )
                            )

                    elif geometry_type == "MultiPolygon":
                        # For each polygon in the multipolygon
                        for polygon in coordinates:
                            # For each ring in the polygon
                            for ring in polygon:
                                lons = [point[0] for point in ring]
                                lats = [point[1] for point in ring]

                                # Create a line trace
                                fig.add_trace(
                                    go.Scattermap(
                                        lon=lons,
                                        lat=lats,
                                        mode="lines",
                                        line=dict(width=shape_width, color=shape_color),
                                        name="Shape Boundary",
                                        showlegend=False,  # Hide from legend
                                    )
                                )

                logger.debug("Successfully added shape boundary using Scattermap")
            except Exception as e:
                logger.error(
                    "Error adding shape boundary traces: %s", str(e), exc_info=True
                )

        # Add a single legend entry for the shape boundary
        if shape_geojson:
            fig.add_trace(
                go.Scattermap(
                    lon=[],
                    lat=[],
                    mode="lines",
                    line=dict(width=shape_width, color=shape_color),
                    name="Shape Boundary",
                    showlegend=True,  # Show in legend
                )
            )

        # Calculate bounds for centering and zoom
        center_lat = -21.0  # Default to New Caledonia
        center_lon = 165.0

        try:
            # Calculate center and zoom based on the bounds from GeoJSON
            all_lons = []
            all_lats = []

            logger.debug(
                "Calculating bounds - shape_geojson present: %s",
                shape_geojson is not None,
            )
            logger.debug(
                "Calculating bounds - forest_geojson present: %s",
                forest_geojson is not None,
            )

            # Extract coordinates from shape_geojson
            if shape_geojson:
                try:
                    for feature in shape_geojson.get("features", []):
                        geometry = feature.get("geometry", {})
                        geometry_type = geometry.get("type", "")

                        if geometry_type == "Polygon":
                            for ring in geometry.get("coordinates", []):
                                for point in ring:
                                    all_lons.append(point[0])
                                    all_lats.append(point[1])
                        elif geometry_type == "MultiPolygon":
                            for polygon in geometry.get("coordinates", []):
                                for ring in polygon:
                                    for point in ring:
                                        all_lons.append(point[0])
                                        all_lats.append(point[1])
                    logger.debug(
                        "Extracted %s points from shape_geojson", len(all_lons)
                    )
                except Exception as e:
                    logger.error(
                        "Error extracting coordinates from shape_geojson: %s", str(e)
                    )

            # Extract coordinates from forest_geojson
            if forest_geojson:
                try:
                    for feature in forest_geojson.get("features", []):
                        geometry = feature.get("geometry", {})
                        geometry_type = geometry.get("type", "")

                        if geometry_type == "Polygon":
                            for ring in geometry.get("coordinates", []):
                                for point in ring:
                                    all_lons.append(point[0])
                                    all_lats.append(point[1])
                        elif geometry_type == "MultiPolygon":
                            for polygon in geometry.get("coordinates", []):
                                for ring in polygon:
                                    for point in ring:
                                        all_lons.append(point[0])
                                        all_lats.append(point[1])
                    logger.debug(
                        "Extracted %s points from forest_geojson", len(all_lons)
                    )
                except Exception as e:
                    logger.error(
                        "Error extracting coordinates from forest_geojson: %s", str(e)
                    )

            # Calculate center
            if all_lons and all_lats:
                min_lon = min(all_lons)
                max_lon = max(all_lons)
                min_lat = min(all_lats)
                max_lat = max(all_lats)
                center_lon = (min_lon + max_lon) / 2
                center_lat = (min_lat + max_lat) / 2
                logger.debug(
                    "Calculated center from coordinates: lat=%s, lon=%s",
                    center_lat,
                    center_lon,
                )
            else:
                logger.debug(
                    "No coordinates found, using default center: lat=%s, lon=%s",
                    center_lat,
                    center_lon,
                )
        except Exception as e:
            logger.error("Error calculating bounding box: %s", str(e), exc_info=True)
            logger.debug("Exception in calculating bounds: %s", str(e))

        # Set up the map layout with zoom from config or default
        try:
            # Calculate optimal zoom if auto_zoom is enabled and we have bounds
            zoom_level = params.zoom if params.zoom is not None else 9.0

            if params.auto_zoom and all_lons and all_lats:
                min_lon = min(all_lons)
                max_lon = max(all_lons)
                min_lat = min(all_lats)
                max_lat = max(all_lats)
                zoom_level = self._calculate_zoom_from_bounds(
                    min_lat, max_lat, min_lon, max_lon
                )
                logger.debug(
                    "Auto-calculated zoom for multi-layer: %s for bounds: lat[%s, %s], lon[%s, %s]",
                    zoom_level,
                    min_lat,
                    max_lat,
                    min_lon,
                    max_lon,
                )

            # Apply the layout
            logger.debug("Figure data before layout update:")
            logger.debug("Number of traces: %s", len(fig.data))
            logger.debug("Layout before update: %s", fig.layout)

            fig.update_layout(
                map_style="carto-positron",
                map_zoom=zoom_level,
                map_center={"lat": center_lat, "lon": center_lon},
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=500,
                annotations=[],  # Remove any annotations including attribution
            )
            # Disable attribution for map layers
            if hasattr(fig, "update_mapboxes"):
                fig.update_mapboxes(accesstoken=None, style="carto-positron")
            logger.debug("Layout updated successfully")
        except Exception as e:
            logger.error("Error updating figure layout: %s", str(e), exc_info=True)

        # Generate HTML
        try:
            # Use centralized render function
            custom_config = get_plotly_config()
            custom_config["toImageButtonOptions"]["filename"] = "niamoto_map"
            map_html = render_plotly_figure(fig, custom_config)
            attribution_class = (
                " hide-attribution" if not params.show_attribution else ""
            )

            return (
                """<div class="map-widget%s"><div class="map-container">%s</div></div>"""
                % (attribution_class, map_html)
            )

        except Exception as e:
            logger.error("Error generating HTML: %s", str(e), exc_info=True)
            return "<p class='error'>Failed to generate map HTML.</p>"
