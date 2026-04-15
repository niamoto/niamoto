#!/usr/bin/env node
/**
 * extract-taxon-data.mjs
 *
 * Extrait les données Plotly inline d'une page taxon Niamoto (HTML générée)
 * vers un JSON structuré consommable par les widgets du teaser Remotion.
 *
 * Usage :
 *   node scripts/extract-taxon-data.mjs \
 *     --input ../../test-instance/nouvelle-caledonie/exports/web/fr/taxons/948049381.html \
 *     --output src/teaser/data/taxon-vedette.json
 *
 * État : **skeleton** — la première version 2026-04-15 de `taxon-vedette.json`
 * a été remplie manuellement à partir des observations des screenshots.
 * Ce script est à finaliser si on change de taxon vedette ou si les données
 * source évoluent.
 *
 * Plotly inline HTML layout attendu :
 *   <script>
 *     Plotly.newPlot(
 *       "widget-id",
 *       [{ x: [...], y: [...], type: "bar", ... }],
 *       { title: "...", ... },
 *       { responsive: true }
 *     );
 *   </script>
 *
 * TODO Phase 2 :
 *  - Parser balanced-parens pour capturer les 3-4 args Plotly.newPlot(div, data, layout, config)
 *  - Mapper widget-ids aux noms sémantiques (sub-taxons, dbh, phenology, holdridge, substrate, rainfall, map)
 *  - Extraire lon/lat depuis le trace de type "scattergeo" ou "scattermapbox"
 *  - Extraire la hiérarchie taxonomique depuis <ul class="tree-nav">
 */

import { readFile, writeFile } from "node:fs/promises";
import { parseArgs } from "node:util";

const { values: args } = parseArgs({
  options: {
    input: { type: "string", short: "i" },
    output: { type: "string", short: "o" },
  },
});

if (!args.input || !args.output) {
  console.error("Usage: extract-taxon-data.mjs --input <html> --output <json>");
  process.exit(1);
}

const html = await readFile(args.input, "utf8");

/**
 * Naive Plotly extraction : cherche tous les `Plotly.newPlot(` et tente
 * d'isoler le bloc jusqu'à la fermeture. Retourne un array d'objets
 * { divId, dataRaw, layoutRaw } (valeurs string à parser JSON).
 *
 * Limitations : ne gère pas les cas avec strings contenant des parenthèses
 * non échappées. Suffisant pour Plotly standard.
 */
function extractPlotlyBlocks(source) {
  const blocks = [];
  const marker = "Plotly.newPlot(";
  let i = 0;
  while ((i = source.indexOf(marker, i)) !== -1) {
    let depth = 1;
    let j = i + marker.length;
    while (j < source.length && depth > 0) {
      const ch = source[j];
      if (ch === "(") depth++;
      else if (ch === ")") depth--;
      j++;
    }
    blocks.push({ start: i, end: j, args: source.slice(i + marker.length, j - 1).trim() });
    i = j;
  }
  return blocks;
}

const blocks = extractPlotlyBlocks(html);
console.log(`Found ${blocks.length} Plotly.newPlot blocks.`);

// TODO : mapper chaque block à une clé sémantique
// TODO : JSON.parse best-effort sur chaque data + layout
// TODO : normaliser vers le schéma de taxon-vedette.json

const output = {
  _status: "skeleton",
  _note: "Ce script est un point de départ — à finaliser Phase 2 si besoin.",
  source: args.input,
  plotlyBlocksFound: blocks.length,
  plotlyBlocksRaw: blocks.map((b) => b.args.slice(0, 200) + "..."),
};

await writeFile(args.output, JSON.stringify(output, null, 2));
console.log(`Wrote skeleton extraction to ${args.output}`);
console.log("Note: taxon-vedette.json version actuelle a été remplie manuellement.");
