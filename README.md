<div align="center">
  <img src="https://raw.githubusercontent.com/niamoto/niamoto/main/assets/niamoto_logo.png" alt="Niamoto" width="180" />

  <h1>Niamoto</h1>

  <p>
    <strong>Turn ecological data into a biodiversity portal — from a native desktop app, or a Python CLI.</strong>
  </p>

  <p>
    <a href="https://pypi.org/project/niamoto"><img src="https://img.shields.io/pypi/v/niamoto?color=2563eb&style=flat-square" alt="PyPI version"></a>
    <a href="https://pypi.org/project/niamoto"><img src="https://img.shields.io/pypi/pyversions/niamoto?style=flat-square" alt="Python versions"></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/niamoto/niamoto?style=flat-square" alt="License"></a>
    <a href="https://codecov.io/gh/niamoto/niamoto"><img src="https://img.shields.io/codecov/c/github/niamoto/niamoto/main?style=flat-square" alt="Coverage"></a>
    <a href="https://niamoto.readthedocs.io"><img src="https://img.shields.io/readthedocs/niamoto/latest?style=flat-square" alt="Documentation"></a>
  </p>

  <p>
    <a href="https://github.com/niamoto/niamoto/releases/latest"><strong>Download the desktop app</strong></a>
    ·
    <a href="https://niamoto.readthedocs.io">Documentation</a>
    ·
    <a href="https://niamoto.github.io/niamoto-static-site/">Live demo</a>
  </p>
</div>

<br/>

<img src="https://raw.githubusercontent.com/niamoto/niamoto/main/assets/screenshots/hero-split.png" alt="Niamoto desktop studio and generated portal" />

## What Niamoto does

- Imports ecological data — CSVs, shapefiles, rasters — into a project.
- Detects column roles (taxonomy, occurrences, plots) with a built-in
  ML classifier, so you do not start from a blank YAML.
- Computes statistics and maps through a plugin-driven transform
  pipeline.
- Generates a static biodiversity portal, ready to publish on GitHub
  Pages, S3, or your own server.

The desktop app is the primary interface. The Python CLI covers
automation, CI, and advanced pipelines.

## Pick your path

| You are…                      | Start here                                                            |
| ----------------------------- | --------------------------------------------------------------------- |
| A researcher or botanist      | [Desktop onboarding](docs/01-getting-started/README.md)               |
| An institution or evaluator   | [User guide](docs/02-user-guide/README.md)                            |
| A developer or plugin author  | [Plugin development guide](docs/04-plugin-development/README.md)      |

## Install

### Desktop (recommended)

Signed builds for macOS, Windows, and Linux live on the
[releases page](https://github.com/niamoto/niamoto/releases/latest).

### Command line (automation, CI)

```bash
pip install niamoto
niamoto --help
```

Requires Python 3.12 or newer. See
[docs/03-cli-automation/README.md](docs/03-cli-automation/README.md)
for scripting recipes.

## A glance at the studio

The desktop reads your raw files, suggests a configuration, previews
each widget, and lets you publish when you are ready:

<img src="https://raw.githubusercontent.com/niamoto/niamoto/main/docs/plans/caps/11.import-config-detected.png" alt="Niamoto import screen with ML auto-detected column roles" />

The full walk-through lives in
[docs/02-user-guide/](docs/02-user-guide/). A video tour will land in
this README shortly — in the meantime,
[the live demo](https://niamoto.github.io/niamoto-static-site/) shows
what the generated portal looks like.

## Resources

- **Documentation** — [niamoto.readthedocs.io](https://niamoto.readthedocs.io)
- **Live demo** — [New Caledonia forests portal](https://niamoto.github.io/niamoto-static-site/)
- **Discussions** — [GitHub Discussions](https://github.com/niamoto/niamoto/discussions)
- **Issues** — [GitHub Issues](https://github.com/niamoto/niamoto/issues)
- **Changelog** — [CHANGELOG.md](CHANGELOG.md)
- **Contributing** — [CONTRIBUTING.md](CONTRIBUTING.md) · [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md)

## License

`niamoto` is distributed under
[GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html).
