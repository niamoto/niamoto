---
title: refactor: Audit test coverage and close high-value gaps
type: refactor
status: active
date: 2026-04-22
---

# refactor: Audit test coverage and close high-value gaps

## Overview

Niamoto has a substantial automated test suite already, especially around Python plugins, import logic, and GUI API routers. The coverage is uneven, though: several shared backend helpers and deploy adapters still rely on indirect coverage, and the React/Vitest surface is much larger than its current test footprint. This plan establishes a reproducible audit first, then adds high-value tests in the places most likely to prevent real regressions.

## Problem Frame

The goal is to perform a complete review of the current tests and determine which tests to add to increase coverage in a significant and relevant way.

Today’s signals show a mixed state:

- Python CI already runs `pytest --cov=niamoto` and uploads `coverage.xml` plus `htmlcov`, so backend coverage is measurable.
- `.coveragerc` defines the Python measurement scope, but there is no visible repo-level threshold or ratchet strategy yet.
- The backend suite is dense around `tests/core/plugins`, `tests/core/imports`, `tests/core/services`, and `tests/gui/api/routers`, but several important modules still have no direct tests.
- The frontend runs `vitest run`, but `src/niamoto/gui/ui/vite.config.ts` does not define coverage reporting and CI does not publish a frontend coverage artifact.
- The frontend contains roughly 450 TypeScript/TSX source files and roughly 31 test files, so raw surface area alone suggests a large blind spot unless the audit narrows that surface to behavior-heavy logic.

The plan therefore needs to avoid vanity work. The right outcome is not “more tests everywhere”; it is “better protection around the riskiest logic, plus a measurement system that keeps future additions focused.”

## Requirements Trace

- R1. Produce a reproducible audit of the current Python and frontend test landscape.
- R2. Identify the tests to add by regression risk and user impact, not by missing-file count alone.
- R3. Increase coverage significantly by targeting behavior-heavy modules, adapters, serializers, and shared helpers first.
- R4. Keep the strategy understandable for maintainers and contributors.
- R5. Add enough tooling, documentation, and CI feedback that the coverage gains can continue incrementally.

## Scope Boundaries

- Do not rewrite already strong test areas just to normalize style.
- Do not target every missing file equally; low-value wrappers and purely presentational UI primitives stay lower priority.
- Do not treat this as a backend-only exercise; the frontend audit is part of the work.
- Do not start with browser-wide E2E automation as the primary answer to missing unit and route coverage.

### Deferred to Separate Tasks

- Add browser or desktop E2E automation only if targeted unit and API coverage still leaves critical behavior unprotected.
- Evaluate mutation testing or diff-coverage gates after the first baseline and ratchet are stable.

## Context & Research

### Relevant Code and Patterns

- `.github/workflows/tests.yml` already runs `uv run --group dev pytest -n auto --cov=niamoto tests/ --cov-report=xml --cov-report=html` and uploads coverage artifacts to Codecov.
- `.coveragerc` measures `src/niamoto`, omits `tests/*` and `__init__*`, but does not define explicit fail-under thresholds.
- `tests/core/services/test_importer.py` is a strong backend pattern for service tests: spec-checked mocks, `tmp_path` fixtures, and behavior-based assertions.
- `tests/gui/api/routers/test_imports.py` is the clearest router pattern: monkeypatch working-directory context, fake service boundaries, and assert structured job and error payloads.
- `src/niamoto/gui/ui/src/features/import/components/dashboard/enrichmentPolling.test.ts` shows the preferred frontend pattern for pure logic and state transitions.
- `src/niamoto/gui/ui/src/features/feedback/lib/__tests__/redact.test.ts` shows the preferred frontend pattern for deterministic helper tests with concrete input/output expectations.
- `src/niamoto/gui/ui/src/features/tools/components/AboutPanel.test.tsx` shows the existing lightweight component-rendering style when a UI surface has meaningful content and branching.
- `src/niamoto/gui/ui/package.json` runs `vitest run`, but `src/niamoto/gui/ui/vite.config.ts` currently has no `test` or coverage block, so frontend coverage is not yet measured in a durable way.

### Audit Findings From Local Research

- Strong Python coverage clusters exist in:
  - `tests/core/plugins/transformers`
  - `tests/core/plugins/widgets`
  - `tests/core/imports`
  - `tests/core/services`
  - `tests/gui/api/routers`
  - `tests/gui/api/services/templates`
