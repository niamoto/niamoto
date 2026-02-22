/**
 * Niamoto Plotly Core bundle — all chart types except maps.
 *
 * Traces: scatter, bar, pie, heatmap, indicator, sunburst, table, barpolar
 * ~1 MB minified (vs ~4.7 MB monolithic)
 */
var Plotly = require("plotly.js/lib/core");

// Register trace types used by Niamoto widgets
Plotly.register([
  require("plotly.js/lib/bar"),
  require("plotly.js/lib/pie"),
  require("plotly.js/lib/heatmap"),
  require("plotly.js/lib/indicator"),
  require("plotly.js/lib/sunburst"),
  require("plotly.js/lib/table"),
  require("plotly.js/lib/barpolar"),
]);

module.exports = Plotly;
