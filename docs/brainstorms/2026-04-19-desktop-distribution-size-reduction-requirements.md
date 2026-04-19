---
date: 2026-04-19
topic: desktop-distribution-size-reduction
---

# Desktop Distribution Size Reduction

## Problem Frame

Niamoto desktop is currently expensive to download and install, and the dominant cost appears to come from the packaged Python sidecar rather than from the Tauri shell itself.

The immediate product need is not "migrate from Tauri to Electron". It is to produce a decision-grade analysis that shows where the shipped size comes from, what can be reduced without losing product capability, and which architecture gives the best size outcome across desktop platforms.

This matters because the chosen direction will affect download friction, release packaging, update costs, and whether a future shell decision is being made on the right bottleneck.

Verified repo context at brainstorm time:
- Current macOS packaged app artifact is about `498 MB` and the DMG is about `195 MB`.
- The bundled Python sidecar under `src-tauri/resources/sidecar` is about `353 MB`.
- The heaviest verified sidecar contributors are geospatial/runtime components such as `pyogrio`, `libgdal`, `rasterio`, `duckdb`, `scipy`, `pyproj`, `plotly`, and the packaged Python runtime.
- Existing benchmark entry points already exist in `scripts/dev/bench_pipeline.py` and `scripts/dev/bench_preview.py`.
- Existing ML model files exist under `ml/models`, with the largest current model being `ml/models/value_model.joblib`.

## Requirements

**Analysis Outputs**
- R1. Produce a packaged-size audit for desktop distribution that measures, at minimum, installer/archive size, installed app size, sidecar size, and major bundled asset families.
- R2. Attribute shipped size to concrete contributors rather than broad guesses, including Python runtime, native libraries, geospatial stack, ML dependencies, model artifacts, frontend assets, and duplicated resources.
- R3. Cover all primary desktop targets in the analysis scope: macOS, Windows, and Linux.
- R4. Distinguish shared contributors from platform-specific contributors so later decisions can separate global wins from OS-local wins.

**Option Evaluation**
- R5. Compare at least these strategic options against the same baseline:
  - keep a single bundled desktop app and optimize the current packaging aggressively
  - restructure the Python runtime or sidecar packaging while keeping the full product scope available
  - make heavy capabilities separable or installable on demand
  - change desktop shell only if it still improves the total shipped size picture
- R6. Evaluate every option primarily on size reduction potential, then secondarily on product complexity, technical complexity, runtime risk, update ergonomics, and reversibility.
- R7. Treat the current full product scope as non-negotiable during evaluation: import, transform, export, preview, maps, ML-assisted workflows, and desktop authoring all remain in scope.
- R8. Do not let shell maturity alone dominate the recommendation if the measured size bottleneck sits elsewhere.

**Model and Dependency Re-evaluation**
- R9. Audit the ML/runtime stack separately from the general Python app stack so the analysis can tell whether model-related size is a primary driver or a secondary one.
- R10. Evaluate whether the current model artifacts can be reduced in size without product-loss regressions, using existing evaluation and benchmark assets where available.
- R11. Evaluate whether heavy scientific or geospatial dependencies are required for all shipped workflows, or only for specific advanced workflows, based on verified code paths rather than assumption.
- R12. Identify cases where duplicate packaging or over-inclusion is inflating size, including duplicated libraries, duplicated data bundles, and assets included for convenience rather than runtime necessity.

**Benchmarking and Decision Support**
- R13. Reuse existing benchmark assets where possible so the analysis is tied to measured behavior, not only static file size inspection.
- R14. Add any missing benchmark definitions needed to compare candidate size-reduction strategies on representative flows such as startup, preview, transform/export, and ML evaluation.
- R15. Produce a ranked opportunity list that includes expected size impact, confidence level, validation effort, and risk of functional regression.
- R16. End with a recommendation and a phased execution plan that separates quick wins, medium-effort experiments, and high-risk architectural bets.

## Success Criteria

- The team gets a quantified top-down view of shipped size across macOS, Windows, and Linux.
- The analysis identifies the top contributors by measured weight and shows which are mandatory versus conditional.
- The analysis compares multiple architecture/package strategies against the same baseline instead of arguing from intuition.
- The analysis determines whether model reduction is materially worth pursuing relative to geospatial/runtime reductions.
- The final recommendation makes clear what to do first, what to test next, and what not to do yet.

## Scope Boundaries

- This work does not commit Niamoto to Electron migration by itself.
- This work does not remove any current product family from scope.
- This work does not assume optional downloads are acceptable; it evaluates that tradeoff.
- This work is analysis-first. Implementation can follow only after the audit, comparison, and recommendation are complete.

## Key Decisions

- Size reduction is the primary optimization target: if tradeoffs are required, prefer the option that reduces shipped size the most.
- The analysis is multi-platform from the start: recommendations must consider macOS, Windows, and Linux rather than only one local target.
- Full product scope is preserved during evaluation: the goal is not to win size by quietly cutting capabilities.
- Shell migration is a secondary question: first prove whether the dominant shipped-size problem is the desktop shell, the Python sidecar, or a specific dependency family.
- The deliverable must include three layers: audit, option comparison, and execution plan.

## Dependencies / Assumptions

- Existing benchmark entry points in `scripts/dev/bench_pipeline.py` and `scripts/dev/bench_preview.py` are assumed usable as part of the measurement baseline, subject to validation during planning.
- Existing ML evaluation assets and docs under `docs/05-ml-detection/` and model artifacts under `ml/models/` are assumed sufficient to support a first no-loss model-size assessment, subject to validation during planning.
- The current packaged sidecar is built through `build_scripts/niamoto.spec`, so packaging behavior and over-inclusion risk should be analyzed there as part of the audit.

## Alternatives Considered

- Optimize only the desktop shell choice: rejected as the primary framing because the currently verified dominant weight appears to be in the Python sidecar and scientific/geospatial runtime.
- Decide now between monolithic bundle and optional modules: rejected because the implications are exactly what the analysis must measure.
- Treat model compression as the main bet from the outset: rejected as the primary framing because current verified model weight appears meaningful but still smaller than the verified geospatial/runtime stack.

## Outstanding Questions

### Deferred to Planning

- [Affects R3][Needs research] Which exact installer/distribution artifacts should define the canonical size baseline on each target platform?
- [Affects R5][Needs research] Which packaging strategies can be realistically prototyped in this repository without a full product rewrite?
- [Affects R10][Needs research] Which no-loss or near-no-loss model optimization techniques are realistic for the current evaluation harness and acceptance bar?
- [Affects R11][Technical] Which heavy geospatial dependencies are imported on core startup paths versus advanced workflow paths only?
- [Affects R14][Technical] Which additional benchmark scripts are required to measure startup and feature-specific regressions for packaging experiments?

## Next Steps

-> `/ce:plan` for structured implementation planning