- Clear backend gaps from the static inventory:
  - `src/niamoto/core/plugins/deployers/*.py` has direct tests only for `github.py`
  - `src/niamoto/gui/api/routers/deploy.py`, `layers.py`, and `transformer_suggestions.py` have no direct route tests
  - `src/niamoto/gui/api/services/help_content.py`, `map_renderer.py`, `preview_utils.py`, `templates/config_scaffold.py`, and `templates/config_service.py` have no direct service tests
  - `src/niamoto/common/bundle.py`, `hierarchy_context.py`, `resource_paths.py`, `table_resolver.py`, and `transform_config_models.py` lack direct tests
  - `src/niamoto/cli/commands/deploy.py` lacks direct command tests
  - `src/niamoto/core/imports/multi_field_detector.py`, `class_object_suggester.py`, `source_registry.py`, and `template_suggester.py` lack direct tests even though adjacent pipeline modules are well covered
- Frontend density signals from static inventory:
  - `src/niamoto/gui/ui/src/features/import` is the largest feature area and has very little direct test coverage relative to its size
  - `site`, `feedback`, `collections`, and `dashboard` are also large surfaces with sparse tests
  - existing frontend tests are concentrated in helpers, routing, a few feature entry points, and selected desktop/runtime helpers

### Institutional Learnings

- No relevant `docs/solutions/` directory or active testing strategy memo exists in the repository today.
- `docs/_archive/11-development/testing.md` is still a placeholder, which means part of this work is to convert implicit patterns into active project guidance.

### External References

- None. Local patterns are strong enough to plan without external research.

## Key Technical Decisions

- Risk-weight the backlog. Missing tests in deploy adapters, shared path/config logic, import suggestion seams, and JSON serialization matter more than missing tests for small presentational wrappers.
- Audit Python and frontend separately. Python already has measurable coverage artifacts; frontend needs explicit Vitest coverage before any serious prioritization or ratchet.
- Start with instrumentation, not with random test additions. A reproducible audit prevents this effort from degrading into opportunistic coverage chasing.
- Prefer characterization tests around current behavior before refactors. The first step is to freeze contracts and error shapes where logic is already in production use.
- Add a ratchet, not a cliff. The first enforcement should prevent regression from the new baseline, not guess an arbitrary global threshold up front.
- Exclude generated and vendored noise from the audit. Frontend inventory must ignore `node_modules`, build output, and generated content so the backlog stays actionable.

## Open Questions

### Resolved During Planning

- Should this be treated as a Python-only coverage initiative? No. The largest measurable asymmetry is on the frontend, so the plan must cover both surfaces.
- Should the work begin by writing tests in the most obviously uncovered files? No. The baseline and prioritization mechanism must be in place first.
- Should every source file with no direct test become part of the initial backlog? No. Low-value wrappers and UI primitives should remain below adapters, route contracts, shared helpers, and stateful hooks.

### Deferred to Implementation

- Exact Python and frontend coverage thresholds after the first baseline run.
- Whether the initial frontend ratchet should be global or limited to selected feature directories first.
- Whether targeted E2E or desktop smoke automation is still required after the planned unit and API gaps are closed.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

| Stage | Input | Decision rule | Output |
|------|------|------|------|
| Inventory | Source tree, test tree, current coverage artifacts | Ignore vendor/generated noise; group by package and feature | Reproducible audit report |
| Prioritization | Audit report plus local risk signals | Prefer sparse, behavior-heavy, shared surfaces | Ranked backlog |
| Gap closure | Ranked backlog | Add characterization, unit, and route tests before refactors | New pytest and Vitest suites |
| Ratchet | Stable new baseline | Enforce no-regression before hard thresholds | CI and contributor guidance |

## Implementation Units

- [ ] **Unit 1: Build a reproducible audit baseline**

**Goal:** Replace ad hoc impressions with a repeatable inventory of current coverage and missing high-value surfaces across Python and the frontend.

**Requirements:** R1, R2, R4, R5

**Dependencies:** None

**Files:**
- Create: `scripts/dev/report_test_inventory.py`
- Create: `tests/scripts/test_report_test_inventory.py`
- Create: `docs/07-architecture/testing-audit.md`
- Modify: `scripts/README.md`

**Approach:**
- Add one dev-facing script that reads available coverage artifacts, inventories source and test files, and emits grouped summaries by backend package and frontend feature area.
- Keep the output focused on actionable signals: high-risk modules with no direct tests, feature areas with sparse test density, and zones already strong enough to deprioritize.
- Write the current audit results into a durable documentation page so the review survives beyond CI artifacts and session history.
- Ignore vendored and generated paths such as frontend `node_modules`, build output, and generated content files so the report remains stable and reviewable.

