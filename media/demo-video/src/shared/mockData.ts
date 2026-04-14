/**
 * Mock data for demo video acts.
 * All data is generic — not New Caledonia-specific.
 */

// Collections (Act 4)
export const MOCK_COLLECTIONS = [
  { name: "Plots", count: 245, widgets: 3, exports: 2, status: "fresh" as const },
  { name: "Taxa", count: 1280, widgets: 5, exports: 3, status: "fresh" as const },
  { name: "Occurrences", count: 48500, widgets: 4, exports: 2, status: "stale" as const },
];

// Import YAML (Act 3)
export const MOCK_YAML = `sources:
  taxon_reference:
    type: csv
    path: taxa.csv
    identifier: id_taxon
  occurrences:
    type: csv
    path: occurrences.csv
    identifier: id_occurrence
  plots:
    type: geopackage
    path: study_plots.gpkg
    identifier: id_plot`;

// Site tree (Act 5)
export const MOCK_SITE_TREE = [
  { label: "Home", icon: "home" as const, type: "page" as const },
  {
    label: "Species",
    icon: "layers" as const,
    type: "collection" as const,
    children: [
      { label: "Species Index", icon: "file" as const, type: "page" as const },
      { label: "Species Detail", icon: "file" as const, type: "template" as const },
    ],
  },
  {
    label: "Plots",
    icon: "layers" as const,
    type: "collection" as const,
    children: [
      { label: "Plot Map", icon: "file" as const, type: "page" as const },
    ],
  },
  { label: "About", icon: "file" as const, type: "page" as const },
];

// Project creation (Act 2)
export const MOCK_PROJECT = {
  name: "my-ecology-project",
  defaultParentPath: "/Users/username/Projects",
  selectedParentPath: "/Users/username/Projects",
  fullPath: "/Users/username/Projects/my-ecology-project",
};

// File types for import (Act 3)
export const FILE_TYPES = [
  { type: "csv" as const, extensions: [".csv"], color: "#3FA9F5", label: "Tabular data" },
  { type: "vector" as const, extensions: [".gpkg", ".geojson"], color: "#4BAF50", label: "Spatial data" },
  { type: "raster" as const, extensions: [".tif"], color: "#9333EA", label: "Raster data" },
];
