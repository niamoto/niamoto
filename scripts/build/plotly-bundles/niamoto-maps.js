/**
 * Niamoto Plotly Maps bundle — core traces + map types.
 *
 * Traces: scatter, bar, pie, heatmap, indicator, sunburst, table, barpolar,
 *         scattermap, choroplethmap
 * ~2.5 MB minified (includes maplibre-gl)
 */
var Plotly = require("plotly.js/lib/core");

// Register trace types used by Niamoto widgets (same as core)
Plotly.register([
  require("plotly.js/lib/bar"),
  require("plotly.js/lib/pie"),
  require("plotly.js/lib/heatmap"),
  require("plotly.js/lib/indicator"),
  require("plotly.js/lib/sunburst"),
  require("plotly.js/lib/table"),
  require("plotly.js/lib/barpolar"),
  // Map trace types
  require("plotly.js/lib/scattermap"),
  require("plotly.js/lib/choroplethmap"),
]);

module.exports = Plotly;