**Execution note:** Start with a failing script test using a tiny synthetic source/test tree and synthetic coverage input so the inventory logic is pinned before it is used on the real repository.

**Patterns to follow:**
- `tests/scripts/test_generate_plugin_manifest.py`
- `tests/scripts/test_sync_about_content.py`
- `scripts/README.md`

**Test scenarios:**
- Happy path — given a synthetic Python tree and matching tests, the audit groups files by domain and reports covered versus missing areas without false positives.
- Happy path — given a synthetic frontend tree with `.test.ts`, `.test.tsx`, generated files, and vendored folders, the audit counts only project source and assigns tests to the correct feature buckets.
- Edge case — missing `coverage.xml` or missing frontend coverage output produces a clear “baseline unavailable” section instead of crashing or silently dropping a domain.
- Edge case — split test families such as `profiler_io` and `profiler_ml` are attributed to the parent module family instead of being treated as unrelated files.
- Error path — malformed coverage input or invalid paths produce an actionable diagnostic and non-zero exit.
- Integration — the generated audit report highlights the same backend gaps already surfaced during planning, including deployers, uncovered routers, and sparse frontend feature areas.

**Verification:**
- A contributor can regenerate the same audit locally and see stable high-level findings without manual tree spelunking.
- `docs/07-architecture/testing-audit.md` reads as an active project artifact, not a transient command dump.

- [ ] **Unit 2: Close backend infrastructure and deploy-stack gaps**

**Goal:** Add pytest coverage for shared backend helpers and deploy surfaces where failures would break setup, publishing, or path and config resolution.

**Requirements:** R2, R3, R4

**Dependencies:** Unit 1

**Files:**
- Create: `tests/common/test_bundle.py`
- Create: `tests/common/test_hierarchy_context.py`
- Create: `tests/common/test_resource_paths.py`
- Create: `tests/common/test_table_resolver.py`
- Create: `tests/common/test_transform_config_models.py`
- Create: `tests/core/plugins/deployers/test_cloudflare.py`
- Create: `tests/core/plugins/deployers/test_netlify.py`
- Create: `tests/core/plugins/deployers/test_render.py`
- Create: `tests/core/plugins/deployers/test_ssh.py`
- Create: `tests/core/plugins/deployers/test_vercel.py`
- Create: `tests/cli/commands/test_deploy.py`

**Approach:**
- Treat shared path and config helpers as contract surfaces: they should resolve valid inputs predictably and fail loudly on invalid project state.
- Cover deploy provider adapters with fake HTTP or process boundaries so payload building, auth validation, and failure wrapping are locked down without external calls.
- Add command-level tests where direct CLI behavior matters, especially provider dispatch, option parsing, and error propagation for deployment workflows.

**Execution note:** Use characterization-first tests around current provider errors and return shapes before changing adapter logic.

**Patterns to follow:**
- `tests/common/test_config.py`
- `tests/common/test_database.py`
- `tests/core/plugins/deployers/test_github.py`
- `tests/cli/commands/test_gui.py`

**Test scenarios:**
- Happy path — shared path and resource helpers resolve the expected files, bundle locations, and table identifiers from valid project context.
- Edge case — missing optional resources or partial hierarchy inputs fall back predictably without breaking unrelated consumers.
- Error path — invalid deploy credentials or missing provider configuration are rejected before network dispatch with provider-specific context in the error.
- Error path — remote provider 4xx, 5xx, or transport failures are wrapped into stable exceptions and messages that higher layers can surface consistently.
- Integration — the deploy CLI command dispatches the correct provider adapter and preserves failure semantics when the adapter raises.
- Integration — table and transform-config helpers return structures compatible with existing service consumers instead of introducing shape drift.

**Verification:**
- Shared helper behavior is pinned by focused tests instead of being exercised only incidentally through larger workflows.
- Every deployer module under `src/niamoto/core/plugins/deployers` has at least one direct contract test.

- [ ] **Unit 3: Characterize the import-suggestion seams that still rely on adjacent coverage**

**Goal:** Fill the remaining holes in the import and suggestion pipeline so coverage reaches missing decision points instead of stopping at neighboring modules.

**Requirements:** R2, R3

**Dependencies:** Unit 1

