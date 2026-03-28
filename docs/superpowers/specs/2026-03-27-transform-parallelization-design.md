# Transform Parallelization Design

Date: 2026-03-27

## Summary

Goal: reduce transform time by parallelizing computation per entity (`group_id`)
while keeping database writes centralized and deterministic.

This first iteration targets only database-backed transforms. CSV-backed runs stay
sequential in v1.

## Baseline

Reference benchmark instance:
- `test-instance/niamoto-subset`

Current subset transform baseline:
- `transform run`: about `140s`

Observed subset workload example:
- taxons: `35` entities
- plots: `22` entities
- shapes: `22` entities

This makes entity-level parallelism materially more promising than group-level
parallelism.

## Scope

In scope:
- add `--workers <int>` to `niamoto transform run`
- parallelize computation per entity (`group_id`)
- keep database writes centralized in the parent process
- support only the DB-backed path in v1

Out of scope:
- CSV-backed parallel transform
- changing `transform.yml`
- parallel writes to DuckDB
- free-threaded Python dependency

## Approach

Recommended approach:
- use `ProcessPoolExecutor`
- parallelize at the level of one entity (`group_id`) per task
- keep `_save_widget_results(...)` and `_flush_group_table(...)` parent-only

Alternatives considered:
- `ThreadPoolExecutor`: simpler, but less attractive for heavier Python-side
  transform workloads and still constrained by GIL-sensitive code paths
- batch-per-worker strategy: lower scheduling overhead, but more moving parts for
  a first implementation

Why processes first:
- transform is closer to CPU/data processing than the HTML export path
- the design should not depend on free-threaded Python
- processes give cleaner isolation for plugin execution

## Architecture

For each transform group:
1. the parent validates the config
2. the parent resolves the list of `group_id`
3. the parent creates the output table
4. workers compute one entity each
5. the parent receives results and writes them to the existing buffers/tables
6. the parent flushes the group table once processing completes

Worker responsibilities:
- open a read-only database connection
- load group data for one `group_id`
- instantiate transformer plugins
- compute all widgets for that entity
- return a serialized payload:
  - `group_by`
  - `group_id`
  - widget results
  - warnings or errors

Parent responsibilities:
- progress reporting
- metrics aggregation
- result buffering
- `_save_widget_results(...)`
- `_flush_group_table(...)`
- final DuckDB optimization/checkpoint

## Isolation Rules

Workers must never write to the database.

Workers may only:
- read from the project database
- compute widget results
- return serializable payloads

Parent-only mutable state:
- table buffers
- flush modes
- metrics
- progress manager
- warning aggregation

This separation is required to avoid:
- concurrent DuckDB writes
- shared SQLAlchemy session state
- table-buffer corruption

## Interface

Add a CLI option:

```bash
niamoto transform run --workers 1
niamoto transform run --workers 4
```

Rules:
- default is `1`
- `workers <= 1` keeps the current sequential path
- `workers > 1` activates the parallel DB-backed path only
- if `--data` is used, v1 falls back to sequential execution
- no `transform.yml` change in v1

## Validation

Success criteria:
- `workers=1` reproduces current behavior
- `workers>1` writes the same rows and values to the output tables
- subset benchmark shows a meaningful gain
- full-instance benchmark confirms the gain at realistic scale

Pragmatic thresholds:
- interesting gain: `>= 30%`
- strong gain: `>= 50%`
- weak gain: `< 20%`

Validation plan:
- targeted tests for CLI propagation of `--workers`
- targeted tests comparing sequential vs parallel DB results on small fixtures
- benchmark on `test-instance/niamoto-subset`
- benchmark on `test-instance/niamoto-nc`

The real oracle is output-table equivalence, not progress output or log text.

## Risks

Main risks:
- process startup overhead reducing gains on small groups
- plugin code that is not safely serializable or not safe to run in workers
- hidden coupling between compute and write phases
- output ordering differences leaking into database writes or metrics

Mitigations:
- keep writes centralized in the parent
- keep `workers=1` as default
- restrict v1 to DB-backed transforms
- benchmark subset first before trusting full-instance results
