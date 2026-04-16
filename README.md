<div align="center">
  <img src="https://raw.githubusercontent.com/niamoto/niamoto/main/assets/niamoto_logo.png" alt="Niamoto Logo" width="200"/>

  <h1>Niamoto</h1>

  <p>
    <strong>A powerful CLI tool for ecological data management and visualization</strong>
  </p>

  <p>
    Transform your ecological data into interactive websites with taxonomic analysis,
    statistical insights, and beautiful visualizations.
  </p>

  [![PyPI - Version](https://img.shields.io/pypi/v/niamoto?color=blue&style=for-the-badge)](https://pypi.org/project/niamoto)
  [![Python Versions](https://img.shields.io/pypi/pyversions/niamoto?style=for-the-badge)](https://pypi.org/project/niamoto)
  [![License](https://img.shields.io/github/license/niamoto/niamoto?style=for-the-badge)](LICENSE)
  [![Codecov (with branch)](https://img.shields.io/codecov/c/github/niamoto/niamoto/main?style=for-the-badge)](https://codecov.io/gh/niamoto/niamoto)
  [![Read the Docs (version)](https://img.shields.io/readthedocs/niamoto/latest?style=for-the-badge)](https://niamoto.readthedocs.io/)

  [🔗 **View Live Demo**](https://niamoto.github.io/niamoto-static-site/) | [📖 **Browse Documentation**](https://niamoto.readthedocs.io/)
</div>

## 🚀 Quick Start

```bash
# Install Niamoto
pip install niamoto

# Initialize your project
niamoto init

# Import your data
niamoto import

# Generate statistics
niamoto transform

# Create your website
niamoto export
```

**✨ That's it!** Your ecological data website is ready at `exports/web/`.

## 🖼️ Screenshots

### Taxonomic Index Page
![Taxonomic Index](https://raw.githubusercontent.com/niamoto/niamoto/main/assets/screenshots/taxon-index.png)
*Browse and search through your taxonomic data with interactive filters*

### Taxon Detail Page
![Taxon Detail](https://raw.githubusercontent.com/niamoto/niamoto/main/assets/screenshots/taxon-detail.png)
*Detailed view with statistics, distributions, and interactive visualizations*

## ✨ Features

- 🌿 **Ecological Data Management** - Import and manage taxonomic, occurrence, and plot data
- 📊 **Statistical Analysis** - Built-in plugins for distributions, rankings, and summaries
- 🗺️ **Geospatial Analysis** - Interactive maps and spatial statistics
- 📈 **Data Visualization** - Charts, maps, and dashboards with Plotly
- 🏗️ **Plugin System** - Extensible architecture for custom transformations and generations
- 🌐 **Static Site Generation** - Generate fast, SEO-friendly websites
- ⚡ **CLI Interface** - Simple commands for the entire workflow
- 🔧 **Configuration-Driven** - YAML-based configuration for reproducibility

## 🎯 Use Cases

Niamoto is perfect for:

- **Research Institutions** - Manage biodiversity databases and generate research websites
- **Conservation Organizations** - Track species distributions and create public dashboards
- **Botanical Gardens** - Document collections and share taxonomic information
- **Environmental Consultants** - Analyze ecological data and create client reports
- **Government Agencies** - Monitor biodiversity and publish open data portals

---

## 📖 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🖼️ Screenshots](#️-screenshots)
  - [Taxonomic Index Page](#taxonomic-index-page)
  - [Taxon Detail Page](#taxon-detail-page)
- [✨ Features](#-features)
- [🎯 Use Cases](#-use-cases)
- [📖 Table of Contents](#-table-of-contents)
- [📦 Installation](#-installation)
  - [For Users](#for-users)
  - [For Developers](#for-developers)
- [🏃‍♂️ Usage](#️-usage)
  - [Initial Setup](#initial-setup)
  - [Data Import](#data-import)
  - [Generate Statistics and Website](#generate-statistics-and-website)
- [📂 Project Structure](#-project-structure)
- [🔧 Configuration](#-configuration)
- [🧩 Plugin System](#-plugin-system)
- [👩‍💻 Development](#-development)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [❓ FAQ](#-faq)
- [🤝 Community \& Support](#-community--support)
- [📅 Changelog](#-changelog)

## 📦 Installation

### For Users
```bash
pip install niamoto
```

### For Developers
```bash
# Clone and setup development environment
git clone https://github.com/niamoto/niamoto.git
cd niamoto
uv venv && source .venv/bin/activate
uv sync --group dev
```

📋 **[Detailed Installation Guide](docs/01-getting-started/installation.md)**

## 🏃‍♂️ Usage

### Initial Setup

```bash
# Initialize your project
niamoto init

# This creates the default configuration files:
# - config/config.yml     (global settings)
# - config/import.yml     (data sources)
# - config/transform.yml  (data processing)
# - config/export.yml     (website generation)
```

### Data Import

```bash
# Import all data sources from import.yml
niamoto import

# Or import specific data types
niamoto import taxonomy <file>
niamoto import occurrences <file>
niamoto import plots <file>
```

### Generate Statistics and Website

```bash
# Process data transformations
niamoto transform

# Generate static website
niamoto export

# Your website is ready at exports/web/
```

📖 **[Complete CLI Reference](docs/05-api-reference/cli-commands.md)** | **[Data Import Guide](docs/02-data-pipeline/import-configuration.md)**

## 📂 Project Structure

```bash
config/          - YAML configuration files for data pipeline:
  config.yml     - Global configuration options
  import.yml     - Data import configuration
  transform.yml  - Data transformation configuration
  export.yml     - Widget and chart configurations

db/              - Database files and schemas
exports/         - Generated widget data and statistics
imports/         - Raw data files (CSV, shapefiles, rasters)
logs/            - Application logs and debug information
plugins/         - Custom plugin directory for extending functionality
templates/       - Custom Jinja2 templates for website generation
```

## 🔧 Configuration

Niamoto uses YAML configuration files to define your data pipeline:

- `config/import.yml` - Data sources (CSV, GIS files)
- `config/transform.yml` - Data processing and statistics
- `config/export.yml` - Website generation and visualizations

📖 **[Complete Configuration Guide](docs/08-configuration/configuration-guide.md)** | **[Data Import Guide](docs/02-data-pipeline/import-configuration.md)**

## 🧩 Plugin System

Niamoto includes built-in plugins for data transformation and visualization, with support for custom plugins.

📖 **[Plugin Development Guide](docs/04-plugin-development/creating-transformers.md)** | **[Plugin API Reference](docs/05-api-reference/plugin-api.md)**

## 👩‍💻 Development

For development setup, testing, and contribution guidelines:

📖 **[Development Setup Guide](docs/11-development/setup.md)** | **[Contributing Guidelines](CONTRIBUTING.md)**

## 📚 Documentation

The complete documentation is available in the `docs/` directory and online:

- 📖 **[Online Documentation](https://niamoto.readthedocs.io/)**
- 🚀 **[Getting Started Guide](docs/01-getting-started/quickstart.md)**
- 📋 **[Configuration Guide](docs/08-configuration/configuration-guide.md)**
- 🧩 **[Plugin Development](docs/04-plugin-development/)**
- 📖 **[API Reference](docs/05-api-reference/)**
- 🤖 **[ML Detection System](docs/03-ml-detection/)**
- 📊 **[Data Pipeline](docs/02-data-pipeline/)**

To build the documentation locally:

```bash
cd docs
sphinx-apidoc -o . ../src/niamoto
make html
```

## 🤝 Contributing

We welcome contributions to Niamoto! Here's how you can help:

1. Check for open issues or open a new issue to start a discussion
2. Fork the repository and create your feature branch
3. Write tests for new features and ensure existing tests pass
4. Follow our coding standards (Black formatting, type hints, docstrings)
5. Submit a pull request

📖 **[Contributing Guide](CONTRIBUTING.md)**

## 📄 License

`niamoto` is distributed under the terms of the [GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html) license.

## ❓ FAQ

<details>
<summary><strong>What data formats does Niamoto support?</strong></summary>

Niamoto supports CSV files for taxonomic and occurrence data, and common GIS formats (Shapefile, GeoPackage, GeoTIFF) for spatial data.
</details>

<details>
<summary><strong>Can I customize the generated website?</strong></summary>

Yes! Niamoto uses Jinja2 templates and supports custom CSS. You can completely customize the look and feel of your website.
</details>

<details>
<summary><strong>How do I add custom data transformations?</strong></summary>

You can create custom plugins by extending the base plugin classes. See our [Plugin Development Guide](docs/04-plugin-development/creating-transformers.md).
</details>

<details>
<summary><strong>Is Niamoto suitable for large datasets?</strong></summary>

Yes! Niamoto uses SQLite with spatial extensions and is optimized for performance. It can handle datasets with millions of records efficiently.
</details>

## 🤝 Community & Support

- 💬 **Discussions** - [GitHub Discussions](https://github.com/niamoto/niamoto/discussions)
- 🐛 **Bug Reports** - [GitHub Issues](https://github.com/niamoto/niamoto/issues)
- 📖 **Documentation** - [niamoto.readthedocs.io](https://niamoto.readthedocs.io/)
- 🔗 **Live Demo** - [niamoto.github.io/niamoto-static-site](https://niamoto.github.io/niamoto-static-site/)

## 📅 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each release.