**Files:**
- Create: `tests/core/imports/test_class_object_suggester.py`
- Create: `tests/core/imports/test_multi_field_detector.py`
- Create: `tests/core/imports/test_source_registry.py`
- Create: `tests/core/imports/test_template_suggester.py`
- Modify: `tests/core/imports/test_profiler_io.py`
- Modify: `tests/core/imports/test_widget_generator_contracts.py`
- Modify: `tests/integration/test_suggestion_pipeline.py`

**Approach:**
- Extend the already strong import test cluster into the remaining orchestration seams where suggestion ranking, multi-field composition, and source registration decisions can still regress unnoticed.
- Keep the emphasis on behavior contracts: accepted inputs, rejected inputs, prioritization, and serialized outputs that downstream routers and services assume.
- Reuse current fixtures under `tests/fixtures/` and current pipeline test patterns instead of inventing a parallel harness.

**Execution note:** Add characterization coverage before refactoring any suggestion heuristics or registry behavior uncovered during the audit.

**Patterns to follow:**
- `tests/core/imports/test_auto_config_service.py`
- `tests/core/imports/test_transformer_suggester.py`
- `tests/core/imports/test_widget_generator_regressions.py`
- `tests/integration/test_suggestion_pipeline.py`

**Test scenarios:**
- Happy path — multi-field detection recognizes valid combinable columns and returns deterministic suggestions in the expected order.
- Happy path — class-object suggestion logic emits widget and template suggestions compatible with current downstream serializers.
- Edge case — sparse or incomplete source metadata falls back to safe defaults instead of producing malformed suggestions.
- Edge case — ambiguous candidate combinations are deduplicated consistently and do not reshuffle rankings unpredictably.
- Error path — unknown source types or unsupported registry entries fail with explicit diagnostics instead of silent omission.
- Integration — `template_suggester` and `widget_generator` continue to produce configurations that satisfy the same contract assertions already used by adjacent pipeline tests.
- Integration — the end-to-end suggestion pipeline still serializes a valid response when the newly covered seams participate in the result.

**Verification:**
- The import-suggestion subsystem no longer depends on indirect coverage for `multi_field_detector`, `class_object_suggester`, `source_registry`, and `template_suggester`.
- Existing integration tests remain the place where cross-module compatibility is proven, with new unit tests covering the local decision branches.

- [ ] **Unit 4: Cover the remaining FastAPI routers and service helpers with direct contract tests**

**Goal:** Remove blind spots in the GUI backend where route schemas and service helpers can regress without any direct API-level assertions.

**Requirements:** R2, R3, R4

**Dependencies:** Units 1 and 2

**Files:**
- Create: `tests/gui/api/routers/test_deploy.py`
- Create: `tests/gui/api/routers/test_layers.py`
- Create: `tests/gui/api/routers/test_transformer_suggestions.py`
- Create: `tests/gui/api/services/test_help_content.py`
- Create: `tests/gui/api/services/test_map_renderer.py`
- Create: `tests/gui/api/services/test_preview_utils.py`
- Create: `tests/gui/api/services/templates/test_config_scaffold.py`
- Create: `tests/gui/api/services/templates/test_config_service.py`
- Create: `tests/gui/api/utils/test_config_updater.py`
- Create: `tests/gui/api/utils/test_import_fields.py`

**Approach:**
- Add route-focused tests for endpoints with no direct coverage, using the established monkeypatch-and-fixture style already present in router tests.
- Cover service and utility helpers where output shape, path resolution, or preview and config normalization is part of the API contract even if the helper itself is small.
- Keep tests close to public behavior: request and response shape, validation failure shape, status mapping, and serialized data consumed by the React UI.

**Patterns to follow:**
- `tests/gui/api/routers/test_imports.py`
- `tests/gui/api/routers/test_preview.py`
- `tests/gui/api/services/test_enrichment_service.py`
- `tests/gui/api/services/templates/test_suggestion_service.py`

**Test scenarios:**
- Happy path — each uncovered router returns the expected payload schema for a valid request and project context.
- Edge case — empty inputs, absent preview data, or missing optional files return stable fallback responses rather than uncaught exceptions.
- Error path — service-layer exceptions are translated into the expected HTTP status and error payload shape.
- Error path — invalid transformer suggestions, config edits, or layer and deploy parameters are rejected with clear validation details.
- Integration — route tests assert that the JSON shape consumed by the frontend remains compatible with current UI expectations for deploy, layer, preview, and transformer-suggestion flows.
- Integration — help-content and preview helpers normalize internal data into exactly the structures that existing routes and UI modules assume.

**Verification:**
- Every router module under `src/niamoto/gui/api/routers` has at least one direct test file.
- Service and utility helpers with serialization logic are no longer covered only transitively through larger route tests.

