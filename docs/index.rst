.. Niamoto documentation master file, created by
   sphinx-quickstart on Mon Nov  6 23:50:41 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Niamoto Documentation
====================

Niamoto is an ecological data platform for creating biodiversity web portals.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   getting-started/installation
   getting-started/quickstart
   getting-started/concepts

.. toctree::
   :maxdepth: 2
   :caption: Practical Guides
   :hidden:

   guides/configuration
   guides/data-import
   guides/data-preparation
   guides/transform_chain_guide
   guides/database-aggregation-plugin
   guides/custom_plugin
   guides/plugin_reference
   guides/api_taxonomy_enricher
   guides/export-guide
   guides/deployment

.. toctree::
   :maxdepth: 2
   :caption: Tutorials
   :hidden:

   tutorials/biodiversity-site
   tutorials/forest-plots
   tutorials/external-data

.. toctree::
   :maxdepth: 2
   :caption: References
   :hidden:

   references/plugin-system-overview
   references/database-schema
   references/pipeline-architecture
   references/cli-commands
   references/yaml-reference

.. toctree::
   :maxdepth: 2
   :caption: Development
   :hidden:

   development/contributing
   development/widget-development

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics
   :hidden:

   advanced/optimization
   advanced/gis-integration

.. toctree::
   :maxdepth: 2
   :caption: Support
   :hidden:

   troubleshooting/common-issues
   faq/general
   resources/glossary
   resources/links

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:

   api/modules

.. toctree::
   :maxdepth: 1
   :caption: Meta
   :hidden:

   DOCUMENTATION_INDEX
   DOCUMENTATION_STRUCTURE
   migration/migration-guide

Quick Start
-----------

1. **Installation**: :doc:`getting-started/installation`

   .. code-block:: bash

      pip install niamoto

2. **First Project**: :doc:`getting-started/quickstart`

   .. code-block:: bash

      niamoto init
      niamoto run

3. **Key Concepts**: :doc:`getting-started/concepts`

Main Resources
--------------

* **Configuration**: :doc:`guides/configuration` - Master YAML files
* **Plugins**: :doc:`guides/custom_plugin` - Create your own plugins
* **Widgets**: :doc:`guides/plugin_reference` - Available visualizations
* **Deployment**: :doc:`guides/deployment` - Publish your site

Getting Help
------------

* `GitHub Issues <https://github.com/niamoto/niamoto/issues>`_
* `Discussions <https://github.com/niamoto/niamoto/discussions>`_
* :doc:`faq/general`

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
