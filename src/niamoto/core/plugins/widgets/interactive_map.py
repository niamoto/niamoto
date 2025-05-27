import json
import logging
from typing import Any, List, Optional, Set
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import topojson
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register


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


@register("interactive_map", PluginType.WIDGET)
class InteractiveMapWidget(WidgetPlugin):
    """Widget to display an interactive map using Plotly Express."""

    param_schema = InteractiveMapParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return set()

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
            logger.warning("GeoJSON FeatureCollection is empty.")
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

    def render(self, data: Optional[Any], params: InteractiveMapParams) -> str:
        """Generate the HTML for the interactive map. Accepts DataFrame or parsed GeoJSON dict."""
        logger.debug("MAIN RENDER CALLED - data type: %s", type(data))

        # Early return if no data
        if data is None:
            logger.debug("No data provided to interactive map widget")
            return "<div class='alert alert-warning'>No valid map data available.</div>"

        # If multi-layer map configuration is provided AND we have shape_coords in data (shape group)
        if params.layers and isinstance(data, dict) and "shape_coords" in data:
            logger.debug("Using multi-layer map with %s layers", len(params.layers))
            try:
                result = self._render_multi_layer_map(data, params)
                return result
            except Exception as e:
                logger.error(
                    "Error rendering multi-layer map: %s", str(e), exc_info=True
                )
                return (
                    "<div class='alert alert-danger'>Failed to render multi-layer map: %s</div>"
                    % str(e)
                )

        # For other groups (taxon, plot, etc.), use the original rendering approach
        logger.debug("Using standard rendering approach (not multi-layer)")

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
                logger.debug(
                    "Received dict data, attempting to parse shape_coords as TopoJSON."
                )
                try:
                    topo_data = data["shape_coords"]
                    # Convert TopoJSON to GeoJSON FeatureCollection. Requires object name ('data' in this case).
                    # This assumes the TopoJSON has an object named 'data'.
                    geojson_str = topojson.Topology(
                        topo_data, object_name="data"
                    ).to_geojson()
                    logger.debug(
                        "Successfully converted shape_coords TopoJSON to GeoJSON"
                    )
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
                            logger.debug("Processing forest_cover_coords as TopoJSON")
                            try:
                                forest_topo_data = data["forest_cover_coords"]
                                forest_geojson_str = topojson.Topology(
                                    forest_topo_data, object_name="data"
                                ).to_geojson()
                                logger.debug(
                                    "Successfully converted forest_cover_coords TopoJSON to GeoJSON"
                                )
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
                logger.debug(
                    "Received dict data, attempting to parse as GeoJSON points."
                )
                df_plot = self._parse_geojson_points(data)
                if df_plot is None:  # Parsing failed
                    logger.warning("Failed to parse dict data as GeoJSON points.")
                # map_mode remains 'scatter'

        # If after processing, we don't have a valid DataFrame for plotting, exit
        # Exception: for choropleth_outline, df_plot might be dummy, but geojson_plot_data must exist
        if (df_plot is None or df_plot.empty) and map_mode != "choropleth_outline":
            logger.warning(
                "No data or invalid data type provided to InteractiveMapWidget (expected non-empty DataFrame or parseable GeoJSON/TopoJSON dict)."
            )
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

        # Calculate center from data only for scatter plots with valid data
        if (
            effective_map_type == "scatter_map"
            and map_mode == "scatter"
            and df_plot is not None
            and not df_plot.empty
        ):
            center_lat = df_plot[latitude_field].mean()
            center_lon = df_plot[longitude_field].mean()

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
                    zoom=params.zoom,
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
                        color_discrete_map={"shape": "#1fb99d", "forest": "#228b22"}
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
                    if geojson_plot_data and "bbox" in geojson_plot_data:
                        center_lon = (
                            geojson_plot_data["bbox"][0] + geojson_plot_data["bbox"][2]
                        ) / 2
                        center_lat = (
                            geojson_plot_data["bbox"][1] + geojson_plot_data["bbox"][3]
                        ) / 2
                        # Use provided zoom or default
                        zoom_level = params.zoom if params.zoom is not None else 9.0
                        logger.debug(
                            "Using center and zoom from GeoJSON bbox: center=(%s, %s), zoom=%s",
                            center_lat,
                            center_lon,
                            zoom_level,
                        )
                    else:
                        zoom_level = params.zoom or 9.0
                        logger.debug(
                            "No bbox in GeoJSON, using provided or default zoom: %s",
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
                fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
                html_content = fig.to_html(full_html=False, include_plotlyjs="cdn")
                return html_content
            else:
                return "<p class='error'>Failed to create map figure.</p>"

        except Exception as e:
            logger.exception("Error rendering InteractiveMapWidget: %s", e)
            return "<p class='error'>Error generating map: %s</p>" % e

    def _render_multi_layer_map(self, data: dict, params: InteractiveMapParams) -> str:
        """Render a multi-layer map based on the configuration in params.layers."""
        logger.debug("RENDER_MULTI_LAYER_MAP CALLED")
        logger.debug(
            "Data keys: %s", data.keys() if isinstance(data, dict) else "Not a dict"
        )
        logger.debug("Params has layers: %s", params.layers is not None)
        logger.debug("Number of layers: %s", len(params.layers) if params.layers else 0)

        # Si aucune couche n'est définie, on ne peut pas rendre la carte
        if not params.layers:
            logger.debug("ERROR - No layers defined in params")
            return "<div class='alert alert-warning'>No layers defined for interactive map.</div>"

        logger.debug("-" * 50)

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
            logger.debug(
                "Processing layer with source_key=%s, data found: %s",
                source_key,
                source_data is not None,
            )
            if source_data is None:
                logger.debug("No data found for source_key=%s", source_key)
                continue

            # Store relevant GeoJSON and styles for shape and forest
            if source_key == "shape_coords":
                logger.debug(
                    "Processing shape_coords, data type: %s", type(source_data)
                )
                try:
                    shape_geojson = self._process_geojson_or_topojson(source_data)
                    logger.debug(
                        "Processed shape_coords successfully: %s",
                        shape_geojson is not None,
                    )
                    if shape_geojson:
                        logger.debug(
                            "Shape GeoJSON type: %s, features: %s",
                            shape_geojson.get("type"),
                            len(shape_geojson.get("features", [])),
                        )
                except Exception as e:
                    logger.error("Error processing shape_coords: %s", str(e))
                shape_style = layer_style
                logger.debug("Shape style: %s", shape_style)

            elif source_key == "forest_cover_coords":
                logger.debug(
                    "Processing forest_cover_coords, data type: %s", type(source_data)
                )
                try:
                    forest_geojson = self._process_geojson_or_topojson(source_data)
                    logger.debug(
                        "Processed forest_cover_coords successfully: %s",
                        forest_geojson is not None,
                    )
                    if forest_geojson:
                        logger.debug(
                            "Forest GeoJSON type: %s, features: %s",
                            forest_geojson.get("type"),
                            len(forest_geojson.get("features", [])),
                        )
                except Exception as e:
                    logger.error("Error processing forest_cover_coords: %s", str(e))
                forest_style = layer_style
                logger.debug("Forest style: %s", forest_style)

        # Create base figure

        fig = go.Figure()

        # Add forest cover layer if available
        if forest_geojson:
            try:
                # Create matching DataFrame for feature IDs
                forest_ids = [
                    feature.get("id") for feature in forest_geojson.get("features", [])
                ]
                forest_df = pd.DataFrame(
                    {"id": forest_ids, "value": [1] * len(forest_ids)}
                )

                # Get style parameters from configuration
                forest_color = forest_style.get(
                    "fillColor", "#228b22"
                )  # Default to forest green
                forest_opacity = forest_style.get("fillOpacity", 0.8)

                # Add forest layer
                fig.add_choroplethmap(
                    geojson=forest_geojson,
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
                logger.debug("Successfully added forest layer to the figure")
            except Exception as e:
                logger.error("Error adding forest layer: %s", str(e), exc_info=True)

        # Add shape boundary layer (without fill) - AFTER the forest layer to ensure it's on top
        if shape_geojson:
            # Use style from configuration instead of hardcoded values
            shape_color = shape_style.get("color", "#1fb99d")
            shape_width = shape_style.get("weight", 2)

            logger.debug(
                "Adding shape layer with color %s and line width %s",
                shape_color,
                shape_width,
            )

            # Extract coordinates from GeoJSON to create line traces
            try:
                for feature in shape_geojson.get("features", []):
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
            # Use configured zoom level or default
            zoom_level = params.zoom if params.zoom is not None else 9.0

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
            )
            logger.debug("Layout updated successfully")
        except Exception as e:
            logger.error("Error updating figure layout: %s", str(e), exc_info=True)

        # Generate HTML
        try:
            logger.debug("About to generate HTML")
            if params.title or params.description:
                title_elements = []
                if params.title:
                    title_elements.append("<h3>%s</h3>" % params.title)
                if params.description:
                    title_elements.append("<p>%s</p>" % params.description)

                title_html = "".join(title_elements)
                map_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
                return """
                <div class="widget map-widget">
                    %s
                    <div class="map-container">
                        %s
                    </div>
                </div>
                """ % (title_html, map_html)
            else:
                return fig.to_html(full_html=False, include_plotlyjs="cdn")

        except Exception as e:
            logger.error("Error generating HTML: %s", str(e), exc_info=True)
            logger.debug("Exception generating HTML: %s", str(e))
            return "<p class='error'>Failed to generate map HTML.</p>"