- [ ] **Unit 5: Add high-ROI frontend tests around critical logic and stateful flows**

**Goal:** Raise frontend coverage where the UI contains behavior, state transitions, or runtime branching, without spending time snapshot-testing every presentational component.

**Requirements:** R1, R2, R3, R4

**Dependencies:** Unit 1

**Files:**
- Create: `src/niamoto/gui/ui/src/features/import/hooks/useAutoConfigureJob.test.ts`
- Create: `src/niamoto/gui/ui/src/features/import/hooks/useImportJob.test.ts`
- Create: `src/niamoto/gui/ui/src/features/import/hooks/useCompatibilityCheck.test.ts`
- Create: `src/niamoto/gui/ui/src/features/publish/hooks/usePublishBootstrap.test.ts`
- Create: `src/niamoto/gui/ui/src/shared/lib/api/errors.test.ts`
- Create: `src/niamoto/gui/ui/src/shared/lib/api/client.test.ts`
- Create: `src/niamoto/gui/ui/src/shared/hooks/useRuntimeMode.test.ts`
- Create: `src/niamoto/gui/ui/src/features/feedback/context/useFeedback.test.ts`
- Modify: `src/niamoto/gui/ui/package.json`
- Modify: `src/niamoto/gui/ui/vite.config.ts`

**Approach:**
- Target runtime branching, API normalization, and job or polling state machines before broad component rendering.
- Prefer narrow logic tests and a few hook or component harnesses for feature entry points over blanket snapshots.
- Add explicit frontend coverage reporting through Vitest so progress is measurable, and align exclusions with generated files and low-value UI primitives.

**Execution note:** Implement tests in the order of purest logic first (`shared/lib`, runtime hooks, routing helpers), then stateful hooks, then selective feature harnesses only if gaps remain after the audit.

**Patterns to follow:**
- `src/niamoto/gui/ui/src/features/import/components/dashboard/enrichmentPolling.test.ts`
- `src/niamoto/gui/ui/src/features/collections/routing.test.ts`
- `src/niamoto/gui/ui/src/shared/desktop/runtime.test.ts`
- `src/niamoto/gui/ui/src/features/feedback/lib/__tests__/redact.test.ts`

**Test scenarios:**
- Happy path — import and publish hooks progress from idle to running to completed states while exposing the derived flags and data the UI depends on.
- Happy path — API client and error helpers normalize successful responses and known failure shapes into predictable frontend-friendly structures.
- Edge case — runtime-mode hooks distinguish web versus desktop bootstrap states and preserve safe defaults when bootstrap metadata is absent.
- Edge case — compatibility and polling hooks stop re-requesting when a terminal state or cooldown boundary is reached.
- Error path — polling hooks and API helpers preserve useful error state on terminal failures instead of looping indefinitely or swallowing the failure.
- Integration — selective hook and component harness tests prove that import and publish entry points react correctly to the normalized API and job state produced by the helpers.
- Integration — frontend coverage configuration excludes generated and vendor files and reports usable per-directory coverage for the chosen high-risk areas.

**Verification:**
- Frontend coverage becomes measurable in CI or local reports instead of being inferred from raw test-file counts.
- The first new frontend tests protect behavior-heavy modules that can break user-visible flows without requiring wide DOM snapshot coverage.

- [ ] **Unit 6: Ratchet the coverage rules and contributor guidance**

**Goal:** Make the audit and new tests durable by turning them into contributor-visible guidance and no-regression checks.

**Requirements:** R1, R4, R5

**Dependencies:** Units 1 through 5

**Files:**
- Modify: `.github/workflows/tests.yml`
- Modify: `.coveragerc`
- Modify: `pyproject.toml`
- Modify: `src/niamoto/gui/ui/package.json`
- Modify: `src/niamoto/gui/ui/README.md`
- Create: `docs/07-architecture/testing-strategy.md`
- Modify: `docs/_archive/11-development/testing.md`

**Approach:**
- Keep the Python coverage job but add explicit no-regression protection at the right level: per-area or diff-aware ratchets before any aggressive global threshold.
- Add frontend coverage collection to the project test scripts and CI, even if the first gate is informational rather than blocking.
- Replace the placeholder testing note with active guidance that explains what to test, what not to test, and which suites already represent good local patterns.
- Leave the archived note as a pointer to the active strategy document rather than maintaining duplicate guidance.

