# Installation

Niamoto gives you two entry points: a desktop app and a Python CLI.
Install the desktop app unless you need automation, CI, or server runs.

## Desktop app (recommended)

Signed builds for macOS, Windows, and Linux live on the
[releases page](https://github.com/niamoto/niamoto/releases/latest).

| Platform         | Artifact                         |
| ---------------- | -------------------------------- |
| macOS (arm64)    | `Niamoto_*_aarch64.dmg`          |
| macOS (x86_64)   | `Niamoto_*_x64.dmg`              |
| Windows (x86_64) | `Niamoto_*_x64_en-US.msi`        |
| Debian / Ubuntu  | `niamoto_*_amd64.deb`            |
| Linux (generic)  | `niamoto_*_amd64.AppImage`       |

### macOS notes

- On the first launch, right-click the `.dmg` or the `.app` and choose
  *Open* to clear Gatekeeper. Later launches go through normally.
- If macOS still blocks the app, open
  *System Settings → Privacy & Security* and click *Open Anyway*.

### Windows notes

- The `.msi` installs for the current user. No admin rights needed.
- WebView2 is bundled; Windows 10 and later include what the app needs.

### Linux notes

- `.deb` works on Debian, Ubuntu, Linux Mint, and derivatives.
- `.AppImage` runs on most distributions without an installer:

  ```bash
  chmod +x niamoto_*_amd64.AppImage
  ./niamoto_*_amd64.AppImage
  ```

## Python CLI (automation, CI)

The CLI runs the same pipeline as the desktop app, without the UI.
It requires Python 3.12 or newer.

### With uv (recommended)

[uv](https://github.com/astral-sh/uv) installs and runs Python tools.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

uv pip install niamoto
niamoto --version
```

### With pip

```bash
pip install niamoto
niamoto --version
```

### Development install

```bash
git clone https://github.com/niamoto/niamoto.git
cd niamoto
uv sync --group dev
```

Add `--extra docs` if you also build the Sphinx docs locally.

## Geospatial dependencies (CLI only)

Niamoto reads shapefiles, GeoPackages, and rasters through GDAL. The desktop app
bundles what it needs. The CLI uses the GDAL libraries on your machine.

### macOS

```bash
brew install gdal
gdalinfo --version
```

### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y \
  gdal-bin libgdal-dev python3-gdal libspatialite-dev
gdalinfo --version
```

### Windows

Install [OSGeo4W](https://trac.osgeo.org/osgeo4w/) and add the GDAL
binary directory to your `PATH`.

## Verify the install

### Desktop app

Launch Niamoto from your Applications / Start menu / launcher. The
welcome screen should appear within a few seconds. If it stalls, see
[../09-troubleshooting/README.md](../09-troubleshooting/README.md).

### CLI

```bash
niamoto --help
```

You should see commands such as `init`, `import`, `transform`, `export`, `run`,
`stats`, `deploy`, and `plugins`.

## Next steps

- Open the desktop app and follow [first-project.md](first-project.md).
- If you installed the CLI, read [quickstart.md](quickstart.md).

## Troubleshooting

- **`command not found: niamoto`**: `~/.local/bin` or the Windows Scripts
  folder is not on `PATH`. Add it, or run
  `python -m niamoto --help`.
- **`No module named 'osgeo'`**: install the system GDAL first, then
  `pip install GDAL==$(gdal-config --version)`.
- Full list: [../09-troubleshooting/README.md](../09-troubleshooting/README.md).
