.. Niamoto documentation master file, created by
   sphinx-quickstart on Mon Nov  6 23:50:41 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Niamoto Documentation
=======================

Niamoto is an ecological data platform for creating biodiversity web portals.

.. toctree::
   :maxdepth: 1
   :caption: Overview
   :hidden:

   README

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Getting Started
   :hidden:

   01-getting-started/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Data Pipeline
   :hidden:

   02-data-pipeline/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: ML Detection
   :hidden:

   03-ml-detection/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Plugin Development
   :hidden:

   04-plugin-development/*
   04-plugin-development/*/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: API Reference
   :hidden:

   05-api-reference/*
   modules

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: GUI
   :hidden:

   06-gui/*
   06-gui/*/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Tutorials
   :hidden:

   07-tutorials/*
   07-tutorials/*/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Configuration
   :hidden:

   08-configuration/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Architecture
   :hidden:

   09-architecture/*
   09-architecture/*/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Roadmaps
   :hidden:

   10-roadmaps/*
   10-roadmaps/*/*
   10-roadmaps/*/*/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Development
   :hidden:

   11-development/*

.. toctree::
   :maxdepth: 2
   :glob:
   :caption: Troubleshooting
   :hidden:

   12-troubleshooting/*

Quick Start
-----------

1. **Installation**: :doc:`01-getting-started/installation`

   .. code-block:: bash

      pip install niamoto

2. **First Project**: :doc:`01-getting-started/quickstart`

   .. code-block:: bash

      niamoto init
      niamoto run

3. **Key Concepts**: :doc:`01-getting-started/concepts`

Main Resources
--------------

* **Configuration**: :doc:`08-configuration/configuration-guide` - Master YAML files
* **Data Pipeline**: :doc:`02-data-pipeline/transform-pipeline` - Manage transformations
* **Plugin Development**: :doc:`04-plugin-development/creating-transformers` - Build custom logic
* **GUI Workflow**: :doc:`06-gui/user-workflow` - Navigate the interface

Getting Help
------------

* `GitHub Issues <https://github.com/niamoto/niamoto/issues>`_
* `Discussions <https://github.com/niamoto/niamoto/discussions>`_
* :doc:`12-troubleshooting/common-issues`

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
