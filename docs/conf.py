# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))
sys.path.insert(0, os.path.abspath("_ext"))


project = "niamoto"
copyright = "2025, Julien Barbe"
author = "Julien Barbe"
release = "0.15.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.extlinks",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
    "sphinx_markdown_builder",
    "mermaid",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx_reredirects",
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# Configuration pour myst_parser
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
myst_heading_anchors = 5
myst_fence_as_directive = ["mermaid"]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "_archive/**",
    "plans/**",
    "brainstorms/**",
    "ideation/**",
]


# -- Redirects for renamed pages ---------------------------------------------
# Public redirects only target pages that exist in the live site.
# Never redirect to _archive/** (archive is not a navigation destination).
redirects = {
    # 02-data-pipeline -> 02-user-guide
    "02-data-pipeline/index": "../02-user-guide/README.html",
    "02-data-pipeline/README": "../02-user-guide/README.html",
    "02-data-pipeline/import-configuration": "../02-user-guide/import.html",
    "02-data-pipeline/transform-pipeline": "../02-user-guide/transform.html",
    "02-data-pipeline/export-process": "../02-user-guide/export.html",
    "02-data-pipeline/data-preparation": "../02-user-guide/import.html",
    "02-data-pipeline/widget-system": "../02-user-guide/transform.html",
    # 05-api-reference -> 06-reference
    "05-api-reference/index": "../06-reference/README.html",
    "05-api-reference/README": "../06-reference/README.html",
    "05-api-reference/cli-commands": "../06-reference/cli-commands.html",
    "05-api-reference/core-api": "../06-reference/core-api.html",
    "05-api-reference/database-schema": "../06-reference/database-schema.html",
    "05-api-reference/plugin-api": "../06-reference/plugin-api.html",
    "05-api-reference/external-apis": "../06-reference/external-apis.html",
    "05-api-reference/api-export-guide": "../06-reference/api-export-guide.html",
    # 06-gui -> split across 02-user-guide, 06-reference, 09-architecture,
    # 99-troubleshooting (see docs/plans/2026-04-17-refactor-documentation-desktop-first-plan.md).
    "06-gui/index": "../02-user-guide/README.html",
    "06-gui/README": "../02-user-guide/README.html",
    "06-gui/operations/import": "../../02-user-guide/import.html",
    "06-gui/operations/transform": "../../02-user-guide/transform.html",
    "06-gui/operations/export": "../../02-user-guide/export.html",
    "06-gui/operations/desktop-smoke-tests": "../../99-troubleshooting/desktop-smoke-tests.html",
    "06-gui/architecture/overview": "../../09-architecture/gui-overview.html",
    "06-gui/architecture/backend-frontend-runtime": "../../09-architecture/gui-runtime.html",
    "06-gui/architecture/preview-system": "../../09-architecture/gui-preview-system.html",
    "06-gui/reference/preview-api": "../../06-reference/gui-preview-api.html",
    "06-gui/reference/transform-plugins": "../../06-reference/transform-plugins.html",
    "06-gui/reference/widgets-and-transform-workflow": "../../06-reference/widgets-and-transform-workflow.html",
    # 08-configuration -> 06-reference
    "08-configuration/index": "../06-reference/README.html",
    "08-configuration/README": "../06-reference/README.html",
    "08-configuration/configuration-guide": "../06-reference/README.html",
    "08-configuration/configuration-analysis": "../06-reference/README.html",
    "08-configuration/yaml-strategies": "../06-reference/README.html",
    "08-configuration/templates-hierarchy": "../06-reference/README.html",
    # 11-development -> CONTRIBUTING (at repo root, linked from docs)
    "11-development/index": "../README.html",
    "11-development/README": "../README.html",
    "11-development/setup": "../README.html",
    "11-development/commands": "../README.html",
    "11-development/contributing": "../README.html",
    "11-development/deployment": "../README.html",
    "11-development/testing": "../README.html",
    # 12-troubleshooting -> 99-troubleshooting
    "12-troubleshooting/index": "../99-troubleshooting/README.html",
    "12-troubleshooting/README": "../99-troubleshooting/README.html",
    "12-troubleshooting/common-issues": "../99-troubleshooting/common-issues.html",
    # Autogenerated API now lives under 06-reference/api
    "modules": "06-reference/api/modules.html",
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
