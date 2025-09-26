# Custom Exporters

Guide to developing custom export plugins for Niamoto.

## Exporter Architecture

Exporters are plugins that generate outputs from processed data.

### Base Exporter Class

```python
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
from typing import Dict, Any
import pandas as pd

@register("my_exporter", PluginType.EXPORTER)
class MyExporter(ExporterPlugin):
    """Custom exporter for specific output format."""

    def export(self, data: pd.DataFrame, config: Dict[str, Any], output_path: str) -> None:
        """
        Export data to specified format.

        Args:
            data: Data to export
            config: Export configuration
            output_path: Output directory path
        """
        # Export logic here
        pass
```

## Exporter Types

### 1. File Exporters
Export data to various file formats.

```python
@register("csv_exporter", PluginType.EXPORTER)
class CSVExporter(ExporterPlugin):
    def export(self, data, config, output_path):
        file_path = os.path.join(output_path, config.get('filename', 'export.csv'))
        data.to_csv(file_path, index=False)
        return file_path
```

### 2. API Exporters
Send data to external APIs.

```python
@register("api_exporter", PluginType.EXPORTER)
class APIExporter(ExporterPlugin):
    def export(self, data, config, output_path):
        endpoint = config['endpoint']
        headers = config.get('headers', {})

        response = requests.post(
            endpoint,
            json=data.to_dict('records'),
            headers=headers
        )
        response.raise_for_status()
        return response.json()
```

### 3. Static Site Exporters
Generate static websites.

```python
@register("site_exporter", PluginType.EXPORTER)
class SiteExporter(ExporterPlugin):
    def export(self, data, config, output_path):
        self.create_site_structure(output_path)
        self.generate_pages(data, config, output_path)
        self.copy_assets(output_path)
        return output_path
```

## Development Process

### 1. Create Exporter Class

```python
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
import json
import os

@register("geojson_exporter", PluginType.EXPORTER)
class GeoJSONExporter(ExporterPlugin):
    """Export data as GeoJSON format."""

    def validate_config(self, config):
        """Validate export configuration."""
        if 'lat_field' not in config or 'lon_field' not in config:
            raise ValueError("lat_field and lon_field are required")

    def export(self, data, config, output_path):
        """Export data as GeoJSON."""
        self.validate_config(config)

        # Create GeoJSON structure
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }

        # Convert each row to GeoJSON feature
        for _, row in data.iterrows():
            feature = self.create_feature(row, config)
            geojson["features"].append(feature)

        # Write to file
        output_file = os.path.join(output_path, config.get('filename', 'export.geojson'))
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Exported {len(data)} features to {output_file}")
        return output_file

    def create_feature(self, row, config):
        """Create GeoJSON feature from data row."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(row[config['lon_field']]),
                    float(row[config['lat_field']])
                ]
            },
            "properties": {
                k: v for k, v in row.items()
                if k not in [config['lat_field'], config['lon_field']]
            }
        }
```

### 2. Configure in export.yml

```yaml
export:
  exporters:
    - type: geojson_exporter
      config:
        filename: "occurrences.geojson"
        lat_field: "latitude"
        lon_field: "longitude"
        properties:
          - species
          - date_observed
          - observer
```

### 3. Handle Large Datasets

```python
@register("chunked_exporter", PluginType.EXPORTER)
class ChunkedExporter(ExporterPlugin):
    """Export large datasets in chunks."""

    def export(self, data, config, output_path):
        chunk_size = config.get('chunk_size', 1000)
        base_name = config.get('filename', 'export')

        for i, chunk_start in enumerate(range(0, len(data), chunk_size)):
            chunk = data.iloc[chunk_start:chunk_start + chunk_size]
            filename = f"{base_name}_part_{i+1}.csv"
            filepath = os.path.join(output_path, filename)
            chunk.to_csv(filepath, index=False)

        return output_path
```

## Common Export Formats

### Darwin Core Archive

```python
@register("dwca_exporter", PluginType.EXPORTER)
class DarwinCoreExporter(ExporterPlugin):
    """Export as Darwin Core Archive."""

    def export(self, data, config, output_path):
        # Create DwC-A structure
        dwca_path = os.path.join(output_path, "dwca")
        os.makedirs(dwca_path, exist_ok=True)

        # Write occurrence.txt
        self.write_occurrences(data, dwca_path)

        # Write meta.xml
        self.write_metadata(config, dwca_path)

        # Create archive
        self.create_archive(dwca_path, output_path)

        return os.path.join(output_path, "dwca.zip")
```

### HTML Reports

```python
@register("html_report", PluginType.EXPORTER)
class HTMLReportExporter(ExporterPlugin):
    """Generate HTML reports."""

    def export(self, data, config, output_path):
        template = self.load_template(config.get('template', 'default'))

        html_content = template.render(
            data=data,
            statistics=self.calculate_statistics(data),
            charts=self.generate_charts(data),
            config=config
        )

        output_file = os.path.join(output_path, "report.html")
        with open(output_file, 'w') as f:
            f.write(html_content)

        return output_file
```

