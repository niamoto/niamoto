# Export Parallelization Design

Date: 2026-03-27

## Summary

Goal: reduce HTML export time by parallelizing detail page generation in the
`html_page_exporter`, while keeping the current behavior unchanged by default.

This first iteration targets only `export`, not `transform`.

## Baseline

Reference instance:
- `test-instance/niamoto-subset`

Measured with:
- `uv run python scripts/dev/bench_pipeline.py --instance test-instance/niamoto-subset`

Current baseline:
- `transform run`: `139.86s`
- `export --target web_pages`: `42.15s`

Only the export baseline is in scope for this design.

## Scope

In scope:
- parallelize HTML detail page generation
- keep static pages, index pages, asset copying, navigation JS, and language
  loops sequential
- add a CLI-only `--workers` option for `niamoto export`
- make the feature opt-in with `workers=1` as the default

Out of scope:
- parallelizing `transform`
- changing `export.yml`
- parallelizing non-HTML exporters
- adding memory or CPU benchmarking

## Approach

Recommended approach:
- use `ThreadPoolExecutor`
- parallelize at the level of one detail page per task

Alternatives considered:
- `ProcessPoolExecutor`: more isolation, but too heavy for a first pass
- hybrid staged pipeline: more control, but more complexity without a clear
  short-term benefit

Why threads first:
- the existing exporter is dominated by per-page rendering, file writes, widget
  rendering, and per-item data fetching
- the change can stay local to `html_page_exporter`
- it preserves a simple rollback path if the gain is not worth the complexity

## Architecture

Parallelization applies only inside the detail-page loop in
`src/niamoto/core/plugins/exporters/html_page_exporter.py`.

Sequential phases remain unchanged:
- static pages
- index generation
- asset copying
- navigation JS generation
- language iteration

Parallel phase:
- for a given language and group, each detail page becomes one task
- the parent thread submits tasks to a `ThreadPoolExecutor(max_workers=n)`
- the parent thread remains responsible for:
  - progress display
  - stats aggregation
  - dependency aggregation
  - error counting and logging

## Isolation Rules

Each detail-page task must be self-contained:
- open its own database connection in read-only mode
- instantiate its own widget plugins
- load item detail data for one item
- render widgets for that item
- render the final detail page
- write the output file
- return a small result payload to the parent

Workers must not mutate shared exporter state.

Shared mutable state that remains parent-only:
- `self.stats`
- progress bars
- global dependency aggregation
- global error counters

## Interface

Add a CLI option to `niamoto export`:

```bash
niamoto export --target web_pages --workers 1
niamoto export --target web_pages --workers 4
```

Rules:
- default is `1`
- `workers <= 1` keeps the current sequential path
- only `html_page_exporter` uses the value in this first iteration
- no `export.yml` change in v1

## Validation

Success criteria:
- `workers=1` reproduces current behavior
- `workers>1` does not change generated content
- `export --target web_pages` is meaningfully faster than the `42.15s` baseline

Pragmatic thresholds:
- interesting gain: `>= 25%`
- strong gain: `>= 40%`
- weak gain: `< 15%`

Validation plan:
- targeted tests for CLI plumbing of `--workers`
- targeted export tests for sequential vs parallel output equivalence
- benchmark rerun on `test-instance/niamoto-subset`
- stop after export if gains are too small to justify extending the work to
  `transform`

## Risks

Main risks:
- unsafe sharing of database or exporter state across threads
- widget rendering code that assumes single-threaded execution
- progress or stats corruption if workers update shared state directly
- limited gain if most of the export time is outside detail page generation

Mitigations:
- one database connection per worker
- parent-only mutation of shared exporter state
- opt-in flag with sequential default
- benchmark before expanding scope
