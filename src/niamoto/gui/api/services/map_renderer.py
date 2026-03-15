"""
Map rendering service with support for multiple rendering engines.

This service centralizes map rendering logic and supports both Plotly and Leaflet
as rendering engines. Plotly is the default engine.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import plotly.graph_objects as go

from niamoto.core.plugins.widgets.plotly_utils import (
    render_plotly_figure,
    get_plotly_config,
)

logger = logging.getLogger(__name__)

# Type alias for engine selection
MapEngine = Literal["plotly", "leaflet"]


@dataclass
class MapStyle:
    """Style configuration for map features."""

    color: str = "#3b82f6"
    fill_color: str = "#3b82f6"
    fill_opacity: float = 0.3
    stroke_width: int = 2
    stroke_opacity: float = 1.0
    point_radius: int = 8


@dataclass
class MapConfig:
    """Configuration for map rendering."""

    title: str = ""
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    zoom: float = 9.0
    auto_zoom: bool = True
    # Use open-street-map by default (raster tiles, no CORS issues)
    # carto-positron uses vector tiles that have CORS issues from localhost
    map_style: str = "open-street-map"
    height: int = 500
    style: MapStyle = field(default_factory=MapStyle)
    # Custom XYZ tiles support
    custom_tiles_url: Optional[str] = None
    custom_tiles_attribution: str = ""


class MapRenderer:
    """
    Centralized map rendering service.

    Supports both Plotly and Leaflet engines with Plotly as default.
    """

    @classmethod
    def render(
        cls,
        geojson: Dict[str, Any],
        config: Optional[MapConfig] = None,
        engine: MapEngine = "plotly",
    ) -> str:
        """
        Render a map from GeoJSON data.

        Args:
            geojson: GeoJSON FeatureCollection with Point, Polygon, or MultiPolygon geometries
            config: Map configuration (uses defaults if not provided)
            engine: Rendering engine - "plotly" (default) or "leaflet"

        Returns:
            HTML string for the map
        """
        if config is None:
            config = MapConfig()

        if not geojson or geojson.get("type") != "FeatureCollection":
            return "<p class='info'>No valid GeoJSON data</p>"

        features = geojson.get("features", [])
        if not features:
            return "<p class='info'>No features to display</p>"

        # Calculate bounds if auto_zoom is enabled
        if config.auto_zoom or config.center_lat is None or config.center_lon is None:
            bounds = cls._calculate_bounds(features)
            if bounds:
                config.center_lat = (bounds["min_lat"] + bounds["max_lat"]) / 2
                config.center_lon = (bounds["min_lon"] + bounds["max_lon"]) / 2
                if config.auto_zoom:
                    config.zoom = cls._calculate_zoom(bounds)

        # Default center if still not set
        if config.center_lat is None:
            config.center_lat = 0
        if config.center_lon is None:
            config.center_lon = 0

        if engine == "leaflet":
            return cls._render_leaflet(geojson, config)
        else:
            return cls._render_plotly(geojson, config)

    @classmethod
    def _render_plotly(cls, geojson: Dict[str, Any], config: MapConfig) -> str:
        """Render map using Plotly."""
        fig = go.Figure()

        features = geojson.get("features", [])

        # Separate points from polygons
        points = []
        polygons = []

        for feature in features:
            geom = feature.get("geometry", {})
            geom_type = geom.get("type", "")

            if geom_type == "Point":
                points.append(feature)
            elif geom_type in ("Polygon", "MultiPolygon"):
                polygons.append(feature)

        # Render polygons as line traces (boundaries)
        for feature in polygons:
            geom = feature.get("geometry", {})
            props = feature.get("properties", {})
            name = props.get("name", f"ID: {props.get('id', '?')}")

            coords_list = cls._extract_polygon_coords(geom)

            for i, coords in enumerate(coords_list):
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]

                fig.add_trace(
                    go.Scattermap(
                        lon=lons,
                        lat=lats,
                        mode="lines",
                        fill="toself",
                        fillcolor=cls._hex_to_rgba(
                            config.style.fill_color, config.style.fill_opacity
                        ),
                        line=dict(
                            width=config.style.stroke_width,
                            color=config.style.color,
                        ),
                        name=name if i == 0 else None,
                        showlegend=(i == 0),
                        hoverinfo="text",
                        hovertext=name,
                    )
                )

        # Render points
        if points:
            lons = []
            lats = []
            names = []

            for feature in points:
                geom = feature.get("geometry", {})
                coords = geom.get("coordinates", [])
                props = feature.get("properties", {})

                if len(coords) >= 2:
                    lons.append(coords[0])
                    lats.append(coords[1])
                    names.append(props.get("name", f"ID: {props.get('id', '?')}"))

            if lons:
                fig.add_trace(
                    go.Scattermap(
                        lon=lons,
                        lat=lats,
                        mode="markers",
                        marker=dict(
                            size=config.style.point_radius,
                            color=config.style.fill_color,
                            opacity=config.style.fill_opacity + 0.4,
                        ),
                        text=names,
                        hovertemplate="<b>%{text}</b><extra></extra>",
                        name="Locations",
                        showlegend=True,
                    )
                )

        # Update layout - explicitly set center and zoom, disable auto-fitting
        map_layout = dict(
            center=dict(lat=config.center_lat, lon=config.center_lon),
            zoom=config.zoom,
        )

        # Use custom tiles if URL is provided, otherwise use predefined style
        if config.custom_tiles_url:
            # Use white-bg as base style and add custom raster tiles layer
            map_layout["style"] = "white-bg"
            map_layout["layers"] = [
                {
                    "sourcetype": "raster",
                    "source": [config.custom_tiles_url],
                    "below": "traces",
                }
            ]
        else:
            map_layout["style"] = config.map_style

        fig.update_layout(
            map=map_layout,
            margin=dict(r=0, t=0, l=0, b=0),
            autosize=True,
            showlegend=False,
        )

        # Force the map bounds to respect our center/zoom (disable auto-fit)
        fig.update_traces(
            selector=dict(type="scattermap"),
            below="",  # Ensure markers are visible
        )

        # Render to HTML
        custom_config = get_plotly_config()
        custom_config["toImageButtonOptions"]["filename"] = "niamoto_map"

        return render_plotly_figure(fig, custom_config, is_map=True)

    @classmethod
    def _render_leaflet(cls, geojson: Dict[str, Any], config: MapConfig) -> str:
        """Render map using Leaflet."""
        style = config.style

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{config.title}</title>
    <link rel="stylesheet" href="/api/site/assets/css/vendor/leaflet/1.9.4_leaflet.css" />
    <script src="/api/site/assets/js/vendor/leaflet/1.9.4_leaflet.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; height: 100%; }}
        #map {{ width: 100%; height: 100%; }}
        .tile-offline-notice {{
            position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
            z-index: 1000; background: rgba(0,0,0,0.7); color: #fff;
            padding: 4px 12px; border-radius: 4px; font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const geojson = {json.dumps(geojson)};
        const map = L.map('map').setView([{config.center_lat}, {config.center_lon}], {config.zoom});

        // Tenter de charger les tuiles OSM, avec fallback fond blanc si offline
        const tileLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> | &copy; OpenStreetMap contributors',
            maxZoom: 19
        }});
        tileLayer.on('tileerror', function() {{
            // Premiere erreur de tuile : afficher un avis
            if (!document.querySelector('.tile-offline-notice')) {{
                const notice = document.createElement('div');
                notice.className = 'tile-offline-notice';
                notice.textContent = 'Fond de carte indisponible hors connexion';
                document.getElementById('map').appendChild(notice);
            }}
        }});
        tileLayer.addTo(map);

        const geojsonLayer = L.geoJSON(geojson, {{
            style: function(feature) {{
                return {{
                    color: '{style.color}',
                    weight: {style.stroke_width},
                    fillColor: '{style.fill_color}',
                    fillOpacity: {style.fill_opacity}
                }};
            }},
            pointToLayer: function(feature, latlng) {{
                return L.circleMarker(latlng, {{
                    radius: {style.point_radius},
                    fillColor: '{style.fill_color}',
                    color: '{style.color}',
                    weight: {style.stroke_width},
                    opacity: {style.stroke_opacity},
                    fillOpacity: {style.fill_opacity + 0.4}
                }});
            }},
            onEachFeature: function(feature, layer) {{
                if (feature.properties && feature.properties.name) {{
                    layer.bindPopup('<strong>' + feature.properties.name + '</strong>');
                }}
            }}
        }}).addTo(map);

        // Fit bounds to show all features
        if (geojson.features.length > 0) {{
            map.fitBounds(geojsonLayer.getBounds(), {{ padding: [20, 20] }});
        }}
    </script>
</body>
</html>
"""

    @staticmethod
    def _extract_polygon_coords(geometry: Dict[str, Any]) -> List[List[List[float]]]:
        """Extract coordinate rings from Polygon or MultiPolygon geometry."""
        geom_type = geometry.get("type", "")
        coords = geometry.get("coordinates", [])

        result = []

        if geom_type == "Polygon":
            # Polygon has array of rings, first is exterior
            for ring in coords:
                result.append(ring)
        elif geom_type == "MultiPolygon":
            # MultiPolygon has array of polygons
            for polygon in coords:
                for ring in polygon:
                    result.append(ring)

        return result

    @staticmethod
    def _calculate_bounds(features: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
        """Calculate bounding box from features."""
        lons = []
        lats = []

        for feature in features:
            geom = feature.get("geometry", {})
            geom_type = geom.get("type", "")
            coords = geom.get("coordinates", [])

            if geom_type == "Point" and len(coords) >= 2:
                lons.append(coords[0])
                lats.append(coords[1])
            elif geom_type == "Polygon":
                for ring in coords:
                    for point in ring:
                        if len(point) >= 2:
                            lons.append(point[0])
                            lats.append(point[1])
            elif geom_type == "MultiPolygon":
                for polygon in coords:
                    for ring in polygon:
                        for point in ring:
                            if len(point) >= 2:
                                lons.append(point[0])
                                lats.append(point[1])

        if not lons or not lats:
            return None

        return {
            "min_lon": min(lons),
            "max_lon": max(lons),
            "min_lat": min(lats),
            "max_lat": max(lats),
        }

    @staticmethod
    def _calculate_zoom(bounds: Dict[str, float]) -> float:
        """Calculate appropriate zoom level from bounds."""
        import math

        lat_diff = bounds["max_lat"] - bounds["min_lat"]
        lon_diff = bounds["max_lon"] - bounds["min_lon"]
        max_diff = max(lat_diff, lon_diff)

        if max_diff == 0:
            return 12.0  # Single point - moderate zoom to ensure visibility

        # Formula: zoom = log2(360 / maxDiff) - buffer
        zoom = math.log2(360 / max_diff) - 1.2

        return max(1.0, min(18.0, zoom))

    @staticmethod
    def _hex_to_rgba(hex_color: str, opacity: float) -> str:
        """Convert hex color to rgba string."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        return f"rgba({r}, {g}, {b}, {opacity})"
