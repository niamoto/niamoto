# Building Widgets

Guide to creating interactive visualization widgets for Niamoto.

## Widget Architecture

Widgets are plugins that create interactive visualizations for exported sites.

### Base Widget Class

```python
from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from typing import Dict, Any

@register("my_widget", PluginType.WIDGET)
class MyWidget(WidgetPlugin):
    """Custom widget for data visualization."""

    def render(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Render widget HTML.

        Args:
            data: Data to visualize
            config: Widget configuration

        Returns:
            HTML string for the widget
        """
        # Generate HTML/JS for visualization
        return html_output
```

## Widget Types

### 1. Chart Widgets
Display data as interactive charts (line, bar, pie, scatter).

```python
@register("chart_widget", PluginType.WIDGET)
class ChartWidget(WidgetPlugin):
    def render(self, data, config):
        chart_type = config.get('type', 'bar')
        return self.generate_chart(data, chart_type)
```

### 2. Map Widgets
Show geographic data on interactive maps.

```python
@register("map_widget", PluginType.WIDGET)
class MapWidget(WidgetPlugin):
    def render(self, data, config):
        return self.generate_leaflet_map(data)
```

### 3. Table Widgets
Display tabular data with sorting and filtering.

```python
@register("table_widget", PluginType.WIDGET)
class TableWidget(WidgetPlugin):
    def render(self, data, config):
        return self.generate_datatable(data)
```

## Development Process

### 1. Create Widget Class

```python
from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

@register("custom_viz", PluginType.WIDGET)
class CustomVizWidget(WidgetPlugin):

    def validate_config(self, config):
        """Validate widget configuration."""
        required = ['title', 'data_source']
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

    def render(self, data, config):
        """Generate widget HTML."""
        self.validate_config(config)

        html = f"""
        <div class="widget-container">
            <h3>{config['title']}</h3>
            <div id="viz-{id(self)}"></div>
            <script>
                // JavaScript for visualization
                const data = {json.dumps(data)};
                // Render visualization
            </script>
        </div>
        """
        return html
```

### 2. Configure in export.yml

```yaml
export:
  widgets:
    - type: custom_viz
      config:
        title: "Species Distribution"
        data_source: "occurrences"
        options:
          color_scheme: "viridis"
          interactive: true
```

### 3. Use JavaScript Libraries

Common libraries for widgets:
- **D3.js**: Custom visualizations
- **Chart.js**: Standard charts
- **Leaflet**: Maps
- **DataTables**: Interactive tables

```python
def render(self, data, config):
    return f"""
    <div id="chart-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        new Chart(document.getElementById('chart-container'), {{
            type: '{config["chart_type"]}',
            data: {json.dumps(self.prepare_chart_data(data))}
        }});
    </script>
    """
```

## Best Practices

### 1. Responsive Design
Ensure widgets work on all screen sizes:

```css
.widget-container {
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
}

@media (max-width: 768px) {
    .widget-container {
        padding: 10px;
    }
}
```

### 2. Performance Optimization
- Lazy load large datasets
- Use pagination for tables
- Implement virtualization for long lists
- Cache rendered output when possible

### 3. Accessibility
- Add ARIA labels
- Ensure keyboard navigation
- Provide text alternatives
- Use semantic HTML

### 4. Error Handling

```python
def render(self, data, config):
    try:
        if not data:
            return self.render_empty_state()

        if len(data) > 10000:
            return self.render_sampled_data(data)

        return self.render_full_visualization(data)

    except Exception as e:
        logger.error(f"Widget rendering failed: {e}")
        return self.render_error_state(str(e))
```

## Example: Species Distribution Widget

```python
@register("species_distribution", PluginType.WIDGET)
class SpeciesDistributionWidget(WidgetPlugin):
    """Interactive species distribution map."""

    def render(self, data, config):
        # Prepare GeoJSON from occurrence data
        geojson = self.create_geojson(data)

        html = f"""
        <div id="map" style="height: 500px;"></div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <script>
            const map = L.map('map').setView([{config['center_lat']}, {config['center_lon']}], {config['zoom']});

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

            const geojsonData = {json.dumps(geojson)};
            L.geoJSON(geojsonData, {{
                pointToLayer: function(feature, latlng) {{
                    return L.circleMarker(latlng, {{
                        radius: 5,
                        fillColor: feature.properties.color,
                        fillOpacity: 0.8
                    }});
                }},
                onEachFeature: function(feature, layer) {{
                    layer.bindPopup(feature.properties.popupContent);
                }}
            }}).addTo(map);
        </script>
        """
        return html

    def create_geojson(self, data):
        """Convert occurrence data to GeoJSON."""
        features = []
        for item in data:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [item['longitude'], item['latitude']]
                },
                "properties": {
                    "species": item['species'],
                    "count": item.get('count', 1),
                    "popupContent": f"<b>{item['species']}</b><br>Count: {item.get('count', 1)}",
                    "color": self.get_species_color(item['species'])
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }
```

## Testing Widgets

```python
import pytest
from niamoto.core.plugins import get_plugin

def test_widget_rendering():
    widget = get_plugin("species_distribution", PluginType.WIDGET)

    test_data = [
        {"species": "Species A", "latitude": -21.5, "longitude": 165.3},
        {"species": "Species B", "latitude": -22.1, "longitude": 166.2}
    ]

    config = {
        "center_lat": -21.8,
        "center_lon": 165.7,
        "zoom": 10
    }

    html = widget.render(test_data, config)

    assert "map" in html
    assert "Species A" in html
    assert "leaflet" in html.lower()
```

## Advanced Topics

### Dynamic Data Loading
Load data asynchronously for better performance:

```javascript
fetch('/api/widget-data/species-distribution')
    .then(response => response.json())
    .then(data => renderVisualization(data));
```

### Widget Communication
Allow widgets to interact:

```javascript
// Publish event
window.dispatchEvent(new CustomEvent('species-selected', {
    detail: { species: 'Species A' }
}));

// Subscribe to event
window.addEventListener('species-selected', (e) => {
    updateVisualization(e.detail.species);
});
```

### Custom Styling
Use CSS variables for theming:

```css
.widget-container {
    --primary-color: var(--theme-primary, #007bff);
    --background: var(--theme-background, #ffffff);

    background: var(--background);
    color: var(--primary-color);
}
```

## Related Documentation

- [Plugin Architecture](architecture.md)
- [Widget System](../02-data-pipeline/widget-system.md)
- [Export Process](../02-data-pipeline/export-process.md)
