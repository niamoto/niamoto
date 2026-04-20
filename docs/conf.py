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
copyright = "2025-2026, Julien Barbe"
author = "Julien Barbe"
release = "0.15.5"

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
suppress_warnings = [
    "autodoc.import_object",
    "misc.highlighting_failure",
]

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
    "superpowers/**",
    "gbif-challenge-2026.html",
    "assets/about/README-about.en.md",
]


# -- Redirects for renamed pages ---------------------------------------------
# Public redirects only target pages that exist in the live site.
# Never redirect to _archive/** (archive is not a navigation destination).
redirects = {
    # 02-user-guide renamed pages
    "02-user-guide/transform": "collections.html",
    "02-user-guide/export": "publish.html",
    # 02-data-pipeline -> 02-user-guide
    "02-data-pipeline/index": "../02-user-guide/README.html",
    "02-data-pipeline/README": "../02-user-guide/README.html",
    "02-data-pipeline/import-configuration": "../02-user-guide/import.html",
    "02-data-pipeline/transform-pipeline": "../02-user-guide/collections.html",
    "02-data-pipeline/export-process": "../02-user-guide/publish.html",
    "02-data-pipeline/data-preparation": "../02-user-guide/import.html",
    "02-data-pipeline/widget-system": "../02-user-guide/widget-catalogue.html",
    # 05-api-reference -> 06-reference.
    "05-api-reference/index": "../06-reference/README.html",
    "05-api-reference/README": "../06-reference/README.html",
    "05-api-reference/cli-commands": "../06-reference/cli-commands.html",
    "05-api-reference/core-api": "../06-reference/core-api.html",
    "05-api-reference/database-schema": "../06-reference/database-schema.html",
    "05-api-reference/plugin-api": "../06-reference/plugin-api.html",
    "05-api-reference/external-apis": "../06-reference/external-apis.html",
    "05-api-reference/api-export-guide": "../06-reference/api-export-guide.html",
    # 09-architecture -> 07-architecture
    "09-architecture/index": "../07-architecture/README.html",
    "09-architecture/README": "../07-architecture/README.html",
    "09-architecture/corrections-roadmap": "../08-roadmaps/README.html",
    "09-architecture/gui-overview": "../07-architecture/gui-overview.html",
    "09-architecture/gui-preview-system": "../07-architecture/gui-preview-system.html",
    "09-architecture/gui-runtime": "../07-architecture/gui-runtime.html",
    "09-architecture/pipeline-unified": "../08-roadmaps/README.html",
    "09-architecture/plugin-improvement": "../08-roadmaps/README.html",
    "09-architecture/plugin-system": "../07-architecture/plugin-system.html",
    "09-architecture/system-overview": "../07-architecture/system-overview.html",
    "09-architecture/target-architecture-2026": "../08-roadmaps/README.html",
    "09-architecture/target-architecture-2026-comex-cto": "../08-roadmaps/README.html",
    "09-architecture/target-architecture-2026-execution-plan": "../08-roadmaps/README.html",
    "09-architecture/technical-analysis": "../08-roadmaps/README.html",
    # 07-architecture pages that were reclassified as roadmaps/plans
    "07-architecture/pipeline-unified": "../08-roadmaps/README.html",
    "07-architecture/corrections-roadmap": "../08-roadmaps/README.html",
    "07-architecture/plugin-improvement": "../08-roadmaps/README.html",
    "07-architecture/target-architecture-2026": "../08-roadmaps/README.html",
    "07-architecture/target-architecture-2026-comex-cto": "../08-roadmaps/README.html",
    "07-architecture/target-architecture-2026-execution-plan": "../08-roadmaps/README.html",
    "07-architecture/technical-analysis": "../08-roadmaps/README.html",
    "09-architecture/adr/0001-adopt-duckdb": "../../07-architecture/adr/0001-adopt-duckdb.html",
    "09-architecture/adr/0002-retire-legacy-importers": "../../07-architecture/adr/0002-retire-legacy-importers.html",
    "09-architecture/adr/0003-derived-references-with-duckdb": "../../07-architecture/adr/0003-derived-references-with-duckdb.html",
    "09-architecture/adr/0004-generic-import-system": "../../07-architecture/adr/0004-generic-import-system.html",
    # 10-roadmaps -> 08-roadmaps
    "10-roadmaps/index": "../08-roadmaps/README.html",
    "10-roadmaps/README": "../08-roadmaps/README.html",
    "10-roadmaps/auto-detection-mvp": "../08-roadmaps/README.html",
    "10-roadmaps/error-handling": "../08-roadmaps/README.html",
    "10-roadmaps/pattern-matching-implementation-summary": "../08-roadmaps/README.html",
    "10-roadmaps/gui-finalization/00-overview": "../../08-roadmaps/README.html",
    "10-roadmaps/gui-finalization/01-phase-import": "../../08-roadmaps/README.html",
    "10-roadmaps/gui-finalization/02-phase-transform-export": "../../08-roadmaps/README.html",
    "10-roadmaps/gui/ARCHITECTURE_MULTI_PROJETS": "../../08-roadmaps/README.html",
    "10-roadmaps/gui/BINARY_DISTRIBUTION": "../../08-roadmaps/README.html",
    "10-roadmaps/gui/DESKTOP_APP": "../../08-roadmaps/README.html",
    "10-roadmaps/gui/PLUGINS_WITH_BINARY": "../../08-roadmaps/README.html",
    "10-roadmaps/gui/fastapi-dual-purpose-architecture": "../../07-architecture/gui-runtime.html",
    "10-roadmaps/gui/operations/export": "../../../02-user-guide/publish.html",
    "10-roadmaps/gui/operations/import": "../../../02-user-guide/import.html",
    "10-roadmaps/gui/operations/transform": "../../../02-user-guide/collections.html",
    # retired 08-roadmaps pages now redirect to section landing pages or current docs
    "08-roadmaps/pattern-matching-implementation-summary": "../08-roadmaps/README.html",
    "08-roadmaps/pipeline-unified": "../08-roadmaps/README.html",
    "08-roadmaps/corrections-roadmap": "../08-roadmaps/README.html",
    "08-roadmaps/plugin-improvement": "../08-roadmaps/README.html",
    "08-roadmaps/technical-analysis": "../08-roadmaps/README.html",
    "08-roadmaps/gui/fastapi-dual-purpose-architecture": "../../07-architecture/gui-runtime.html",
    "08-roadmaps/gui/operations/import": "../../02-user-guide/import.html",
    "08-roadmaps/gui/operations/transform": "../../02-user-guide/collections.html",
    "08-roadmaps/gui/operations/export": "../../02-user-guide/publish.html",
    # 99-troubleshooting -> 09-troubleshooting
    "99-troubleshooting/index": "../09-troubleshooting/README.html",
    "99-troubleshooting/README": "../09-troubleshooting/README.html",
    "99-troubleshooting/common-issues": "../09-troubleshooting/common-issues.html",
    "99-troubleshooting/desktop-smoke-tests": "../09-troubleshooting/desktop-smoke-tests.html",
    # 06-gui -> split across 02-user-guide, 06-reference, 07-architecture,
    # 09-troubleshooting (see docs/plans/2026-04-17-refactor-documentation-desktop-first-plan.md).
    "06-gui/index": "../02-user-guide/README.html",
    "06-gui/README": "../02-user-guide/README.html",
    "06-gui/operations/import": "../../02-user-guide/import.html",
    "06-gui/operations/transform": "../../02-user-guide/collections.html",
    "06-gui/operations/export": "../../02-user-guide/publish.html",
    "06-gui/operations/desktop-smoke-tests": "../../09-troubleshooting/desktop-smoke-tests.html",
    "06-gui/architecture/overview": "../../07-architecture/gui-overview.html",
    "06-gui/architecture/backend-frontend-runtime": "../../07-architecture/gui-runtime.html",
    "06-gui/architecture/preview-system": "../../07-architecture/gui-preview-system.html",
    "06-gui/reference/preview-api": "../../06-reference/gui-preview-api.html",
    "06-gui/reference/transform-plugins": "../../06-reference/transform-plugins.html",
    "06-gui/reference/widgets-and-transform-workflow": "../../06-reference/widgets-and-transform-workflow.html",
    # 08-configuration -> 06-reference
    "08-configuration/index": "../06-reference/configuration-guide.html",
    "08-configuration/README": "../06-reference/configuration-guide.html",
    "08-configuration/configuration-guide": "../06-reference/configuration-guide.html",
    "08-configuration/configuration-analysis": "../06-reference/configuration-analysis.html",
    "08-configuration/yaml-strategies": "../06-reference/yaml-strategies.html",
    "08-configuration/templates-hierarchy": "../06-reference/templates-hierarchy.html",
    # 11-development -> CONTRIBUTING (at repo root, linked from docs)
    "11-development/index": "../README.html",
    "11-development/README": "../README.html",
    "11-development/setup": "../README.html",
    "11-development/commands": "../README.html",
    "11-development/contributing": "../README.html",
    "11-development/deployment": "../README.html",
    "11-development/testing": "../README.html",
    # 12-troubleshooting -> 09-troubleshooting
    "12-troubleshooting/index": "../09-troubleshooting/README.html",
    "12-troubleshooting/README": "../09-troubleshooting/README.html",
    "12-troubleshooting/common-issues": "../09-troubleshooting/common-issues.html",
    # 07-tutorials was archived; land on the user guide index until
    # tutorial pages are rewritten under 02-user-guide/tutorials/.
    "07-tutorials/index": "../02-user-guide/README.html",
    "07-tutorials/README": "../02-user-guide/README.html",
    "07-tutorials/biodiversity-site": "../02-user-guide/README.html",
    "07-tutorials/forest-plot-analysis": "../02-user-guide/README.html",
    "07-tutorials/ml-training-example": "../05-ml-detection/README.html",
    # 03-ml-detection became 05-ml-detection (the former slot is now
    # 03-cli-automation).
    "03-ml-detection/index": "../05-ml-detection/README.html",
    "03-ml-detection/README": "../05-ml-detection/README.html",
    # Autogenerated API now lives under 06-reference/api
    "modules": "06-reference/api/modules.html",
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
