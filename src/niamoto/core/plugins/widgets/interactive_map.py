import logging
import json
from typing import Any, List, Optional, Set
import topojson

import pandas as pd
import plotly.express as px
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


class InteractiveMapParams(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
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
        default="scatter_mapbox", description="'scatter_mapbox' or 'choropleth_mapbox'."
    )
    mapbox_style: str = Field(
        default="carto-positron",
        description="Mapbox base style (e.g., 'open-street-map', 'carto-positron', 'stamen-terrain').",
    )
    zoom: int = Field(default=8, description="Initial map zoom level.")
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
        default=15, description="Maximum marker size for scatter_mapbox."
    )
    opacity: Optional[float] = Field(
        default=0.8, description="Marker/feature opacity (0 to 1)."
    )
    featureidkey: Optional[str] = Field(
        None,
        description="Key in GeoJSON features to link with location_field (e.g., 'properties.id').",
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

    def render(self, data: Optional[Any], params: InteractiveMapParams) -> str:
        """Generate the HTML for the interactive map. Accepts DataFrame or parsed GeoJSON dict."""
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
                logger.debug("Received dict data, attempting to parse as TopoJSON.")
                topo_data = data["shape_coords"]
                try:
                    # Convert TopoJSON to GeoJSON FeatureCollection. Requires object name ('data' in this case).
                    # This assumes the TopoJSON has an object named 'data'.
                    geojson_str = topojson.Topology(
                        topo_data, object_name="data"
                    ).to_geojson()
                    geojson_plot_data = json.loads(geojson_str)  # Parse string to dict
                    map_mode = "choropleth_outline"
                    # Create a dummy DataFrame needed by choropleth_mapbox
                    # Add an 'id' property to the first feature for matching
                    if geojson_plot_data and geojson_plot_data.get("features"):
                        geojson_plot_data["features"][0]["id"] = (
                            0  # Add id for matching
                        )
                        df_plot = pd.DataFrame(
                            {"shape_id": [0], "value": [1]}
                        )  # Dummy df
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
        if not effective_map_type:  # If not specified in params, infer from data
            if map_mode == "choropleth_outline":
                effective_map_type = (
                    "choropleth_mapbox"  # Treat outline as choropleth for later logic
                )
            else:
                effective_map_type = "scatter_mapbox"  # Default inferred type

        # --- Check requirements based on effective_map_type and map_mode ---

        if effective_map_type == "scatter_mapbox":
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
                    f"DataFrame missing required coordinate columns ('{latitude_field}', '{longitude_field}') for scatter_mapbox."
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

        elif effective_map_type == "choropleth_mapbox":
            # Check for location field only if it's an explicitly configured choropleth
            # (not the implicit choropleth_outline which uses a dummy df)
            if map_mode != "choropleth_outline":
                if not params.location_field:
                    return "<p class='error'>Configuration Error: Location field is required for choropleth_mapbox.</p>"
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

        map_center = None
        if params.center_lat is not None and params.center_lon is not None:
            map_center = {"lat": params.center_lat, "lon": params.center_lon}
        # Calculate center from data only for scatter plots with valid data
        elif (
            effective_map_type == "scatter_mapbox"
            and map_mode == "scatter"
            and df_plot is not None
            and not df_plot.empty
        ):
            map_center = {
                "lat": df_plot[latitude_field].mean(),
                "lon": df_plot[longitude_field].mean(),
            }

        try:
            fig = None
            if (
                effective_map_type == "scatter_mapbox"
                and map_mode == "scatter"
                and df_plot is not None
                and not df_plot.empty
            ):
                fig = px.scatter_mapbox(
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
                    center=map_center,
                    mapbox_style=params.mapbox_style,
                    title=None,
                )
            elif effective_map_type == "choropleth_mapbox":
                # Note: Choropleth expects the original DataFrame, not the potentially
                # parsed GeoJSON points DataFrame (df_plot) if data was dict.
                # For now, assuming choropleth always gets a DataFrame directly.

                fig = px.choropleth_mapbox(
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
                    else "value",
                    color_continuous_scale=params.color_continuous_scale,
                    range_color=params.range_color,
                    # For outline, don't show a color bar legend
                    color_continuous_midpoint=None
                    if map_mode == "choropleth_outline"
                    else params.color_continuous_midpoint,
                    hover_name=params.hover_name,
                    hover_data=params.hover_data,
                    opacity=params.opacity,
                    zoom=params.zoom,
                    center=map_center,
                    mapbox_style=params.mapbox_style,
                    title=None,
                )
                # Make outline visible for choropleth outline
                if map_mode == "choropleth_outline":
                    fig.update_layout(
                        mapbox_zoom=8, mapbox_center={"lat": 37.0902, "lon": -95.7129}
                    )
                    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
                    fig.update_layout(mapbox_accesstoken=None)

            if fig:
                fig.update_layout(
                    margin={"r": 0, "t": 0, "l": 0, "b": 0}, mapbox_accesstoken=None
                )
                html_content = fig.to_html(full_html=False, include_plotlyjs="cdn")
                return html_content
            else:
                return "<p class='error'>Failed to create map figure.</p>"

        except Exception as e:
            logger.exception(f"Error rendering InteractiveMapWidget: {e}")
            return f"<p class='error'>Error generating map: {e}</p>"
