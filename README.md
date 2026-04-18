<div align="center">
  <img src="https://raw.githubusercontent.com/niamoto/niamoto/main/assets/niamoto_logo.png" alt="Niamoto" width="180" />

  <h1>Niamoto</h1>

  <p>
    <strong>Turn ecological data into a biodiversity portal from a native desktop app or a Python CLI.</strong>
  </p>

  <p>
    <a href="https://pypi.org/project/niamoto"><img src="https://img.shields.io/pypi/v/niamoto?color=2563eb&style=flat-square" alt="PyPI version"></a>
    <a href="https://pypi.org/project/niamoto"><img src="https://img.shields.io/pypi/pyversions/niamoto?style=flat-square" alt="Python versions"></a>
    <a href="https://github.com/niamoto/niamoto/blob/main/LICENSE"><img src="https://img.shields.io/github/license/niamoto/niamoto?style=flat-square" alt="License"></a>
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

- Import ecological tables, layers, and rasters into one project.
- Suggest file and column roles, so you can start from a working configuration.
- Build collections, widgets, statistics, and maps from that data.
- Publish a static biodiversity portal to GitHub Pages, Cloudflare Workers,
  Netlify, Vercel, Render, or your own server over SSH.

The desktop app is the main interface. The Python CLI handles automation, CI,
and repeatable runs.

## Pick your path

| You are…         | Start here                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| A researcher      | [Desktop onboarding](https://niamoto.readthedocs.io/en/latest/01-getting-started/README.html)         |
| A project lead    | [User guide](https://niamoto.readthedocs.io/en/latest/02-user-guide/README.html)                      |
| A developer       | [Plugin development guide](https://niamoto.readthedocs.io/en/latest/04-plugin-development/README.html) |

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
[CLI & automation docs](https://niamoto.readthedocs.io/en/latest/03-cli-automation/README.html)
for scripting recipes.

## Quick start

### Desktop path

1. Download the latest desktop build from the
   [releases page](https://github.com/niamoto/niamoto/releases/latest).
2. Grab a sample dataset from
   [niamoto-example-data](https://github.com/niamoto/niamoto-example-data) or
   open your own CSVs, layers, and rasters.
3. Continue with
   [Desktop onboarding](https://niamoto.readthedocs.io/en/latest/01-getting-started/README.html)
   and then the
   [Desktop App Tour](https://niamoto.readthedocs.io/en/latest/02-user-guide/README.html).

### CLI path

1. Install the package with `pip install niamoto`.
2. Run `niamoto --help`.
3. Follow the
   [CLI & automation docs](https://niamoto.readthedocs.io/en/latest/03-cli-automation/README.html)
   for project init, scripted runs, and CI.

## A glance at the studio

The desktop app reads your raw files, suggests a configuration, previews each
widget, and lets you publish the result:

<img src="https://raw.githubusercontent.com/niamoto/niamoto/main/docs/assets/screenshots/desktop/11.import-config-detected.png" alt="Niamoto import screen with ML auto-detected column roles" />

The full walk-through lives in the
[Desktop App Tour](https://niamoto.readthedocs.io/en/latest/02-user-guide/README.html).
If you want to see the generated result first,
[the live demo](https://niamoto.github.io/niamoto-static-site/) shows what the
published portal looks like.

## Resources

- **Documentation** — [niamoto.readthedocs.io](https://niamoto.readthedocs.io)
- **Live demo** — [New Caledonia forests portal](https://niamoto.github.io/niamoto-static-site/)
- **Discussions** — [GitHub Discussions](https://github.com/niamoto/niamoto/discussions)
- **Issues** — [GitHub Issues](https://github.com/niamoto/niamoto/issues)
- **Changelog** — [CHANGELOG.md](https://github.com/niamoto/niamoto/blob/main/CHANGELOG.md)
- **Contributing** — [CONTRIBUTING.md](https://github.com/niamoto/niamoto/blob/main/CONTRIBUTING.md) · [STYLE_GUIDE.md](https://github.com/niamoto/niamoto/blob/main/docs/STYLE_GUIDE.md)

<!-- about:start -->

## About Niamoto

Niamoto is developed by a small interdisciplinary team and supported by institutional partners committed to biodiversity conservation.

### Niamoteam

Open-source collaborative project for biodiversity conservation.

- **Philippe Birnbaum** — CIRAD · UMR AMAP
- **Dimitri Justeau-Allaire** — IRD · UMR AMAP
- **Gilles Dauby** — IRD · UMR AMAP
- **Julien Barbe** — Developer

### Partners & funders

Niamoto was developed within the ADMIRE research project ("Partnership for the Analysis of Reforestation Dynamics and Forest Resilience"), established by Province Nord, IAC, and Cirad. The project develops software that supports decision-making for the management of natural areas in Province Nord, New Caledonia.

<p align="center">
  <a href="https://www.province-nord.nc/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/pn_100.png" alt="Province Nord" height="52" /></a>
  <a href="https://www.province-sud.nc/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/ps_100.png" alt="Province Sud" height="52" /></a>
  <a href="https://endemia.nc/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/endemia_100.png" alt="Endemia" height="52" /></a>
  <a href="https://amap.cirad.fr/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/amap_100.png" alt="UMR AMAP" height="52" /></a>
  <a href="http://publish.plantnet-project.org/project/nou"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/herbarium_100.png" alt="Herbarium" height="52" /></a>
  <a href="https://iac.nc/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/iac_100.png" alt="IAC" height="52" /></a>
  <a href="https://nouvelle-caledonie.ird.fr/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/ird_100.png" alt="IRD" height="52" /></a>
  <a href="https://cirad.fr/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/cirad_100.png" alt="Cirad" height="52" /></a>
  <a href="https://www.ofb.gouv.fr/"><img src="https://raw.githubusercontent.com/niamoto/niamoto/HEAD/docs/assets/funders/ofb_100.png" alt="OFB" height="52" /></a>
</p>

<p align="center"><sub><a href="https://www.province-nord.nc/">Province Nord</a> · <a href="https://www.province-sud.nc/">Province Sud</a> · <a href="https://endemia.nc/">Endemia</a> · <a href="https://amap.cirad.fr/">UMR AMAP</a> · <a href="http://publish.plantnet-project.org/project/nou">Herbarium</a> · <a href="https://iac.nc/">IAC</a> · <a href="https://nouvelle-caledonie.ird.fr/">IRD</a> · <a href="https://cirad.fr/">Cirad</a> · <a href="https://www.ofb.gouv.fr/">OFB</a></sub></p>

<!-- about:end -->

## License

`niamoto` is distributed under
[GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html).
