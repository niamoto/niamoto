# Common Issues and Troubleshooting

This guide helps you diagnose and resolve common issues when working with Niamoto.

## Overview

This troubleshooting guide is organized by:

1. [Installation Issues](#installation-issues)
2. [Import Problems](#import-problems)
3. [Transformation Errors](#transformation-errors)
4. [Export Issues](#export-issues)
5. [Performance Problems](#performance-problems)
6. [Deployment Issues](#deployment-issues)

## Installation Issues

### Command Not Found: niamoto

**Problem**: `bash: niamoto: command not found`

**Causes & Solutions**:

1. **Niamoto not installed**:
   ```bash
   pip install niamoto
   # or
   uv pip install niamoto
   ```

2. **Installation in wrong environment**:
   ```bash
   # Check which Python you're using
   which python
   which pip

   # Activate correct environment
   source venv/bin/activate  # or your environment
   pip install niamoto
   ```

3. **PATH issues**:
   ```bash
   # Check installation location
   python -m site --user-base

   # Add to PATH (Linux/macOS)
   export PATH="$HOME/.local/bin:$PATH"

   # Or use python -m
   python -m niamoto --version
   ```

4. **Windows PATH issues**:
   ```cmd
   # Add Python Scripts to PATH
   # Usually: C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts

   # Or use py launcher
   py -m niamoto --version
   ```

### GDAL Installation Problems

**Problem**: `ImportError: No module named 'osgeo'`

**Solutions by Platform**:

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev python3-gdal
pip install GDAL==$(gdal-config --version)
```

**macOS**:
```bash
brew install gdal
pip install GDAL==$(gdal-config --version)
```

**Windows**:
1. Download OSGeo4W installer
2. Install GDAL package
3. Add to system PATH
4. `pip install GDAL`

**Alternative (conda)**:
```bash
conda install -c conda-forge gdal
```

### Python Version Compatibility

**Problem**: `ImportError` or `SyntaxError` on import

**Solution**: Ensure Python 3.9+ is being used:
```bash
python --version  # Should be 3.9 or higher
pip install --upgrade niamoto
```

## Import Problems

### File Not Found Errors

**Problem**: `FileNotFoundError: [Errno 2] No such file or directory: 'imports/data.csv'`

**Solutions**:

1. **Check file paths** (relative to project root):
   ```bash
   ls -la imports/
   # Verify files exist and names match configuration
   ```

2. **Check working directory**:
   ```bash
   pwd  # Should be in project root
   cd /path/to/your/project
   ```

3. **Verify configuration** in `config/import.yml`:
   ```yaml
   occurrences:
     type: csv
     path: "imports/occurrences.csv"  # Relative to project root
   ```

### Invalid Coordinate Errors

**Problem**: `Invalid coordinates` or `Coordinate out of bounds`

**Diagnosis**:
```bash
# Check coordinate ranges
head -5 imports/occurrences.csv
awk -F',' 'NR>1 {print $3, $4}' imports/occurrences.csv | head -10
```

**Solutions**:

1. **Wrong coordinate system**:
   ```bash
   # Convert UTM to WGS84
   ogr2ogr -t_srs EPSG:4326 -s_srs EPSG:32633 output.csv input.csv
   ```

2. **Swapped lat/lon**:
   ```yaml
   # In import.yml, swap x and y
   geo_pt:
     x: "latitude"   # Should be longitude
     y: "longitude"  # Should be latitude
   ```

3. **Invalid values**:
   ```bash
   # Find invalid coordinates
   awk -F',' 'NR>1 && ($3<-90 || $3>90 || $4<-180 || $4>180) {print NR": " $3 "," $4}' imports/occurrences.csv
   ```

### CSV Encoding Issues

**Problem**: `UnicodeDecodeError` or garbled characters

**Solutions**:

1. **Specify encoding** in import configuration:
   ```yaml
   occurrences:
     type: csv
     path: "imports/occurrences.csv"
     encoding: "utf-8"  # or "latin1", "cp1252"
   ```

2. **Convert file encoding**:
   ```bash
   # Convert to UTF-8
   iconv -f latin1 -t utf-8 input.csv > output.csv
   ```

3. **Check file encoding**:
   ```bash
   file -bi imports/occurrences.csv
   ```

### Database Lock Errors

**Problem**: `database is locked` or `OperationalError`

**Solutions**:

1. **Close other connections**:
   ```bash
   # Kill any running niamoto processes
   ps aux | grep niamoto
   kill -9 <process_id>
   ```

2. **Reset database**:
   ```bash
   niamoto init --reset
   ```

3. **Check disk space**:
   ```bash
   df -h .
   ```

## Transformation Errors

### Plugin Not Found

**Problem**: `Plugin 'my_plugin' not found`

**Solutions**:

1. **List available plugins**:
   ```bash
   niamoto plugins --type transformer
   ```

2. **Check plugin spelling** in `transform.yml`
3. **Install missing plugin**:
   ```bash
   pip install niamoto-plugin-name
   ```

4. **For custom plugins**, ensure they're in `plugins/` directory and properly registered

### Memory Errors

**Problem**: `MemoryError` or process killed during transformation

**Solutions**:

1. **Process data in chunks**:
   ```yaml
   - plugin: large_dataset_processor
     params:
       chunk_size: 1000
       memory_limit: "2GB"
   ```

2. **Increase system memory** or use smaller datasets for testing

3. **Check memory usage**:
   ```bash
   niamoto transform --verbose
   # Monitor with: top or htop
   ```

### Data Type Errors

**Problem**: `ValueError: could not convert string to float`

**Solutions**:

1. **Check data types** in source files:
   ```bash
   csvstat imports/occurrences.csv
   ```

2. **Handle missing values**:
   ```yaml
   fields:
     - source: occurrences
       field: dbh
       target: diameter
       default: 0.0  # Default for missing values
   ```

3. **Data cleaning**:
   ```python
   # Clean data before import
   import pandas as pd
   df = pd.read_csv('imports/occurrences.csv')
   df['dbh'] = pd.to_numeric(df['dbh'], errors='coerce')
   df.to_csv('imports/occurrences_clean.csv', index=False)
   ```

### Transformation Configuration Errors

**Problem**: `Invalid transformation configuration`

**Diagnosis**:
```bash
# Validate configuration
niamoto transform check
```

**Solutions**:

1. **Check YAML syntax**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/transform.yml'))"
   ```

2. **Verify data source references**:
   ```yaml
   widgets_data:
     my_widget:
       plugin: field_aggregator
       params:
         source: occurrences  # Must match imported data
   ```

3. **Check field names**:
   ```bash
   # List available fields
   niamoto stats --detailed
   ```

## Export Issues

### Template Not Found

**Problem**: `TemplateNotFound: custom_template.html`

**Solutions**:

1. **Check template exists**:
   ```bash
   ls -la templates/
   ```

2. **Use default templates** (remove template specification):
   ```yaml
   static_pages:
     - name: home
       # template: "custom_home.html"  # Remove this line
       output_file: "index.html"
   ```

3. **Check template directory configuration**:
   ```yaml
   params:
     template_dir: "templates/"  # Correct path
   ```

### Widget Rendering Errors

**Problem**: `Widget failed to render` or blank widget areas

**Solutions**:

1. **Check widget data source exists**:
   ```bash
   niamoto stats --group taxon
   ```

2. **Verify widget configuration**:
   ```yaml
   widgets:
     - plugin: interactive_map
       data_source: distribution_map  # Must exist in transform.yml
   ```

3. **Check widget parameters**:
   ```yaml
   - plugin: bar_plot
     params:
       x_field: "name"      # Field must exist in data
       y_field: "count"     # Field must exist in data
   ```

4. **View detailed error logs**:
   ```bash
   niamoto export --verbose
   tail -f logs/niamoto.log
   ```

### Asset Loading Issues

**Problem**: CSS/JS files not loading, broken images

**Solutions**:

1. **Check asset paths**:
   ```yaml
   copy_assets_from:
     - "templates/assets/"  # Path relative to project root
   ```

2. **Verify files exist**:
   ```bash
   ls -la templates/assets/
   ls -la exports/web/assets/
   ```

3. **Fix relative paths** in templates:
   ```html
   <!-- Wrong -->
   <link rel="stylesheet" href="/assets/css/custom.css">

   <!-- Correct for GitHub Pages -->
   <link rel="stylesheet" href="{{ base_url }}assets/css/custom.css">
   ```

### Empty or Malformed HTML

**Problem**: Generated HTML is empty or malformed

**Solutions**:

1. **Check data availability**:
   ```bash
   niamoto stats
   ```

2. **Test with minimal configuration**:
   ```yaml
   # Minimal export.yml
   exports:
     - name: web_pages
       exporter: html_page_exporter
       params:
         output_dir: "exports/web"
         static_pages:
           - name: home
             output_file: "index.html"
   ```

3. **Validate HTML output**:
   ```bash
   html5validator exports/web/*.html
   ```

## Performance Problems

### Slow Import

**Problem**: Import takes very long time

**Solutions**:

1. **Check file sizes**:
   ```bash
   du -sh imports/*
   ```

2. **Use database optimization**:
   ```bash
   # Enable SQLite optimizations
   export NIAMOTO_SQLITE_OPTIMIZE=1
   niamoto import
   ```

3. **Process in batches**:
   ```yaml
   occurrences:
     type: csv
     path: "imports/large_file.csv"
     batch_size: 10000
   ```

### High Memory Usage

**Problem**: Process uses too much RAM

**Solutions**:

1. **Monitor memory usage**:
   ```bash
   # During niamoto run
   top -p $(pgrep niamoto)
   ```

2. **Configure memory limits**:
   ```yaml
   # In configuration
   memory_limit: "4GB"
   enable_garbage_collection: true
   ```

3. **Use streaming processing**:
   ```yaml
   processing_mode: "streaming"
   chunk_size: 1000
   ```

### Slow Website Loading

**Problem**: Generated website loads slowly

**Solutions**:

1. **Optimize images**:
   ```bash
   # Install optimization tools
   pip install Pillow
   python scripts/optimize_images.py
   ```

2. **Minimize file sizes**:
   ```bash
   # Enable compression
   gzip exports/web/*.html
   gzip exports/web/assets/css/*.css
   ```

3. **Reduce data size**:
   ```yaml
   # Limit records in exports
   filters:
     - field: "rank"
       value: "species"  # Only export species
   ```

## Deployment Issues

### GitHub Pages Build Failures

**Problem**: GitHub Actions fails to build

**Solutions**:

1. **Check Python version** in workflow:
   ```yaml
   - name: Set up Python
     uses: actions/setup-python@v4
     with:
       python-version: '3.11'  # Specify exact version
   ```

2. **Add missing dependencies**:
   ```yaml
   - name: Install system dependencies
     run: |
       sudo apt-get update
       sudo apt-get install -y gdal-bin libgdal-dev
   ```

3. **Check repository secrets** are configured

4. **Verify workflow file syntax**:
   ```bash
   # Test locally with act
   npm install -g @nektos/act
   act
   ```

### DNS and Domain Issues

**Problem**: Custom domain not working

**Solutions**:

1. **Check DNS records**:
   ```bash
   dig yourdomain.com
   nslookup yourdomain.com
   ```

2. **Verify CNAME file** (GitHub Pages):
   ```bash
   echo "yourdomain.com" > exports/web/CNAME
   ```

3. **Wait for propagation** (can take 24-48 hours)

### SSL Certificate Issues

**Problem**: HTTPS not working

**Solutions**:

1. **Enable HTTPS** in hosting platform settings
2. **Check certificate status** in platform dashboard
3. **Force HTTPS redirects**:
   ```html
   <script>
   if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
     location.replace('https:' + window.location.href.substring(window.location.protocol.length));
   }
   </script>
   ```

## Debugging Tips

### Enable Verbose Logging

```bash
# Run with detailed output
niamoto run --verbose

# Check log files
tail -f logs/niamoto.log

# Set log level
export NIAMOTO_LOG_LEVEL=DEBUG
niamoto run
```

### Check Configuration

```bash
# Validate YAML files
python -c "import yaml; print(yaml.safe_load(open('config/import.yml')))"

# Check current configuration
niamoto config show
```

### Test Components Separately

```bash
# Test each step individually
niamoto import
niamoto stats
niamoto transform --group taxon
niamoto export --target web_pages
```

### Use Development Server

```bash
# Test exported site locally
cd exports/web
python -m http.server 8000
# Visit http://localhost:8000
```

### Profile Performance

```bash
# Time each step
time niamoto import
time niamoto transform
time niamoto export

# Memory profiling (requires memory_profiler)
pip install memory_profiler
mprof run niamoto run
mprof plot
```

## Getting Help

### Check Documentation

1. [Installation Guide](../getting-started/installation.md)
2. [Data Import Guide](../guides/data-import.md)
3. [Export Guide](../guides/export-guide.md)
4. [CLI Reference](../references/cli-commands.md)

### Community Resources

1. **GitHub Issues**: [Report bugs](https://github.com/niamoto/niamoto/issues)
2. **Discussions**: [Ask questions](https://github.com/niamoto/niamoto/discussions)
3. **Documentation**: [Latest docs](https://niamoto.readthedocs.io)

### Creating Bug Reports

When reporting issues, include:

1. **Niamoto version**: `niamoto --version`
2. **Python version**: `python --version`
3. **Operating system**: `uname -a` (Linux/macOS) or Windows version
4. **Full error message** and stack trace
5. **Configuration files** (remove sensitive data)
6. **Sample data** (if possible)
7. **Steps to reproduce** the issue

### Example Bug Report

```markdown
**Niamoto Version**: 0.5.3
**Python Version**: 3.11.0
**OS**: Ubuntu 22.04

**Issue**: Import fails with coordinate error

**Error Message**:
```
ValueError: Invalid coordinates: lat=-999, lon=-999
```

**Configuration**:
```yaml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  mapping:
    geo_pt:
      x: "longitude"
      y: "latitude"
```

**Sample Data**:
```csv
id,latitude,longitude
1,-22.2764,166.4580
2,-999,-999
```

**Steps to Reproduce**:
1. Create project with `niamoto init`
2. Add sample data to imports/
3. Run `niamoto import`
```

This structured approach helps maintainers quickly understand and resolve issues.
