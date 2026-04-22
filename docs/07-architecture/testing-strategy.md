# Testing Strategy

This is the active testing reference for Niamoto contributors.

Use it together with [testing-audit.md](./testing-audit.md):

- `testing-audit.md` explains where the current gaps are
- this document explains what to test, how to run it, and how coverage is tracked

## Goals

Niamoto does not optimize for raw test count. The goal is to protect the parts
of the product most likely to cause real regressions:

- shared backend helpers that many flows depend on
- plugin adapters and deploy boundaries
- FastAPI route contracts and serialized payloads consumed by the UI
- import and suggestion heuristics with non-trivial decision branches
- frontend hooks and API normalization logic that drive user-visible state

Pure wrappers and low-logic presentation components are lower priority unless
they encode important branching or content rules.

## Preferred Test Layers

### Python

Use focused pytest modules first:

- unit tests for shared helpers and decision-heavy modules
- direct router tests for FastAPI status and payload contracts
- integration tests only where cross-module compatibility really matters

Strong local patterns already exist in:

- `tests/core/services/test_importer.py`
- `tests/gui/api/routers/test_imports.py`
- `tests/gui/api/services/templates/test_suggestion_service.py`

### Frontend

Prefer narrow Vitest tests over broad snapshots:

- pure helpers in `shared/lib`, `shared/desktop`, and feature `lib/`
- hooks with meaningful state transitions or polling behavior
- selective jsdom harnesses for feature entry points when state wiring matters

Useful local patterns include:

- `src/features/import/components/dashboard/enrichmentPolling.test.ts`
- `src/shared/desktop/runtime.test.ts`
- `src/features/feedback/lib/__tests__/server-error-feedback.test.ts`

## Coverage Workflow

### Backend coverage

Backend coverage is produced by pytest:

```bash
uv run --group dev pytest -n auto --cov=niamoto tests/ --cov-report=xml --cov-report=html
```

The Python measurement scope comes from `.coveragerc`.

### Frontend coverage

Frontend coverage is produced by Vitest:

```bash
cd src/niamoto/gui/ui
pnpm test:coverage
```

The frontend report is written to `src/niamoto/gui/ui/coverage/` and currently
emits:

- text summary
- HTML report
- `json-summary`
- `lcov`

The Vitest coverage config excludes:

- generated TypeScript files
- test files themselves
- `vite-env.d.ts`
- `main.tsx`

These exclusions keep the report centered on behavior-bearing app code instead
of scaffolding.

## What To Add First

When you touch behavior-bearing code, prefer this order:

1. Add or update the nearest direct unit test.
2. Add a router or serialization test if the UI or CLI depends on the payload.
3. Add integration coverage only if the regression risk crosses module or layer boundaries.

This keeps the suite diagnostic and avoids hiding regressions behind slow,
over-broad scenarios.

## Contributor Checklist

Before finishing a change:

- run the smallest relevant pytest or Vitest target first
- broaden only after the local contract is stable
- update docs if the workflow, payload contract, or test command changed
- avoid adding coverage only to move percentages; protect real behavior

## CI Notes

CI publishes Python coverage artifacts and now also runs frontend coverage on a
single Node-enabled matrix leg to avoid duplicate reports. Frontend coverage is
currently informational infrastructure: it makes regressions visible and gives a
stable baseline for future ratchets.