**Patterns to follow:**
- `.github/workflows/tests.yml`
- `.coveragerc`
- `src/niamoto/gui/ui/README.md`

**Test scenarios:**
- Happy path — CI emits Python and frontend coverage artifacts in a form contributors can inspect locally and in pull requests.
- Edge case — uncovered but explicitly excluded generated and vendor files do not create false regressions.
- Error path — a meaningful drop in protected coverage areas fails the quality gate with a readable explanation.
- Integration — contributor documentation and scripts stay aligned so the workflow described in docs matches the actual commands and artifacts used in CI.

**Verification:**
- A new contributor can understand where to add tests and how coverage is evaluated without relying on old session context.
- Coverage can grow incrementally without regressions disappearing into CI noise.

## System-Wide Impact

- **Interaction graph:** CLI commands call core services and provider adapters; GUI routers depend on shared service helpers and import or deploy contracts; React features depend on stable JSON and error shapes from those routers and helpers.
- **Error propagation:** New tests must preserve the current boundary between internal exceptions, CLI user-facing errors, and HTTP response payloads so regressions do not surface as uncaught tracebacks or opaque failures.
- **State lifecycle risks:** Import and publish job polling, deploy state, and preview generation all have multi-step states where stale, partial, or terminal responses can drift from UI expectations.
- **API surface parity:** Deploy, import, suggestion, and preview behavior should stay consistent whether triggered from CLI or GUI routes when both surfaces wrap the same lower layers.
- **Integration coverage:** Unit tests alone will not prove that router JSON matches UI assumptions or that importer suggestions remain serializable, so the plan keeps selected integration tests in scope.
- **Unchanged invariants:** Existing strong suites around core plugins, major import services, and established routers should remain stable and are not targets for broad rewrites. The goal is to close gaps around them, not churn already useful coverage.

## Alternative Approaches Considered

- Raise a single global coverage threshold immediately: rejected because the frontend is not instrumented yet and Python per-area baselines are not formalized.
- Focus only on backend pytest coverage: rejected because the largest surface asymmetry is on the React side.
- Start with E2E or desktop smoke automation: rejected because it is slower and less diagnostic than closing the current unit and API blind spots first.

## Success Metrics

- The repository has a reproducible audit artifact that identifies test gaps by domain and risk.
- Every deploy provider and every GUI router module has at least one direct contract test.
- The import-suggestion pipeline no longer relies on indirect coverage for its remaining uncovered decision seams.
- Frontend coverage is published in a measurable form and has first-pass tests around critical hooks, API normalization, and runtime branching.
- CI prevents silent coverage regression in the newly protected areas.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| The audit script reports misleading gaps because it matches files too naively | Build the inventory against synthetic fixtures first, then validate it against known current gaps before treating it as a source of truth |
| The initiative over-optimizes for raw percentage instead of real regressions | Rank backlog items by behavior and blast radius, and explicitly document low-priority areas to avoid vanity work |
| Frontend coverage setup becomes noisy because of generated or vendored files | Configure exclusions up front and treat the first frontend coverage runs as informational until the numbers stabilize |
| New tests around deployers or import flows become flaky due to filesystem or network coupling | Use local fixtures, strict mocks, and fake provider boundaries rather than remote calls or shared mutable state |
| CI time grows too quickly | Prefer targeted unit and route tests first, keep integration tests selective, and add ratchets gradually instead of turning on expansive suites immediately |

## Documentation / Operational Notes

- `docs/07-architecture/testing-audit.md` should capture the current gap inventory and the rationale behind the ranked backlog.
- `docs/07-architecture/testing-strategy.md` should become the active reference for future contributors, replacing the current placeholder guidance.
- If frontend coverage is first introduced in informational mode, the follow-up step should promote it to a protected ratchet only after one or two stable CI cycles.

## Sources & References

- Related code: `.github/workflows/tests.yml`
- Related code: `.coveragerc`
- Related code: `pyproject.toml`
- Related code: `tests/core/services/test_importer.py`
- Related code: `tests/gui/api/routers/test_imports.py`
- Related code: `src/niamoto/gui/ui/src/features/import/components/dashboard/enrichmentPolling.test.ts`
- Related code: `src/niamoto/gui/ui/src/features/feedback/lib/__tests__/redact.test.ts`
- Related code: `src/niamoto/gui/ui/src/features/tools/components/AboutPanel.test.tsx`
- Related docs: `docs/_archive/11-development/testing.md`
- Related plan: `docs/plans/2026-03-13-feat-battle-test-smartmatcher-import-suggestions-plan.md`
