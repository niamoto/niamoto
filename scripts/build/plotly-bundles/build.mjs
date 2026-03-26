/**
 * Build custom Plotly.js bundles for Niamoto.
 *
 * Output:
 *   ../../../src/niamoto/publish/assets/js/vendor/plotly/plotly-niamoto-core.min.js
 *   ../../../src/niamoto/publish/assets/js/vendor/plotly/plotly-niamoto-maps.min.js
 */
import { build } from "esbuild";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(
  __dirname,
  "../../../src/niamoto/publish/assets/js/vendor/plotly"
);

const bundles = [
  { entry: "./niamoto-core.js", out: "plotly-niamoto-core.min.js" },
  { entry: "./niamoto-maps.js", out: "plotly-niamoto-maps.min.js" },
];

for (const { entry, out } of bundles) {
  console.log(`Building ${out}...`);
  const t0 = Date.now();

  await build({
    entryPoints: [resolve(__dirname, entry)],
    outfile: resolve(outDir, out),
    bundle: true,
    minify: true,
    format: "iife",
    globalName: "Plotly",
    platform: "browser",
    target: ["es2020"],
    // plotly.js injects its version; we don't need source maps in production.
    sourcemap: false,
  });

  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`  → ${out} built in ${elapsed}s`);
}

console.log("Done.");