## Best Practices

### 1. Error Handling

```python
def export(self, data, config, output_path):
    try:
        # Validate inputs
        if data.empty:
            logger.warning("No data to export")
            return None

        # Create output directory
        os.makedirs(output_path, exist_ok=True)

        # Export with progress
        return self._export_with_progress(data, config, output_path)

    except PermissionError as e:
        raise ExportError(f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise ExportError(str(e))
```

### 2. Progress Reporting

```python
from tqdm import tqdm

def export(self, data, config, output_path):
    total_rows = len(data)

    with tqdm(total=total_rows, desc="Exporting") as pbar:
        for batch in self.get_batches(data, batch_size=100):
            self.export_batch(batch, output_path)
            pbar.update(len(batch))
```

### 3. Configuration Validation

```python
from pydantic import BaseModel, Field

class ExporterConfig(BaseModel):
    filename: str
    format: str = Field(default="csv", pattern="^(csv|json|xml)$")
    encoding: str = "utf-8"
    compression: Optional[str] = None

def validate_config(self, config):
    try:
        validated = ExporterConfig(**config)
        return validated.dict()
    except ValidationError as e:
        raise ConfigError(f"Invalid configuration: {e}")
```

## Advanced Features

### Multi-format Export

```python
@register("multi_format", PluginType.EXPORTER)
class MultiFormatExporter(ExporterPlugin):
    """Export to multiple formats simultaneously."""

    EXPORTERS = {
        'csv': CSVExporter(),
        'json': JSONExporter(),
        'excel': ExcelExporter()
    }

    def export(self, data, config, output_path):
        formats = config.get('formats', ['csv'])
        results = {}

        for fmt in formats:
            if fmt in self.EXPORTERS:
                exporter = self.EXPORTERS[fmt]
                result = exporter.export(data, config, output_path)
                results[fmt] = result

        return results
```

### Incremental Export

```python
@register("incremental", PluginType.EXPORTER)
class IncrementalExporter(ExporterPlugin):
    """Export only changed data."""

    def export(self, data, config, output_path):
        last_export = self.get_last_export_timestamp(output_path)

        if last_export:
            # Filter for new/changed records
            data = data[data['modified'] > last_export]

        if data.empty:
            logger.info("No new data to export")
            return None

        # Export new data
        result = self.export_data(data, output_path)

        # Update timestamp
        self.update_export_timestamp(output_path)

        return result
```

### Cloud Export

```python
@register("s3_exporter", PluginType.EXPORTER)
class S3Exporter(ExporterPlugin):
    """Export to Amazon S3."""

    def export(self, data, config, output_path):
        import boto3

        s3 = boto3.client('s3')
        bucket = config['bucket']
        key = config['key']

        # Convert data to bytes
        buffer = io.BytesIO()
        data.to_parquet(buffer, index=False)
        buffer.seek(0)

        # Upload to S3
        s3.upload_fileobj(buffer, bucket, key)

        return f"s3://{bucket}/{key}"
```

## Testing Exporters

```python
import pytest
import tempfile
import os

def test_exporter():
    # Create test data
    data = pd.DataFrame({
        'species': ['A', 'B', 'C'],
        'count': [10, 20, 30]
    })

    # Test configuration
    config = {
        'filename': 'test_export.csv'
    }

    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = get_plugin("csv_exporter", PluginType.EXPORTER)
        result = exporter.export(data, config, tmpdir)

        # Verify export
        assert os.path.exists(result)

        # Check content
        exported_data = pd.read_csv(result)
        assert len(exported_data) == 3
        assert 'species' in exported_data.columns
```

## Performance Optimization

### Streaming Export

```python
def export(self, data, config, output_path):
    """Export data using streaming to handle large datasets."""
    output_file = os.path.join(output_path, config['filename'])

    with open(output_file, 'w') as f:
        # Write header
        f.write(','.join(data.columns) + '\n')

        # Stream data in chunks
        for chunk in pd.read_sql(query, connection, chunksize=1000):
            chunk.to_csv(f, header=False, index=False, mode='a')
```

### Parallel Export

```python
from concurrent.futures import ThreadPoolExecutor

def export(self, data, config, output_path):
    """Export using parallel processing."""
    n_workers = config.get('workers', 4)
    chunks = np.array_split(data, n_workers)

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            future = executor.submit(
                self.export_chunk,
                chunk,
                config,
                output_path,
                i
            )
            futures.append(future)

        results = [f.result() for f in futures]

    return self.merge_results(results, output_path)
```

## Related Documentation

- [Plugin Architecture](architecture.md)
- [Export Process](../02-data-pipeline/export-process.md)
- [Configuration](../08-configuration/)
