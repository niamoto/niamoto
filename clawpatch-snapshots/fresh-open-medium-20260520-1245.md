# clawpatch report

findings: 191
clusters: 2

## action clusters

### cluster 1: src/niamoto performance waste (5 findings)

- medium/high fnd_sig-feat-route-367db9e746-37012b_a1dbe73354: Async route runs blocking database work on the event loop
- medium/high fnd_sig-feat-route-9d5ebd4604-c0b7c3_d2a3967e9c: Blocking suggestion work runs on the FastAPI event loop
- medium/high fnd_sig-feat-route-d5546eef9f-7c1f78_5a9ed40c52: Preview route blocks the FastAPI event loop with synchronous database work
- medium/medium fnd_sig-feat-route-536a72b579-372aeb_88f6d686f1: Blocking analyzers run inline on the FastAPI event loop
- medium/medium fnd_sig-feat-route-53287c8347-f4f49a_40c95c0809: GET /data-content can block the FastAPI event loop while reading and parsing arbitrary project JSON

### cluster 2: src/niamoto duplication (2 findings)

- medium/high fnd_sig-feat-route-d33a2eca2b-bb59d4_151042d7e7: Async route blocks the event loop while analyzing CSV files
- medium/high fnd_sig-feat-route-b5d2f5987d-0ba162_386912d0c5: GET /files performs unbounded synchronous recursive traversal

## medium: `--repo-root` only works when the current directory is also that repo root

id: fnd_sig-feat-library-9f6260a4b9-5b40_29734b41d3
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source scripts/dev (feat_library_9f6260a4b9)
next: clawpatch show --finding fnd_sig-feat-library-9f6260a4b9-5b40_29734b41d3

evidence:
- scripts/dev/report_test_inventory.py:437-452 (_artifact_from_python_coverage)
- scripts/dev/report_test_inventory.py:530-542 (_parse_args)

When a caller passes `--repo-root` for another checkout, the default coverage paths still point at the script checkout via `DEFAULT_COVERAGE_XML` and `DEFAULT_FRONTEND_COVERAGE`. Even if the caller passes a relative `--coverage-xml coverage.xml`, it is interpreted relative to the current working directory rather than `--repo-root`. `_artifact_from_python_coverage` then joins coverage filenames against the requested repo root, so the script can silently report missing or stale coverage for the wrong repository depending on where it is launched.

recommendation:
After parsing args, resolve default and relative coverage artifact paths against `args.repo_root` rather than module-level `REPO_ROOT` or the process current directory.

test analysis:
The included context tests exercise preview smoke scripts only; there is no test covering `report_test_inventory.py` argument resolution or launching it with `--repo-root` from a different working directory.

suggested regression test:
Add a unit test for `_parse_args`/`build_inventory` invocation that uses a temporary repo root plus cwd outside that root, supplies relative coverage paths, and asserts the artifacts are read from the requested repo root.

minimum fix scope:
`scripts/dev/report_test_inventory.py` argument normalization in `main`, plus a focused test for repo-root-relative coverage path resolution.

repro:
From outside the target repository, run `python /path/to/repo/scripts/dev/report_test_inventory.py --repo-root /path/to/repo` without explicitly passing absolute coverage artifact paths. The inventory scans `/path/to/repo` sources but looks for coverage artifacts at the script-defined defaults or process cwd-relative paths instead of `/path/to/repo/coverage.xml` and `/path/to/repo/src/niamoto/gui/ui/coverage/coverage-summary.json`.

## medium: Active import jobs are not scoped to the current project

id: fnd_sig-feat-route-a09521f656-6b92ed_aae2acd018
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /status (feat_route_a09521f656)
next: clawpatch show --finding fnd_sig-feat-route-a09521f656-6b92ed_aae2acd018

evidence:
- src/niamoto/gui/api/routers/pipeline.py:505-524 (_get_active_import_jobs)
- src/niamoto/gui/api/routers/pipeline.py:582-589 (get_pipeline_status)
- tests/gui/api/routers/test_pipeline.py:401-448 (test_pipeline_status_reports_active_in_memory_import_job)

GET /status reads the current working directory, but the in-memory import-job fallback scans every active entry in the module-level import_jobs dictionary and chooses the newest one without checking that it belongs to the current work_dir. If a user switches projects or multiple project contexts have active imports in the same API process, this route can report data.status='running' and a running_job for another project, blocking or misleading the dashboard for the current project.

recommendation:
Pass the current work_dir into the active import snapshot helper and filter import jobs by their stored working_directory before sorting/selecting them. Keep legacy/no-working-directory jobs only if they are known to belong to the current project, or ignore them after migration.

test analysis:
The existing /status import test only installs a single in-memory job and asserts it is surfaced. It does not include a job whose working_directory differs from the current get_working_directory result.

suggested regression test:
Add a /status test with import_jobs containing an active job for a different working_directory and assert response.data.status is not running and response.running_job is None for the current project.

minimum fix scope:
Update _get_active_import_jobs and its get_pipeline_status call site to filter by current project identity; add one targeted router test.

## medium: All-groups transform runs are invisible to per-group last-run lookups

id: fnd_sig-feat-route-e653e47740-c73f79_85c16654b4
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /last-run/{group_by} (feat_route_e653e47740)
next: clawpatch show --finding fnd_sig-feat-route-e653e47740-c73f79_85c16654b4

evidence:
- tests/cli/test_transform.py:103-122 (test_successful_all_transform)
- src/niamoto/gui/api/routers/transform.py:190-240 (execute_transform_background)
- src/niamoto/gui/api/routers/transform.py:425-430 (execute_transform)
- src/niamoto/gui/api/routers/transform.py:651-664 (get_last_transform_run)
- src/niamoto/gui/api/services/job_file_store.py:274-280 (JobFileStore.get_last_run)

A transform request with no group filter is an all-groups run: the background worker leaves requested_groups empty and includes every configured transform group, matching the CLI behavior covered by test_successful_all_transform. However execute_transform records that job with group_by=None and group_bys=None. Later, GET /last-run/{group_by} asks JobFileStore for a completed transform matching the requested group, and JobFileStore only matches explicit group_by or membership in group_bys. The all-groups completed job therefore does not match any specific group, so /last-run/taxons can return null immediately after a successful full transform run.

recommendation:
Persist explicit group_bys for all configured groups when a no-filter transform run is created or completed, or teach the last-run lookup to treat transform jobs with both group_by and group_bys absent as all-groups jobs without accidentally matching unrelated single-group jobs.

test analysis:
The included CLI test verifies that an unfiltered transform means all groups, and router tests cover explicit multi-group jobs, but there is no API regression that completes an unfiltered transform and then queries /last-run/{group_by}.

suggested regression test:
Add a router or JobFileStore integration test that creates/completes an unfiltered transform job and asserts get_last_transform_run("taxons") returns that completed job for a configured taxons group.

minimum fix scope:
Update transform job metadata or JobFileStore matching semantics for unfiltered transform jobs, then add the focused /last-run/{group_by} regression test.

repro:
Run POST /api/transform/execute with the default body against a transform.yml containing a taxons group, let it complete, then call GET /api/transform/last-run/taxons. The completed job has group_by=None and group_bys=None, so the lookup does not return it.

## medium: Ambiguous transform requests can run one group while recording another

id: fnd_sig-feat-library-8911c6c7d9-03ac_97d89d99f3
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/gui/api/routers#3 (feat_library_8911c6c7d9)
next: clawpatch show --finding fnd_sig-feat-library-8911c6c7d9-03ac_97d89d99f3

evidence:
- src/niamoto/gui/api/routers/transform.py:43-48 (TransformRequest)
- src/niamoto/gui/api/routers/transform.py:190-191 (execute_transform_background)
- src/niamoto/gui/api/routers/transform.py:316-323 (execute_transform_background)
- src/niamoto/gui/api/routers/transform.py:425-430 (execute_transform)

The request model allows callers to provide both `group_by` and `group_bys`. When that happens, execution silently ignores `group_by` because `group_bys` wins in `requested_groups`, and the transformer is invoked with `service_group_by=None`; however the created job still records the original `group_by`. A request such as `{group_by: "taxons", group_bys: ["plots"]}` therefore executes only `plots` while status/history can claim or match `taxons`, which can mislead the UI and downstream last-run lookups.

recommendation:
Add a Pydantic model validator that rejects requests containing both `group_by` and non-empty `group_bys`, or normalize to a single authoritative field before both filtering and job creation.

test analysis:
The linked `tests/cli/test_transform.py` exercises the CLI command path, not the GUI API request model. The router tests cover single-field `group_by` and `group_bys` cases but not a request containing both fields.

suggested regression test:
Add an API/router test that posts both `group_by` and `group_bys` and asserts a 422/400 response, or asserts that normalized job metadata exactly matches the groups actually executed.

minimum fix scope:
`TransformRequest` validation plus any affected API tests.

repro:
POST `/api/transform/execute` with JSON `{ "group_by": "taxons", "group_bys": ["plots"] }`; the prepared config is filtered to `plots`, while the job metadata stores `group_by="taxons"`.

## medium: API export preview ignores the configured database path

id: fnd_sig-feat-route-767d8e57f0-345196_bb9cde7096
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /export/api-targets/{export_name}/groups/{group_by}/preview (feat_route_767d8e57f0)
next: clawpatch show --finding fnd_sig-feat-route-767d8e57f0-345196_bb9cde7096

evidence:
- src/niamoto/gui/api/routers/config.py:2858-2864 (_load_api_export_preview_items)
- src/niamoto/gui/api/routers/config.py:2910-2914 (_apply_api_export_preview_transformer)
- tests/common/test_config.py:64-75 (test_database_path_expands_home_path)

The preview route builds both the sampled data connection and transformer-preview connection from a hardcoded project-relative db/niamoto.duckdb path. Niamoto configuration explicitly supports custom database paths, including expanded home paths, so projects using database.path outside the default location will get a false 404 or preview data from the wrong default database while the rest of the app/export pipeline uses the configured database.

recommendation:
Use the existing get_database_path(get_working_directory()) helper in both _load_api_export_preview_items and _apply_api_export_preview_transformer, and preserve the 404 only when that helper returns no existing configured/fallback database.

test analysis:
The included Config test verifies custom database paths resolve, but there is no route-level preview test that patches config.yml to a non-default database path. The preview route tests also monkeypatch the item-loading helpers, so they bypass the hardcoded path.

suggested regression test:
Add a FastAPI route or helper test that patches get_working_directory to a temp project with config/config.yml pointing at a non-default DuckDB path, creates the preview table only there, and asserts POST preview succeeds and samples that database.

minimum fix scope:
Replace the hardcoded db path resolution in the two preview database helpers and add one targeted regression test for configured database paths.

repro:
Set config/config.yml to database.path: ~/custom.duckdb, create the transformed preview table only in that database, and call POST /api/config/export/api-targets/{export_name}/groups/{group_by}/preview. The route checks only <working_directory>/db/niamoto.duckdb and returns Database not found or samples the wrong database if a stale default file exists.

## medium: Async column metadata route blocks the FastAPI event loop

id: fnd_sig-feat-route-3bf18a4d4c-b31ffc_ad395d7576
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /tables/{table_name}/columns (feat_route_3bf18a4d4c)
next: clawpatch show --finding fnd_sig-feat-route-3bf18a4d4c-b31ffc_ad395d7576

evidence:
- src/niamoto/gui/api/routers/data_explorer.py:571-592 (get_table_columns_endpoint)
- tests/gui/api/routers/test_data_explorer.py:163-164 (test_list_tables_is_sync_so_fastapi_runs_it_off_event_loop)
- tests/gui/api/routers/test_data_explorer.py:167-183 (test_get_table_columns_uses_duckdb_fixture_without_reflection_errors)

The handler is declared async but performs synchronous database opening and schema introspection directly. FastAPI runs async handlers on the event loop, so a slow DuckDB open or column lookup can stall unrelated requests. The same module explicitly tests sync handlers for other database routes so FastAPI offloads them, but the column endpoint tests only validate the response and missing-table behavior, not event-loop offloading.

recommendation:
Make get_table_columns_endpoint a regular def handler so FastAPI runs it in the threadpool, or keep it async and move the blocking database section into run_in_threadpool.

test analysis:
The included tests assert list_tables and query_table are sync handlers, but there is no equivalent inspect.iscoroutinefunction assertion for get_table_columns_endpoint and no concurrent request test that would expose event-loop blocking.

suggested regression test:
Add a test asserting not inspect.iscoroutinefunction(data_explorer_router.get_table_columns_endpoint), or an async concurrency test with a delayed database stub proving the route does not block the event loop.

minimum fix scope:
Change only the route handler declaration/offloading path for get_table_columns_endpoint and add the focused regression test.

repro:
Use a database fixture or monkeypatch where open_database, get_table_names, or get_columns sleeps, then issue concurrent requests to an async-only endpoint and GET /api/data/tables/dataset_occurrences/columns; the unrelated request will wait while the column route blocks the event loop.

## medium: Async POST handler can block the FastAPI event loop on config locking and file I/O

id: fnd_sig-feat-route-a0633a5463-78af14_b9b3feb4a0
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST  (feat_route_a0633a5463)
next: clawpatch show --finding fnd_sig-feat-route-a0633a5463-78af14_b9b3feb4a0

evidence:
- src/niamoto/gui/api/routers/standard_profiles.py:201-227 (_standard_profile_config_lock)
- src/niamoto/gui/api/routers/standard_profiles.py:465-477 (create_standard_profile)

The route is declared async, but it performs the entire mutation path synchronously: it enters a threading/file lock, loads and validates configuration, mutates the store, and saves export.yml without using run_in_threadpool or a synchronous FastAPI handler. If another process holds the fcntl lock, LOCK_EX waits inside the event-loop thread, freezing unrelated requests served by that worker. Even without cross-process contention, YAML/config I/O and validation run on the event loop and can make the GUI API unresponsive during profile creation.

recommendation:
Move the whole create mutation into a synchronous function executed by FastAPI's threadpool, or make the route a regular def handler so blocking lock and filesystem work happen off the event loop. Keep the process lock inside that worker-thread section and return the created profile after persistence succeeds.

test analysis:
The existing route tests use synchronous TestClient flows for success and validation failures; they do not simulate lock contention or assert that unrelated async requests remain responsive while create waits on the process-safe lock.

suggested regression test:
Add an async API test that monkeypatches the lock acquisition or save path to block, starts POST /api/standard-profiles, then asserts an unrelated lightweight endpoint still responds within a short timeout.

minimum fix scope:
Change create_standard_profile and any shared mutation helper it uses so blocking lock, config load, validation, and save work run outside the event loop.

repro:
Hold the same export lock from another process, then send POST /api/standard-profiles and a second unrelated API request to the same server worker; the unrelated request cannot be handled until the blocking flock call returns.

## medium: Async route blocks the event loop while analyzing CSV files

id: fnd_sig-feat-route-d33a2eca2b-bb59d4_151042d7e7
category: performance
confidence: high
triage: risk
status: open
feature: FastAPI route GET /widget-suggestions/{group_by} (feat_route_d33a2eca2b)
next: clawpatch show --finding fnd_sig-feat-route-d33a2eca2b-bb59d4_151042d7e7

evidence:
- src/niamoto/gui/api/routers/templates.py:1274-1280 (get_widget_suggestions)
- src/niamoto/gui/api/routers/templates.py:1303-1304 (get_widget_suggestions)
- src/niamoto/gui/api/routers/templates.py:1347-1348 (get_widget_suggestions)

The handler is declared async, but it performs synchronous file I/O and CSV analysis directly on the event loop. This endpoint is explicitly for analyzing tabular sources, so a large configured CSV or repeated requests can stall other FastAPI requests until analysis completes.

recommendation:
Move the blocking work behind run_in_threadpool, or make the endpoint a synchronous def so FastAPI runs it in a worker thread. Keep HTTPException handling around the threaded call so API errors remain stable.

test analysis:
The linked tests only use tiny fixture CSV files through TestClient and do not assert concurrent request behavior or event-loop responsiveness.

suggested regression test:
Add an async concurrency test that patches analyze_csv to block briefly, fires this endpoint and a lightweight endpoint concurrently, and asserts the lightweight endpoint is not delayed by the analysis.

minimum fix scope:
Wrap transform.yml loading, validation, source resolution, and analyze_csv execution for this route in a threadpool-safe helper, then return the same response model.

repro:
Configure a large tabular source in transform.yml, then issue GET /api/templates/widget-suggestions/{group_by} concurrently with another API request; the second request can be delayed until the CSV analysis returns.

## medium: Async route blocks the FastAPI event loop while scanning CSVs

id: fnd_sig-feat-route-e4405fbb64-d9a896_62f5a9d87a
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /detect-relationships (feat_route_e4405fbb64)
next: clawpatch show --finding fnd_sig-feat-route-e4405fbb64-d9a896_62f5a9d87a

evidence:
- src/niamoto/gui/api/routers/smart_config.py:723-744 (detect_relationships)
- src/niamoto/core/imports/auto_config_service.py:168-207 (AutoConfigService.detect_relationships)
- src/niamoto/core/imports/auto_config_service.py:662-684 (AutoConfigService._read_csv_columns_and_rows)

The FastAPI handler is declared async but never awaits before doing synchronous disk I/O and CPU work through AutoConfigService.detect_relationships. In an async endpoint, that work runs on the event loop thread, so a request with many target files or slow filesystem reads can stall unrelated API requests served by the same worker. Neighboring smart_config endpoints already offload comparable service calls with asyncio.to_thread, which makes this route the inconsistent one.

recommendation:
Offload the synchronous service call, for example: return await asyncio.to_thread(service.detect_relationships, source_file=request.source_file, target_files=request.target_files). Alternatively make the endpoint a normal sync def so FastAPI runs it in the threadpool.

test analysis:
The linked route tests assert status codes and response bodies for normal and invalid inputs, but they do not exercise concurrent requests or assert that this async handler offloads blocking work.

suggested regression test:
Add an async route test that monkeypatches AutoConfigService.detect_relationships to block briefly, starts /detect-relationships, then verifies a second lightweight request can complete before the blocking call finishes; or monkeypatch asyncio.to_thread and assert the endpoint dispatches through it, matching the existing auto-configure threading test style.

minimum fix scope:
Change only src/niamoto/gui/api/routers/smart_config.py so detect_relationships dispatches AutoConfigService.detect_relationships through the threadpool, then add a focused route test for the offload behavior.

repro:
Send POST /api/smart/detect-relationships with a valid source CSV and a large list of target CSVs while issuing another lightweight API request to the same worker; the lightweight request waits until the relationship scan returns.

## medium: Async route performs blocking database and spatial work on the event loop

id: fnd_sig-feat-route-6e1e289f52-b00026_e9454c176b
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /spatial-map/{reference_name} (feat_route_6e1e289f52)
next: clawpatch show --finding fnd_sig-feat-route-6e1e289f52-b00026_e9454c176b

evidence:
- src/niamoto/gui/api/routers/stats.py:2875-2881 (get_spatial_map_inspection)
- src/niamoto/gui/api/routers/stats.py:2887-2895 (get_spatial_map_inspection)
- src/niamoto/gui/api/routers/stats.py:2671-2779 (_build_spatial_map_inspection)

FastAPI runs async route bodies on the event loop. This handler does not await anything; it opens the database and runs synchronous SQL/spatial processing directly through _build_spatial_map_inspection. For large spatial references or slow DuckDB spatial operations, one GET /spatial-map request can block the loop and delay unrelated API requests.

recommendation:
Make get_spatial_map_inspection a synchronous def so FastAPI dispatches it through the threadpool, or keep it async and wrap the database work in run_in_threadpool, matching the pattern used by get_import_summary.

test analysis:
The route tests use TestClient serially and assert response payloads; they do not exercise concurrent requests or event-loop responsiveness.

suggested regression test:
Add an async concurrency test that monkeypatches _build_spatial_map_inspection to block and verifies another async endpoint can still respond when /spatial-map is in flight.

minimum fix scope:
Change only the /spatial-map/{reference_name} handler dispatch path so synchronous database/spatial work runs off the event loop.

repro:
Issue concurrent requests where one calls /api/stats/spatial-map/{reference_name} against a large spatial table; while that request is inside the synchronous database/spatial section, other async endpoints on the same worker cannot progress.

## medium: Async route runs blocking database work on the event loop

id: fnd_sig-feat-route-367db9e746-37012b_a1dbe73354
category: performance
confidence: high
triage: risk
status: open
feature: FastAPI route GET /value-validation/{entity} (feat_route_367db9e746)
next: clawpatch show --finding fnd_sig-feat-route-367db9e746-37012b_a1dbe73354

evidence:
- src/niamoto/gui/api/routers/stats.py:3390-3391 (get_value_validation)
- src/niamoto/gui/api/routers/stats.py:3415-3424 (get_value_validation)
- src/niamoto/gui/api/routers/stats.py:3461-3468 (get_value_validation)
- src/niamoto/gui/api/routers/stats.py:3522-3529 (get_value_validation)

The handler is declared async but performs synchronous database connection and multiple aggregate, percentile, sample, and histogram queries inline for every numeric column. In FastAPI, blocking work inside an async route runs on the event loop, so a large value-validation request can stall unrelated GUI API requests until the database loop completes.

recommendation:
Move the database-heavy body into a synchronous helper and either make the route a normal def handler or call the helper through run_in_threadpool so FastAPI does not run this workload on the event loop.

test analysis:
The provided context test file tests/cli/test_stats.py exercises the CLI stats command, not this FastAPI route. The GUI route tests cover response values and validation errors but do not assert that value-validation is dispatched off the event loop.

suggested regression test:
Add a router test similar to the existing sync-handler guard for heavy stats endpoints, asserting not inspect.iscoroutinefunction(stats_router.get_value_validation) if the route is converted to def, or add a concurrency test that monkeypatches the DB helper to block and verifies another async request can still complete.

minimum fix scope:
Change only get_value_validation dispatch structure: keep its response model and SQL behavior, but execute the existing DB work outside the event loop.

repro:
Issue GET /api/stats/value-validation/{large_entity} against an entity with many numeric columns while making another lightweight API request; the second request can be delayed because the event loop is occupied by synchronous DB work.

## medium: Async schema route blocks the FastAPI event loop during database introspection

id: fnd_sig-feat-route-654f864f9c-57adcc_fc27126a70
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /schema (feat_route_654f864f9c)
next: clawpatch show --finding fnd_sig-feat-route-654f864f9c-57adcc_fc27126a70

evidence:
- src/niamoto/gui/api/routers/database.py:125-137 (get_database_schema)
- src/niamoto/gui/api/routers/database.py:145-184 (get_database_schema)

The handler is declared async, so FastAPI executes it on the event loop, but it performs synchronous filesystem access, opens a synchronous SQLAlchemy database connection, reflects metadata, and runs COUNT(*) queries for every table and view. On large DuckDB or SQLite projects, a single GET /schema request can monopolize the event loop and delay unrelated API requests from the same worker.

recommendation:
Make get_database_schema a synchronous def route so FastAPI runs it in the threadpool, or move the blocking schema collection into run_in_threadpool while keeping the HTTP wrapper async.

test analysis:
The linked route test exercises a tiny DuckDB fixture and asserts the response payload, but it does not assert that GET /schema runs outside the event loop or remains responsive under concurrent requests. The existing threadpool-specific guard only covers get_table_stats, not get_database_schema.

suggested regression test:
Add a test mirroring test_table_stats_route_is_sync_for_threadpool_execution that asserts database_router.get_database_schema is not a coroutine function, or add an async concurrency test that monkeypatches introspection to block and verifies another request can complete.

minimum fix scope:
Change only the GET /schema route execution boundary; the schema response model and introspection logic can remain unchanged.

repro:
Serve the GUI API with one worker, create a project database with several large tables, request GET /api/database/schema, and concurrently request a lightweight endpoint such as health; the lightweight request is delayed until schema introspection yields or completes.

## medium: Batch fusion extraction can wipe out an entire branch after one extraction failure

id: fnd_sig-feat-library-c6e9398720-af7a_c764665fb4
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source ml/scripts/train (feat_library_c6e9398720)
next: clawpatch show --finding fnd_sig-feat-library-c6e9398720-af7a_c764665fb4

evidence:
- ml/scripts/train/train_fusion.py:154-177 (extract_fusion_branch_probabilities_batch)
- ml/scripts/train/train_fusion.py:179-200 (extract_fusion_branch_probabilities_batch)
- ml/scripts/train/train_fusion.py:386-404 (extract_fusion_features_batch)

The batch path handles branch failures at whole-batch granularity. For the value branch, any exception while extracting features or predicting probabilities leaves aligned_value as the all-zero matrix for every record in that batch. For the header branch, text construction happens before the try block and prediction failures similarly zero the whole header branch. This contradicts the advertised same-result-as-record-by-record contract and can silently train or evaluate the fusion model on corrupted branch features because the training path uses this batch helper.

recommendation:
Handle branch extraction per record for recoverable failures, or collect per-record failures while preserving successful rows. If batch predict_proba fails, either fall back to per-record prediction or raise a clear training error instead of returning all-zero features for the whole branch.

test analysis:
No linked tests are declared for this feature. The existing batch equivalence coverage only exercises the happy path where both branch models succeed, so it cannot catch failure-induced divergence from the single-record path.

suggested regression test:
Add a fusion batch test with a fake value model or monkeypatched extractor that fails for one record and assert successful records still match extract_fusion_branch_probabilities, or assert the batch helper raises rather than zeroing the whole branch.

minimum fix scope:
Update ml/scripts/train/train_fusion.py batch branch probability extraction error handling and add focused regression coverage.

repro:
Create two records and monkeypatch extract_value_features or a branch model so only the second record raises. The single-record helper preserves probabilities for the first record; extract_fusion_branch_probabilities_batch returns zero value probabilities for both records or aborts for header text failures.

## medium: Behavioral tests can pass without validating their named behavior

id: fnd_sig-feat-test-suite-ae17aa3ff9-a_13de2d9c97
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/transformers/geospatial (feat_test-suite_ae17aa3ff9)
next: clawpatch show --finding fnd_sig-feat-test-suite-ae17aa3ff9-a_13de2d9c97

evidence:
- tests/core/plugins/transformers/geospatial/test_raster_stats.py:624-639 (TestCalculateStatistics.test_calculate_statistics_with_area)
- tests/core/plugins/transformers/geospatial/test_vector_overlay.py:430-442 (TestClipOperation.test_perform_clip_with_attribute)
- tests/core/plugins/transformers/geospatial/test_vector_overlay.py:734-756 (TestTransformIntegration.test_transform_crs_mismatch_handling)

These tests are intended to cover area statistics, clipped attributes, and CRS mismatch handling, but their assertions do not require those behaviors to be correct. The raster area test only asserts that min is present, the clip attribute test skips the attribute assertion when clipped_features is empty, and the CRS mismatch test only asserts the result is not None.

recommendation:
Strengthen the assertions to require the target behavior: assert total_area/area_unit or a specific controlled area result, assert clipped_features is non-empty and contains expected attribute values, and assert CRS mismatch handling yields the expected non-empty overlay stats/features after reprojection.

test analysis:
The current tests mostly assert unrelated keys, permissive presence checks, or non-null results, so regressions in the named behavior can still pass.

suggested regression test:
Monkeypatch or temporarily mutate each target branch to omit area calculation, omit clipped feature attributes, or skip overlay reprojection; the corresponding test should fail.

minimum fix scope:
Update the assertions in the existing tests; no production change is required.

## medium: Blocking filesystem and geospatial reads run on the event loop

id: fnd_sig-feat-route-b16bd086e5-649c3b_48c10ef9ca
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET  (feat_route_b16bd086e5)
next: clawpatch show --finding fnd_sig-feat-route-b16bd086e5-649c3b_48c10ef9ca

evidence:
- src/niamoto/gui/api/routers/layers.py:157-160 (list_layers)
- src/niamoto/gui/api/routers/layers.py:181-198 (list_layers)
- src/niamoto/gui/api/routers/layers.py:211-212 (list_layers)
- tests/gui/api/routers/test_layers.py:40-41 (test_get_layer_info_runs_as_sync_threadpool_route)

The list route is declared async but performs recursive filesystem scanning, stat calls, and by default rasterio/geopandas/pyogrio metadata reads directly in the coroutine. In FastAPI, blocking work inside an async route runs on the event loop, so a workspace with many or slow geospatial files can stall unrelated GUI API requests. The tests explicitly protect the heavier per-layer route as a sync threadpool route, but there is no equivalent protection for the list route even though it performs the same metadata extraction by default.

recommendation:
Make list_layers a synchronous def route so FastAPI runs it in the threadpool, or keep the route async but offload the blocking scan/metadata work with run_in_threadpool. Consider defaulting include_metadata to false if metadata extraction is optional and expensive.

test analysis:
The existing tests cover response shape and missing working directory behavior for GET /api/layers, and they assert only get_layer_info is sync. They do not assert list_layers is protected from blocking the event loop or exercise concurrent requests during metadata extraction.

suggested regression test:
Add a test mirroring test_get_layer_info_runs_as_sync_threadpool_route that asserts list_layers is not a coroutine function, or an async concurrency test that monkeypatches metadata extraction to block and verifies another request can still complete promptly.

minimum fix scope:
Change only the list_layers execution model and update/add the route-level regression test.

repro:
Create an imports directory containing many large vector/raster layers, call GET /api/layers with default include_metadata=true, and concurrently call another lightweight GUI API endpoint. The lightweight request can be delayed until the blocking layer scan yields or finishes.

## medium: Blocking suggestion work runs on the FastAPI event loop

id: fnd_sig-feat-route-9d5ebd4604-c0b7c3_d2a3967e9c
category: performance
confidence: high
triage: risk
status: open
feature: FastAPI route GET /{reference_name}/suggestions (feat_route_9d5ebd4604)
next: clawpatch show --finding fnd_sig-feat-route-9d5ebd4604-c0b7c3_d2a3967e9c

evidence:
- src/niamoto/gui/api/routers/templates.py:234-240 (get_reference_suggestions)
- src/niamoto/gui/api/routers/templates.py:259-325 (get_reference_suggestions)
- src/niamoto/gui/api/routers/templates.py:337-350 (get_reference_suggestions)
- src/niamoto/gui/api/routers/templates.py:421 (get_enrichment_catalog)

The route is declared async but performs plugin loading, filesystem/config reads, database access, profile conversion, template suggestion generation, and several synchronous suggestion service calls directly. In FastAPI, synchronous work inside an async handler blocks the event loop for the request duration, so one expensive suggestions request can stall unrelated API requests. The adjacent enrichment endpoint already uses run_in_threadpool for synchronous suggestion work, which shows the intended mitigation is available in this module.

recommendation:
Move the synchronous body into a helper and call it with await run_in_threadpool, or make this route a synchronous FastAPI handler so Starlette runs it in its threadpool. Keep response construction and error propagation equivalent.

test analysis:
The existing tests assert response content and validation behavior, but they do not exercise concurrent requests or detect event-loop starvation.

suggested regression test:
Add an async concurrency test that monkeypatches a suggestion helper to block and verifies another lightweight async route can respond while /suggestions is in flight, or at least assert the handler delegates the blocking suggestion builder through run_in_threadpool.

minimum fix scope:
Refactor get_reference_suggestions so all blocking suggestion generation runs off the event loop.

## medium: Build can delete the existing generated docs before a later failure

id: fnd_sig-feat-library-8b25f0076b-dd67_cafff8aef1
category: build-release
confidence: high
triage: risk
status: open
feature: Python source src/niamoto/gui/help_content (feat_library_8b25f0076b)
next: clawpatch show --finding fnd_sig-feat-library-8b25f0076b-dd67_cafff8aef1

evidence:
- src/niamoto/gui/help_content/builder.py:123-130 (build_help_content)
- src/niamoto/gui/help_content/builder.py:286-287 (_discover_pages)
- src/niamoto/gui/help_content/builder.py:325-326 (_read_source_document)

`build_help_content` removes the current `pages`, `assets`, manifest, and search index before parsing every source document and before copying all assets. Any exception after the cleanup, for example malformed YAML frontmatter, unreadable source content, or a copy failure, leaves the package-local help-content directory empty or partially regenerated. Because the default output root is the shipped package directory, a failed release sync can turn a previously valid in-app docs pack into missing/corrupted build artifacts.

recommendation:
Generate into a staging directory, validate/render/copy everything there, then atomically replace the old generated directories and JSON files only after the build succeeds. Keep the old output intact on failure.

test analysis:
The existing tests cover successful generation and the explicit `output_root == docs_root` guard, but they do not simulate a failure after cleanup and assert that the previous generated pack remains intact.

suggested regression test:
Seed `output_root` with an existing manifest/page/asset, create a docs page with invalid YAML frontmatter, assert `build_help_content` raises and the original output files still exist unchanged.

minimum fix scope:
Change `build_help_content` output handling to use a temporary staging output and commit it atomically after all pages/assets/manifests are written successfully.

## medium: Bulk route can overwrite import.yml with non-object entity sections

id: fnd_sig-feat-route-3d77931dbf-ae5bd9_3ce0e07184
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /management/entities/bulk (feat_route_3d77931dbf)
next: clawpatch show --finding fnd_sig-feat-route-3d77931dbf-ae5bd9_3ce0e07184

evidence:
- src/niamoto/gui/api/routers/smart_config.py:888-889 (CreateEntitiesBulkRequest)
- src/niamoto/gui/api/routers/smart_config.py:921-927 (create_entities_bulk)
- src/niamoto/gui/api/routers/smart_config.py:957-964 (create_entities_bulk)
- src/niamoto/core/imports/config_models.py:288-291 (EntitiesConfig)

The request model accepts arbitrary values under entities, and the route writes datasets/references directly into config/import.yml without checking that they are mappings. A client can POST entities.datasets as a list or string; _validate_bulk_config_paths does not reject that shape, the temp file replaces the existing import.yml, and the response even computes len() on the invalid value. The persisted file then violates the import schema that expects entities.datasets and entities.references to be objects, so a single bad API request can replace a valid project import configuration with malformed YAML.

recommendation:
Before writing, require entities.datasets and entities.references to be dict-like sections, and reject any non-object value with 400. Prefer a small Pydantic request schema for the top-level sections, or validate the constructed import_config against the existing import config model if the auto-config output already matches that schema.

test analysis:
The linked smart_config tests cover valid mappings, empty entities, traversal rejection, auxiliary_sources, overwrites, and write-failure preservation, but they do not send malformed datasets/references shapes.

suggested regression test:
Add a POST /api/smart/management/entities/bulk test with entities.datasets as a list and an existing import.yml; assert status 400 and assert the original import.yml is unchanged.

minimum fix scope:
Validate the top-level entities.datasets and entities.references types inside create_entities_bulk before constructing import_config and before replacing config/import.yml.

repro:
POST /api/smart/management/entities/bulk with {"entities":{"datasets":["not","a","mapping"],"references":{}}}; the handler accepts the payload, writes entities.datasets as a YAML list, and returns success with dataset_count 3.

## medium: Cached enrichment payloads are returned by reference and can be corrupted by callers

id: fnd_sig-feat-library-1ec3b98877-50ad_e9b5c47556
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/loaders (feat_library_1ec3b98877)
next: clawpatch show --finding fnd_sig-feat-library-1ec3b98877-50ad_e9b5c47556

evidence:
- src/niamoto/core/plugins/loaders/api_elevation_enricher.py:112-119 (ApiElevationEnricher.load_data)
- src/niamoto/core/plugins/loaders/api_elevation_enricher.py:135-146 (ApiElevationEnricher.load_data)
- src/niamoto/core/plugins/loaders/api_spatial_enricher.py:120-127 (ApiSpatialEnricher.load_data)
- src/niamoto/core/plugins/loaders/api_spatial_enricher.py:143-154 (ApiSpatialEnricher.load_data)
- src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py:382-404 (ApiTaxonomyEnricher.load_data)
- src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py:585-603 (ApiTaxonomyEnricher.load_data)

The loaders store mutable dict/list payloads in class-level caches and later attach the exact cached objects to returned result dictionaries. A downstream consumer that mutates api_enrichment, api_response_processed, or api_response_raw on one returned row mutates the cache itself, so future calls for the same key can return contaminated enrichment data without another API request.

recommendation:
Deep-copy payloads when writing to and reading from the cache, or treat cached objects as immutable and return defensive copies from every cache hit path.

test analysis:
The existing taxonomy cache test only verifies call count and equality across two unmodified results; it never mutates the first returned payload before reading from cache.

suggested regression test:
Add a cache test that mutates the first returned api_enrichment nested dict/list, calls load_data again with the same cache key, and asserts the second result contains the original API-derived values.

minimum fix scope:
Update the three API enrichment loaders' cache-hit and cache-store paths to use copy.deepcopy for mapped, processed, and raw payloads.

repro:
Call an API enricher with cache_results=True, mutate result1["api_enrichment"] or a nested value, then call load_data again with the same entity/config. The second result will expose the mutation because cached["mapped"] is reused by reference.

## medium: Cancellation marks the job terminal before the transform thread has stopped

id: fnd_sig-feat-route-6eb697214c-cdceaa_740c83302e
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route DELETE /jobs/{job_id} (feat_route_6eb697214c)
next: clawpatch show --finding fnd_sig-feat-route-6eb697214c-cdceaa_740c83302e

evidence:
- src/niamoto/gui/api/routers/transform.py:317-324 (execute_transform_background)
- src/niamoto/gui/api/routers/transform.py:538-544 (cancel_transform_job)
- src/niamoto/gui/api/services/job_file_store.py:137-150 (JobFileStore.cancel_job)
- src/niamoto/gui/api/services/job_file_store.py:199-208 (JobFileStore.get_running_job)

DELETE /jobs/{job_id} immediately persists the transform job as the terminal status cancelled, but the actual transform work is running inside asyncio.to_thread and only observes cancellation at progress callbacks or after transform_data returns. Because cancelled is terminal, get_running_job stops treating the work as active while the thread may still be mutating transform tables. A user can therefore start another transform after DELETE returns, creating overlapping writes in the same project database.

recommendation:
Make transform cancellation two-phase like the export route: mark the job as cancelling/requested while the worker is still alive, keep it non-terminal for concurrency guards, and have execute_transform_background mark it cancelled only after TransformCancelled is raised or transform_data returns after observing cancellation. Alternatively, block new transform creation on a separate in-flight worker flag until the background task exits.

test analysis:
The included tests/cli/test_transform.py exercises CLI transform commands, not this FastAPI route. The API cancel test present in tests/gui/api/routers/test_transform.py only stubs cancel_job and asserts the returned status/message; it does not run a background transform or verify that a second job remains blocked until the first worker has stopped.

suggested regression test:
Add an API test with a fake TransformerService.transform_data that waits on an event inside asyncio.to_thread. Start a transform, DELETE it, then assert POST /execute still returns 409 while the fake worker is blocked. Release the worker, let cancellation complete, and assert a new transform can then start.

minimum fix scope:
Change cancel_transform_job and execute_transform_background cancellation state handling for transform jobs; keep JobFileStore terminal cancellation only for the point where the background worker is actually finished.

repro:
Run a transform whose transformer_service.transform_data blocks for a while before invoking the progress callback. Call DELETE /jobs/{job_id}; it returns status cancelled immediately. Before the worker thread exits, call POST /execute again; the job store no longer reports a running job, so a second transform can start while the first is still executing.

## medium: Cancelling a selected export can leave the job stuck in cancelling

id: fnd_sig-feat-route-4981fe5cdf-1e1b7d_69e2dc76d7
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /execute (feat_route_4981fe5cdf)
next: clawpatch show --finding fnd_sig-feat-route-4981fe5cdf-1e1b7d_69e2dc76d7

evidence:
- src/niamoto/gui/api/routers/export.py:447-474 (execute_export_background)
- src/niamoto/gui/api/routers/export.py:520-528 (execute_export_background)
- src/niamoto/gui/api/routers/export.py:603-614 (execute_export_background)
- tests/gui/api/routers/test_export.py:179-205 (test_cancel_export_job_marks_running_job_cancelling)

DELETE /jobs/{job_id} moves an export job into the visible cancelling state. In the all-exports branch, the background worker eventually calls cancel_job when it observes cancellation. In the selected export_types branch, the worker only returns after observing cancellation, and the finally block only restores cwd and releases the lock. As a result, a cancellation requested while a specific target is running can finish the worker without ever transitioning the job to a terminal cancelled state.

recommendation:
Centralize cancellation finalization or call job_store.cancel_job before every cancellation return path, including the selected export loop and the include_transform post-transform cancellation checks. Preserve the all-exports behavior of waiting for the non-cooperative worker before releasing the cwd lock.

test analysis:
The tests cover that DELETE marks a job as cancelling, CLI cancellation reaches cancelled, and the all-exports background branch holds the cwd lock while cancelling. They do not cover cancellation of a specific export_types job after run_export returns.

suggested regression test:
Add an async test for execute_export_background with export_types=["web_pages"] using a cancellable dummy job store and a blocking exporter; request cancellation while run_export is active, release the exporter, and assert cancel_job was called and the completed/failed callbacks were not called.

minimum fix scope:
Cancellation handling in execute_export_background plus one targeted test in tests/gui/api/routers/test_export.py.

repro:
Start /api/export/execute with export_types set to a specific target whose run_export blocks briefly, call DELETE /api/export/jobs/{job_id}, then let run_export return. The background task exits at the cancellation check without calling cancel_job, so polling /api/export/status/{job_id} remains at cancelling.

## medium: Cancelling a selected export can leave the job stuck in cancelling

id: fnd_sig-feat-route-57ca612246-499d1e_300f6579ae
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route DELETE /jobs/{job_id} (feat_route_57ca612246)
next: clawpatch show --finding fnd_sig-feat-route-57ca612246-499d1e_300f6579ae

evidence:
- src/niamoto/gui/api/routers/export.py:39 (ExportRequest.export_types)
- src/niamoto/gui/api/routers/export.py:469-474 (execute_export_background)
- src/niamoto/gui/api/routers/export.py:744-762 (cancel_export_job)
- src/niamoto/gui/api/routers/export.py:631-637 (execute_export)
- tests/gui/api/routers/test_export.py:179-208 (test_cancel_export_job_marks_running_job_cancelling)

DELETE /jobs/{job_id} marks the job as cancelling. In the selected-export path, execute_export_background awaits the blocking run_export call directly and, after it finishes, returns as soon as it sees the cancelling state. That path never calls cancel_job, complete_job, or fail_job, so the active job can remain non-terminal after the worker has already stopped. Because new exports reject any running/non-terminal job, this can block future export starts until the job file is manually cleared or overwritten.

recommendation:
When a cancellation is observed after a selected export or transform completes, transition the job to a terminal cancelled state before returning. Consider a small helper such as _finish_cancelled_job(job_store, job_id) and call it at every _job_is_cancelled return point after the job has been accepted.

test analysis:
The existing route test only verifies the immediate DELETE response and status transition to cancelling on a store-created job. It does not run execute_export_background with export_types while cancellation is requested, so it misses the non-terminal lifecycle outcome.

suggested regression test:
Add an anyio test that starts execute_export_background with export_types=["web_pages"], uses a dummy ExporterService that waits until the test requests cancellation, then returns success; assert the final job status is cancelled and that a new export job can be created.

minimum fix scope:
Update src/niamoto/gui/api/routers/export.py cancellation handling in execute_export_background for selected exports, and add a focused test in tests/gui/api/routers/test_export.py.

repro:
Start an export with export_types set to a specific target, issue DELETE /api/export/jobs/{job_id} while ExporterService.run_export is running, then let run_export return successfully. GET /api/export/status/{job_id} remains cancelling and a subsequent POST /api/export/execute returns 409.

## medium: Cancelling selected exports can leave the job stuck in non-terminal state

id: fnd_sig-feat-library-9282ce0cc6-e684_b6eaa64eeb
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/routers#1 (feat_library_9282ce0cc6)
next: clawpatch show --finding fnd_sig-feat-library-9282ce0cc6-e684_b6eaa64eeb

evidence:
- src/niamoto/gui/api/routers/export.py:631-636 (execute_export)
- src/niamoto/gui/api/routers/export.py:745-747 (cancel_export_job)
- src/niamoto/gui/api/routers/export.py:469-474 (execute_export_background)
- src/niamoto/gui/api/routers/export.py:520-528 (execute_export_background)

The cancel endpoint moves jobs into a cancellling/non-terminal state. In the all-exports branch, cancellation is finalized with cancel_job, but the selected export_types path returns immediately after the worker thread completes without marking the job cancelled. Because execute_export rejects any non-terminal running job, that stale cancelling job can block future exports.

recommendation:
Centralize cancellation finalization so every _job_is_cancelled return path records a terminal cancelled status, including selected export targets and post-transform checks.

test analysis:
The included export tests cover CLI export behavior, not the GUI background export cancellation path for selected export targets.

suggested regression test:
Add an async router test that uses a fake JobFileStore, triggers request_cancellation while a selected target export is running, completes the fake run_export, and asserts the final job status is cancelled and a new job can be created.

minimum fix scope:
Update execute_export_background cancellation branches to call job_store.cancel_job before returning, or wrap the cancelled check in a helper that finalizes consistently.

repro:
Start /api/export/execute with export_types set to one long-running target, call DELETE /api/export/jobs/{job_id} while run_export is in progress, then wait for run_export to return. The background task exits at the cancellation check without calling cancel_job, so subsequent /execute calls see a non-terminal active job and return 409.

## medium: Cascade deduplication drops valid same-name plugins of different types

id: fnd_sig-feat-library-c7e00644cc-4892_90823f25c0
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins (feat_library_c7e00644cc)
next: clawpatch show --finding fnd_sig-feat-library-c7e00644cc-4892_90823f25c0

evidence:
- src/niamoto/core/plugins/plugin_loader.py:124-145 (PluginLoader.load_plugins_with_cascade)
- src/niamoto/core/plugins/registry.py:28-35 (PluginRegistry)
- tests/core/plugins/test_registry.py:86-106 (TestPluginRegistry.test_metadata_is_isolated_by_plugin_type)

The registry intentionally scopes plugin names by PluginType, and the tests confirm same-name plugins of different types can coexist. The cascade loader, however, stores discovered candidates in a dict keyed only by plugin_name, so a loader, transformer, widget, exporter, or deployer sharing a name with another type is treated as a conflict and one valid plugin is skipped.

recommendation:
Key cascade discovery and conflict checks by (PluginType, plugin_name), and make PluginInfo expose or cache the resolved PluginType so conflicts are detected only within the same type.

test analysis:
tests/core/plugins/test_registry.py verifies type-scoped registry behavior, but the included loader tests do not exercise load_plugins_with_cascade or _discover_plugins_in_location with same-name plugins across different PluginType values.

suggested regression test:
Add a cascade test with a same-name loader and transformer and assert PluginRegistry.has_plugin(name, PluginType.LOADER) and PluginRegistry.has_plugin(name, PluginType.TRANSFORMER) are both true after loading.

minimum fix scope:
PluginLoader discovered_plugins keying plus loader tests for cross-type same-name plugins.

repro:
Create two plugins named 'shared_plugin', one LOADER and one TRANSFORMER, in any scanned cascade locations. load_plugins_with_cascade records only one key in discovered_plugins, so only one type is tracked/loaded even though PluginRegistry supports both.

## medium: Cascade loading cannot override plugins already registered from a lower-priority scope

id: fnd_sig-feat-library-c7e00644cc-c4a1_d81d54b09f
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins (feat_library_c7e00644cc)
next: clawpatch show --finding fnd_sig-feat-library-c7e00644cc-c4a1_d81d54b09f

evidence:
- src/niamoto/core/plugins/plugin_loader.py:218-223 (PluginLoader._discover_plugins_in_location)
- src/niamoto/core/plugins/plugin_loader.py:244-257 (PluginLoader._discover_plugins_in_location)
- src/niamoto/core/plugins/registry.py:67-89 (PluginRegistry.register_plugin)

Discovery executes each plugin module immediately, so decorators mutate the global PluginRegistry before the loader has decided the cascade winner. If a previous loader call registered a system plugin, a later project plugin with the same name and type raises PluginRegistrationError during discovery and is skipped as though the existing lower-priority plugin were higher-priority. This violates the documented project > user > system cascade and can leave custom project overrides inactive in long-lived processes or repeated loads.

recommendation:
Make cascade discovery independent of the current global registry. For example, capture decorator registrations during discovery without mutating PluginRegistry, key the discovered candidates with their priority, then update the registry only after selecting winners; alternatively clear/unregister only lower-priority conflicts before importing higher-priority candidates.

test analysis:
The included plugin loader tests cover failed imports, reload rollback, and successful discover_plugins cleanup, but they do not call load_plugins_with_cascade with a pre-populated registry containing a lower-priority conflicting plugin.

suggested regression test:
Add a test that first registers a lower-priority plugin class, then loads a project plugin with the same name/type through load_plugins_with_cascade and asserts the project class is registered and tracked.

minimum fix scope:
PluginLoader discovery/registration flow, with a targeted cascade regression test.

repro:
Register or load a system plugin named X, then create a project plugin with @register('X', same PluginType) and call load_plugins_with_cascade(project_path) without clearing PluginRegistry. The project plugin is skipped during discovery and the system class remains registered.

## medium: children_properties is ignored for extracted child geometries

id: fnd_sig-feat-library-87cb77a4b6-4f42_def7b13200
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/extraction (feat_library_87cb77a4b6)
next: clawpatch show --finding fnd_sig-feat-library-87cb77a4b6-4f42_def7b13200

evidence:
- src/niamoto/core/plugins/transformers/extraction/geospatial_extractor.py:137-139 (GeospatialExtractorParams.children_properties)
- src/niamoto/core/plugins/transformers/extraction/geospatial_extractor.py:496-510 (GeospatialExtractor.transform)
- src/niamoto/core/plugins/transformers/extraction/geospatial_extractor.py:617-622 (GeospatialExtractor.transform)
- tests/core/plugins/transformers/extraction/test_geospatial_extractor.py:582-601 (TestGeospatialExtractorTransform.test_transform_with_external_source_failure_raises)

The config model exposes children_properties specifically for properties to include when extract_children is true, but transform always uses params.properties for output filtering. When child rows are loaded via _get_children_from_source, children_properties is never read, so a config with extract_children=true and children_properties=['name'] will return child features without the requested child fields unless the same fields are duplicated in properties.

recommendation:
When extract_children is true, use children_properties as the property list for the output, or merge it with properties if both parent and child properties are intentionally supported.

test analysis:
The geospatial tests cover external source loading, missing fields, invalid geometries, and grouped points, but none assert the output properties for extract_children with children_properties populated.

suggested regression test:
Add a geospatial extractor transform test with extract_children=true, children_properties=['name'], properties=[], and child rows containing geometry plus name; assert each returned feature includes the name property.

minimum fix scope:
Update GeospatialExtractor.transform property selection for the extract_children path and add one focused regression test.

repro:
Call GeospatialExtractor.transform with source='plots', extract_children=true, children_properties=['child_name'], properties=[], and a mocked _get_children_from_source returning child rows with geometry and child_name. The returned GeoJSON features omit child_name because only params.properties is consulted.

## medium: Class-object numeric validation only checks one value

id: fnd_sig-feat-library-705734df4d-643b_f135f514ef
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/imports#1 (feat_library_705734df4d)
next: clawpatch show --finding fnd_sig-feat-library-705734df4d-643b_f135f514ef

evidence:
- src/niamoto/core/imports/class_object_analyzer.py:196-200 (ClassObjectAnalyzer.analyze)
- src/niamoto/core/imports/class_object_analyzer.py:280-289 (ClassObjectAnalyzer._analyze_class_object)

The analyzer intends to validate that `class_value` is numeric, but the validation query casts only one non-null row. A later non-numeric value can either crash during per-class sample extraction or be missed entirely if it is outside the first five rows for that class object, returning `is_valid=True` for invalid data.

recommendation:
Validate the whole column with `TRY_CAST(class_value AS DOUBLE)` and count/report rows where the original value is non-null but the cast result is null. Reuse the safe cast for sample extraction so invalid data returns `is_valid=False` instead of raising.

test analysis:
The analyzer tests cover missing required columns and valid numeric data, but there is no malformed numeric `class_value` case.

suggested regression test:
Add a CSV fixture with a non-numeric `class_value` after an initial numeric row and assert `analysis.is_valid is False` with a numeric validation error, without raising from `analyze_csv`.

minimum fix scope:
Replace the single-row cast validation with full-column `TRY_CAST` validation in `ClassObjectAnalyzer.analyze` and make sample extraction robust to invalid values.

repro:
Create a class-object CSV where the first `class_value` is `1.0` and a later row has `class_value='bad'`; the validation step can pass because of `LIMIT 1`, and the invalid row is not reliably reported as a validation error.

## medium: CLI export job can deadlock when stdout or stderr fills its pipe

id: fnd_sig-feat-route-966951e705-2523bd_71cc2b71bc
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /execute-cli (feat_route_966951e705)
next: clawpatch show --finding fnd_sig-feat-route-966951e705-2523bd_71cc2b71bc

evidence:
- src/niamoto/gui/api/routers/export.py:907-914 (execute_export_cli.run_export_command)
- src/niamoto/gui/api/routers/export.py:916-942 (execute_export_cli.run_export_command)
- tests/gui/api/routers/test_export.py:210-218 (TestExportHistory.test_execute_cli_job_is_visible_to_export_job_endpoints)

The route starts `niamoto export` with both output streams piped, but it does not drain either stream while the subprocess is running. It repeatedly waits for process exit and only calls `communicate()` after `process.returncode` is no longer `None`. If the CLI writes enough output to fill stdout or stderr, the child blocks on write, never exits, and this loop never reaches `communicate()`. The active export job then remains non-terminal and `get_running_job()` will make later export attempts return 409.

recommendation:
Drain stdout and stderr concurrently while the process runs. One safe shape is to create a `communicate()` task immediately and race it against cancellation polling; on cancellation, terminate/kill the process and then await the communicate task to collect remaining output. Alternatively, consume both stream readers in background tasks before awaiting `process.wait()`.

test analysis:
The execute-cli tests use fake process objects that return small in-memory byte strings and do not model real pipe backpressure. The cancellation test also fakes `wait()` and `communicate()` rather than exercising `asyncio.subprocess.PIPE` behavior.

suggested regression test:
Add an async test for `execute_export_cli` where the subprocess fake keeps `returncode=None` until its stdout/stderr are consumed, or use a real Python subprocess that writes more than the pipe buffer and assert the job reaches a terminal state.

minimum fix scope:
Change only `execute_export_cli.run_export_command` subprocess handling so output is drained while waiting and cancellation still terminates the child process.

repro:
Use a test double for `asyncio.create_subprocess_exec` that writes more than the OS pipe buffer to stdout/stderr before exiting, or run a verbose `niamoto export` that emits enough output. The background task remains running and `/api/export/status/{job_id}` never reaches completed or failed.

## medium: Cloudflare upload test collapses distinct files into one hash

id: fnd_sig-feat-test-suite-3dcab2a2f8-9_2b780ed136
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/deployers (feat_test-suite_3dcab2a2f8)
next: clawpatch show --finding fnd_sig-feat-test-suite-3dcab2a2f8-9_2b780ed136

evidence:
- tests/core/plugins/deployers/test_cloudflare.py:125-129 (test_cloudflare_deployer_uploads_manifest_and_returns_branch_url)
- tests/core/plugins/deployers/test_cloudflare.py:159-162 (test_cloudflare_deployer_uploads_manifest_and_returns_branch_url)
- tests/core/plugins/deployers/test_cloudflare.py:190-202 (test_cloudflare_deployer_uploads_manifest_and_returns_branch_url)

The test creates two different export files but monkeypatches every file hash to the same value and then expects only one uploaded bucket entry. That means the suite does not prove that Cloudflare deployments preserve the one-to-one relationship between distinct file contents, manifest hashes, and uploaded asset payloads. A regression that accidentally reuses one hash or uploads the wrong file for a hash could pass this test while producing missing or corrupted deployed assets.

recommendation:
Let the real hash function run, or compute deterministic expected hashes for the two fixture files, and assert that both unique hashes appear in the manifest and upload payloads. Keep a separate explicit deduplication/collision-style test only if that behavior is intentional.

test analysis:
The current Cloudflare success test intentionally replaces hashing with a constant, so it covers the same-hash case rather than the normal multi-file unique-hash case.

suggested regression test:
Create two files with different contents, avoid monkeypatching _hash_file, return both hashes from the fake upload-session buckets, and assert that both multipart entries contain the matching file contents.

minimum fix scope:
Update tests/core/plugins/deployers/test_cloudflare.py only.

## medium: ColumnClassifier tests never exercise the fusion path

id: fnd_sig-feat-test-suite-5496f416d9-0_19b48b0e14
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/imports#2 (feat_test-suite_5496f416d9)
next: clawpatch show --finding fnd_sig-feat-test-suite-5496f416d9-0_19b48b0e14

evidence:
- tests/core/imports/test_column_classifier.py:39-43 (test_classify_many_batches_header_and_value_predictions)
- tests/core/imports/test_column_classifier.py:52-56 (test_classify_many_batches_header_and_value_predictions)

The test configures only the header and value models, with both branches returning the same class and the asserted confidence coming from the header branch. It proves batching and call counts, but it does not cover the runtime fusion model path, class-space alignment, or fused prediction result. A regression that breaks fusion feature construction or ignores the fusion model entirely would still leave this test green.

recommendation:
Add a classifier test that sets `_fusion_model` and `_fusion_concepts` to a small dummy model, gives header/value models different class probabilities, and asserts `classify_many` returns the fusion model's selected class and confidence while preserving one batched call per branch.

test analysis:
The included classifier test intentionally leaves `_fusion_model` unset, so `classify_many` follows the non-fusion fallback path only.

suggested regression test:
Create dummy header/value models with two concepts and a dummy fusion model whose `predict_proba` records the feature matrix and returns a third deterministic probability vector; assert the returned concept comes from the fusion model and that the dummy fusion saw one row per input column.

minimum fix scope:
One focused test in `tests/core/imports/test_column_classifier.py` plus any small helper dummy model classes needed for the fusion path.

## medium: Compressed JSON API outputs publish links to missing .json files

id: fnd_sig-feat-library-db85b6eec6-dd4d_2cc6e8e6a0
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/core/plugins/exporters (feat_library_db85b6eec6)
next: clawpatch show --finding fnd_sig-feat-library-db85b6eec6-dd4d_2cc6e8e6a0

evidence:
- src/niamoto/core/plugins/exporters/json_api_exporter.py:748-753 (JsonApiExporter._write_json_file)
- src/niamoto/core/plugins/exporters/json_api_exporter.py:1213-1216 (DataMapper._generate_endpoint_url)
- tests/core/plugins/exporters/test_json_api_exporter.py:407-428 (test_map_index_data_adds_detail_url_when_not_configured)

When compress is enabled, detail and index writes only create files such as taxon/1.json.gz and all_taxon.json.gz. The index detail_url generator still advertises the uncompressed detail_output_pattern, such as /api/taxon/1.json, and no uncompressed file is written. This breaks the static API navigation contract documented by the tests that index rows should link to matching detail JSON.

recommendation:
Either write the uncompressed .json alongside the .gz precompressed variant, or make all generated URLs and index filenames consistently include .gz when compression changes the public filename. The former is usually safer for static hosting compatibility.

test analysis:
Compression is only tested by asserting gzip.open is called; no test combines compression with detail generation plus index detail_url resolution or verifies that the advertised URL exists on disk.

suggested regression test:
Run _generate_detail_file and _generate_index_file with JsonOptions(compress=True), then assert every generated index detail_url resolves to an existing file or that an uncompressed .json file exists for the URL.

minimum fix scope:
JSON API file writing and URL generation contract for compressed outputs.

repro:
Set json_options.compress=true for a group with the default detail_output_pattern. Export one item. The generated detail file is taxon/<id>.json.gz, while the index row's detail_url is /api/taxon/<id>.json.

## medium: Config updater writes legacy top-level import.yml sections instead of current entity schema

id: fnd_sig-feat-library-4638bcbf5d-c96b_069e6c9223
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/gui/api/utils (feat_library_4638bcbf5d)
next: clawpatch show --finding fnd_sig-feat-library-4638bcbf5d-c96b_069e6c9223

evidence:
- src/niamoto/gui/api/utils/config_updater.py:98 (update_import_config)
- src/niamoto/gui/api/utils/config_updater.py:132-134 (update_import_config)
- src/niamoto/gui/api/utils/config_updater.py:136-146 (update_import_config)
- src/niamoto/gui/api/utils/config_updater.py:180-205 (update_import_config)
- tests/gui/api/utils/test_config_updater.py:41-49 (test_update_import_config_writes_plots_without_advanced_options)

The helper claims to update Niamoto import.yml for GUI imports, but it emits legacy top-level keys such as taxonomy, plots, occurrences, and shapes. The current import configuration model in this project is entity-based, under entities.datasets and entities.references, so a config generated by this utility is not consumable by the active import pipeline and can leave users with an import.yml that looks saved but is ignored or rejected by current code. The linked tests currently lock in the legacy top-level shape rather than validating compatibility with the active schema.

recommendation:
Rewrite update_import_config and clean_unused_config around the current GenericImportConfig shape: create or update entities.datasets.occurrences and entities.references entries for taxonomy/plots/shapes, preserving version and unrelated entities. Retire or migrate the legacy top-level schema handling if it is no longer supported.

test analysis:
The existing config updater tests assert the obsolete top-level YAML output directly and never load the generated file through Config.get_imports_config or the generic import models.

suggested regression test:
Generate each import type with update_import_config, then load the resulting import.yml through the current config/import model and assert the expected entity exists under entities.datasets or entities.references with a valid connector/schema.

minimum fix scope:
Update src/niamoto/gui/api/utils/config_updater.py and replace the legacy-shape assertions in tests/gui/api/utils/test_config_updater.py with current entity-schema assertions.

repro:
Call update_import_config(config_path, "plots", "plots.csv", {"identifier": "id_plot", "locality": "plot_name", "location": "geo_pt"}) on an empty import.yml. The file contains only a top-level plots section, with no version or entities.references/datasets structure for the generic importer to load.

## medium: Configured class_object defaults ask widgets for labels that transformer emulation never returns

id: fnd_sig-feat-library-3a8da0b259-a8c3_b7daa64899
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/services/templates (feat_library_3a8da0b259)
next: clawpatch show --finding fnd_sig-feat-library-3a8da0b259-a8c3_b7daa64899

evidence:
- src/niamoto/gui/api/services/templates/utils/class_object_rendering.py:101-121 (_execute_configured_transformer)
- src/niamoto/gui/api/services/templates/utils/class_object_rendering.py:185-195 (_execute_configured_transformer)
- src/niamoto/gui/api/services/templates/utils/class_object_rendering.py:318-343 (_build_widget_params_for_configured)
- src/niamoto/gui/api/services/templates/utils/class_object_rendering.py:351-353 (_build_widget_params_for_configured)

The emulated class_object binary/categories transformers return label data under tops, but the configured widget default params point bar_plot and donut_chart at labels. When export.yml does not provide an explicit remap, rendering receives data without the requested labels key and the widget reports missing input columns or renders an error instead of a preview.

recommendation:
Use tops as the default label field for configured class_object outputs, or add a labels alias before rendering whenever the helper selects labels.

test analysis:
The existing class_object_rendering tests explicitly allow params["x_axis"] == "labels" even when labels is not in the transformer result, so they document the current mismatch rather than failing on it.

suggested regression test:
Tighten the binary and categories configured-widget tests to assert every default axis/field selected by _build_widget_params_for_configured exists in the emulated transformer result.

minimum fix scope:
src/niamoto/gui/api/services/templates/utils/class_object_rendering.py: change configured class_object bar_plot/donut defaults, or normalize data with labels = tops before plugin rendering.

repro:
Call _execute_configured_transformer("class_object_binary_aggregator", {"groups": [{"field": "is_endemic"}]}, {"is_endemic": {"tops": ["Endemic"], "counts": [1]}}, "plots"), then _build_widget_params_for_configured("class_object_binary_aggregator", "bar_plot", result, "Endemic"); params["x_axis"] is "labels" while result only has tops/counts.

## medium: Configured endpoint omits export-only widgets saved by the same workflow

id: fnd_sig-feat-route-ccfc8564f2-c6e582_cbfdaaaa69
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /{group_by}/configured (feat_route_ccfc8564f2)
next: clawpatch show --finding fnd_sig-feat-route-ccfc8564f2-c6e582_cbfdaaaa69

evidence:
- src/niamoto/gui/api/routers/templates.py:56-58 (_is_export_only_widget_config)
- src/niamoto/gui/api/routers/templates.py:939-944 (save_transform_config)
- src/niamoto/gui/api/routers/templates.py:995-999 (save_transform_config)
- src/niamoto/gui/api/routers/templates.py:1098-1101 (get_configured_widgets)

The save path deliberately filters hierarchical_nav_widget out of transform.yml, while still passing the original request widgets into export.yml generation. The configured endpoint only reads transform.yml widgets_data, so a saved export-only navigation widget will not be returned as configured. A client using this route to preselect saved widgets will treat that saved widget as missing.

recommendation:
Include configured export-only widget IDs by reading the matching export.yml group in addition to transform.yml, or change the save/read contract so export-only widgets have a canonical marker returned by this endpoint.

test analysis:
The existing route test only covers a transform.yml widget ID and does not save or read an export-only hierarchical_nav_widget.

suggested regression test:
Add a router test that writes a matching export.yml group with a hierarchical_nav_widget data_source and verifies GET /api/templates/{group_by}/configured returns that ID even when transform.yml omits it.

minimum fix scope:
Update get_configured_widgets to merge transform.yml widget IDs with export.yml IDs for export-only widgets, plus add the focused route regression test.

repro:
Save a group containing only a hierarchical_nav_widget, then call GET /api/templates/{group_by}/configured. The widget is persisted to export.yml but configured_ids is empty because transform.yml has no entry for it.

## medium: Configured occurrence geometry columns are ignored by the distribution route

id: fnd_sig-feat-route-8b3d0a7459-f8beaf_07841adc8c
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /geo-coverage/distribution (feat_route_8b3d0a7459)
next: clawpatch show --finding fnd_sig-feat-route-8b3d0a7459-f8beaf_07841adc8c

evidence:
- src/niamoto/gui/api/routers/stats.py:4096-4105 (get_geo_coverage)
- src/niamoto/gui/api/routers/stats.py:4511-4516 (get_shape_distribution)

The overview endpoint resolves the occurrence geometry column from import.yml metadata before falling back to name-based detection, but POST /geo-coverage/distribution only uses _find_geometry_column. A valid project whose occurrence geometry is configured in import.yml under a non-heuristic column name can be reported as ready by /geo-coverage and then fail distribution with status no_geo_column for the same dataset.

recommendation:
Mirror the occurrence geometry resolution used by get_geo_coverage: build columns_by_lower, resolve the dataset config with _resolve_dataset_config_for_table, use _find_configured_geometry_column, and recompute occ_geo_is_native when the configured column differs from the detected column.

test analysis:
The linked test file exercises the CLI stats command and helper display/export behavior, not the FastAPI geo coverage distribution route or import.yml-driven geometry resolution.

suggested regression test:
Add a FastAPI route test for POST /geo-coverage/distribution where the occurrence table has a configured geometry column whose name is not detected by _find_geometry_column, and assert the route uses that column instead of returning no_geo_column.

minimum fix scope:
Update get_shape_distribution's occurrence geometry detection and add one route-level regression test.

repro:
Use an occurrences table with a WKT geometry column named outside the built-in heuristics, for example `coordinates_wkt_text`, and configure it as the geometry field in import.yml. /geo-coverage can resolve it through _find_configured_geometry_column, while /geo-coverage/distribution returns no_geo_column because it never reads the dataset config.

## medium: Configured occurrence geometry is ignored by analyze

id: fnd_sig-feat-route-2d0780c4e2-6e05bb_4073c253aa
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /geo-coverage/analyze (feat_route_2d0780c4e2)
next: clawpatch show --finding fnd_sig-feat-route-2d0780c4e2-6e05bb_4073c253aa

evidence:
- src/niamoto/gui/api/routers/stats.py:4096-4105 (get_geo_coverage)
- src/niamoto/gui/api/routers/stats.py:4235-4238 (analyze_spatial_coverage)
- tests/gui/api/routers/test_stats.py:1292-1355 (test_geo_coverage_uses_configured_occurrence_geometry_column)
- tests/gui/api/routers/test_stats.py:1374-1432 (test_geo_coverage_analyze_ignores_invalid_wkt_rows)

The GET overview resolves the occurrence geometry column from import.yml before falling back to name heuristics, and tests document that a configured field such as footprint is valid and makes the dataset ready for analysis. The POST /geo-coverage/analyze route only calls _find_geometry_column, so the same project will return status no_geo_column when the configured geometry field does not match the hardcoded WKT/native naming patterns.

recommendation:
Mirror the overview resolution in analyze_spatial_coverage: resolve the dataset config with _resolve_dataset_config_for_table, call _find_configured_geometry_column with the occurrence columns, prefer that configured column over the heuristic one, and recompute occ_geo_is_native when the configured column differs.

test analysis:
The existing configured-geometry test only exercises GET /geo-coverage. The analyze test uses geo_pt, which is found by the heuristic path, so it cannot catch the missing import.yml lookup.

suggested regression test:
Add a POST /api/stats/geo-coverage/analyze test using a configured occurrence geometry column named footprint, matching test_geo_coverage_uses_configured_occurrence_geometry_column, and assert status success, geo_column footprint, and the expected covered count.

minimum fix scope:
Update analyze_spatial_coverage occurrence geometry resolution and add one API regression test.

repro:
Use the setup from test_geo_coverage_uses_configured_occurrence_geometry_column, then call POST /api/stats/geo-coverage/analyze. The route will not find footprint and returns no_geo_column instead of the expected success coverage result.

## medium: Constant-value numeric columns generate bins that exclude the data

id: fnd_sig-feat-library-f782651b22-cd0a_a6527bee09
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/imports#2 (feat_library_f782651b22)
next: clawpatch show --finding fnd_sig-feat-library-f782651b22-cd0a_a6527bee09

evidence:
- src/niamoto/core/imports/widget_generator.py:577-580 (WidgetGenerator._generate_smart_bins)

When a numeric profile has an equal min and max, such as a constant elevation value of 1000, the generated fallback bins are fixed to 0..50 and do not cover the observed value. The resulting binned_distribution suggestion can render an empty or misleading histogram even though the column has valid data.

recommendation:
Generate bins around the actual constant value, for example [value - step, value, value + step], or skip the binned_distribution suggestion when a meaningful bin range cannot be built.

test analysis:
The included tests cover normal numeric profiles and one downsampling edge case, but do not exercise value_range where min equals max, especially away from the 0..50 fallback range.

suggested regression test:
Add a WidgetGenerator test for value_range=(1000.0, 1000.0) asserting generated bins include 1000.0 and remain strictly ascending.

minimum fix scope:
Update WidgetGenerator._generate_smart_bins and add the targeted regression test.

## medium: Custom SQL safety tests miss SELECT-based file and network reads

id: fnd_sig-feat-test-suite-7937c9eeaa-1_c88ce4c2ca
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/gui/api/routers#1 (feat_test-suite_7937c9eeaa)
next: clawpatch show --finding fnd_sig-feat-test-suite-7937c9eeaa-1_c88ce4c2ca

evidence:
- tests/gui/api/routers/test_database_routes.py:306-324 (test_query_endpoint_allows_safe_identifiers_and_literals_with_keyword_substrings)
- tests/gui/api/routers/test_database_routes.py:327-351 (test_query_endpoint_rejects_mutation_and_multistatement_sql_before_opening_db)
- tests/gui/api/routers/test_database_routes.py:378-400 (test_query_endpoint_uses_read_only_duckdb_connection)

The query endpoint tests establish that arbitrary SELECT statements are allowed, mutations and comments are rejected, and the database is opened read-only. They do not cover DuckDB SELECT forms that can read local files or remote resources through table functions or extensions, which are not prevented by a read-only database connection. A regression could therefore pass this suite while still allowing data exfiltration through a syntactically read-only query.

recommendation:
Add explicit rejection tests for SELECT-based file/network access attempts, and assert they fail before the database is opened. Useful cases include read_csv_auto/read_json_auto/read_parquet over absolute paths and remote URLs, plus any DuckDB extension-loading or filesystem functions the endpoint should forbid.

test analysis:
The existing rejection parameterization only exercises DML, semicolons/comments, and a forbidden table name containing drop; the read-only test uses SELECT 1 and only verifies connection mode, not allowed SQL surface.

suggested regression test:
Parametrize /api/database/query with queries such as SELECT * FROM read_csv_auto('/etc/passwd') and SELECT * FROM read_json_auto('https://example.com/data.json'), monkeypatch open_database to fail if called, and expect 400 with opened_database remaining false.

minimum fix scope:
tests/gui/api/routers/test_database_routes.py plus the query validator if the new cases currently pass.

## medium: Custom transformer groups are rejected by the route validation path

id: fnd_sig-feat-route-93c882552e-87402f_77007fa0db
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /export/api-targets/{export_name}/groups/{group_by} (feat_route_93c882552e)
next: clawpatch show --finding fnd_sig-feat-route-93c882552e-87402f_77007fa0db

evidence:
- src/niamoto/gui/api/routers/config.py:2420-2421 (ApiExportGroupConfigUpdate)
- src/niamoto/gui/api/routers/config.py:2702-2742 (update_api_export_group_config)
- src/niamoto/core/plugins/models.py:535-539 (TargetConfig.check_exporter_specific_fields)
- src/niamoto/core/plugins/models.py:476-483 (GroupConfigDwc)
- tests/gui/api/routers/test_config_api_exports.py:1011-1034 (test_update_api_export_group_config_preserves_omitted_existing_fields)

The route accepts and preserves arbitrary transformer_plugin/transformer_params values, and the JSON API exporter model also supports arbitrary transformer plugins. But the final export.yml validation classifies every group containing transformer_plugin as GroupConfigDwc, which requires DwC-specific params. Updating an existing group that uses a non-DwC transformer, or saving one through this route, will fail validation before the config is saved. The relevant route test encodes custom_transformer as intended behavior, but it mocks out the validator that would reject it in production.

recommendation:
Change TargetConfig validation so json_api_exporter groups with transformer_plugin are only parsed as GroupConfigDwc when the plugin is niamoto_to_dwc_occurrence; otherwise allow the generic JSON API group shape with transformer_plugin/transformer_params, or validate against JsonApiExporter.GroupConfig.

test analysis:
The closest test uses a custom_transformer fixture but monkeypatches _validate_export_config_or_raise, so it bypasses the failing production validation path.

suggested regression test:
Add a route-level test without mocking _validate_export_config_or_raise that updates an existing json_api_exporter group with transformer_plugin='custom_transformer' and asserts a 200 response plus preserved transformer fields.

minimum fix scope:
Validation model logic for json_api_exporter groups, plus one route regression test.

repro:
Create a json_api_exporter target with a group containing transformer_plugin='custom_transformer' and transformer_params={'custom': true}, then PUT /api/config/export/api-targets/json_api/groups/taxons with {"enabled": true, "index": {"fields": ["id"]}}. The route preserves the custom transformer and then _validate_export_config_or_raise rejects the config as a DwC group.

## medium: Data-options reads can race with collection config writes

id: fnd_sig-feat-route-f3b51008ea-045553_4af7753f3b
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /{collection_name}/data-options (feat_route_f3b51008ea)
next: clawpatch show --finding fnd_sig-feat-route-f3b51008ea-045553_4af7753f3b

evidence:
- src/niamoto/gui/api/routers/collections.py:74-81 (_data_options_service)
- src/niamoto/gui/api/routers/collections.py:114-115 (get_collection_data_options)
- src/niamoto/gui/api/routers/collections.py:134-142 (update_collection)
- src/niamoto/gui/api/routers/collections.py:155-161 (create_collection)

The mutation routes serialize catalog changes with COLLECTION_CONFIG_LOCK while loading, mutating, and saving import.yml, but GET /{collection_name}/data-options builds its service and reloads the same import/export/transform configuration without taking that lock. FastAPI can serve concurrent network requests, so a data-options request can observe stale or partially written config while a PATCH/POST is saving collection metadata, producing intermittent 404s, incorrect recommendations, or config parse failures for a collection that is being updated or created.

recommendation:
Acquire COLLECTION_CONFIG_LOCK around the config-loading and get_options call in get_collection_data_options, or move shared config file reads/writes behind a service-level read/write synchronization mechanism used by both readers and writers.

test analysis:
The existing concurrency test only proves two create_collection calls contend on COLLECTION_CONFIG_LOCK. The data-options tests exercise normal recommendations, configured outputs, missing evidence, and unknown collection handling, but they do not issue GET /data-options concurrently with collection mutations.

suggested regression test:
Monkeypatch _data_options_service or the config loader/save path so a collection mutation blocks mid-save, start that mutation in one thread, assert a concurrent get_collection_data_options call contends on COLLECTION_CONFIG_LOCK instead of entering the read path, then release the save and verify the GET returns the final collection state.

minimum fix scope:
Wrap the route handler body for get_collection_data_options in COLLECTION_CONFIG_LOCK, or introduce a shared config access lock used by _data_options_service and _save_service_config.

repro:
Add a test similar to test_concurrent_collection_creates_preserve_both_metadata_entries that blocks _save_service_config after truncating or before replacing import.yml, then issue get_collection_data_options for the affected collection in a second thread. The GET can run while the write is in progress because it does not acquire COLLECTION_CONFIG_LOCK.

## medium: Dataset updates are blocked by unrelated legacy reference configs

id: fnd_sig-feat-route-77ddaa9848-578b5e_2fcdb40241
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /datasets/{dataset_name}/config (feat_route_77ddaa9848)
next: clawpatch show --finding fnd_sig-feat-route-77ddaa9848-578b5e_2fcdb40241

evidence:
- src/niamoto/gui/api/routers/config.py:61-62 (_validate_reference_config_update)
- src/niamoto/gui/api/routers/config.py:1033-1038 (update_dataset_config)
- src/niamoto/core/imports/config_models.py:243-247 (BaseEntityConfig)
- src/niamoto/core/imports/config_models.py:287-291 (EntitiesConfig)
- tests/gui/api/routers/test_config_datasets.py:29-33 (test_update_reference_config_serializes_concurrent_import_writes)

The reference update path explicitly preserves legacy minimal reference entries, and existing regression tests use references with only a kind. The dataset update route replaces only one dataset, but then validates the entire import.yml with GenericImportConfig. That model requires every reference to inherit BaseEntityConfig.connector, so a valid dataset update will return 422 whenever an unrelated legacy/minimal reference is still present. This makes the dataset editor unable to save in projects that the neighboring reference route intentionally supports.

recommendation:
Validate only the replaced dataset entry plus the surrounding dataset container, or use an import validation path that is intentionally tolerant of legacy/minimal references while still rejecting invalid dataset payloads. Keep the no-write-before-validation behavior.

test analysis:
The dataset route concurrency test builds import.yml with only entities.datasets, and the invalid dataset tests use empty references; none combine a valid dataset update with an existing minimal reference entry, even though the reference route tests show that shape is supported.

suggested regression test:
Add a PUT /api/config/datasets/{name}/config test where import.yml contains a minimal reference such as {kind: hierarchical} plus a valid dataset, then assert a valid dataset update succeeds and preserves the reference unchanged.

minimum fix scope:
src/niamoto/gui/api/routers/config.py validation inside update_dataset_config, plus a targeted router regression test.

repro:
Use import.yml with entities.references.taxons: {kind: hierarchical} and entities.datasets.observations containing a valid file connector. PUT /api/config/datasets/observations/config with a valid dataset connector body. The route reaches GenericImportConfig.model_validate(candidate_config) and fails on the existing reference's missing connector before writing the dataset update.

## medium: DELETE leaves widgets stored under params.groups

id: fnd_sig-feat-route-5428c53b99-c31485_4e4d1858fb
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route DELETE /{group_by}/{widget_id} (feat_route_5428c53b99)
next: clawpatch show --finding fnd_sig-feat-route-5428c53b99-c31485_4e4d1858fb

evidence:
- src/niamoto/gui/api/routers/recipes.py:1255 (_export_widget_id_exists)
- src/niamoto/gui/api/routers/recipes.py:1661-1668 (delete_widget_recipe)
- tests/gui/api/routers/test_recipes.py:631-640 (test_delete_recipe_removes_widget_only_from_html_page_exporter)

The same router treats html_page_exporter groups in either root-level groups or params.groups when checking widget-id uniqueness, but delete_widget_recipe only iterates root-level web_export["groups"]. For an export.yml that stores the html_page_exporter groups under params.groups, deleting a recipe removes widgets_data from transform.yml and saves export.yml without removing the matching export widget, leaving a stale widget reference to a deleted data source.

recommendation:
Resolve the export groups with the same root-or-params lookup used by _export_widget_id_exists, then filter the matching group's widgets there. Consider extracting a shared helper so uniqueness checks, save/update, reorder, and delete do not drift.

test analysis:
The delete regression only builds export_config with root-level groups, so the params.groups layout is never exercised.

suggested regression test:
Add a delete test with html_page_exporter params.groups containing the target widget and assert that DELETE removes it while also removing the transform widgets_data entry.

minimum fix scope:
Update delete_widget_recipe's html_page_exporter group lookup and add the params.groups regression test.

repro:
Configure export.yml with an html_page_exporter whose group is under params.groups and contains {"data_source": "alpha"}; configure transform.yml widgets_data.alpha; call DELETE /api/recipes/taxons/alpha. The transform entry is removed, but the export widget remains under params.groups.

## medium: Discovered doc symlinks can include files outside the docs tree

id: fnd_sig-feat-library-8b25f0076b-045d_271b024c50
category: security
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/help_content (feat_library_8b25f0076b)
next: clawpatch show --finding fnd_sig-feat-library-8b25f0076b-045d_271b024c50

evidence:
- src/niamoto/gui/help_content/builder.py:276-293 (_discover_pages)
- src/niamoto/gui/help_content/builder.py:316-317 (_read_source_document)

Page discovery accepts any `rglob` result whose symlink path is a file, computes the generated slug from the path inside `docs_root`, then resolves and reads the target. There is no containment check on the resolved source path during discovery, so a symlink such as `docs/01-guide/secret.md -> ../../.env` would be read and emitted into the generated help JSON under an innocuous docs slug. Link targets are constrained elsewhere, but discovered pages themselves are not.

recommendation:
Reject discovered source pages whose resolved path is not within `docs_root`, or skip symlinks entirely for page discovery. Apply the same resolved-path containment rule before reading source documents.

test analysis:
The linked help-content tests create regular files only; none add a symlink inside a numbered docs section pointing outside the docs tree.

suggested regression test:
Create a symlinked `.md` file inside a numbered docs section pointing to a file outside `docs_root`, run `build_help_content`, and assert the symlinked page is skipped or the build fails without writing that external content.

minimum fix scope:
Add a resolved-path containment check in `_discover_pages` before `_read_source_document`, and cover symlinked source pages with a regression test.

## medium: DNS pinning replaces socket.getaddrinfo process-wide during active fetches

id: fnd_sig-feat-library-301e41a152-c9e7_aeda180cb8
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api (feat_library_301e41a152)
next: clawpatch show --finding fnd_sig-feat-library-301e41a152-c9e7_aeda180cb8

evidence:
- src/niamoto/gui/api/url_security.py:74-89 (pin_public_dns_for_url)
- src/niamoto/gui/api/url_security.py:91-96 (pin_public_dns_for_url)

The lock serializes callers entering this context manager, but the monkeypatch itself is global. While one request is inside the context, any other thread in the FastAPI process resolving the same hostname will receive the pinned address, even if it is not part of that fetch. That can misroute unrelated network calls and makes behavior timing-dependent under concurrent requests.

recommendation:
Avoid process-wide monkeypatching for DNS pinning. Use an HTTP client transport/resolver that applies the validated addresses only to the specific request, or connect to the validated IP with explicit Host/SNI handling in the fetch callers.

test analysis:
tests/gui/api/test_url_security.py verifies that getaddrinfo is restored after the context exits, but it does not exercise concurrent resolution while the context is active.

suggested regression test:
Add a concurrency test that keeps pin_public_dns_for_url open in one thread and asserts an unrelated resolver call is not affected, after replacing the implementation with request-scoped DNS pinning.

minimum fix scope:
src/niamoto/gui/api/url_security.py and the fetch callers that depend on pin_public_dns_for_url.

repro:
Start one thread inside pin_public_dns_for_url('https://example.com/path', ('93.184.216.34',)) and, before it exits, call socket.getaddrinfo('example.com', 443) from another thread. The second thread receives the pinned address despite not opting into the context.

## medium: DuckDB table names are not actually SQL-quoted in import SQL

id: fnd_sig-feat-library-705734df4d-19b4_332a847a05
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/imports#1 (feat_library_705734df4d)
next: clawpatch show --finding fnd_sig-feat-library-705734df4d-19b4_332a847a05

evidence:
- src/niamoto/core/imports/engine.py:66-69 (GenericImporter._write_dataframe_to_table)
- src/niamoto/core/imports/engine.py:184-187 (GenericImporter.import_from_csv)

`quoted_name` only carries SQLAlchemy quoting intent; converting it with `str()` leaves the raw table name. Manual DuckDB SQL built from that value will fail for valid Niamoto entity/table names containing hyphens or spaces, and table names are derived from import entity names/file stems rather than constrained here. The module already uses `quote_identifier` correctly for geometry SQL, but the main write/count path does not.

recommendation:
Use `quote_identifier(self.db, table_name)` for every manual SQL identifier in `engine.py`, including drop/create/count paths, instead of `str(quoted_name(...))`. Add the same protection to any reset/drop path that builds table names from entity names.

test analysis:
The existing generic importer tests cover default ID generation and quoting in `_add_native_geometry_column`, but they do not import through `_write_dataframe_to_table` or `import_from_csv` with a table name that requires quoting.

suggested regression test:
Add a DuckDB importer test that calls `import_from_csv` with `table_name='dataset-occurrences'` and asserts the import succeeds and the row count query works.

minimum fix scope:
Replace raw `quoted_name` string interpolation in `GenericImporter` with the existing database-aware identifier quoting helper and cover the DuckDB write/count path.

repro:
Import a DuckDB CSV into a table such as `dataset_occurrences-2024`; `_write_dataframe_to_table` emits `DROP TABLE IF EXISTS dataset_occurrences-2024`, which DuckDB parses as an expression rather than a quoted identifier.

## medium: Duplicate citation keys can still be emitted when a generated suffix collides with a later base key

id: fnd_sig-feat-route-df0fc656d5-707dc9_04e9695955
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /export-bibtex (feat_route_df0fc656d5)
next: clawpatch show --finding fnd_sig-feat-route-df0fc656d5-707dc9_04e9695955

evidence:
- src/niamoto/gui/api/routers/site.py:2920-2932 (_references_to_bibtex)
- tests/gui/api/routers/test_site.py:94-111 (test_export_bibtex_suffixes_duplicate_keys_in_linear_counter_order)

The exporter tracks used_keys but never consults it before appending an entry. It only increments a per-base counter, so two identical references with base key 'doe2024same' produce 'doe2024same' and 'doe2024same2'; a later distinct reference whose natural base key is already 'doe2024same2' will be emitted with the same key. Duplicate BibTeX keys make the exported file ambiguous and can cause reference managers or BibTeX processors to overwrite or resolve citations unpredictably.

recommendation:
When assigning a key, loop until the candidate key is absent from used_keys. For duplicate bases, continue incrementing the suffix until a globally unique key is found, then record it in used_keys.

test analysis:
The existing test only covers repeated identical references and verifies linear suffixing for one base key. It does not include a later reference whose natural base key collides with a previously generated suffixed key.

suggested regression test:
Add a POST /api/site/export-bibtex test with two 'Same' references and one 'Same2' reference, then assert each '@article{...,' key appears exactly once and the third key is advanced to a unique suffix such as 'doe2024same22'.

minimum fix scope:
Update _references_to_bibtex key generation in src/niamoto/gui/api/routers/site.py and add one focused regression test in tests/gui/api/routers/test_site.py.

repro:
POST /api/site/export-bibtex with three references: two with authors='Doe, Jane', year='2024', title='Same', followed by one with authors='Doe, Jane', year='2024', title='Same2'. The response will contain two entries keyed 'doe2024same2'.

## medium: Entity listing accepts unbounded and invalid pagination parameters

id: fnd_sig-feat-route-37c3d91e7a-26aaea_c1c94d51f4
category: performance
confidence: high
triage: risk
status: open
feature: FastAPI route GET /entities/{reference_name} (feat_route_37c3d91e7a)
next: clawpatch show --finding fnd_sig-feat-route-37c3d91e7a-26aaea_c1c94d51f4

evidence:
- src/niamoto/gui/api/routers/enrichment.py:337-349 (list_entities_for_reference)
- tests/gui/api/routers/test_enrichment.py:726-730 (test_get_all_results_rejects_invalid_pagination)
- tests/gui/api/routers/test_enrichment.py:767-813 (test_list_entities_for_reference_uses_worker_thread)

The route exposes network-controlled limit and offset as plain int query parameters, so FastAPI only type-checks them and accepts values like limit=100000000, limit=0, and offset=-1. Nearby results endpoints use Query bounds and have an explicit 422 test for invalid pagination, showing the intended API pattern. The entity route forwards the user-supplied pagination to the entity listing service, so a very large limit can trigger excessive database reads and response serialization, while invalid values produce inconsistent behavior instead of a client error.

recommendation:
Declare the parameters with FastAPI Query constraints, for example limit: int = Query(default=100, ge=1, le=500) and offset: int = Query(default=0, ge=0), matching the bounded pagination contract used by the results endpoints.

test analysis:
The included entity test calls list_entities_for_reference directly and asserts forwarding to the worker thread. It does not exercise the FastAPI route with invalid or excessive query parameters, unlike the results pagination test.

suggested regression test:
Add a gui_duckdb_client test for /api/enrichment/entities/taxons asserting 422 for limit=0, limit=-1, limit=501 or another chosen maximum, and offset=-1, plus a valid request asserting forwarding of bounded values.

minimum fix scope:
Update only src/niamoto/gui/api/routers/enrichment.py to use Query validation on list_entities_for_reference, then add targeted route-level tests in tests/gui/api/routers/test_enrichment.py.

repro:
GET /api/enrichment/entities/taxons?limit=100000000 or GET /api/enrichment/entities/taxons?limit=0 currently passes validation at the route layer instead of returning 422.

## medium: Entity lists fail for valid tables without general_info

id: fnd_sig-feat-route-65c24d450f-16e558_1cba6b59e2
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /entities/{group_by} (feat_route_65c24d450f)
next: clawpatch show --finding fnd_sig-feat-route-65c24d450f-16e558_1cba6b59e2

evidence:
- src/niamoto/gui/api/routers/entities.py:216-223 (list_entities)
- src/niamoto/gui/api/routers/entities.py:226-233 (list_entities)
- tests/gui/api/routers/test_entities.py:238-271 (test_entity_detail_handles_table_without_general_info)

The list route always references general_info and filters on it. The linked tests establish that an entity table without general_info is a supported shape for the entity detail route, with fallback naming from the table and id. Calling GET /entities/shapes for the same supported table would fail at SQL binding time instead of returning summaries such as shapes_12, so the list and detail APIs disagree for the same entity table.

recommendation:
Mirror the detail route's column detection: check whether general_info exists before building the query, select NULL as name when absent, and omit the WHERE general_info IS NOT NULL filter in that case so fallback names are returned.

test analysis:
The existing test covers get_entity_detail for a table without general_info, but no test calls list_entities against that same schema.

suggested regression test:
Add a test that creates shapes(shapes_id INTEGER, metrics JSON), calls /api/entities/entities/shapes, and expects [{"id":"12","name":"shapes_12","display_name":"shapes_12"}].

minimum fix scope:
Update list_entities query construction and add one route regression test.

repro:
Create a table with an id column and JSON data but no general_info, as in test_entity_detail_handles_table_without_general_info, then call GET /api/entities/entities/shapes. The query references missing column general_info and returns a 500 instead of a list response.

## medium: Environment initialization leaks the temporary DuckDB database lifecycle

id: fnd_sig-feat-library-34fbee6012-0a79_5e4d6324a2
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/common#1 (feat_library_34fbee6012)
next: clawpatch show --finding fnd_sig-feat-library-34fbee6012-0a79_5e4d6324a2

evidence:
- src/niamoto/common/environment.py:123-126 (Environment.initialize)
- src/niamoto/common/database.py:123-126 (Database.__init__)
- src/niamoto/common/database.py:190-194 (Database._resolve_duckdb_read_only_mode)
- src/niamoto/common/database.py:220-227 (Database._wrap_engine_dispose)
- tests/common/test_environment.py:75-76 (test_initialize)

Environment.initialize constructs a Database solely for side effects and discards it without closing the session or disposing the engine. For DuckDB, construction registers a process-local writable mode count, and the release path only runs from engine.dispose(). Because the temporary Database is never disposed, later read_only=True openings in the same process can be incorrectly downgraded to writable mode and resources may remain open longer than intended.

recommendation:
Store the temporary Database in a local variable and close/dispose it in a finally block after initialization, or add a Database.close() method that calls close_db_session() and engine.dispose() and use it here.

test analysis:
Environment tests patch Database and only assert it was constructed. Database tests cover mode release when engine.dispose() is explicitly called, but there is no integration test asserting Environment.initialize releases the temporary database handle or clears _duckdb_mode_counts.

suggested regression test:
Add an Environment.initialize test with a real DuckDB temp path that asserts Database._duckdb_mode_counts has no entry for the path after initialize returns, then verifies Database(path, read_only=True).read_only remains True.

minimum fix scope:
src/niamoto/common/environment.py lifecycle cleanup, with a focused regression in tests/common/test_environment.py.

repro:
Call Environment.initialize() for a DuckDB project, then create Database(same_path, read_only=True) in the same process. The stale writable mode registration can cause the read-only request to be downgraded even though no live Environment database handle exists.

## medium: Existing directories can escape the route's HTTP error handling

id: fnd_sig-feat-route-6c8536c8db-9e08e7_371b73d11d
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /data-content (feat_route_6c8536c8db)
next: clawpatch show --finding fnd_sig-feat-route-6c8536c8db-9e08e7_371b73d11d

evidence:
- src/niamoto/gui/api/routers/site.py:2378-2384 (update_data_content)
- src/niamoto/gui/api/routers/site.py:2335-2336 (get_data_content)

PUT /data-content validates the extension and then immediately backs up any existing path, but it never checks that an existing path is a regular file. A user-controlled path such as data/items.json can legally resolve under the allowed data root while being a directory; _create_backup then attempts to open that directory as a file before the route's write try/except, producing an unhandled OSError instead of the documented 400-style API error used by the GET endpoint.

recommendation:
Before creating a backup, add the same existing-path file check used by GET: if file_path.exists() and not file_path.is_file(), raise HTTPException(400, "Path is not a file"). Consider moving backup creation inside the outer try so filesystem failures are consistently converted to HTTPException responses.

test analysis:
The included data-content tests only exercise GET validation for malformed JSON arrays; they do not send PUT requests or cover existing directory paths.

suggested regression test:
Add a PUT /api/site/data-content test that creates data/items.json as a directory and asserts status 400 with detail "Path is not a file".

minimum fix scope:
update_data_content path validation before _create_backup, plus one route-level regression test.

repro:
Create a directory named data/items.json in the working project, then PUT /api/site/data-content with {"path":"data/items.json","data":[]}. The suffix check passes, file_path.exists() is true, and _create_backup tries to open the directory.

## medium: Explicit null sections in export.yml make GET /config return a server error

id: fnd_sig-feat-route-13177d44c7-1e4ed6_ff469ae4c3
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /config (feat_route_13177d44c7)
next: clawpatch show --finding fnd_sig-feat-route-13177d44c7-1e4ed6_ff469ae4c3

evidence:
- src/niamoto/gui/api/routers/site.py:556-558 (_get_export_config)
- src/niamoto/gui/api/routers/site.py:740-746 (get_site_config)
- src/niamoto/gui/api/routers/site.py:141-158 (_normalize_navigation_items)

YAML explicit null values are loaded as None. GET /config only supplies defaults for missing keys, then immediately calls params.get(...) and iterates navigation/static_pages/footer_navigation as lists. A user-edited export.yml with params: null, navigation: null, footer_navigation: null, or static_pages: null will therefore raise AttributeError or TypeError and surface as a 500 instead of returning defaults or a clear 422 configuration error. This blocks the Site Builder from opening the config that the user needs to repair.

recommendation:
Normalize nullable containers before use, for example params = web_pages.get("params") or {}, raw_navigation = params.get("navigation") or [], raw_footer_navigation = params.get("footer_navigation") or [], raw_static_pages = web_pages.get("static_pages") or []. For non-dict/non-list values, return HTTPException 422 with a precise configuration message rather than allowing Python runtime errors.

test analysis:
The GET /config tests cover params as an empty dict and static_pages as an empty list, but they do not cover explicit YAML null values for these sections.

suggested regression test:
Add a GET /api/site/config test with export.yml containing params: null, navigation: null, footer_navigation: null, and static_pages: null, asserting either a 200 response with defaults or a deliberate 422 diagnostic instead of a 500.

minimum fix scope:
Update get_site_config container normalization and add targeted router tests for explicit null YAML sections.

repro:
Create config/export.yml with a web_pages export where params: null, then request GET /api/site/config. The handler reaches params.get(...) on None.

## medium: Export validate route accepts configs that save validation rejects

id: fnd_sig-feat-route-49f178367a-590bdd_4f7d7624fb
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /{config_name}/validate (feat_route_49f178367a)
next: clawpatch show --finding fnd_sig-feat-route-49f178367a-590bdd_4f7d7624fb

evidence:
- src/niamoto/gui/api/routers/config.py:1216-1218 (update_config)
- src/niamoto/gui/api/routers/config.py:444-462 (_validate_config_update_content)
- src/niamoto/gui/api/routers/config.py:1294-1312 (validate_config)

The save path validates export.yml through _validate_config_update_content, which rejects empty export configs and runs ExportConfigModel.model_validate to catch missing required target fields such as exporter. POST /{config_name}/validate takes a different export path that only checks whether exports/static_pages are lists and otherwise leaves valid=true. For example, POST /api/config/export/validate with {"exports":[{"name":"web"}]} returns valid=true, but PUT /api/config/export would reject the same content. This makes the validation route an unreliable preflight for the write route.

recommendation:
Make validate_config delegate export payloads to _validate_config_update_content, as it already does for transform payloads, or factor the export branch so both validate and update use the same ExportConfigModel-backed validation.

test analysis:
tests/common/test_config.py exercises Config loading and unrelated config/router behavior, but it does not call POST /api/config/export/validate or compare validate-route results with update-route validation semantics.

suggested regression test:
Add an API test that POSTs {"exports":[{"name":"web"}]} to /api/config/export/validate and asserts valid is false with a model validation error; also assert an empty export object is invalid if PUT /api/config/export rejects it.

minimum fix scope:
src/niamoto/gui/api/routers/config.py validate_config export branch plus a focused route test for export validation parity.

repro:
POST /api/config/export/validate with JSON {"exports":[{"name":"web"}]} and compare it with PUT /api/config/export using {"content":{"exports":[{"name":"web"}]}}; the validate endpoint reports success while the update endpoint fails validation.

## medium: Export widget operations inconsistently ignore params.groups

id: fnd_sig-feat-library-9282ce0cc6-7c1c_5e58084ab2
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/gui/api/routers#1 (feat_library_9282ce0cc6)
next: clawpatch show --finding fnd_sig-feat-library-9282ce0cc6-7c1c_5e58084ab2

evidence:
- src/niamoto/gui/api/routers/config.py:164-180 (_find_export_group_in_supported_locations)
- src/niamoto/gui/api/routers/config.py:1998-2007 (update_export_widget)
- src/niamoto/gui/api/routers/entities.py:440-447 (render_widget)
- src/niamoto/gui/api/routers/config.py:1940-1947 (list_export_widgets)

The router declares both top-level groups and params.groups as supported, and list/delete paths use the shared helper. update_export_widget manually uses an either/or expression, so params.groups is skipped whenever root groups exists for another group. render_widget only looks at top-level groups. Valid configs can therefore list a widget but fail to update or render it, or create duplicate groups in a different location.

recommendation:
Use _find_export_group_in_supported_locations, or an equivalent iterator over both locations, in update_export_widget and render_widget. Avoid the root-groups-or-params-groups shortcut.

test analysis:
The included router tests cover collection/data/deploy/enrichment flows, but not rendering or updating export widgets stored under params.groups with another top-level group present.

suggested regression test:
Add tests with export.yml containing both groups and params.groups: assert PUT updates the params.groups widget in place, and render_widget resolves the params.groups widget configuration.

minimum fix scope:
Refactor group lookup in update_export_widget and render_widget to share the same supported-location lookup behavior used by list_export_widgets/delete_export_widget.

repro:
Create export.yml with one export containing groups for taxons and params.groups for plots. /api/config/export/plots/widgets can list the params.groups widget, but PUT /api/config/export/plots/widgets/plot_map will not find it when root groups is non-empty, and /api/entities/render-widget/plots/{id}/plot_map will report no widget configured.

## medium: Export widget updates can target non-web export groups

id: fnd_sig-feat-route-61f33cad14-d47be1_a1ad434b91
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /export/{group_by}/widgets/{widget_id} (feat_route_61f33cad14)
next: clawpatch show --finding fnd_sig-feat-route-61f33cad14-d47be1_a1ad434b91

evidence:
- src/niamoto/gui/api/routers/config.py:1998-2007 (update_export_widget)
- src/niamoto/gui/api/routers/config.py:2042-2084 (update_export_widget)
- tests/common/test_config.py:90-123 (TestConfig.test_transform_widget_route_handles_null_widgets_data)

The route is specifically for export widgets, which are consumed by the HTML page exporter, but the group lookup scans every export target without checking exporter type. If a json_api_exporter target appears before web_pages and has the same group_by, the route returns 200 while adding a widgets list to the API export group instead of updating the web page group. The intended web widget is not created or updated, and export.yml is silently changed in the wrong section.

recommendation:
Restrict update_export_widget group resolution to html_page_exporter targets, preferably through a helper shared with list/delete/reorder semantics for web widgets. When no matching web group exists, create it only under the web_pages/html_page_exporter target.

test analysis:
The included context test file only exercises transform widget behavior and general Config loading; it does not cover PUT /export/{group_by}/widgets/{widget_id} with both JSON API and HTML export groups present.

suggested regression test:
Add a FastAPI test with a json_api_exporter group before a web_pages group for the same group_by, then assert the PUT writes only to web_pages.groups[*].widgets and does not add widgets to the json_api_exporter group.

minimum fix scope:
Change the target-group lookup inside update_export_widget to consider only html_page_exporter exports, then add the regression test.

repro:
Use an export.yml where exports[0] is a json_api_exporter with groups: [{group_by: taxons}] and exports[1] is web_pages with groups: [{group_by: taxons, widgets: []}]. PUT /api/config/export/taxons/widgets/richness with {"plugin":"bar_plot","data_source":"richness","params":{}}. The saved widget lands under the json_api_exporter group, leaving web_pages unchanged.

## medium: Exported preview serves active HTML without isolation headers

id: fnd_sig-feat-route-7fb219e8d3-9de16d_0a00d3fc3f
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /preview-exported/{requested_path:path} (feat_route_7fb219e8d3)
next: clawpatch show --finding fnd_sig-feat-route-7fb219e8d3-9de16d_0a00d3fc3f

evidence:
- src/niamoto/gui/api/routers/site.py:912-917 (preview_exported_site)
- src/niamoto/gui/api/routers/site.py:2534-2544 (serve_file)
- tests/gui/api/routers/test_site.py:1608-1630 (test_files_serves_svg_as_attachment_with_defensive_headers)
- tests/gui/api/routers/test_site.py:596-631 (test_preview_exported_site_follows_current_working_directory)

The preview route returns exported files inline with FileResponse and no CSP, nosniff, or attachment/sandbox treatment. Exported files commonly include .html, .svg, and .js content; when served from /api/site/preview-exported they execute on the GUI API origin. The same router already treats active files under /api/site/files as dangerous and forces sandbox/attachment defensive headers, and the tests assert that behavior there. The preview-exported tests only validate body selection, so active exported content can run without the isolation policy used elsewhere.

recommendation:
Apply the same active-content isolation policy to preview-exported responses, or a preview-specific CSP sandbox that preserves required preview behavior without allow-same-origin. At minimum, add defensive headers for active extensions and cover direct route access, not only the embedding UI.

test analysis:
The preview-exported tests assert status and selected file contents only. Defensive header assertions exist for /api/site/files active content, but there is no corresponding test for /api/site/preview-exported/*.html or *.svg.

suggested regression test:
Add a test that writes exports/web/index.html with a script, requests /api/site/preview-exported/index.html, and asserts the response includes the chosen sandbox CSP and X-Content-Type-Options policy while still returning the file content.

minimum fix scope:
Update preview_exported_site or a small response helper in src/niamoto/gui/api/routers/site.py, then add focused assertions in tests/gui/api/routers/test_site.py for active preview files.

repro:
Create exports/web/index.html containing a script, then request /api/site/preview-exported/index.html in a browser. The response is served as the API origin document without a Content-Security-Policy sandbox header.

## medium: External hierarchical nav mode breaks for non-JavaScript referential_data identifiers

id: fnd_sig-feat-library-e404792a3a-a153_9fc798d8de
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/widgets#1 (feat_library_e404792a3a)
next: clawpatch show --finding fnd_sig-feat-library-e404792a3a-a153_9fc798d8de

evidence:
- src/niamoto/core/plugins/widgets/hierarchical_nav_widget.py:156-164 (HierarchicalNavWidget.render)
- src/niamoto/core/plugins/widgets/hierarchical_nav_widget.py:172-185 (HierarchicalNavWidget.render)
- src/niamoto/core/plugins/widgets/hierarchical_nav_widget.py:233-240 (HierarchicalNavWidget.render)
- tests/core/plugins/widgets/test_hierarchical_nav_widget.py:139-170 (TestHierarchicalNavWidget)

referential_data is only typed as a string, but external-JS rendering interpolates it into a raw JavaScript identifier and script path. A valid-looking data-source name such as 'taxon-ref' produces data_var='taxon-refNavigationData' and JavaScript like 'typeof taxon-refNavigationData', which is parsed as an expression rather than a variable name and prevents initialization. The same unsanitized value is also inserted into HTML id attributes and the script src path.

recommendation:
Normalize referential_data into separate safe values: HTML ids via escaping/slugification, file paths via URL/path-safe encoding, and JS variable access via bracket notation on window with a JSON-encoded string, e.g. window[dataVarName].

test analysis:
The hierarchical nav tests use inline data and safe underscore identifiers; they do not cover load_from_js or referential_data values containing hyphens, dots, quotes, or other non-identifier characters.

suggested regression test:
Add a load_from_js test with referential_data='taxon-ref' that asserts the output uses window['taxon-refNavigationData'] or another safe lookup and does not emit raw 'typeof taxon-refNavigationData'.

minimum fix scope:
src/niamoto/core/plugins/widgets/hierarchical_nav_widget.py identifier/path/id generation in render, plus one external-JS regression test.

repro:
Create HierarchicalNavWidgetParams(referential_data='taxon-ref', id_field='id', name_field='name', base_url='/taxon/') and render {'load_from_js': True}; the output contains 'typeof taxon-refNavigationData' and 'config.items = taxon-refNavigationData'.

## medium: FieldAggregator database-source tests do not assert the lookup key or query parameters

id: fnd_sig-feat-test-suite-0b8bb8d338-9_66873ef817
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/transformers/aggregation (feat_test-suite_0b8bb8d338)
next: clawpatch show --finding fnd_sig-feat-test-suite-0b8bb8d338-9_66873ef817

evidence:
- tests/core/plugins/transformers/aggregation/test_field_aggregator.py:262-285 (TestFieldAggregator.test_transform_with_db_source)
- tests/core/plugins/transformers/aggregation/test_field_aggregator.py:287-293 (TestFieldAggregator.test_transform_with_db_source)
- tests/core/plugins/transformers/aggregation/test_field_aggregator.py:331-361 (TestFieldAggregator.test_transform_with_import_source)

These tests claim to exercise the real DB lookup path, but fetch_one returns data unconditionally and the assertions only check that it was called once. They do not provide a group_id or verify the query parameters, so an implementation that queries with the wrong id, None, or the wrong table can still pass while returning the mocked row.

recommendation:
Include group_id in the transform config and assert fetch_one was called with the expected quoted table/field query and {"id_value": group_id}. Use side effects that fail when parameters are wrong instead of unconditional return values.

test analysis:
The mocks bypass the database selection semantics and the assertions stop at call count, so they do not validate the key behavior that determines which row is read.

suggested regression test:
Call transform with config containing group_id=123 and assert fetch_one receives params {"id_value": 123}; repeat for import: sources and registry-resolved sources.

minimum fix scope:
Tighten the two database-source tests in test_field_aggregator.py.

## medium: fragmentation_analysis accepts patch_density but never computes or returns it

id: fnd_sig-feat-library-7e7ea31318-919f_1d644bc5a7
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/core/plugins/transformers/ecological (feat_library_7e7ea31318)
next: clawpatch show --finding fnd_sig-feat-library-7e7ea31318-919f_1d644bc5a7

evidence:
- src/niamoto/core/plugins/transformers/ecological/fragmentation.py:56-70 (FragmentationParams.metrics)
- src/niamoto/core/plugins/transformers/ecological/fragmentation.py:96-105 (FragmentationParams.validate_metrics)
- src/niamoto/core/plugins/transformers/ecological/fragmentation.py:280-448 (FragmentationAnalysis.transform)

patch_density is advertised in the schema/UI and passes validation, but transform has no branch that calculates result['patch_density']. A user requesting only this valid metric receives no patch density value, just the trailing area_unit, which breaks the metric contract.

recommendation:
Either implement patch_density, for example patch_count divided by landscape_area in the requested area unit with an explicit unit, or remove it from ui:options and valid_metrics until supported.

test analysis:
Fragmentation tests cover patch_count, meff, edge_density, largest_patch_index, core_area, connectivity_index, and size_distribution, but none request patch_density.

suggested regression test:
Request metrics=['patch_density'] on the deterministic three-patch fixture and assert the returned density and unit, such as 3 patches / 10000 ha.

minimum fix scope:
Add patch_density handling to FragmentationAnalysis.transform and _empty_results, plus a focused regression test.

## medium: GBIF CSVs with zero matching annotated columns are treated as successful evaluations

id: fnd_sig-feat-library-2254297684-3266_1123d3b50d
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source ml/scripts/eval (feat_library_2254297684)
next: clawpatch show --finding fnd_sig-feat-library-2254297684-3266_1123d3b50d

evidence:
- ml/scripts/eval/evaluate_instance.py:111-119 (resolve_csv_paths)
- ml/scripts/eval/evaluate_instance.py:266-271 (compute_metrics)
- ml/scripts/eval/run_eval_suite.py:197-203 (evaluate_one)

In GBIF single-file mode, a CSV path is accepted as soon as the file exists, even when none of the GBIF annotations are present in its header. That produces a non-empty csv_gt_pairs list with an empty ground-truth list, so the suite does not skip or fail; it evaluates zero columns and compute_metrics returns an empty dict. This can make a broken or mismatched benchmark input look like a valid run with 0 columns, hiding annotation drift or the wrong CSV being wired into the suite.

recommendation:
In GBIF mode, only append the pair when filtered is non-empty. If the CSV exists but no annotated columns match, print a clear warning and return no pairs or raise a SystemExit in the CLI path so the suite reports the dataset as skipped/failed rather than evaluated.

test analysis:
The linked tests cover product score helpers and the evaluation harness, but they do not exercise evaluate_instance.resolve_csv_paths or run_eval_suite.evaluate_one with a GBIF CSV whose headers have no annotation overlap.

suggested regression test:
Add a test that builds a temporary GBIF annotation mapping and a CSV with unrelated headers, calls resolve_csv_paths(..., is_gbif=True, csv_override=...), and asserts that no evaluation pair is returned or that the CLI/suite reports the dataset as unmatched.

minimum fix scope:
Update resolve_csv_paths GBIF handling and add a focused regression test for the zero-overlap CSV case.

repro:
Run evaluate_one or evaluate_instance with gbif_darwin_core.yml and any existing CSV whose columns do not overlap the annotations. resolve_csv_paths returns one pair with an empty gt list, evaluate_dataset returns no results, and the suite continues instead of failing the dataset.

## medium: General-info count previews ignore configured relations

id: fnd_sig-feat-library-fb0afdb4d9-347d_d4dd31093a
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/services/preview_engine (feat_library_fb0afdb4d9)
next: clawpatch show --finding fnd_sig-feat-library-fb0afdb4d9-347d_d4dd31093a

evidence:
- src/niamoto/gui/api/services/preview_engine/engine.py:814-815 (PreviewEngine._render_inline)
- src/niamoto/gui/api/services/preview_engine/engine.py:1259-1265 (PreviewEngine._resolve_general_info_count_relation)
- src/niamoto/gui/api/services/preview_engine/engine.py:1291-1315 (PreviewEngine._resolve_general_info_count_filter)
- tests/gui/api/services/preview_engine/test_engine.py:253-263 (test_render_general_info_count_uses_configured_relation)

Dans ce fichier, les autres appels chargent import.yml avec self._work_dir, mais _resolve_general_info_count_relation appelle load_import_config() sans argument et avale l’exception en retournant une relation vide. Les champs count perdent donc la clé de relation configurée et tombent sur le fallback id_field, ce qui omet les compteurs ou compte avec la mauvaise colonne pour les références dont la clé source est par exemple plot_code/taxon_id.

recommendation:
Passer self._work_dir à _resolve_general_info_count_relation et l’utiliser dans load_import_config(self._work_dir), ou injecter la configuration déjà chargée depuis l’appelant. Ne pas masquer cette erreur de signature comme une relation absente.

test analysis:
Le test existant remplace load_import_config par une lambda sans argument, ce qui fait réussir le chemin relationnel tout en cachant l’appel de production incorrect.

suggested regression test:
Modifier test_render_general_info_count_uses_configured_relation pour ne pas monkeypatcher load_import_config avec une lambda sans argument, ou ajouter un test qui monkeypatch seulement le fichier import.yml réel et vérifie que la requête count utilise la clé de relation configurée.

minimum fix scope:
PreviewEngine._resolve_general_info_count_relation et son appel depuis _render_general_info.

## medium: GeoDataFrame inputs ignore the configured geometry field

id: fnd_sig-feat-library-a8c20fbb8f-d732_0f8332c598
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/geospatial (feat_library_a8c20fbb8f)
next: clawpatch show --finding fnd_sig-feat-library-a8c20fbb8f-d732_0f8332c598

evidence:
- src/niamoto/core/plugins/transformers/geospatial/raster_stats.py:184-190 (RasterStats.transform)
- src/niamoto/core/plugins/transformers/geospatial/raster_stats.py:221-228 (RasterStats._extract_geometry)
- src/niamoto/core/plugins/transformers/geospatial/vector_overlay.py:253-258 (VectorOverlay._prepare_main_geodataframe)
- tests/core/plugins/transformers/geospatial/test_vector_overlay.py:168-173 (TestPrepareGeoDataFrame.test_prepare_with_geodataframe)

Both public configs expose shape_field, but for GeoDataFrame inputs the implementations use the active geometry column unconditionally. If a caller provides a GeoDataFrame with multiple geometry columns and sets shape_field to a non-active column, raster extraction and vector overlay silently run against the wrong shape, producing valid-looking but incorrect spatial results.

recommendation:
When input is a GeoDataFrame, validate that params['shape_field'] exists and either select that geometry explicitly or call set_geometry(shape_field) before downstream work. Preserve the existing default behavior when shape_field is 'geometry'.

test analysis:
The included tests only pass shape_field='geometry' and assert the default active geometry path, so they cannot detect a mismatch between configured and active geometry columns.

suggested regression test:
Add RasterStats and VectorOverlay tests using a GeoDataFrame with two geometry columns where the configured shape_field differs from the active geometry, and assert that the computed result matches the configured column.

minimum fix scope:
Update RasterStats._extract_geometry and VectorOverlay._prepare_main_geodataframe to honor shape_field for GeoDataFrame inputs.

repro:
Create a GeoDataFrame whose active geometry is a broad polygon and whose alternate column named analysis_geometry is a small polygon. Run RasterStats or VectorOverlay with params.shape_field='analysis_geometry'. The result is computed from the active geometry instead of analysis_geometry.

## medium: GET /exports/list follows symlinks under exports

id: fnd_sig-feat-route-e97d2671e2-f9f93e_e50b2d0c84
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /exports/list (feat_route_e97d2671e2)
next: clawpatch show --finding fnd_sig-feat-route-e97d2671e2-f9f93e_e50b2d0c84

evidence:
- src/niamoto/gui/api/routers/files.py:951-952 (list_exports)
- src/niamoto/gui/api/routers/files.py:972-980 (list_exports)
- src/niamoto/gui/api/routers/files.py:986-994 (list_exports)
- tests/gui/api/routers/test_files.py:458-479 (test_exports_structure_skips_symlinks)

The list_exports route walks exports/web, exports/api, and exports/dwc with Path.rglob and then calls item.stat(), which follows symlinked matching files. It also never rejects a symlinked exports root. Other export file endpoints treat symlinks as outside the allowed export boundary, and the included tests explicitly require /exports/structure to skip symlinks. As written, a symlink such as exports/api/leak.json pointing outside the project, or a symlinked exports directory, can make GET /exports/list disclose external file names plus size and mtime metadata over the network-facing API even though /exports/read would reject the same target.

recommendation:
Make /exports/list use the same containment policy as the other export file routes: reject a symlinked exports root, skip symlinked entries, resolve each candidate strictly, require it to remain under the resolved exports directory, and use stat(follow_symlinks=False) for listed metadata.

test analysis:
The included tests cover symlink rejection for /exports/read and symlink skipping for /exports/structure, but there is no included test that creates a symlinked export file or symlinked exports root and calls /exports/list.

suggested regression test:
Add a /api/files/exports/list test that creates exports/api/public.json plus exports/api/linked-secret.json -> tmp_path/secret.json and asserts only public.json appears; add a second test for a symlinked exports root returning a rejection or an empty safe result, matching the chosen contract.

minimum fix scope:
Update list_exports in src/niamoto/gui/api/routers/files.py and add focused tests for /exports/list symlink handling.

repro:
Create work_dir/exports/api/leak.json as a symlink to a JSON file outside the project, monkeypatch get_working_directory to work_dir, then GET /api/files/exports/list. The response will include api/leak.json with the target file's size and modified time.

## medium: GET /files performs unbounded synchronous recursive traversal

id: fnd_sig-feat-route-b5d2f5987d-0ba162_386912d0c5
category: performance
confidence: high
triage: risk
status: open
feature: FastAPI route GET /files (feat_route_b5d2f5987d)
next: clawpatch show --finding fnd_sig-feat-route-b5d2f5987d-0ba162_386912d0c5

evidence:
- src/niamoto/gui/api/routers/site.py:1019-1049 (list_project_files)
- tests/gui/api/routers/test_site.py:1558-1588 (test_files_listing_allows_site_content_roots)

The route is declared async but recursively walks the entire requested content tree with blocking filesystem calls and returns every file in one response. A large files/ or templates/content tree can monopolize the event loop and allocate a large response, making the GUI API slow or unavailable for other requests. Because folder is user-controlled within allowed roots, any client can repeatedly trigger the expensive scan.

recommendation:
Add pagination or a bounded max result count, consider shallow listing by default, and run expensive filesystem scans in a threadpool if recursive listing remains necessary.

test analysis:
The linked tests validate behavior with one file per allowed root and do not exercise large directory trees, response limits, or concurrent requests while a scan is running.

suggested regression test:
Add a test that monkeypatches a low max-results limit and verifies the endpoint truncates or rejects listings beyond that limit with a clear response.

minimum fix scope:
Introduce an explicit result limit or pagination contract in list_project_files, then cover the limit in tests.

repro:
Populate files/ with tens of thousands of nested files and request GET /api/site/files?folder=files. The handler blocks while rglob/stat walks the whole tree and serializes the full list.

## medium: GET /history includes import jobs from every loaded project

id: fnd_sig-feat-route-273f356c50-428312_f796c9b69f
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /history (feat_route_273f356c50)
next: clawpatch show --finding fnd_sig-feat-route-273f356c50-428312_f796c9b69f

evidence:
- src/niamoto/gui/api/routers/pipeline.py:20
- src/niamoto/gui/api/routers/pipeline.py:485-502 (_get_import_history_entries)
- src/niamoto/gui/api/routers/pipeline.py:562-565 (get_pipeline_history)
- tests/gui/api/routers/test_pipeline.py:338-382 (test_pipeline_history_merges_terminal_import_jobs)

The route resolves a project-specific job_store from the current app, but the import side of the merged history is built from the module-global import_jobs dictionary with no current-working-directory filter. In a long-lived GUI process that has handled imports for multiple project instances, requesting one project's pipeline history can expose another project's terminal import IDs, entity names, messages, errors, and result summaries. The existing history tests assert merging terminal import jobs, but their fixtures do not include per-project metadata or any cross-project exclusion case.

recommendation:
Make _get_import_history_entries accept the current work_dir or normalized working_directory key and skip import jobs whose working_directory does not match. Preserve legacy jobs without a working_directory only if that is an intentional compatibility choice, and document/test that behavior.

test analysis:
The included /history tests only verify that terminal import jobs are merged and sorted. They never include a foreign-project import job or assert that the route filters import_jobs to the current project.

suggested regression test:
Add a /history test with two terminal import jobs carrying different working_directory values, monkeypatch the current working directory to one of them, and assert only that project's import job appears in the response.

minimum fix scope:
src/niamoto/gui/api/routers/pipeline.py plus a focused test in tests/gui/api/routers/test_pipeline.py

repro:
Populate pipeline_router.import_jobs with two terminal import jobs from different project working directories, configure the app/job_store for only one project, then call GET /api/pipeline/history. Both import jobs are eligible for _get_import_history_entries() and can be returned after sorting.

## medium: GET /jobs applies the history limit before filtering transform jobs

id: fnd_sig-feat-route-1311e76ce6-9f9050_893629ccca
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /jobs (feat_route_1311e76ce6)
next: clawpatch show --finding fnd_sig-feat-route-1311e76ce6-9f9050_893629ccca

evidence:
- src/niamoto/gui/api/routers/transform.py:499-502 (list_transform_jobs)

The route promises to list transform jobs, but it asks the shared job history for the latest 10 jobs across all job types and only then filters to type == "transform". If the project has recent import or export jobs, older transform jobs can be pushed outside that unfiltered limit and disappear from GET /jobs even though fewer than 10 transform jobs are returned. The JobFileStore API supports type-filtered history, so this route should filter before applying the limit.

recommendation:
Call `job_store.get_history(limit=10, job_type="transform")` and remove the redundant `entry.get("type") == "transform"` filtering, keeping the existing de-duplication against the active job.

test analysis:
The declared associated test file is CLI-only and does not exercise the FastAPI GET /jobs route. The linked route regression only covers duplicate removal when history already contains transform jobs, not mixed job history where non-transform entries consume the limit first.

suggested regression test:
Add a transform router test where `get_history(limit=10, job_type="transform")` is expected, or use a JobFileStore populated with many recent export/import entries plus an older transform entry and assert GET /api/transform/jobs still returns the transform entry.

minimum fix scope:
Update `list_transform_jobs` to request type-filtered history from the store and adjust/add the route regression test for mixed job history.

repro:
Create more than 10 recent non-transform history entries after a completed transform job, then call GET /api/transform/jobs. The completed transform job is omitted even though it is within the latest transform history.

## medium: GET /references ignore la configuration database.path personnalisée

id: fnd_sig-feat-route-4db4308700-cc187e_3385db09a6
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /references (feat_route_4db4308700)
next: clawpatch show --finding fnd_sig-feat-route-4db4308700-cc187e_3385db09a6

evidence:
- src/niamoto/gui/api/routers/config.py:708-712 (get_references)
- src/niamoto/gui/api/routers/config.py:774-783 (get_references)
- tests/common/test_config.py:64-75 (TestConfig.test_database_path_expands_home_path)

La route lit toujours la base à l'emplacement par défaut db/niamoto.duckdb. Pourtant la configuration du projet permet un chemin de base personnalisé, comme le montre le test de configuration. Pour un projet dont config.yml pointe vers une autre base existante, GET /references retourne encore les références de import.yml, mais perd les informations issues de la base: table_name réel via EntityRegistry, entity_count et hierarchy_fields.

recommendation:
Remplacer le chemin codé en dur par get_database_path(get_working_directory()) dans get_references, puis ne tenter l'introspection que si un Path non nul existe.

test analysis:
Les tests associés couvrent la prise en charge d'un chemin de base personnalisé par Config, et le test de route existant crée la base uniquement à l'emplacement par défaut db/niamoto.duckdb. Aucun test n'exerce GET /references avec database.path personnalisé.

suggested regression test:
Ajouter un test FastAPI qui écrit config.yml avec database.path vers un fichier DuckDB non standard, peuple EntityRegistry et la table de référence dans ce fichier, puis vérifie que /api/config/references retourne le table_name réel, entity_count et les champs hiérarchiques.

minimum fix scope:
Modifier uniquement get_references dans src/niamoto/gui/api/routers/config.py pour résoudre le chemin de base via l'aide existante get_database_path.

repro:
Créer un projet avec config/import.yml contenant une référence, config/config.yml contenant database.path: data/custom.duckdb, puis créer data/custom.duckdb avec niamoto_metadata_entities et la table de référence. Appeler /api/config/references: la réponse utilise le fallback reference_<name> et entity_count reste null au lieu d'utiliser la base configurée.

## medium: GET /spatial exposes raw exception details in 500 responses

id: fnd_sig-feat-route-209e3b8e15-52a290_c54a969363
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /spatial (feat_route_209e3b8e15)
next: clawpatch show --finding fnd_sig-feat-route-209e3b8e15-52a290_c54a969363

evidence:
- src/niamoto/gui/api/routers/stats.py:3003-3008 (get_spatial_stats)
- src/niamoto/gui/api/routers/stats.py:3145-3148 (get_spatial_stats)
- tests/cli/test_stats.py:14-22

The route is a network-facing GET endpoint with user-controlled query parameters and database/spatial parsing work. Its generic exception handler serializes str(e) directly into the HTTP response, so unexpected database, file, SQL, or spatial-extension errors can disclose local paths, SQL fragments, table names, or other internal details to callers.

recommendation:
Log the exception server-side and return a generic 500 detail such as "Error getting spatial stats" while continuing to re-raise HTTPException unchanged.

test analysis:
The listed context test file tests the CLI stats command module, not the FastAPI /spatial route or its 500 response body. It does not assert that unexpected route errors are sanitized.

suggested regression test:
Add a FastAPI TestClient test for /api/stats/spatial that monkeypatches an internal helper to raise RuntimeError("secret /tmp/spatial.sql") and asserts status 500, generic detail, and absence of the secret text.

minimum fix scope:
Change only the generic exception handler in get_spatial_stats and add one route-level regression test.

repro:
Monkeypatch a helper reached by GET /api/stats/spatial, such as _compute_geometry_count_and_bbox, to raise RuntimeError("secret /tmp/spatial.sql"), then request /api/stats/spatial?entity=shapes. The response detail will include the secret string.

## medium: GET /status silently returns an empty status because it calls a non-existent registry method

id: fnd_sig-feat-route-1abb1a69f8-fa7653_1a4762d5b1
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /status (feat_route_1abb1a69f8)
next: clawpatch show --finding fnd_sig-feat-route-1abb1a69f8-fa7653_1a4762d5b1

evidence:
- src/niamoto/gui/api/routers/imports.py:749-752 (get_import_status)
- src/niamoto/gui/api/routers/imports.py:786-793 (get_import_status)
- tests/gui/api/routers/test_imports.py:88-93 (test_get_import_status_classifies_references_and_datasets)

The production route instantiates EntityRegistry and calls registry.list_all(), but the actual registry API exposes list_entities(...), not list_all(). Because get_import_status catches every non-HTTP exception and returns empty references/datasets, the AttributeError is hidden and the endpoint reports no imported entities even when the registry has data. The included status test masks this by replacing EntityRegistry with a fake that implements list_all().

recommendation:
Change get_import_status to iterate over registry.list_entities() and keep the row-count logic unchanged. Consider logging the caught exception or narrowing the exception handling so unexpected programming errors do not become successful empty responses.

test analysis:
The only positive route test monkeypatches EntityRegistry with a FakeRegistry that provides list_all(), so it verifies the handler against a test-only API rather than the real EntityRegistry contract.

suggested regression test:
Update test_get_import_status_classifies_references_and_datasets so its FakeRegistry matches the real API by implementing list_entities(), or add an integration-style unit test that uses the real EntityRegistry with a small temporary database and asserts imported references/datasets are returned.

minimum fix scope:
src/niamoto/gui/api/routers/imports.py plus the GET /status test fake in tests/gui/api/routers/test_imports.py

repro:
With a normal configured working directory and a database containing registered imported entities, call GET /api/imports/status. The handler raises AttributeError at registry.list_all(), catches it, and responds 200 with {"references":[],"datasets":[]} instead of the real statuses.

## medium: GET /widgets returns a successful empty list when widget discovery fails

id: fnd_sig-feat-route-61a42f0933-20f61b_6de3df8102
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /widgets (feat_route_61a42f0933)
next: clawpatch show --finding fnd_sig-feat-route-61a42f0933-20f61b_6de3df8102

evidence:
- src/niamoto/gui/api/routers/recipes.py:1228-1243 (list_widgets)
- tests/gui/api/routers/test_recipes.py:261-278 (test_recipes_widgets_lists_all_core_widget_modules)
- tests/gui/api/routers/test_recipes.py:344-357 (test_recipes_list_transformers_reports_registry_failures)

The route catches every exception from plugin loading, registry access, or response construction and converts it into HTTP 200 with an empty widget list. That makes an infrastructure or registry failure indistinguishable from a valid project with no widgets, so clients will silently hide all widget choices instead of surfacing an API error. The sibling transformer listing route treats the same class of registry failure as a 500, and the tests encode that expectation for transformers while only covering the widget success path.

recommendation:
Match `list_transformers`: let `HTTPException` propagate if introduced, and convert unexpected exceptions to `HTTPException(status_code=500, detail="Unable to list widgets")` rather than returning `[]`.

test analysis:
The included widget test only verifies the happy path where core widget modules are discovered. Failure behavior is covered for `/transformers`, but there is no analogous `/widgets` registry-failure regression test.

suggested regression test:
Add `test_recipes_list_widgets_reports_registry_failures` that monkeypatches `_ensure_plugins_loaded` to no-op, monkeypatches `PluginRegistry.get_plugins_by_type` to raise, calls `/api/recipes/widgets`, and asserts status 500 with detail `Unable to list widgets`.

minimum fix scope:
Change only the `list_widgets` exception handler and add the focused route regression test.

repro:
Monkeypatch `PluginRegistry.get_plugins_by_type` to raise `RuntimeError("registry unavailable")` and call `GET /api/recipes/widgets`; the handler logs the exception and returns `200 []` instead of a failure response.

## medium: GET dataset config does not validate malformed import.yml structure

id: fnd_sig-feat-route-8ccd6757e9-ff18ca_29ee8d918d
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /datasets/{dataset_name}/config (feat_route_8ccd6757e9)
next: clawpatch show --finding fnd_sig-feat-route-8ccd6757e9-ff18ca_29ee8d918d

evidence:
- src/niamoto/gui/api/routers/config.py:974-987 (get_dataset_config)
- src/niamoto/gui/api/routers/config.py:1014-1026 (update_dataset_config)
- tests/gui/api/routers/test_config_datasets.py:304-327 (test_update_dataset_config_rejects_malformed_entities_without_writing)
- tests/gui/api/routers/test_config_datasets.py:437-465 (test_update_dataset_config_rejects_malformed_datasets_without_writing)

The GET route assumes import.yml, entities, and entities.datasets are mappings. If import.yml has a non-object root or a non-object entities value, AttributeError is caught and returned as a 500. If entities.datasets is a list, a missing dataset is reported as 404 instead of malformed configuration, and a matching string can produce a TypeError. The sibling PUT route explicitly treats the same malformed structures as 400 responses, with regression tests establishing that contract.

recommendation:
Mirror update_dataset_config's structural checks in get_dataset_config before lookup: require the YAML root, entities, and entities.datasets to be dicts and raise the same 400 malformed import.yml errors.

test analysis:
The existing GET tests cover valid lookup, missing dataset, and missing import.yml only. Malformed import.yml coverage exists for PUT, not for this GET route.

suggested regression test:
Add GET /api/config/datasets/{name}/config tests for non-object root, non-object entities, and non-object entities.datasets asserting 400 with the malformed import.yml messages.

minimum fix scope:
Add structural validation to get_dataset_config and corresponding route tests.

repro:
Create config/import.yml with `entities: [not, a, dict]`, then call GET /api/config/datasets/observations/config. The route returns a 500 from `entities.get(...)` instead of the 400 malformed-config response used by the dataset update route.

## medium: GET export widgets can return the wrong group when another exporter shares group_by

id: fnd_sig-feat-route-6fc1e94006-577ab4_b9d493389a
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /export/{group_by}/widgets (feat_route_6fc1e94006)
next: clawpatch show --finding fnd_sig-feat-route-6fc1e94006-577ab4_b9d493389a

evidence:
- src/niamoto/gui/api/routers/config.py:164-178 (_find_export_group_in_supported_locations)
- src/niamoto/gui/api/routers/config.py:1929-1947 (list_export_widgets)
- src/niamoto/gui/api/routers/config.py:212-232 (_find_export_group_with_index_generator)

list_export_widgets uses a generic group finder that returns the first matching group_by from any export target before checking params.groups. If a json_api_exporter or other non-web exporter appears before the html_page_exporter for the same group_by, the route returns that non-web group and then [] for widgets, hiding the actual configured web widgets. The neighboring index-generator path already avoids this class of bug by filtering to html_page_exporter before selecting a group.

recommendation:
Use a web-export-specific finder for this route, filtering export entries to exporter == "html_page_exporter" and checking both root groups and params.groups there before returning widgets.

test analysis:
tests/common/test_config.py does not exercise GET /export/{group_by}/widgets. The existing export widgets route test only covers a single export target with params.groups, so it never puts a non-web group with the same group_by before the web widgets group.

suggested regression test:
Add a route test with a json_api_exporter group before a html_page_exporter group for the same group_by and assert GET /api/config/export/plots/widgets returns the html_page_exporter widgets.

minimum fix scope:
Change only the group selection used by list_export_widgets, plus a focused regression test for mixed exporter ordering.

repro:
Create export.yml with exports[0] as json_api_exporter containing groups: [{group_by: plots, index: {fields: []}}] and exports[1] as html_page_exporter containing groups: [{group_by: plots, widgets: [{plugin: interactive_map, data_source: plot_map, params: {}}]}]. GET /api/config/export/plots/widgets returns [] instead of the interactive_map widget.

## medium: GET plugin details is ambiguous for same-name plugins registered under different types

id: fnd_sig-feat-route-b5a2541152-ad55dd_000e9b5e22
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /{plugin_id} (feat_route_b5a2541152)
next: clawpatch show --finding fnd_sig-feat-route-b5a2541152-ad55dd_000e9b5e22

evidence:
- src/niamoto/gui/api/routers/plugins.py:459-462 (get_plugin)
- src/niamoto/core/plugins/registry.py:67-92 (PluginRegistry.register_plugin)
- tests/core/plugins/test_registry.py:86-105 (test_metadata_is_isolated_by_plugin_type)
- tests/gui/api/routers/test_plugins.py:179-193 (test_get_plugin_uses_registry_type_when_class_type_disagrees)

The registry is type-scoped and tests explicitly allow the same plugin name to exist under multiple PluginType values. The GET /api/plugins/{plugin_id} route accepts only the name, then returns the first matching type in enum order. If a loader and transformer share an id, clients cannot request the loader details and may receive the wrong type, output_format, and parameter schema.

recommendation:
Make plugin detail lookup type-aware. Add an optional required-on-ambiguity type query parameter, or return a 409/400 when the same id exists in multiple plugin types. Keep the untyped path working only when the id is unique across registered types.

test analysis:
The GUI router tests only register one plugin type per id for GET /{plugin_id}. The core registry tests cover same-name plugins across types, but no API test exercises that valid registry state through this route.

suggested regression test:
Add a GUI API test that registers the same plugin id under two PluginType values, calls GET /api/plugins/{plugin_id}, and asserts the chosen contract: either a clear ambiguity error or the correct result when a type query parameter is provided.

minimum fix scope:
Update src/niamoto/gui/api/routers/plugins.py get_plugin lookup semantics and add a focused test in tests/gui/api/routers/test_plugins.py.

repro:
Register two plugins with the same name under PluginType.TRANSFORMER and PluginType.LOADER, then call GET /api/plugins/shared_plugin. The route returns whichever type appears first in PluginType iteration instead of detecting ambiguity or letting the caller choose the type.

## medium: Group index preview ignores index_generator output_pattern

id: fnd_sig-feat-route-c0bfa615fb-abb891_76d1c6aafc
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /preview-group-index/{group_name} (feat_route_c0bfa615fb)
next: clawpatch show --finding fnd_sig-feat-route-c0bfa615fb-abb891_76d1c6aafc

evidence:
- src/niamoto/gui/api/routers/site.py:1937-1943 (preview_group_index)
- tests/gui/api/routers/test_site.py:513-543 (TestSiteGroups.test_groups_endpoint_falls_back_to_default_output_patterns)

The route accepts saved or draft index_generator config, but the preview context always uses the top-level group output_pattern. A custom index_generator.output_pattern is a supported configuration shape, as shown by the groups endpoint test, so previewing a saved or draft group index with a custom detail-link pattern will render stale/wrong preview context and can disagree with the real generated page.

recommendation:
Build the preview output_pattern from index_gen.get("output_pattern") first, fall back to group_config output_pattern only when absent, and format any {group_by} placeholder while preserving {id}, matching the production index generator behavior.

test analysis:
The existing tests verify that /groups preserves index_generator.output_pattern, but the preview route tests never include a custom output_pattern or assert the rendered indexConfig JSON.

suggested regression test:
Add a preview-group-index test with index_generator.output_pattern set to custom-plots/{id}.html and assert the response HTML contains that pattern in indexConfig instead of the group default.

minimum fix scope:
src/niamoto/gui/api/routers/site.py inside preview_group_index output_pattern construction plus one targeted test in tests/gui/api/routers/test_site.py

repro:
Create a group with index_generator.output_pattern set to custom-plots/{id}.html and a group output_pattern omitted or set to plots/{id}.html, then POST /api/site/preview-group-index/plots using a template that reads index_config.output_pattern. The response uses plots/{id}.html instead of custom-plots/{id}.html.

## medium: Highest elevation bin edge is excluded from forest overlay and forest-elevation percentages

id: fnd_sig-feat-library-7e7ea31318-60bd_ac56934e88
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/ecological (feat_library_7e7ea31318)
next: clawpatch show --finding fnd_sig-feat-library-7e7ea31318-60bd_ac56934e88

evidence:
- src/niamoto/core/plugins/transformers/ecological/elevation_profile.py:178-179 (ElevationProfile.transform)
- src/niamoto/core/plugins/transformers/ecological/elevation_profile.py:312-318 (ElevationProfile._calculate_forest_distribution)
- src/niamoto/core/plugins/transformers/ecological/forest_elevation.py:300-308 (ForestElevationAnalysis.transform)

np.histogram includes values equal to the final bin edge in the last bin, but the manual bin masks use '< bin_edges[i + 1]' for every bin. Pixels exactly equal to the maximum custom bin or final elevation bin are omitted from forest_distribution totals and from ForestElevationAnalysis percentages. This can make overlay totals disagree with the main elevation histogram and undercount real pixels at common rounded bin boundaries.

recommendation:
For the final bin, use '<= upper_edge' or delegate bin assignment to numpy.digitize/searchsorted with explicit right-edge handling so the last class includes values exactly equal to its upper bound.

test analysis:
The current DEM fixtures top out at 990 while the final bin edge is 1000, so no test exercises a pixel exactly on the upper edge.

suggested regression test:
Use elevation values [0, 100, 200] with bins [0, 100, 200] and assert the 200-valued pixel is counted in the last class for both forest overlay and forest elevation totals.

minimum fix scope:
Adjust the bin-mask construction in ElevationProfile._calculate_forest_distribution and all ForestElevationAnalysis bin loops.

## medium: Import summary includes Niamoto metadata tables as user entities

id: fnd_sig-feat-route-bb0f9ee92d-a7dddc_f6bacac0da
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /summary (feat_route_bb0f9ee92d)
next: clawpatch show --finding fnd_sig-feat-route-bb0f9ee92d-a7dddc_f6bacac0da

evidence:
- src/niamoto/gui/api/routers/stats.py:2141-2152 (_compute_import_summary)
- src/niamoto/gui/api/routers/stats.py:2169-2176 (_compute_import_summary)
- src/niamoto/core/imports/registry.py:35-39 (EntityRegistry)
- tests/gui/api/routers/test_stats.py:509-526 (test_import_summary_uses_duckdb_fixture_without_sqlalchemy_reflection_errors)

The route claims to return an import summary per entity, and the route test expects only imported domain tables. In real Niamoto databases, EntityRegistry creates the internal niamoto_metadata_entities table, but _compute_import_summary only filters names starting with '_' or 'sqlite'. That means metadata tables are counted as datasets, inflate total_entities/total_rows, expose internal column names, and can create bogus empty-table alerts.

recommendation:
Use a shared internal/system table filter for summary enumeration, at minimum excluding niamoto_metadata_entities, alembic_version, spatial_ref_sys, geography_columns, geometry_columns, and spatial_ref_sys_aux before counting and serializing entities.

test analysis:
The summary endpoint test fixture creates only two domain tables and a view, so the assertion that total_entities is 2 never exercises a realistic database with niamoto_metadata_entities present.

suggested regression test:
Add a stats router test that creates niamoto_metadata_entities alongside the two domain tables, calls /api/stats/summary, and asserts total_entities remains 2 and the metadata table is absent from entities and alerts.

minimum fix scope:
Filter internal/system table names inside _compute_import_summary before row-count queries and entity serialization.

repro:
Create or use a project database containing dataset_occurrences, entity_taxons, and niamoto_metadata_entities, then GET /api/stats/summary. The response will include niamoto_metadata_entities in entities and count its rows in total_rows.

## medium: Index entity merge misses rows when join key types differ

id: fnd_sig-feat-library-db85b6eec6-ee92_c62f375a3f
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/exporters (feat_library_db85b6eec6)
next: clawpatch show --finding fnd_sig-feat-library-db85b6eec6-ee92_c62f375a3f

evidence:
- src/niamoto/core/plugins/exporters/index_generator.py:209-244 (IndexGeneratorPlugin._resolve_entity_join_column)
- src/niamoto/core/plugins/exporters/index_generator.py:334-339 (IndexGeneratorPlugin._get_entity_rows_by_group_id)
- src/niamoto/core/plugins/exporters/index_generator.py:400-405 (IndexGeneratorPlugin._get_group_data)
- tests/core/plugins/exporters/test_index_generator.py:291-333 (test_get_group_data_uses_entity_leaf_fallback_for_legacy_filter_paths)

The join-column selection intentionally treats string and numeric IDs as equivalent, but the later merge keys entity_rows by the raw database value and looks up with the raw transformed item value. If the transformed table stores plots_id as "1" and the reference table stores id as 1, _resolve_entity_join_column will choose id, but entity_rows.get("1") will not find the entity row keyed by 1. Entity fallback fields and legacy filters then fail even though the join was detected as valid.

recommendation:
Normalize the lookup key consistently after join-column detection. For example, store entity rows by both raw key and str(key), or look up item_id first raw then str(item_id), while avoiding collisions deterministically.

test analysis:
The existing legacy fallback test uses matching integer IDs on both sides, so it exercises the intended merge path but not the mixed text/numeric ID case that the join detection code explicitly tries to support.

suggested regression test:
Add a variant of test_get_group_data_uses_entity_leaf_fallback_for_legacy_filter_paths where the group table returns plots_id as "1" and the entity table returns id as 1, then assert the entity fallback field is merged and filtered correctly.

minimum fix scope:
IndexGeneratorPlugin entity row keying and lookup during _get_group_data.

repro:
Use group rows [{"plots_id": "1"}] and entity rows [{"id": 1, "locality_name": "Pic Ningua"}] with a legacy filter/display fallback on locality_name. The join column is detected, but the entity row is not merged because "1" != 1.

## medium: Interactive map tests can pass while the exercised behavior is broken

id: fnd_sig-feat-test-suite-648ebff255-8_1a5a63643f
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/widgets#1 (feat_test-suite_648ebff255)
next: clawpatch show --finding fnd_sig-feat-test-suite-648ebff255-8_1a5a63643f

evidence:
- tests/core/plugins/widgets/test_interactive_map.py:508-514 (TestInteractiveMapWidgetRender.test_render_topojson_parsing)
- tests/core/plugins/widgets/test_interactive_map.py:762-768 (TestInteractiveMapWidgetMultiLayer.test_render_multi_layer_with_layers_but_no_content)

The TopoJSON test explicitly accepts either successful output or error output as long as a string is returned, so a regression that fails conversion/rendering can still pass. The multi-layer empty-content test replaces the private renderer with the expected result, so it verifies the mock rather than the widget's real fallback behavior. These are intended map coverage points, but they do not fail when the map path breaks.

recommendation:
Make the tests assert the real behavior: patch only external Plotly/TopoJSON dependencies, assert no error HTML is returned, assert the selected renderer/call args, and inspect the generated DataFrame/traces or expected warning string from the real _render_multi_layer_map implementation.

test analysis:
The current assertions are too permissive and one test replaces the code path that should be validated.

suggested regression test:
For TopoJSON, assert choropleth_map or the expected multi-layer renderer is called with converted features and that the result contains plotly-graph-div without error text. For empty multi-layer content, call the real renderer and assert the documented empty-layer message without mocking _render_multi_layer_map.

minimum fix scope:
Update the two interactive map tests to stop accepting error output and stop mocking the method whose behavior is under review.

repro:
Change the TopoJSON render path to return an error string, or change _render_multi_layer_map's empty-content behavior; these tests can still pass because they only assert non-None output or mock the implementation under test.

## medium: Interactive query tool can modify the database despite being presented as an inspection helper

id: fnd_sig-feat-library-44f43ae273-c634_c3fdf67e50
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: Python source scripts/data (feat_library_44f43ae273)
next: clawpatch show --finding fnd_sig-feat-library-44f43ae273-c634_c3fdf67e50

evidence:
- scripts/data/query_db.py:128-169 (execute_query)
- scripts/data/query_db.py:223-228 (main)

The script is documented and named as a query/inspection utility, but execute_query sends arbitrary user-provided SQL directly to the DuckDB connection. Because the default connection is not read-only and --read-only is optional, an accidental DELETE, UPDATE, DROP, or CREATE statement can mutate or destroy the development database while using a helper intended for inspection. The code also calls fetchall()/result.keys() unconditionally, so write statements may fail after already applying changes, making the mutation easy to miss behind an error message.

recommendation:
Make read-only mode the default for this script, or reject non-SELECT/PRAGMA/SHOW/DESCRIBE statements unless an explicit `--write` flag is provided. For write mode, handle statements that do not return rows without calling fetchall().

test analysis:
No linked tests were provided for scripts/data, and the owned files do not include regression coverage for read-only defaults or SQL statement classification.

suggested regression test:
Add a CLI test using a temporary DuckDB database that verifies a destructive statement is rejected by default and only allowed when an explicit write flag is supplied.

minimum fix scope:
Update `scripts/data/query_db.py` argument defaults and `execute_query` statement handling.

repro:
Run `uv run python scripts/data/query_db.py "DROP TABLE taxon"` against a writable database; the command is accepted by the script path that is otherwise described as a query utility.

## medium: Invalid complement_mode silently falls back to ratio mode

id: fnd_sig-feat-library-789e16e347-3e1f_6787f42ee1
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/core/plugins/transformers/class_objects (feat_library_789e16e347)
next: clawpatch show --finding fnd_sig-feat-library-789e16e347-3e1f_6787f42ee1

evidence:
- src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py:43-50 (DistributionConfig.complement_mode)
- src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py:287-292 (ClassObjectSeriesRatioAggregator.transform)

The schema advertises only ratio and difference, but the model accepts any string and transform treats every non-"difference" value as ratio. A typo such as "differnce" will pass validation and produce ratio complements instead of failing fast, which can silently publish incorrect distribution data.

recommendation:
Constrain complement_mode with Literal["ratio", "difference"] or a Pydantic validator, and keep the transform branch explicit for both supported modes.

test analysis:
The provided linked test file does not exercise class_object_series_ratio_aggregator. Existing validation paths only check missing distributions, not invalid complement_mode values.

suggested regression test:
Add a validation test asserting complement_mode values outside "ratio" and "difference" raise DataTransformError.

minimum fix scope:
DistributionConfig in src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py and a focused config validation test.

repro:
Configure complement_mode as "differnce" for a total/subset pair. Validation succeeds and the transformer computes ratio mode rather than raising an invalid configuration error.

## medium: Invalid deploy.yml is silently ignored

id: fnd_sig-feat-library-34fbee6012-3830_00ac2800f1
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/common#1 (feat_library_34fbee6012)
next: clawpatch show --finding fnd_sig-feat-library-34fbee6012-3830_00ac2800f1

evidence:
- src/niamoto/common/config.py:234-241 (Config._load_files)
- src/niamoto/common/config.py:984-992 (Config.get_deploy_config)
- src/niamoto/cli/commands/deploy.py:102-120 (deploy_commands)
- tests/common/test_config.py:425-439 (test_file_format_error)

deploy.yml is optional when absent, but once present it is user configuration for deployment defaults. Catching every exception and replacing it with {} hides malformed YAML and read errors, so deploy commands report misleading missing platform/project errors or proceed with CLI defaults while silently dropping branch/extra settings. The other config files surface invalid YAML as ConfigurationError, so deploy.yml currently has a weaker and surprising error contract.

recommendation:
Parse deploy.yml with the same error handling as the other YAML files: raise a ConfigurationError/FileFormatError when the file exists but cannot be parsed or read. Keep {} only for the absent-file case.

test analysis:
The config tests cover invalid YAML for config.yml but not deploy.yml. Deploy command tests mock get_deploy_config directly, so they cannot catch parsing failures being swallowed in Config._load_files.

suggested regression test:
Add a Config test that writes malformed deploy.yml alongside valid required config files and asserts Config(...).get_deploy_config raises a ConfigurationError that includes deploy.yml.

minimum fix scope:
src/niamoto/common/config.py deploy.yml loading plus tests/common/test_config.py coverage.

repro:
Create config/deploy.yml containing invalid YAML, then run niamoto deploy. Config loads successfully with an empty deploy config, and the CLI errors as if no deploy defaults were configured instead of pointing to the malformed file.

## medium: Invalid one-character CSV delimiters return 500 instead of a client error

id: fnd_sig-feat-route-27fbbd5e55-b3f6dc_b0bd043f74
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /import-csv (feat_route_27fbbd5e55)
next: clawpatch show --finding fnd_sig-feat-route-27fbbd5e55-b3f6dc_b0bd043f74

evidence:
- src/niamoto/gui/api/routers/site.py:3032-3043 (import_csv)
- src/niamoto/gui/api/routers/site.py:3093-3098 (import_csv)
- tests/gui/api/routers/test_site.py:265-276 (test_import_csv_rejects_invalid_delimiters)

The endpoint validates only delimiter length, but Python's csv module also rejects some single-character delimiters such as newline, carriage return, and quote. Those are fully user-controlled query values. Because csv.reader/list(reader) errors are caught by the generic exception handler, the route returns HTTP 500 with an internal parser message instead of the same 400-style validation response used for other invalid delimiter inputs.

recommendation:
Validate delimiter against csv module constraints before parsing, or catch csv.Error/ValueError from csv.reader creation and iteration and convert them to HTTP 400 with a stable client-facing message.

test analysis:
The existing invalid delimiter test covers only length-zero and multi-character values, so it never exercises one-character values that pass the current guard but are rejected by csv.reader.

suggested regression test:
Add a parametrized test for delimiters like "\n", "\r", and "\"" asserting HTTP 400 and the stable delimiter validation detail.

minimum fix scope:
Update import_csv delimiter validation/error handling in src/niamoto/gui/api/routers/site.py and extend tests/gui/api/routers/test_site.py for csv-module-invalid one-character delimiters.

repro:
POST /api/site/import-csv?delimiter=%0A with a small valid data.csv upload. In a TestClient check with raise_server_exceptions=False, this returns 500 {"detail":"Error processing CSV file: bad delimiter value"}.

## medium: Invalid reference_kind values silently generate generic sources

id: fnd_sig-feat-route-66e52a2d79-5b7e60_1b89789439
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /generate-config (feat_route_66e52a2d79)
next: clawpatch show --finding fnd_sig-feat-route-66e52a2d79-5b7e60_1b89789439

evidence:
- src/niamoto/gui/api/models/templates.py:116-119 (GenerateConfigRequest.reference_kind)
- src/niamoto/gui/api/routers/templates.py:544-590 (generate_transform_config)

The request contract documents only hierarchical, generic, and spatial, but the model accepts any string and the handler treats every unknown value as generic. A typo such as "hierachical" returns 200 with a direct_reference source instead of the nested_set source the caller intended or a validation error. That can produce a wrong transform configuration that still flows into save-config.

recommendation:
Constrain reference_kind with Literal["hierarchical", "generic", "spatial"] or an enum in GenerateConfigRequest, and keep an explicit defensive error in the route for unknown values.

test analysis:
Existing tests cover hierarchical, generic, and spatial happy paths, but no test sends an unsupported reference_kind.

suggested regression test:
Add a test that POSTs reference_kind="hierachical" and asserts FastAPI returns 422, or 400 if validation is handled manually.

minimum fix scope:
Update GenerateConfigRequest.reference_kind validation and add one router test for invalid values.

repro:
POST /api/templates/generate-config with group_by "taxons", a valid template, and reference_kind "hierachical". The route reaches the final else branch and returns a generic direct_reference source instead of rejecting the invalid enum value.

## medium: Invalid uploads keep the reserved file and block retry

id: fnd_sig-feat-route-17e9348762-60eae7_e8a6443da4
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /{reference_name}/upload (feat_route_17e9348762)
next: clawpatch show --finding fnd_sig-feat-route-17e9348762-60eae7_e8a6443da4

evidence:
- src/niamoto/gui/api/routers/sources.py:373-389 (upload_precalc_source)
- src/niamoto/gui/api/routers/sources.py:421-433 (upload_precalc_source)
- src/niamoto/gui/api/routers/sources.py:435-444 (upload_precalc_source)

The route persists imports/raw_<source_name>.csv before analysis, then returns 200 with success=false when the analyzer reports validation errors. Cleanup only runs for HTTPException or unexpected exceptions, so a non-empty but invalid CSV remains on disk. Because future uploads use exclusive create mode, the user cannot upload a corrected file with the same source_name and gets 409 instead.

recommendation:
After analysis, if analysis.is_valid is false, delete the saved file before returning the validation response, or allow a controlled overwrite/replacement flow for failed validation artifacts.

test analysis:
The upload tests cover oversized files, existing files, path-component source names, and empty CSV cleanup, but they do not cover a non-empty CSV that the analyzer marks invalid without raising an exception.

suggested regression test:
Add a TestClient test that uploads a non-empty invalid CSV, asserts the response has success=false, asserts imports/raw_<source>.csv is removed, then uploads a corrected CSV with the same source_name and gets 200.

minimum fix scope:
Update upload_precalc_source cleanup handling around the analysis result and add a route-level regression test.

repro:
POST a non-empty CSV missing required class_object/class_name/class_value columns to /api/sources/taxons/upload?source_name=bad_stats. The response is a validation failure with success=false, but imports/raw_bad_stats.csv remains. POST a corrected CSV with the same source_name and the route returns 409.

## medium: Irregular target entity names bypass semantic relationship detection

id: fnd_sig-feat-library-61c2081729-ac22_bef3ac65a6
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/utils (feat_library_61c2081729)
next: clawpatch show --finding fnd_sig-feat-library-61c2081729-ac22_bef3ac65a6

evidence:
- src/niamoto/core/utils/column_detector.py:593-608 (ColumnDetector._detect_semantic_relationship)
- src/niamoto/core/utils/column_detector.py:611-617 (ColumnDetector._detect_semantic_relationship)
- src/niamoto/core/utils/column_detector.py:940-943 (ColumnDetector._infer_entity_token)

Semantic matching normalizes the target entity by stripping a trailing "s" instead of using the existing entity-token vocabulary. A common taxonomy file/entity named "taxa" therefore stays "taxa", so a source field like "taxon_name" never reaches candidate scoring even when source and target sample values overlap. The same input works when the target entity is named "taxons", which shows the failure is the ad hoc plural normalization rather than the samples or scoring.

recommendation:
Normalize target_entity_name through cls._infer_entity_token, falling back to the existing string behavior only when no domain token is found. Use that normalized token in the keyword comparison and scoring path.

test analysis:
The relationship tests cover target_entity_name="taxons" for taxon identifiers, but not the irregular plural "taxa" or a taxon label relationship to a generic target "name" column.

suggested regression test:
Add a ColumnDetector.detect_relationships test with source_columns=["taxon_name"], target_columns=["id", "name"], overlapping source/target name samples, and target_entity_name="taxa"; assert it returns target_field="name".

minimum fix scope:
Update _detect_semantic_relationship target entity normalization and add the focused regression test.

repro:
PYTHONPATH=src python3 -c "from niamoto.core.utils.column_detector import ColumnDetector; sample_src=[{'taxon_name':'Araucaria columnaris'}]; sample_tgt=[{'id':'101','name':'Araucaria columnaris'}]; print(ColumnDetector.detect_relationships(['taxon_name'], ['id','name'], sample_src, sample_tgt, 'occurrences', 'taxa')); print(ColumnDetector.detect_relationships(['taxon_name'], ['id','name'], sample_src, sample_tgt, 'occurrences', 'taxons'))" prints [] for "taxa" and a semantic_context relationship for "taxons".

## medium: Job status lookup bypasses current working-directory scope

id: fnd_sig-feat-route-341c0aea45-bc831c_7898b6a571
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /jobs/{job_id} (feat_route_341c0aea45)
next: clawpatch show --finding fnd_sig-feat-route-341c0aea45-bc831c_7898b6a571

evidence:
- src/niamoto/gui/api/routers/imports.py:481-488 (get_job_status)
- src/niamoto/gui/api/routers/imports.py:500-507 (list_import_jobs)
- tests/gui/api/routers/test_imports.py:1007-1037 (test_list_import_jobs_filters_to_current_working_directory)

The list endpoint explicitly scopes visible jobs to the current working directory, and the linked test confirms jobs from another project are hidden. The single-job endpoint only checks that the supplied job_id exists globally, then returns the job. Anyone who has or guesses a retained job id can fetch status, events, errors, and the stored working_directory for a different project even while the UI context is scoped elsewhere.

recommendation:
Apply the same working-directory check in get_job_status before returning the job. If a current working directory is set and the job's working_directory differs, return 404. Keep the existing behavior for no current working directory only if that global view is intentional.

test analysis:
The existing tests cover traceback redaction for GET /jobs/{job_id} and working-directory filtering for GET /jobs, but there is no test that requests a specific job from a different working directory.

suggested regression test:
Add a test_get_job_status_filters_to_current_working_directory that inserts job-a under project-a and job-b under project-b, sets get_working_directory to project-b, asserts GET /api/imports/jobs/job-a returns 404, and asserts GET /api/imports/jobs/job-b returns 200.

minimum fix scope:
Update get_job_status in src/niamoto/gui/api/routers/imports.py and add the focused router regression test.

repro:
Create two import_jobs entries with different working_directory values, monkeypatch get_working_directory to project-b, then GET /api/imports/jobs/job-a. The current handler returns 200 for project-a instead of the same not-found/hidden behavior implied by list_import_jobs.

## medium: Job status response can expose an inconsistent terminal snapshot

id: fnd_sig-feat-route-8f77fcdc48-8d2aa4_a97dbba34c
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /auto-configure/jobs/{job_id} (feat_route_8f77fcdc48)
next: clawpatch show --finding fnd_sig-feat-route-8f77fcdc48-8d2aa4_a97dbba34c

evidence:
- src/niamoto/gui/api/routers/smart_config.py:201-204 (_AutoConfigureJobStore.get_job)
- src/niamoto/gui/api/routers/smart_config.py:238-241 (_AutoConfigureJobStore.complete_with_event)
- src/niamoto/gui/api/routers/smart_config.py:828-836 (get_auto_configure_job)

The store returns the live mutable job object after releasing its lock, and GET /auto-configure/jobs/{job_id} then reads result, events, timestamps, and status as separate unlocked accesses while the background thread mutates the same object under the store lock. A request can read result as None, then the worker can complete the job, and the same response can return status="completed" with result=null. Clients commonly stop polling on a terminal status, so this can lose the successful auto-config result for that poll cycle.

recommendation:
Add a store-level snapshot method that copies status, events, result, error, and timestamps while holding _lock, and have get_auto_configure_job build the Pydantic response from that immutable snapshot. Reuse the same snapshot approach for event streaming if it needs consistent indexing.

test analysis:
tests/gui/api/routers/test_smart_config.py polls until completion and asserts the final result exists, but it does not force the completion interleaving between the unlocked field reads, so the race remains nondeterministic and likely invisible in normal test runs.

suggested regression test:
Add a controlled unit test around a new snapshot API: hold the store lock or use a barrier to simulate completion during status serialization, then assert a terminal completed snapshot always includes the completed result from the same locked state.

minimum fix scope:
Implement an atomic snapshot/read method in _AutoConfigureJobStore and update get_auto_configure_job to use it instead of reading the live _AutoConfigureJob fields directly.

repro:
Poll GET /api/smart/auto-configure/jobs/{job_id} while a background auto-config thread completes. With an interleaving between line 828 and line 834, the response can contain status completed and result null.

## medium: Labels can become misaligned when categories are inferred

id: fnd_sig-feat-library-9718bfdcc9-5353_5bfdc84540
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/distribution (feat_library_9718bfdcc9)
next: clawpatch show --finding fnd_sig-feat-library-9718bfdcc9-5353_5bfdc84540

evidence:
- src/niamoto/core/plugins/transformers/distribution/categorical_distribution.py:51-56 (CategoricalDistributionParams.validate_labels_length)
- src/niamoto/core/plugins/transformers/distribution/categorical_distribution.py:205-206 (CategoricalDistribution.transform)
- src/niamoto/core/plugins/transformers/distribution/categorical_distribution.py:235-239 (CategoricalDistribution.transform)
- tests/core/plugins/transformers/distribution/test_categorical_distribution.py:72-83 (TestCategoricalDistribution.test_invalid_config_mismatched_labels_categories)

When labels are provided but categories are omitted, validation skips the length check because categories is still empty. transform then derives categories from the data but keeps the provided labels unchanged, so the returned categories/counts/labels arrays can have different lengths. Downstream chart widgets typically treat these arrays as parallel series, so this can produce mislabeled or broken distributions instead of rejecting an invalid configuration.

recommendation:
After deriving categories, validate that any provided labels length matches the derived category count, or require categories whenever labels is non-empty. Raise a clear ValueError before returning mismatched arrays.

test analysis:
The existing mismatch test only covers labels with explicit categories. The auto-derived category path is tested only without user-provided labels.

suggested regression test:
Add a categorical_distribution test where labels are provided without categories and the input data has a different number of unique categories; assert that transform raises a clear ValueError or returns aligned labels.

minimum fix scope:
Update CategoricalDistribution.transform or parameter validation to validate labels after category inference.

repro:
Call transform with data pd.DataFrame({'category': ['A', 'B', 'C']}) and config {'params': {'source': 'occurrences', 'field': 'category', 'labels': ['Only one']}}. The result contains three categories and counts but only one label.

## medium: Le manifeste peut omettre silencieusement des plugins enregistrés

id: fnd_sig-feat-library-2852349fd3-8ef7_e0dd6dd54b
category: build-release
confidence: high
triage: risk
status: open
feature: Python source scripts (feat_library_2852349fd3)
next: clawpatch show --finding fnd_sig-feat-library-2852349fd3-8ef7_e0dd6dd54b

evidence:
- scripts/generate-plugin-manifest.py:43-51 (_extract_type_from_register_args)
- scripts/generate-plugin-manifest.py:111-120 (_plugins_in_file)
- src/niamoto/core/plugins/base.py:438-445 (register)

Le script extrait uniquement le type passé en deuxième argument positionnel, puis saute le plugin si aucune des heuristiques ne marche. Or l’API réelle de register accepte aussi plugin_type comme argument nommé. Un plugin valide écrit avec @register("x", plugin_type=PluginType.WIDGET), ou tout autre cas non couvert, serait donc absent de .marketing/plugins.json tout en ne faisant pas échouer la génération. Comme ce fichier est consommé par le site marketing et vérifié en CI, cela peut publier un catalogue incomplet avec une réussite apparente.

recommendation:
Lire aussi les keywords du décorateur, notamment plugin_type, et transformer les types non résolus en erreur bloquante au lieu de continuer silencieusement. Cela garde le manifeste exhaustif ou fait échouer la CI quand le script ne comprend pas une forme valide.

test analysis:
Les tests du générateur couvrent le type positionnel, le fallback via attribut type, le fallback via classe de base et les erreurs de syntaxe, mais pas la forme plugin_type=... ni le fait qu’un type non résolu devrait échouer plutôt que produire un manifeste partiel.

suggested regression test:
Ajouter un test avec @register("keyword_widget", plugin_type=PluginType.WIDGET) et vérifier que le plugin est inclus avec type "widget". Ajouter aussi un test avec @register("unknown") sans type inférable qui attend une exception au lieu d’un skip silencieux.

minimum fix scope:
Modifier scripts/generate-plugin-manifest.py pour extraire plugin_type depuis ast.Call.keywords, lever une exception quand ptype reste None, puis étendre tests/scripts/test_generate_plugin_manifest.py avec les deux cas de régression.

repro:
Ajouter un plugin de test avec @register("keyword_widget", plugin_type=PluginType.WIDGET) sur une classe sans base WidgetPlugin directe ni attribut type, puis exécuter extract_plugins: le plugin est imprimé comme ignoré sur stderr et absent du résultat au lieu d’être inclus ou de faire échouer la génération.

## medium: Legacy preview validation errors are returned as successful HTTP responses

id: fnd_sig-feat-route-03e5b72e47-de1aaa_f18d572aff
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /preview (feat_route_03e5b72e47)
next: clawpatch show --finding fnd_sig-feat-route-03e5b72e47-de1aaa_f18d572aff

evidence:
- src/niamoto/gui/api/routers/enrichment.py:329-334 (preview_enrichment)
- tests/gui/api/routers/test_enrichment.py:164-186 (test_preview_legacy_route_translates_service_validation_errors)
- src/niamoto/gui/api/services/enrichment_service.py:2912-2919 (preview_reference_enrichment)
- src/niamoto/gui/api/services/enrichment_service.py:3017-3025 (preview_default_enrichment)

The route only converts validation failures when preview_default_enrichment raises ValueError, and the router test encodes that intended 404 contract using a mock that raises. The real preview service catches the same configuration/source validation ValueErrors and returns PreviewResponse(success=False, error=...), so POST /api/enrichment/preview can return HTTP 200 for missing configuration or an unknown source_id. Clients then cannot distinguish invalid preview requests from valid previews where all source calls failed.

recommendation:
Keep validation failures on one side of the contract: either let preview_reference_enrichment/preview_default_enrichment propagate configuration/source ValueErrors to the router, or have the preview routes inspect unsuccessful PreviewResponse errors that match _raise_http_error and raise the corresponding HTTPException before returning.

test analysis:
The existing test monkeypatches preview_default_enrichment to raise ValueError, so it verifies only the router's exception path. It does not exercise the real service path that converts those same validation errors into PreviewResponse objects.

suggested regression test:
Add a route test using the real preview service path for an unknown source_id or missing default enrichment configuration and assert POST /api/enrichment/preview returns 404 rather than 200 with success=false.

minimum fix scope:
Adjust the preview validation path shared by preview_default_enrichment and preview_reference_enrichment, then cover the legacy POST /preview route with a non-mocked validation-failure test.

repro:
Configure a default enrichment reference without source_id 'gbif' and call POST /api/enrichment/preview with {"taxon_name":"Araucaria","source_id":"gbif"}; _ensure_startable_sources raises a ValueError, preview_reference_enrichment catches it into PreviewResponse(success=false), and preview_enrichment returns that body with status 200 instead of the tested 404 contract.

## medium: LineString spatial references render as an empty Plotly map

id: fnd_sig-feat-route-f0375f5d63-7a2f35_6d6311b3c7
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /spatial-map/{reference_name}/render (feat_route_f0375f5d63)
next: clawpatch show --finding fnd_sig-feat-route-f0375f5d63-7a2f35_6d6311b3c7

evidence:
- src/niamoto/gui/api/routers/stats.py:1975-1980 (_classify_geometry_kind)
- src/niamoto/gui/api/routers/stats.py:2766-2771 (_build_spatial_map_inspection)
- src/niamoto/gui/api/routers/stats.py:2965-2970 (render_spatial_map)
- src/niamoto/gui/api/services/map_renderer.py:124-135 (MapRenderer._render_plotly)
- src/niamoto/gui/api/services/map_renderer.py:398-415 (MapRenderer._calculate_bounds)

The route pipeline accepts and classifies LineString/MultiLineString geometries as mappable, serializes them into GeoJSON features, and then treats any non-empty feature collection as renderable. The Plotly renderer it calls only splits Point, Polygon, and MultiPolygon features into traces, and its bounds calculation also ignores line geometries. A valid spatial reference made of LineString geometries therefore reaches the render path, but produces a map with no traces and default bounds instead of displaying the line data or returning a clear unsupported-geometry message.

recommendation:
Either add LineString and MultiLineString support to MapRenderer for Plotly bounds and trace generation, or have render_spatial_map reject geometry_kind == "line" with an explicit informational response before calling MapRenderer.

test analysis:
The linked CLI stats tests do not exercise the FastAPI spatial-map render route. The GUI route tests cover polygon rendering and error hiding, but no test uses a LineString or MultiLineString spatial reference.

suggested regression test:
Add a FastAPI route test that creates a spatial reference with LINESTRING WKT, calls /api/stats/spatial-map/{reference_name}/render, and asserts the rendered HTML contains the line feature label/coordinates or, if unsupported by design, a clear unsupported-geometry message instead of an empty Plotly map.

minimum fix scope:
Update src/niamoto/gui/api/services/map_renderer.py to render and compute bounds for LineString/MultiLineString, plus a focused route or renderer regression test.

repro:
Create a spatial reference table with a WKT geometry column containing LINESTRING values, configure it as a spatial reference, then request GET /api/stats/spatial-map/{reference_name}/render. The JSON inspection will include features, but the rendered Plotly map will not draw them because the renderer ignores LineString/MultiLineString.

## medium: Malformed CSV source entries cannot be deleted

id: fnd_sig-feat-route-d5de0e4ce4-dec1cf_847e5cfffb
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route DELETE /{reference_name}/sources/{source_name} (feat_route_d5de0e4ce4)
next: clawpatch show --finding fnd_sig-feat-route-d5de0e4ce4-dec1cf_847e5cfffb

evidence:
- src/niamoto/gui/api/routers/sources.py:657-660 (remove_source_config)
- src/niamoto/gui/api/routers/sources.py:693-700 (remove_source_config)
- src/niamoto/gui/api/routers/sources.py:154-171 (_resolve_imports_source_path)

The DELETE handler only removes transform.yml configuration, but before removing a CSV stats source it calls _resolve_imports_source_path, which rejects paths outside imports/ or non-CSV paths. A malformed or legacy stats_loader CSV entry such as data: ../old.csv is exactly the kind of stale config users may need to delete, yet the route returns 400 before mutating the config. Because no file is read or deleted by this route, enforcing imports/ containment during deletion blocks cleanup without providing path traversal protection for an actual file operation.

recommendation:
For DELETE, authorize removability from the source type/name and remove the matching config entry without resolving or requiring the data path to be under imports/. If path validation is still desired, make it advisory or only use it for routes that read or write the referenced file.

test analysis:
The inspected delete test only verifies that non-CSV sources are rejected without mutation; it does not cover deleting a CSV stats_loader entry whose configured path is invalid or outside imports/.

suggested regression test:
Add a test that writes a transform.yml source with name escaped_stats, data ../secret.csv, and relation.plugin stats_loader, calls DELETE /api/sources/taxons/sources/escaped_stats, and asserts the response succeeds and the source is removed from transform.yml.

minimum fix scope:
Update remove_source_config so deletion does not call _resolve_imports_source_path before removing the config entry, and add the targeted regression test for malformed CSV stats source cleanup.

repro:
Create a transform.yml group with a stats_loader source named escaped_stats and data: ../secret.csv, then call DELETE /api/sources/taxons/sources/escaped_stats. The handler raises HTTP 400 from _resolve_imports_source_path and leaves the source in transform.yml.

## medium: Merge saves can silently drop legacy export-only widgets

id: fnd_sig-feat-route-35491c462f-8973a3_51cc6a7092
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /save-config (feat_route_35491c462f)
next: clawpatch show --finding fnd_sig-feat-route-35491c462f-8973a3_51cc6a7092

evidence:
- src/niamoto/gui/api/routers/templates.py:948-955 (save_transform_config)
- src/niamoto/gui/api/routers/templates.py:960-969 (save_transform_config)
- src/niamoto/gui/api/routers/templates.py:995-1000 (save_transform_config)
- tests/e2e/test_gui_config_generation.py:858-888 (test_export_only_widgets_routed_to_export_yml)

In merge mode, the handler promises to preserve existing widgets, but it first filters export-only widgets out of the existing transform widgets and then writes only the non-export-only merged set back to transform.yml. The export.yml update is built from request.widgets_data only, so a pre-existing export-only widget that was present in transform.yml but not included in the current merge request is removed from transform.yml and is not migrated into export.yml. This can lose existing navigation/widget configuration during a normal add-one-widget merge save, especially for projects created before export-only widgets were routed exclusively to export.yml.

recommendation:
In the merge path, preserve existing export-only widgets by migrating them into the export build input before removing them from transform.yml, or explicitly load existing export widgets and ensure every filtered export-only transform widget is present in export.yml before committing the replacement files.

test analysis:
The existing export-only coverage exercises replace mode where the export-only widget is present in the request payload. It does not cover merge mode with an existing export-only widget that is absent from the request payload.

suggested regression test:
Add a save-config merge test that seeds transform.yml with a hierarchical_nav_widget, sends a merge request for a different widget only, and asserts the hierarchical navigation data_source exists in export.yml after the save while remaining absent from transform.yml.

minimum fix scope:
Update save_transform_config's merge handling and export build input in src/niamoto/gui/api/routers/templates.py, plus add one focused router/e2e regression test for legacy export-only widget migration.

repro:
Start with transform.yml containing group taxons with widgets_data.taxons_hierarchical_nav_widget = {plugin: hierarchical_nav_widget, params: {}} and no matching export.yml widget. POST /api/templates/save-config with mode=merge and widgets_data containing only a new non-export-only widget. The saved transform.yml no longer contains taxons_hierarchical_nav_widget, and export.yml is built only from the request widget, so the navigation widget is gone.

## medium: Missing query_field can turn a successful preview into a 500

id: fnd_sig-feat-route-dda806c6b2-03955a_96769a77f0
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /enrichment/preview (feat_route_dda806c6b2)
next: clawpatch show --finding fnd_sig-feat-route-dda806c6b2-03955a_96769a77f0

evidence:
- src/niamoto/gui/api/routers/data_explorer.py:672-675 (preview_enrichment)
- src/niamoto/gui/api/routers/data_explorer.py:698-700 (preview_enrichment)
- tests/gui/api/routers/test_data_explorer.py:380-387 (test_preview_enrichment_route_reads_config_and_returns_preview)

The handler treats query_field as optional when preparing taxon_data by defaulting to full_name, but the response unconditionally indexes plugin_config["params"]["query_field"]. An import.yml that omits query_field can therefore validate and run the loader with the intended default, then fail while serializing config_used with a KeyError that is converted to a 500.

recommendation:
Compute the effective query field once, store it in enrichment_params with setdefault("query_field", "full_name"), and use that same value for taxon_data and config_used.

test analysis:
Every happy-path preview fixture in tests/gui/api/routers/test_data_explorer.py includes query_field, so the defaulting path is never exercised through response serialization.

suggested regression test:
Add a preview test whose import.yml omits query_field and assert the response is 200 with config_used.query_field == "full_name".

minimum fix scope:
Update preview_enrichment in src/niamoto/gui/api/routers/data_explorer.py to normalize defaults before building plugin_config and config_used.

repro:
Create config/import.yml with taxonomy.api_enrichment containing api_url, query_param_name, and response_mapping but no query_field; make the loader return api_enrichment successfully; POST /api/data/enrichment/preview. The route raises KeyError on config_used instead of returning the preview with query_field=full_name.

## medium: Multi-source references can auto-select a non-registry source

id: fnd_sig-feat-route-9d5ebd4604-21a8fe_a8a8bf5dbb
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /{reference_name}/suggestions (feat_route_9d5ebd4604)
next: clawpatch show --finding fnd_sig-feat-route-9d5ebd4604-21a8fe_a8a8bf5dbb

evidence:
- src/niamoto/gui/api/routers/templates.py:116-120 (_reference_source_candidates)
- src/niamoto/gui/api/routers/templates.py:157-165 (_resolve_reference_source_name)
- src/niamoto/gui/api/routers/templates.py:282-292 (get_reference_suggestions)

The candidate builder explicitly accepts names from connector.sources, but the default resolver never considers connector.sources in configuration order. When entity is omitted, it falls through to sorted(candidates), so a multi-source reference can select a source label instead of the actual reference or intended dataset. The route then validates that selected name against EntityRegistry and can return 404, or use the wrong semantic profile, even though the reference itself is valid.

recommendation:
Resolve connector.sources defaults explicitly. Prefer connector.source or relation.dataset when present, then either default multi-source references to reference_name or choose the first configured source only when it is known to be a registered entity. Avoid lexicographic fallback for user-facing routing behavior.

test analysis:
The router tests cover rejecting an explicit cross-reference entity and an explicit missing registry source, but they do not cover an omitted entity on a reference configured with connector.sources.

suggested regression test:
Add a route test with an import.yml multi-source reference and no entity query parameter, with the registry containing only the reference entity, and assert GET /api/templates/{reference}/suggestions succeeds instead of looking up a source label.

minimum fix scope:
Update _resolve_reference_source_name default selection and add a focused route regression test for connector.sources.

repro:
Configure a reference such as shapes with connector.sources entries like Holdridge Zones and Mines, omit the entity query parameter, and call GET /api/templates/shapes/suggestions. The resolver can choose Holdridge Zones lexicographically before shapes, then registry.get(source_name) fails if the registry entity is shapes.

## medium: Native GEOMETRY columns with neutral names are not detected

id: fnd_sig-feat-route-ab5f280e83-cd852b_e522d97914
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /geo-coverage (feat_route_ab5f280e83)
next: clawpatch show --finding fnd_sig-feat-route-ab5f280e83-cd852b_e522d97914

evidence:
- src/niamoto/gui/api/routers/stats.py:960-981 (_find_geometry_column)
- src/niamoto/gui/api/routers/stats.py:4090-4103 (get_geo_coverage)

The route relies on _find_geometry_column when import.yml does not explicitly name the geometry column. That helper only returns native GEOMETRY/BYTEA columns when the column name also matches a small geometry-name pattern. A real native geometry column named something neutral such as footprint, boundary, or shape_body is ignored even though its SQL type is authoritative, so GET /geo-coverage can return geo_column null and ready_for_analysis false for a spatially usable dataset.

recommendation:
Treat any column declared as GEOMETRY/BYTEA as a native geometry candidate, preferably returning the first such column before WKT-like text candidates. Keep configured geometry fields as the override path.

test analysis:
The included CLI stats test file exercises niamoto.cli.commands.stats rather than this FastAPI route. The route tests present in tests/gui/api/routers/test_stats.py cover configured neutral geometry fields and native columns with geometry-like names, but not an unconfigured native geometry column with a neutral name.

suggested regression test:
Add a GET /api/stats/geo-coverage test with dataset_occurrences containing a native GEOMETRY column named footprint and no configured geometry_field, asserting geo_column == "footprint" and ready_for_analysis reflects the valid geometries.

minimum fix scope:
Update _find_geometry_column and add a focused route or helper regression test.

repro:
Create an occurrence table with a native GEOMETRY column named footprint and no schema geometry_field in import.yml, then call GET /api/stats/geo-coverage. The route will not select footprint unless the name matches native_patterns or WKT patterns.

## medium: Nested widget configs are rejected before their transformer plugin is read

id: fnd_sig-feat-library-3a8da0b259-2788_796d4fb1f7
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/gui/api/services/templates (feat_library_3a8da0b259)
next: clawpatch show --finding fnd_sig-feat-library-3a8da0b259-2788_796d4fb1f7

evidence:
- src/niamoto/gui/api/services/templates/utils/widget_utils.py:484-489 (load_configured_widget)
- src/niamoto/gui/api/services/templates/utils/widget_utils.py:491-507 (load_configured_widget)

The function documents and implements support for configs where the transformer plugin lives under params.transformer.plugin, but it returns None when the top-level widget_config.plugin is absent before reaching that nested parsing block. Any widget saved only in the documented nested format cannot be loaded or previewed.

recommendation:
Parse raw_params["transformer"] before the missing-plugin guard, then require transformer_plugin only after nested extraction has had a chance to populate it.

test analysis:
The inspected widget_utils/template tests exercise configured widgets with top-level plugin values; they do not include a nested-only widgets_data entry despite the code comment documenting that format.

suggested regression test:
Add a load_configured_widget test with no top-level plugin and params.transformer.plugin set, asserting the returned transformer_plugin and transformer_params are populated.

minimum fix scope:
src/niamoto/gui/api/services/templates/utils/widget_utils.py: reorder the top-level plugin guard around the nested config parsing.

repro:
Create transform.yml with a group widgets_data entry like {params: {transformer: {plugin: "statistical_summary", params: {field: "height"}}, widget: {plugin: "radial_gauge", params: {}}}} and no top-level plugin; load_configured_widget(widget_id, group_by) returns None.

## medium: Netlify polling network errors escape the SSE error path

id: fnd_sig-feat-library-6bfcb2751e-d39e_5be3805df6
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/deployers (feat_library_6bfcb2751e)
next: clawpatch show --finding fnd_sig-feat-library-6bfcb2751e-d39e_5be3805df6

evidence:
- src/niamoto/core/plugins/deployers/netlify.py:147-151 (NetlifyDeployer.deploy)
- src/niamoto/core/plugins/deployers/netlify.py:189-200 (NetlifyDeployer._poll_deploy)
- tests/core/plugins/deployers/test_netlify.py:160-184 (test_netlify_unpublish_reports_network_errors)

After the ZIP upload succeeds, deploy() awaits _poll_deploy() without a surrounding httpx.RequestError/HTTPError handler. _poll_deploy() only swallows HTTPStatusError raised by raise_for_status(); connection resets, DNS failures, timeouts, and other RequestError subclasses from client.get() propagate out of the async generator. That breaks the deploy stream without emitting an SSE ERROR or DONE, leaving callers with an exception or hanging UI after Netlify already accepted the deploy.

recommendation:
Catch httpx.HTTPError (or at least httpx.RequestError plus HTTPStatusError) inside _poll_deploy(), or wrap the polling call in deploy() and yield a clear SSE error followed by DONE when polling cannot continue.

test analysis:
The Netlify tests cover successful polling via a monkeypatched _poll_deploy(), missing exports before HTTP, and network errors for unpublish only. They do not exercise deploy-status polling with client.get() raising a RequestError.

suggested regression test:
Add a Netlify deploy test whose fake client returns a valid deploy id from post() and raises httpx.ConnectError from get(); assert deploy() yields an ERROR about polling/deployment status and ends with data: DONE.

minimum fix scope:
src/niamoto/core/plugins/deployers/netlify.py::_poll_deploy and a focused Netlify deploy polling test.

repro:
Mock client.get('/api/v1/deploys/<id>') to raise httpx.ConnectError during _poll_deploy(); collecting NetlifyDeployer.deploy() raises instead of returning lines ending in data: DONE.

## medium: Non-zero Codex executions can still be evaluated and committed

id: fnd_sig-feat-library-8b7f2c330d-4323_f286a9e4d8
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source ml/scripts/research (feat_library_8b7f2c330d)
next: clawpatch show --finding fnd_sig-feat-library-8b7f2c330d-4323_f286a9e4d8

evidence:
- ml/scripts/research/run_fusion_surrogate_autoresearch.py:386-400 (run_iteration)
- ml/scripts/research/run_fusion_surrogate_autoresearch.py:414-423 (run_iteration)
- ml/scripts/research/run_fusion_surrogate_autoresearch.py:457-464 (run_iteration)

The runner only treats a Codex failure as an error when no files changed. If Codex exits non-zero after leaving partial edits in an allowed file, the code proceeds through scope checks, evaluates the candidate, and can commit it. A non-zero tool exit is a strong signal that the edit may be incomplete or produced after an interrupted/crashed run, so accepting it can promote corrupt research candidates.

recommendation:
Treat any non-zero Codex exit as a failed iteration. If changed_files is non-empty, restore those paths before returning codex_error, or require an explicit success condition before evaluation.

test analysis:
No linked tests cover run_iteration failure handling or partial-file changes after a failed Codex subprocess.

suggested regression test:
Add a unit test for run_iteration where run_codex_iteration returns returncode=1 with an allowed changed file, asserting restore_paths is called and evaluate_metric/commit_winner are not called.

minimum fix scope:
Update run_iteration's codex_result.returncode handling before the no-changes branch.

repro:
Mock run_codex_iteration to return returncode=1 while current_changed_files returns an allowed path; run_iteration will evaluate metrics and can call commit_winner instead of restoring the edits and returning codex_error.

## medium: Option-specific widget tests mostly assert only successful rendering

id: fnd_sig-feat-test-suite-648ebff255-2_9251d1e8cf
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/widgets#1 (feat_test-suite_648ebff255)
next: clawpatch show --finding fnd_sig-feat-test-suite-648ebff255-2_9251d1e8cf

evidence:
- tests/core/plugins/widgets/test_bar_plot.py:638-668 (TestBarPlotWidget.test_render_auto_bar_width_calculation)
- tests/core/plugins/widgets/test_line_plot.py:403-419 (TestLinePlotWidget.test_render_sorting_numeric_x)
- tests/core/plugins/widgets/test_radial_gauge.py:448-467 (TestRadialGaugeWidget.test_render_with_threshold)

Several tests are named and commented as covering behavioral options, but the assertions only prove that some Plotly HTML was produced. A regression that ignores auto bar width, skips numeric sorting, or drops gauge thresholds would still return a Plotly div and pass. This creates false confidence around feature-specific widget parameters.

recommendation:
Capture or parse the generated Plotly figure JSON and assert the option-specific state: calculated bar width per dataset size, sorted x/y sequences, and gauge threshold/steps/axis fields. Where parsing HTML is awkward, patch the local figure creation/render helper and assert the Figure object before serialization.

test analysis:
The current tests stop at smoke assertions such as result is a string, no error paragraph, and plotly-graph-div exists.

suggested regression test:
Add focused assertions that inspect figure JSON for the exact bar width, sorted data order, and threshold configuration produced by the tested parameters.

minimum fix scope:
Strengthen the affected option tests so each one verifies the behavior named by the test, not just render success.

repro:
Remove the option propagation for auto bar width, line-plot x sorting, or radial-gauge threshold generation while still returning a Plotly figure; these tests do not assert the corresponding figure data/layout and can remain green.

## medium: Ordering assertions can pass when expected rows are missing

id: fnd_sig-feat-test-suite-b2806023db-8_7b32164557
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/widgets#2 (feat_test-suite_b2806023db)
next: clawpatch show --finding fnd_sig-feat-test-suite-b2806023db-8_7b32164557

evidence:
- tests/core/plugins/widgets/test_raw_data_widget.py:155-162 (TestRawDataWidget.test_render_with_sorting_ascending)
- tests/core/plugins/widgets/test_table_view.py:170-176 (TestTableViewWidget.test_render_with_single_column_sorting)
- tests/core/plugins/widgets/test_table_view.py:204-206 (TestTableViewWidget.test_render_with_multiple_column_sorting)

Several tests use str.find() directly in ordering assertions. Because find() returns -1 for missing content, an implementation that accidentally omits the first expected row can still satisfy comparisons such as -1 < later positions. These tests are meant to verify sorted table contents, so they should fail loudly when any compared row is absent.

recommendation:
Assert every searched token is present before comparing positions, or parse the HTML table and compare the actual ordered cell values.

test analysis:
The existing tests only compare integer positions from find(); they do not assert those positions are non-negative or validate parsed row order.

suggested regression test:
Update the affected sorting tests to assert each position is not -1 before assertLess, or replace substring position checks with pandas.read_html/BeautifulSoup row-order assertions.

minimum fix scope:
Adjust the ordering assertions in the widget tests that call result.find() directly.

repro:
For example, if a regression rendered only Species B and Species C in test_render_with_sorting_ascending, species_a_pos would be -1 and the first ordering assertion would still pass.

## medium: Outlier export blocks the FastAPI event loop during bound calculation

id: fnd_sig-feat-route-c508b99dad-909669_6ab878cb59
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /value-validation/{entity}/export-outliers (feat_route_c508b99dad)
next: clawpatch show --finding fnd_sig-feat-route-c508b99dad-909669_6ab878cb59

evidence:
- src/niamoto/gui/api/routers/stats.py:3904-3911 (export_outliers_csv)
- src/niamoto/gui/api/routers/stats.py:3926-3957 (export_outliers_csv)
- src/niamoto/gui/api/routers/stats.py:3962-4016 (export_outliers_csv)
- tests/gui/api/routers/test_stats.py:1495-1496 (test_shape_distribution_is_sync_so_fastapi_runs_it_off_event_loop)

FastAPI executes async route bodies on the event loop. This handler is async but performs synchronous DuckDB/SQLAlchemy work and full-column aggregate scans before returning the StreamingResponse, so a large export request can stall unrelated API requests. The same test module explicitly checks another heavy stats route is synchronous so FastAPI runs it off the event loop, which supports the intended pattern.

recommendation:
Make export_outliers_csv a synchronous def handler so FastAPI runs the pre-stream database work in its threadpool, or move the synchronous bound calculation into run_in_threadpool before constructing the StreamingResponse.

test analysis:
The export tests assert response status, CSV escaping, validation, and generator behavior, but they do not assert that the route is non-coroutine or exercise concurrent requests while the bound calculation is running.

suggested regression test:
Add a test mirroring test_shape_distribution_is_sync_so_fastapi_runs_it_off_event_loop that asserts not inspect.iscoroutinefunction(stats_router.export_outliers_csv).

minimum fix scope:
Change only the export_outliers_csv execution model or wrap its pre-response database work in a threadpool; the CSV generator can remain synchronous.

repro:
Create a large numeric table, request /api/stats/value-validation/{entity}/export-outliers, and issue another API request while the percentile/stddev query is running; the second request is delayed until the synchronous bound calculation completes.

## medium: overwrite=false can still overwrite files during concurrent uploads

id: fnd_sig-feat-route-96e0fef7ce-80dea8_275a5789bc
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /upload-files (feat_route_96e0fef7ce)
next: clawpatch show --finding fnd_sig-feat-route-96e0fef7ce-80dea8_275a5789bc

evidence:
- src/niamoto/gui/api/routers/smart_config.py:460-486 (upload_files)
- src/niamoto/gui/api/routers/smart_config.py:602-621 (_handle_zip_upload)

The route checks whether the destination exists, then later performs an unconditional replace. With two concurrent requests for the same filename and overwrite=false, both can pass the existence check before either replace happens; the second replace silently overwrites the first upload even though the API contract says existing files are skipped unless overwrite=true. The same time-of-check/time-of-use pattern exists for ZIP members.

recommendation:
For overwrite=false, make destination creation atomic. Write to a temp file, then use an exclusive finalization primitive such as os.link(temp, target) or another O_EXCL-based reservation so the operation fails if another request created the destination meanwhile. Apply the same pattern to ZIP member destinations.

test analysis:
Existing upload tests cover sequential overwrite behavior but do not run two simultaneous requests against the same target name.

suggested regression test:
Add a concurrency test that blocks two uploads after the existence check, releases both, and asserts only one succeeds while the other is reported as existing without changing the first file's contents.

minimum fix scope:
Update finalization logic for normal uploads and ZIP member uploads when overwrite is false.

repro:
Start two concurrent POST /api/smart/upload-files requests for files named data.csv with different contents and overwrite=false. If both requests evaluate target_path.exists() before either replace, both report an upload and the final imports/data.csv content is whichever request replaced last.

## medium: Parameterized plugin tests silently pass when a plugin class is not loaded

id: fnd_sig-feat-test-suite-da793e85aa-6_0188bf59cf
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins (feat_test-suite_da793e85aa)
next: clawpatch show --finding fnd_sig-feat-test-suite-da793e85aa-6_0188bf59cf

evidence:
- tests/core/plugins/test_plugin_parametrized.py:61-72 (TestPluginParametrized.test_transformer_initialization)
- tests/core/plugins/test_plugin_parametrized.py:80-98 (TestPluginParametrized.test_transformer_config_validation)
- tests/core/plugins/test_plugin_parametrized.py:226-249 (TestLoaderPluginsBehavior.test_loader_output_structure)

These tests are intended to prove that named representative plugins initialize, validate, and produce output. However, every test guards all assertions behind `if plugin_class:`. If `load_test_plugin` returns a falsey value for a missing class, failed import, or fixture regression, pytest will report the case as passed without executing any assertion. That turns plugin disappearance or loader breakage into a false positive across the parametrized suite.

recommendation:
Replace each conditional with an explicit assertion, for example `assert plugin_class is not None, f"Could not load {module_path}.{class_name}"`, then run the existing assertions unconditionally.

test analysis:
The tests themselves contain the false-positive guard, so a missing plugin class exercises the skip path rather than failing.

suggested regression test:
Add a small test-only parametrized case or monkeypatched `load_test_plugin` returning `None` and assert the test helper fails explicitly instead of passing silently.

minimum fix scope:
Update `tests/core/plugins/test_plugin_parametrized.py` to fail fast when `load_test_plugin` returns no class.

repro:
Make `load_test_plugin` return `None` for one configured tuple such as `("transformers.extraction.direct_attribute", "DirectAttribute")`; the corresponding parametrized case will execute no assertions and pass.

## medium: Partial null IDs cause all source IDs to be overwritten

id: fnd_sig-feat-library-705734df4d-7f90_14c533427c
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/imports#1 (feat_library_705734df4d)
next: clawpatch show --finding fnd_sig-feat-library-705734df4d-7f90_14c533427c

evidence:
- src/niamoto/core/imports/engine.py:597-602 (GenericImporter._ensure_identifier)
- src/niamoto/core/imports/engine.py:106-112 (GenericImporter.import_from_csv)

When a CSV already has an `id` column but only some rows are missing IDs, `_ensure_identifier` replaces every ID with positional values. That silently corrupts stable external identifiers for rows that were valid. The caller then writes this normalized DataFrame in the DuckDB path, so the original IDs are lost in the imported table and registry metadata.

recommendation:
Either fail validation when an existing ID column contains nulls, or fill only null rows with generated non-conflicting IDs while preserving non-null source IDs. Prefer an explicit validation error if mixed generated/source IDs would be ambiguous.

test analysis:
`test_duckdb_csv_import_generates_default_id_when_source_has_no_id` only covers the no-ID-column case. There is no test for an existing ID column with partial nulls.

suggested regression test:
Add an import test with an existing `id` column containing one null and assert non-null IDs are preserved, or assert a clear validation error is raised.

minimum fix scope:
Change `_ensure_identifier` to avoid whole-column replacement on partial nulls and update the import path expectation for existing nullable IDs.

repro:
Import a CSV with `id,name` rows `100,a`, empty ID for `b`, and `102,c` without an explicit `id_field`; the imported `id` values become `1,2,3` instead of preserving `100` and `102`.

## medium: PATCH handler blocks the event loop while waiting on file locks and disk I/O

id: fnd_sig-feat-route-bea3100aa5-d3dee9_954fa6dfca
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PATCH /{profile_name} (feat_route_bea3100aa5)
next: clawpatch show --finding fnd_sig-feat-route-bea3100aa5-d3dee9_954fa6dfca

evidence:
- src/niamoto/gui/api/routers/standard_profiles.py:480-493 (update_standard_profile)
- src/niamoto/gui/api/routers/standard_profiles.py:201-227 (_standard_profile_config_lock)
- src/niamoto/gui/api/routers/standard_profiles.py:177-185 (_save_store_config)

The route is declared async but performs synchronous lock acquisition, config loading/validation, and export.yml saving directly on the event-loop thread. If another process holds the fcntl lock, or if YAML validation/saving is slow, this can stall unrelated requests handled by the same event loop. The output routes already use run_in_threadpool for blocking work, but this mutating route does not.

recommendation:
Move the whole synchronous mutation critical section into a regular helper and call it with run_in_threadpool, or make the route a synchronous FastAPI handler so FastAPI runs it in the threadpool. Keep the existing in-process and process-safe locks inside that helper.

test analysis:
The discovered router tests exercise successful PATCH behavior and validation errors through TestClient, but they do not simulate a contended file lock or assert that concurrent requests remain responsive while PATCH waits.

suggested regression test:
Add an async test that monkeypatches _standard_profile_config_lock or save_export_config to block briefly, starts a PATCH request, and verifies a second lightweight API request can complete before the PATCH unblocks.

minimum fix scope:
Refactor only update_standard_profile and its synchronous mutation body, plus a focused concurrency regression test for the PATCH route.

repro:
Start the API, hold the generated standard profile lock file with an exclusive fcntl lock from another process, then send PATCH /api/standard-profiles/{profile_name}. While that request waits, other requests on the same worker are delayed because the event loop is blocked in flock.

## medium: Pipeline command coverage is entirely mocked, so end-to-end data-flow regressions can pass

id: fnd_sig-feat-test-suite-68c4bfc567-9_23d8013e77
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/cli (feat_test-suite_68c4bfc567)
next: clawpatch show --finding fnd_sig-feat-test-suite-68c4bfc567-9_23d8013e77

evidence:
- tests/cli/test_run.py:4-10
- tests/cli/test_run.py:68-72 (test_run_pipeline_all_phases)

The suite explicitly states that the complete pipeline is not tested end to end, and the run command tests replace reset, import, transform, and export with mocks. That verifies orchestration calls, but it cannot catch regressions where real import output no longer feeds transform correctly, transform output no longer feeds export, or project configuration/database paths no longer compose across phases.

recommendation:
Add one small integration test around a minimal fixture project that invokes the real run pipeline with temporary inputs/outputs and asserts a generated database table plus an exported artifact. Keep the existing unit tests for option routing.

test analysis:
The current tests intentionally mock each phase and assert call parameters/output text rather than exercising real services together.

suggested regression test:
Create a tiny isolated Niamoto project fixture, run `run_pipeline` without phase mocks, and assert import data exists, at least one transform result is created, and the requested export target writes output.

minimum fix scope:
Add a focused integration test module for the run CLI and necessary tiny fixture data/config only.

## medium: Placeholder integration test gives false coverage for full JSON API export

id: fnd_sig-feat-test-suite-2fc396d61c-7_1657cf882b
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/exporters (feat_test-suite_2fc396d61c)
next: clawpatch show --finding fnd_sig-feat-test-suite-2fc396d61c-7_1657cf882b

evidence:
- tests/core/plugins/exporters/test_json_api_exporter.py:1301-1309 (TestJsonApiExporterIntegration.test_full_export_with_real_data)

The test is marked as an integration test and named as if it validates complete JSON API export behavior, but it only contains pass. This means the suite reports an integration scenario as covered while exercising none of the exporter/database/filesystem behavior it describes.

recommendation:
Replace the placeholder with a real integration test that builds a minimal DuckDB fixture, runs JsonApiExporter.export, and asserts the generated detail, index, metadata, and error-handling outputs.

test analysis:
The included test is the intended integration coverage, but it performs no actions and has no assertions.

suggested regression test:
Create a small real database with one group table, run export with detail and index enabled into tmp_path, then assert the expected JSON files exist and contain mapped data plus detail_url links.

minimum fix scope:
Update tests/core/plugins/exporters/test_json_api_exporter.py to implement or remove the placeholder integration test.

## medium: POST /execute accepts export config paths outside the project

id: fnd_sig-feat-route-4981fe5cdf-ea3e27_30bae0931c
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /execute (feat_route_4981fe5cdf)
next: clawpatch show --finding fnd_sig-feat-route-4981fe5cdf-ea3e27_30bae0931c

evidence:
- src/niamoto/gui/api/routers/export.py:35-40 (ExportRequest)
- src/niamoto/gui/api/routers/export.py:128-138 (_resolve_export_config_path)
- src/niamoto/gui/api/routers/export.py:158-169 (get_export_config)
- src/niamoto/gui/api/routers/export.py:639-643 (execute_export)

The route takes a user-controlled config_path, resolves absolute paths unchanged, and opens the resulting path before creating the job. Relative paths with '..' also remain possible because the resolver joins them under work_dir/config without normalizing and checking containment. This lets a caller make the API read and parse arbitrary YAML-readable files outside the project instead of restricting export execution to the project export.yml.

recommendation:
Add an export config path validator equivalent in spirit to the transform route: reject absolute paths and '..', resolve the candidate path, and require it to equal work_dir/config/export.yml before any job-store lookup or file open.

test analysis:
The included export route test posts only config/export.yml and verifies invalid HTML params; no test sends an absolute path or traversal path to /api/export/execute.

suggested regression test:
Add tests that POST /api/export/execute with /tmp/attacker-export.yml and ../other.yml, assert HTTP 400, and assert no job is created or background task is scheduled.

minimum fix scope:
src/niamoto/gui/api/routers/export.py path validation for ExportRequest.config_path plus focused route tests in tests/gui/api/routers/test_export.py.

repro:
POST /api/export/execute with a body such as {"config_path":"/tmp/attacker.yml"} or {"config_path":"../../attacker.yml"}; the server attempts to open and parse that path rather than rejecting it as outside the project config.

## medium: Preview route blocks the FastAPI event loop with synchronous database work

id: fnd_sig-feat-route-d5546eef9f-7c1f78_5a9ed40c52
category: performance
confidence: high
triage: risk
status: open
feature: FastAPI route GET /tables/{table_name}/preview (feat_route_d5546eef9f)
next: clawpatch show --finding fnd_sig-feat-route-d5546eef9f-7c1f78_5a9ed40c52

evidence:
- src/niamoto/gui/api/routers/database.py:255-261 (get_table_preview)
- src/niamoto/gui/api/routers/database.py:279-305 (get_table_preview)

The handler is declared async but performs synchronous SQLAlchemy/DuckDB work directly, including opening the database, schema inspection, COUNT(*), and SELECT. In FastAPI, blocking work inside an async route runs on the event loop instead of the threadpool, so a slow table preview can stall unrelated API requests. This route is especially exposed because table_name, limit, and offset are network-controlled and COUNT(*) can be expensive on large datasets.

recommendation:
Change get_table_preview to a synchronous def so FastAPI runs it in the worker threadpool, or wrap the blocking database section in run_in_threadpool while keeping the response construction unchanged.

test analysis:
tests/common/test_database.py exercises the common Database wrapper, not the FastAPI route execution model or concurrent request behavior. The route tests cover successful preview output and read-only mode but do not assert that preview runs off the event loop.

suggested regression test:
Add a route-level test analogous to the stats route threadpool guard that asserts not inspect.iscoroutinefunction(database_router.get_table_preview).

minimum fix scope:
Update only get_table_preview's execution model, keeping the existing query validation, serialization behavior, and response schema intact.

repro:
Start the API, request /api/database/tables/<large_table>/preview from one client, then issue another lightweight API request concurrently; the second request can be delayed until the synchronous preview query returns because the event loop is occupied.

## medium: Preview source overrides can trigger server-side requests to arbitrary URLs

id: fnd_sig-feat-route-ac4d098a4a-f169ce_8d0b9d98fb
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /preview/{reference_name} (feat_route_ac4d098a4a)
next: clawpatch show --finding fnd_sig-feat-route-ac4d098a4a-f169ce_8d0b9d98fb

evidence:
- src/niamoto/gui/api/routers/enrichment.py:47-53 (ReferencePreviewRequest)
- src/niamoto/gui/api/routers/enrichment.py:313-320 (preview_enrichment_for_reference)
- tests/gui/api/routers/test_enrichment.py:216-230 (test_preview_reference_route_forwards_source_override)
- src/niamoto/gui/api/services/enrichment_service.py:2059-2077 (_ensure_override_sources)
- src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py:546-548 (ApiTaxonomyEnricher.load_data)

The route accepts an arbitrary source_config dict from the POST body and forwards it as source_override. The service only checks that an api_url exists, then the configured plugin performs a server-side requests.get to that URL. A caller can therefore POST a preview override pointing at localhost, link-local metadata, or private network services and make the GUI backend issue the request. The included router test confirms that forwarding unsaved api_url overrides is intended, but there is no allowlist or private-address validation at this route boundary.

recommendation:
Validate preview override URLs before building the enricher: require http/https, resolve DNS, reject loopback/private/link-local/multicast addresses, reject private redirects/rebound peers, and preferably reuse the existing API URL validation pattern already present elsewhere in the GUI API.

test analysis:
The route test only verifies that a public BHL override is forwarded. It does not exercise internal, link-local, localhost, redirect, or DNS-rebinding targets.

suggested regression test:
Add a router or service test posting source_config.config.api_url values such as http://localhost:8000 and http://169.254.169.254/latest/meta-data/ and assert the request is rejected before the enricher/load_data path is invoked.

minimum fix scope:
Add URL validation for ReferencePreviewRequest.source_config before calling preview_reference_enrichment, or enforce it in _ensure_override_sources so all preview callers are protected.

repro:
POST /api/enrichment/preview/taxons with a valid query and source_config.config.api_url set to http://169.254.169.254/latest/meta-data/ or http://127.0.0.1:<port>/; the backend will attempt the outbound request during preview.

## medium: Preview validation can exit successfully when no targets were validated

id: fnd_sig-feat-library-a67705f9ea-5621_edf8e88c4b
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source scripts/_archive (feat_library_a67705f9ea)
next: clawpatch show --finding fnd_sig-feat-library-a67705f9ea-5621_edf8e88c4b

evidence:
- scripts/_archive/validate_preview.py:415-420 (main)
- scripts/_archive/validate_preview.py:451-453 (main)

Missing finalized widgets are skipped instead of recorded as failed validations. If every configured widget is absent, results remains empty and all([]) evaluates to True, so the script reports success despite validating nothing. This undermines the script's purpose as a regression check.

recommendation:
Append a failed ValidationResult for missing widgets, and explicitly return non-zero when results is empty or when any configured target was missing.

test analysis:
The included tests exercise auto-detection, auto-suggestions, and pattern matching; none invoke validate_preview.py or cover missing finalized export keys.

suggested regression test:
Add a unit test for main or a small helper around target collection using finalized={} and assert it returns a non-zero status with failed results for each missing target.

minimum fix scope:
scripts/_archive/validate_preview.py target loop and exit-status logic.

repro:
Use an exported taxon JSON that lacks all keys from VALIDATION_TARGETS. The loop continues for each target, results stays empty, generate_report prints 0/0, and main returns 0.

## medium: PUT /import accepts malformed legacy source shapes and can write invalid import.yml

id: fnd_sig-feat-route-1156352d6f-4117a5_00c62507b7
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /{config_name} (feat_route_1156352d6f)
next: clawpatch show --finding fnd_sig-feat-route-1156352d6f-4117a5_00c62507b7

evidence:
- src/niamoto/gui/api/routers/config.py:400-415 (_validate_import_config_content)
- src/niamoto/gui/api/routers/config.py:1216-1231 (update_config)

The import validator marks any present legacy key as a data source, but it only validates dict values and shapes lists. Scalar values such as {"taxonomy": 1} or {"plots": "bad"} leave validation_result valid, so update_config proceeds to write them to import.yml. For shapes lists, non-container entries such as {"shapes": [1]} also trigger a TypeError in the membership check before the route's write try/except, producing a 500 instead of a validation response. Both cases are user-input paths on the PUT route and can either persist an invalid project config or return an internal error for malformed input.

recommendation:
Require legacy import source values to be dictionaries, and require every shapes item to be a dictionary before checking path/file. Return validation_result errors for unsupported shapes rather than warnings or unhandled exceptions.

test analysis:
The included tests exercise Config behavior and missing database paths, and the route tests found in tests/gui/api/routers/test_config_import_v2.py only cover empty import payloads, not malformed non-dict legacy source values or malformed shapes list entries.

suggested regression test:
Add a TestClient PUT /api/config/import test that sends {'taxonomy': 1} and {'shapes': [1]}, asserts 400 with valid=false, and verifies the existing import.yml remains unchanged.

minimum fix scope:
Update _validate_import_config_content in src/niamoto/gui/api/routers/config.py and add focused router tests for malformed legacy import source values.

repro:
PUT /api/config/import with JSON {"content":{"taxonomy":1},"backup":false}; the validator treats taxonomy as present and writes taxonomy: 1 instead of rejecting it.

## medium: PUT can attach index_generator to non-HTML export groups

id: fnd_sig-feat-route-3ad36b73d0-3a7c5a_8c53749616
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /export/{group_by}/index-generator (feat_route_3ad36b73d0)
next: clawpatch show --finding fnd_sig-feat-route-3ad36b73d0-3a7c5a_8c53749616

evidence:
- src/niamoto/gui/api/routers/config.py:151-166 (_find_export_group_in_supported_locations)
- src/niamoto/gui/api/routers/config.py:2313-2324 (update_index_generator)

The update route uses _find_export_group_in_supported_locations, which first delegates to _find_export_group and does not filter by exporter type before selecting the group to mutate. The GET side for this same feature uses _find_export_group_with_index_generator, which explicitly filters to html_page_exporter groups. If export.yml contains a json_api_exporter group for the same group_by before the web export group, PUT /export/{group_by}/index-generator will write index_generator onto the JSON API group, while subsequent GET still looks for the HTML group and may report missing or stale data. This creates inconsistent API behavior and corrupts the wrong export target.

recommendation:
Make the PUT lookup use the same web-export filtering semantics as GET. Either update _find_export_group_in_supported_locations to accept an exporter filter for this route, or introduce a dedicated helper that searches only html_page_exporter groups in both top-level groups and params.groups.

test analysis:
tests/common/test_config.py has no coverage for PUT /export/{group_by}/index-generator, and the route-specific tests found in the repository cover GET skipping non-web groups and PUT round-trips, but not PUT when a non-HTML export with the same group_by appears first.

suggested regression test:
Add a FastAPI test with a json_api_exporter taxons group before an html_page_exporter taxons group, call PUT /api/config/export/taxons/index-generator, and assert only the html_page_exporter group receives index_generator.

minimum fix scope:
Change the target group selection used by update_index_generator and add one regression test for mixed exporter ordering.

repro:
Create export.yml with exports[0] as json_api_exporter containing groups: [{group_by: "taxons"}] and exports[1] as html_page_exporter containing groups: [{group_by: "taxons", widgets: []}]. PUT /api/config/export/taxons/index-generator with a valid payload. The route mutates exports[0].groups[0] instead of the HTML page group.

## medium: PUT crashes when an existing group has null widgets_data

id: fnd_sig-feat-route-a3a5de2733-1fa378_f683801bc1
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route PUT /transform/{group_by}/widgets/{widget_id} (feat_route_a3a5de2733)
next: clawpatch show --finding fnd_sig-feat-route-a3a5de2733-1fa378_f683801bc1

evidence:
- src/niamoto/gui/api/routers/config.py:1734-1740 (_normalize_widgets_data)
- src/niamoto/gui/api/routers/config.py:1859-1865 (update_transform_widget)
- src/niamoto/gui/api/routers/config.py:1881-1882 (update_transform_widget)
- tests/common/test_config.py:90-129 (test_transform_widget_route_handles_null_widgets_data)

The read paths explicitly normalize widgets_data: null to an empty mapping, and the included tests establish null widgets_data as an expected legacy/config state. The PUT handler only initializes widgets_data when the key is absent, so a group containing widgets_data: null reaches group["widgets_data"][widget_id] and raises TypeError. That is caught by the broad exception handler and returned as a 500 instead of creating the widget or returning the same controlled 400 used for malformed widgets_data.

recommendation:
In update_transform_widget, normalize the existing value before mutation. For example, call _normalize_widgets_data(group.get("widgets_data")), assign the normalized mapping back to group["widgets_data"], then write the widget. This also preserves the existing 400 behavior for non-object widgets_data.

test analysis:
The included regression tests cover GET behavior for null widgets_data, but there is no PUT test exercising the same legacy null state. Existing update coverage uses widgets_data as an empty dict, so it misses the crash path.

suggested regression test:
Add a TestClient PUT test with transform.yml containing [{"group_by":"plots","widgets_data":null}] and assert the response is 200 with the new widget persisted, or assert a deliberate 400 if the API chooses to reject null consistently.

minimum fix scope:
src/niamoto/gui/api/routers/config.py update_transform_widget plus one focused route regression test.

repro:
Create transform.yml with [{"group_by": "plots", "widgets_data": null}] and send PUT /api/config/transform/plots/widgets/foo with {"plugin":"field_aggregator","params":{}}. The handler attempts item assignment on None and returns a 500.

## medium: Queued winners remain dirty when commits are disabled

id: fnd_sig-feat-library-8b7f2c330d-e4c4_c315fbcada
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source ml/scripts/research (feat_library_8b7f2c330d)
next: clawpatch show --finding fnd_sig-feat-library-8b7f2c330d-e4c4_c315fbcada

evidence:
- ml/scripts/research/run_fusion_surrogate_autoresearch.py:439-467 (run_iteration)
- ml/scripts/research/run_fusion_surrogate_autoresearch.py:507-511 (main)
- ml/scripts/research/run_fusion_surrogate_autoresearch.py:580-581 (main)

With the default deferred stack validation path and --no-commit-winners, a candidate that passes surrogate-fast and surrogate-mid is queued, baselines are updated, and run_iteration returns without committing or restoring the changed files. The main loop only stops for status keep when commits are disabled, not for queue_stack_validation, so the next iteration starts from a dirty worktree and compounds changes onto the queued candidate. That breaks per-iteration isolation and makes later diffs, scores, and promotion records ambiguous.

recommendation:
When commit_winners is false and a deferred candidate is queued, either stop the loop so the user can inspect the dirty candidate, or restore the candidate after capturing its diff before continuing. Make the behavior explicit in the option help.

test analysis:
No linked tests cover the main loop interaction between defer_stack_validation, commit_winners=false, and worktree cleanliness.

suggested regression test:
Add a loop-level test that simulates queue_stack_validation with commit_winners=false and asserts the runner does not start a second iteration with the same dirty worktree.

minimum fix scope:
Update main's break condition for commit_winners=false, or update run_iteration to restore queued candidates when continuing without commits.

repro:
Run the autoresearch script with --no-commit-winners and a candidate that passes surrogate-mid. The loop continues after status queue_stack_validation with the candidate still present in the worktree.

## medium: Raw SQL bypasses the transaction helpers and commits independently

id: fnd_sig-feat-library-34fbee6012-6487_2d12b23769
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/common#1 (feat_library_34fbee6012)
next: clawpatch show --finding fnd_sig-feat-library-34fbee6012-6487_2d12b23769

evidence:
- src/niamoto/common/database.py:779-780 (Database.begin_transaction)
- src/niamoto/common/database.py:679-700 (Database.execute_sql)
- src/niamoto/common/database.py:817-818 (Database.rollback_transaction)
- tests/common/test_database.py:73-80 (test_transaction_helpers)

The transaction state is tracked on the scoped ORM session, but execute_sql opens an independent engine connection and commits each statement itself. The included test shows execute_sql is expected to participate in the transaction helper contract, but rollback_transaction only rolls back the session and cannot undo raw SQL that was already committed on a separate connection. Any caller wrapping multiple execute_sql writes in begin_transaction/rollback_transaction can end up with partial committed data after an error.

recommendation:
Make transaction helpers and execute_sql share the same transactional connection/session when active_transaction is true, and suppress per-call commits until commit_transaction. Alternatively remove the misleading transaction API for raw SQL and document/enforce that it only covers ORM session operations.

test analysis:
The current transaction test only exercises the successful commit path and asserts the row exists. It never calls rollback_transaction after execute_sql writes or checks atomicity across multiple raw SQL statements.

suggested regression test:
Add a test that starts a transaction, performs an INSERT through execute_sql, calls rollback_transaction, and asserts the row is absent. Add a second test where one of two execute_sql writes fails and the first write is rolled back.

minimum fix scope:
src/niamoto/common/database.py transaction handling plus tests/common/test_database.py rollback/atomicity coverage.

repro:
Create a table, call begin_transaction(), insert via execute_sql(), then call rollback_transaction(); the inserted row remains because execute_sql committed outside the session transaction.

## medium: Real preview validation failures bypass the route's HTTP error contract

id: fnd_sig-feat-route-ac4d098a4a-7b1839_a87d0341d4
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /preview/{reference_name} (feat_route_ac4d098a4a)
next: clawpatch show --finding fnd_sig-feat-route-ac4d098a4a-7b1839_a87d0341d4

evidence:
- src/niamoto/gui/api/routers/enrichment.py:313-322 (preview_enrichment_for_reference)
- tests/gui/api/routers/test_enrichment.py:254-275 (test_preview_reference_route_translates_service_validation_errors)
- src/niamoto/gui/api/services/enrichment_service.py:2912-2919 (preview_reference_enrichment)
- src/niamoto/gui/api/services/enrichment_service.py:2024-2034 (_ensure_startable_sources)

The route is written and tested as though preview validation ValueErrors become HTTP errors, for example 404 for a missing source. In the real service path, _ensure_startable_sources raises those ValueErrors, but preview_reference_enrichment catches them and returns a PreviewResponse with success=false. That means the actual endpoint returns HTTP 200 for missing source/config cases instead of the 404 contract asserted by the router test.

recommendation:
Choose one contract and make route, service, and tests agree. If validation failures should be HTTP errors, let preview_reference_enrichment raise those ValueErrors or have the route translate failed PreviewResponse validation errors into HTTPException. If 200 with success=false is desired, update the router tests and client contract accordingly.

test analysis:
The router test monkeypatches preview_reference_enrichment to raise ValueError, so it never exercises the real service behavior where the ValueError is caught and serialized into a successful HTTP response.

suggested regression test:
Add an integration-style router test using the real preview_reference_enrichment path for a missing source or missing reference config and assert the chosen HTTP status and response body.

minimum fix scope:
Align preview_reference_enrichment error propagation with preview_enrichment_for_reference's HTTP handling, plus one regression test for the real service path.

repro:
Configure a reference without source 'gbif', then POST /api/enrichment/preview/taxons with {"query":"Araucaria","source_id":"gbif"}. The real service catches the missing-source ValueError and the route returns a 200 PreviewResponse rather than the tested 404.

## medium: Reference parsing accepts malformed references with trailing text

id: fnd_sig-feat-library-d802abf076-8e68_b2ab6369b3
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/chains (feat_library_d802abf076)
next: clawpatch show --finding fnd_sig-feat-library-d802abf076-8e68_b2ab6369b3

evidence:
- src/niamoto/core/plugins/transformers/chains/reference_resolver.py:65-67 (ReferenceResolver.REF_PATTERN)
- src/niamoto/core/plugins/transformers/chains/reference_resolver.py:142-144 (ReferenceResolver._resolve_reference)
- src/niamoto/core/plugins/transformers/chains/chain_validator.py:229-232 (TransformChainValidator._find_references)

Both resolver and validator use re.match without anchoring or fullmatch. A value like '@step1.simple_number trailing' matches the '@step1.simple_number' prefix and is resolved as if the trailing text did not exist. In transform chains that turns a typo in YAML into a silently accepted parameter value instead of a configuration error.

recommendation:
Use fullmatch for reference parsing, or anchor the configured pattern with \A...\Z. Apply the same rule in TransformChainValidator._find_references so validation and runtime resolution agree.

test analysis:
The resolver tests cover missing dots, missing steps, invalid fields, invalid functions, and index errors, but none include otherwise valid references with extra trailing characters.

suggested regression test:
Add a ReferenceResolver test asserting '@step1.simple_number trailing' and '@step1.simple_list|sum trailing' raise ValueError, plus a validator test that rejects the same malformed references.

minimum fix scope:
Update reference parsing in src/niamoto/core/plugins/transformers/chains/reference_resolver.py and src/niamoto/core/plugins/transformers/chains/chain_validator.py, then add targeted resolver and validator tests.

repro:
With context {'step1': {'simple_number': 123.45}}, ReferenceResolver.resolve('@step1.simple_number trailing') resolves the number instead of rejecting the malformed reference because the regex matches only the prefix.

## medium: Reference reproduction E2E tests are skipped by the advertised pytest command

id: fnd_sig-feat-library-18c2813052-284e_0e90d2352e
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python source tests/e2e (feat_library_18c2813052)
next: clawpatch show --finding fnd_sig-feat-library-18c2813052-284e_0e90d2352e

evidence:
- tests/e2e/test_reference_reproduction.py:31-33

The linked test file marks the entire module as slow. The feature declares `uv run pytest` as the command, and the repository pytest configuration uses `-m 'not slow'`, so this whole E2E reproduction suite is deselected under the advertised validation command. That leaves the reference reproduction, export regeneration, preview smoke, and publication pipeline checks out of the normal feature validation path.

recommendation:
Update the linked test command to run slow tests explicitly, for example `uv run pytest -m slow tests/e2e/test_reference_reproduction.py`, or remove the module-level slow mark from the subset that must validate this feature by default.

test analysis:
The tests exist, but their module-level marker prevents them from running under the declared default command.

suggested regression test:
Add CI or clawpatch metadata that invokes `uv run pytest -m slow tests/e2e/test_reference_reproduction.py` for this feature and fails if zero tests are selected.

minimum fix scope:
Adjust feature test command metadata or marker placement for `tests/e2e/test_reference_reproduction.py`.

repro:
Run `uv run pytest tests/e2e/test_reference_reproduction.py --collect-only -q`; with the repository addopts, the module is deselected unless `-m slow` or marker override is supplied.

## medium: Reference reproduction E2E tests are skipped by the default test command

id: fnd_sig-feat-test-suite-44633d2941-9_63a10e1cf3
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/e2e (feat_test-suite_44633d2941)
next: clawpatch show --finding fnd_sig-feat-test-suite-44633d2941-9_63a10e1cf3

evidence:
- tests/e2e/test_reference_reproduction.py:31-36
- tests/e2e/test_reference_reproduction.py:367-371 (TestPublicationPipeline.test_publish_to_ui_preview)

The whole reference reproduction file is module-marked as slow, while the feature advertises `uv run pytest` as the linked test command and the repository's default pytest configuration deselects slow tests. As a result, the parity, export generation, preview smoke, and publication pipeline checks in this owned file do not run under the claimed command, leaving the feature's strongest regression coverage inactive in normal CI/default test runs.

recommendation:
Either remove the module-level slow mark from the critical reproduction tests that should run by default, or make the linked/CI command explicit, for example `uv run pytest -m slow tests/e2e/test_reference_reproduction.py`, so clawpatch and CI actually execute this suite.

test analysis:
The affected tests are the coverage; because the module-level marker deselects them under the declared command, they cannot catch their own omission.

minimum fix scope:
Adjust the marker strategy or the feature/CI test command for `tests/e2e/test_reference_reproduction.py`.

repro:
Run `uv run pytest tests/e2e/test_reference_reproduction.py` with the repository default pytest options; pytest deselects the module because it is marked slow. Run with `-m slow` to collect it.

## medium: reference_kind accepts invalid values despite documented enum

id: fnd_sig-feat-library-979007f0c7-49c3_e436a72a61
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/gui/api/models (feat_library_979007f0c7)
next: clawpatch show --finding fnd_sig-feat-library-979007f0c7-49c3_e436a72a61

evidence:
- src/niamoto/gui/api/models/templates.py:116-119 (GenerateConfigRequest.reference_kind)

The request schema documents reference_kind as a closed set, but the type is an unrestricted str. The generate-config endpoint branches on exact values, so a typo such as "spaital" is accepted by validation and then handled like the generic fallback instead of returning a 422. That can silently generate the wrong transform sources for spatial or hierarchical references.

recommendation:
Change reference_kind to a Literal, for example Literal["hierarchical", "generic", "spatial"], or introduce an enum shared with the frontend/import config kinds. Add any intentionally supported aliases explicitly rather than relying on the fallback branch.

test analysis:
The inspected model tests cover NiamotoConfig and general response models, but no test exercises invalid GenerateConfigRequest.reference_kind values or the API's 422 behavior for malformed reference kinds.

suggested regression test:
Add a model or route test asserting that GenerateConfigRequest rejects reference_kind="spaital" with a validation error, and accepts "hierarchical", "generic", and "spatial".

minimum fix scope:
Update GenerateConfigRequest.reference_kind typing and adjust any route tests/OpenAPI expectations that consume the schema.

repro:
Instantiate GenerateConfigRequest with reference_kind="spaital" or POST /templates/generate-config with that value; Pydantic validation accepts it instead of rejecting the request.

## medium: Repository-wide cleanup can delete legitimate project files

id: fnd_sig-feat-library-184acbe1c1-49b3_565cdfbd6b
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: Python source tests (feat_library_184acbe1c1)
next: clawpatch show --finding fnd_sig-feat-library-184acbe1c1-49b3_565cdfbd6b

evidence:
- tests/conftest.py:70-89 (cleanup_magicmocks)
- tests/conftest.py:103-127 (_cleanup_magicmock_paths)
- tests/conftest.py:156-177 (pytest_sessionfinish)

The autouse fixture walks the whole repository after every test and deletes any file or directory whose name matches the broad MagicMock patterns. Session finish also deletes root-level database files with common prefixes such as test_, temp_, tmp_, and mock_. These deletions are not limited to paths created by the current test run, so running the suite in a dirty workspace can silently remove a legitimate fixture, local database, or developer file whose name happens to match the cleanup heuristic.

recommendation:
Scope cleanup to paths that tests explicitly create, a dedicated temporary artifact directory, or a recorded allow-list populated by the helpers that create these files. Avoid repository-wide recursive deletion based only on filename patterns.

test analysis:
The included CLI tests exercise command behavior and mostly place artifacts under pytest tmp paths, but none assert that cleanup preserves unrelated matching files in the repository.

suggested regression test:
Add a conftest-level test that creates a matching but unregistered file under a temporary repository fixture and verifies cleanup leaves it in place while still removing explicitly registered generated artifacts.

minimum fix scope:
Update `tests/conftest.py` cleanup helpers to track generated artifact paths or constrain deletion to a dedicated test artifact directory.

repro:
Create `test_analysis.db` at the repository root or a directory named `MagicMockFixture` under `tests/fixtures`, then run any pytest target. The session or autouse cleanup will remove the matching path even though it was not registered as a test artifact.

## medium: Router tests depend on desktop auth being absent in the ambient environment

id: fnd_sig-feat-library-bc6044f560-6efc_7054c2599f
category: build-release
confidence: high
triage: risk
status: open
feature: Python source tests/gui (feat_library_bc6044f560)
next: clawpatch show --finding fnd_sig-feat-library-bc6044f560-6efc_7054c2599f

evidence:
- tests/gui/api/routers/conftest.py:110-114 (gui_duckdb_client)
- tests/gui/api/routers/test_collections.py:35-42 (test_update_collection_review_state_persists_metadata)
- tests/gui/api/routers/test_config_transform_widgets.py:47-50 (test_update_transform_widget_updates_existing_group)
- tests/gui/api/routers/test_config_import_v2.py:181-188 (test_update_config_uses_export_write_lock)

These tests exercise mutating /api routes through create_app() without clearing the desktop auth environment or sending the desktop auth header. If NIAMOTO_DESKTOP_AUTH_TOKEN is present in a developer shell or CI job, the app middleware rejects these POST/PUT/PATCH/DELETE requests with 401 before the route behavior under test runs. That makes the suite environment-dependent and can mask the actual regression signal behind unrelated auth failures.

recommendation:
Add an autouse fixture in tests/gui/api/routers/conftest.py that deletes NIAMOTO_DESKTOP_AUTH_TOKEN by default, and let explicit auth-focused tests set it themselves. Alternatively, centralize a TestClient helper that supplies the desktop token header whenever the environment token is configured.

test analysis:
The included router tests only cover the no-token environment; none of these files sets, clears, or asserts behavior when NIAMOTO_DESKTOP_AUTH_TOKEN is present.

suggested regression test:
Add a small router-level test or fixture assertion that a representative config mutation still reaches the route when unrelated developer environment variables are present, or explicitly assert the autouse fixture clears NIAMOTO_DESKTOP_AUTH_TOKEN before creating TestClient.

minimum fix scope:
tests/gui/api/routers/conftest.py

repro:
Run with NIAMOTO_DESKTOP_AUTH_TOKEN=secret, for example: NIAMOTO_DESKTOP_AUTH_TOKEN=secret uv run pytest tests/gui/api/routers/test_config_transform_widgets.py::test_update_transform_widget_updates_existing_group. The request is expected to reach the route and return 200, but the auth middleware can reject it first.

## medium: Scaffolding treats any export group as a web_pages group and can skip web output creation

id: fnd_sig-feat-library-3a8da0b259-3510_58de95c58c
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/services/templates (feat_library_3a8da0b259)
next: clawpatch show --finding fnd_sig-feat-library-3a8da0b259-3510_58de95c58c

evidence:
- src/niamoto/gui/api/services/templates/config_scaffold.py:153-156 (scaffold_configs)
- src/niamoto/gui/api/services/templates/config_service.py:204-209 (find_export_group)
- src/niamoto/gui/api/services/templates/config_scaffold.py:273-299 (_add_export_group)

scaffold_configs is trying to ensure a web_pages export group exists, but the existence check searches every exporter. If export.yml already contains a non-web exporter group for the same reference, find_export_group returns it and _add_export_group is skipped, leaving web_pages absent or missing that group.

recommendation:
Make the scaffold check specific to the web_pages/html_page_exporter entry, then add the group to that export when it is missing regardless of other exporters.

test analysis:
The inspected scaffold tests cover empty export config and existing web_pages groups, but not a config where the same group exists only under another exporter.

suggested regression test:
Add a scaffold_configs test with a pre-existing non-web export group and assert web_pages is created with the reference group.

minimum fix scope:
src/niamoto/gui/api/services/templates/config_scaffold.py and/or config_service.py: introduce a web_pages-specific group lookup for scaffolding.

repro:
Use export.yml with exports: [{name: "data_export", groups: [{group_by: "plots"}]}] and import.yml references.plots, with no web_pages export. scaffold_configs sees plots through find_export_group and does not add plots to web_pages.

## medium: Series ratio sums string class values by concatenation before numeric conversion

id: fnd_sig-feat-library-789e16e347-f22c_39c4a2f7e1
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/class_objects (feat_library_789e16e347)
next: clawpatch show --finding fnd_sig-feat-library-789e16e347-f22c_39c4a2f7e1

evidence:
- src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py:255-263 (ClassObjectSeriesRatioAggregator.transform)
- src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py:279-284 (ClassObjectSeriesRatioAggregator.transform)
- src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py:295-302 (ClassObjectSeriesRatioAggregator.transform)

This transformer groups and sums class_value before coercing it to numeric. If class_value arrives as object strings from CSV/import data, duplicate buckets concatenate instead of adding, for example "60" + "40" becomes "6040" before float conversion. The later float() calls make the result look numeric but the ratio is computed from corrupted totals/subsets. Other class-object transformers convert class_value before aggregation, so this path is inconsistent and can silently export wrong ratios.

recommendation:
Convert total_data_raw["class_value"] and subset_data_raw["class_value"] with pd.to_numeric(errors="raise") before groupby, or route both through aggregate_class_values before alignment.

test analysis:
The linked context test imports niamoto.core.plugins.transformers.aggregation.field_aggregator, not this owned transformer. The ratio duplicate-bucket behavior is only safe for numeric dtype inputs; it is not covered for string/object class_value inputs.

suggested regression test:
Add a class_object_series_ratio_aggregator test with duplicate class_name rows whose class_value values are strings, asserting the grouped totals are numerically summed before ratio/difference calculation.

minimum fix scope:
src/niamoto/core/plugins/transformers/class_objects/series_ratio_aggregator.py transform aggregation path plus one focused regression test.

repro:
Use duplicate rows for the same class_name with string values: total class_value "60" and "40", subset "25" and "25". The expected complement is 1 - 50/100 = 0.5, but grouping first produces totals 6040 and 2525, yielding a different complement.

## medium: Shared temporary output paths make concurrent profile writes race

id: fnd_sig-feat-library-f45ccafac1-f38c_121bf89c9d
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/standards (feat_library_f45ccafac1)
next: clawpatch show --finding fnd_sig-feat-library-f45ccafac1-f38c_121bf89c9d

evidence:
- src/niamoto/core/standards/output_service.py:506-507 (StandardProfileOutputService._write_api_json)
- src/niamoto/core/standards/output_service.py:510-531 (StandardProfileOutputService._write_api_json)
- src/niamoto/core/standards/output_service.py:603-617 (StandardProfileOutputService._write_standard_files)
- src/niamoto/core/standards/output_service.py:917-921 (_atomic_write_text)

API JSON and Humboldt/Event standard file generation derive temporary filenames only from the final output path. Two simultaneous executions for the same profile and output directory therefore write, read, replace, and unlink the same temp files. One run can truncate the other run's records temp file, read records from the other run while keeping its own metadata, replace a temp file still being written, or remove another run's temp in cleanup. This can produce corrupted output, mismatched metadata/records, or intermittent FileNotFoundError under concurrent GUI/API requests.

recommendation:
Use per-execution unique temp files in the target directory, for example tempfile.mkstemp/NamedTemporaryFile(delete=False, dir=output_dir), then os.replace the unique temp into the final path. Apply the same approach to records temp files, event.csv temp files, and _atomic_write_text. If concurrent final writes should be serialized rather than last-writer-wins, add a per-output lock around the final replace sequence.

test analysis:
The output tests exercise serial writes only. They include a uniqueness test for DwC archive staging, but there is no concurrent test for api_json or standard_files temp paths.

suggested regression test:
Add a test that runs two concurrent execute_profile(api_json) calls for the same profile/output_dir using blocking iterators to force interleaving, then assert both calls complete without temp-file errors and the final JSON is well-formed with internally consistent metadata.records_count and records. Add the same shape for standard_files metadata.json/event.csv.

minimum fix scope:
Change temporary file allocation in src/niamoto/core/standards/output_service.py for _write_api_json, _write_standard_files, and _atomic_write_text; add focused concurrency regression tests in tests/core/standards/test_output_service.py.

repro:
Run two threads calling execute_profile for the same api_json profile and output_dir, with record iterators that sleep after yielding the first row. Both calls will use the same .<profile>.records.tmp and .<profile>.json.tmp paths, so interleaving can make one output contain the other call's records or fail during replace/cleanup. The same pattern applies to standard_files event.csv and metadata.json temps.

## medium: SPA fallback turns unknown API GET routes into 200 HTML responses

id: fnd_sig-feat-library-301e41a152-e48c_f0a316b162
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/gui/api (feat_library_301e41a152)
next: clawpatch show --finding fnd_sig-feat-library-301e41a152-e48c_f0a316b162

evidence:
- src/niamoto/gui/api/app.py:252-258 (create_app.SPAStaticFiles.get_response)
- src/niamoto/gui/api/app.py:260-261 (create_app)

When the UI build exists, the root StaticFiles mount catches every unmatched GET path, including paths under /api/. For an unknown API route, StaticFiles raises 404 and the handler returns index.html with a 200 response. API clients, health checks, and frontend code probing a typo such as /api/pipline would see a successful HTML response instead of a 404 API error, masking integration failures.

recommendation:
Do not fall back to index.html for /api/ paths. In SPAStaticFiles.get_response, inspect scope['path'] and re-raise 404 for API-prefixed requests, or mount the SPA only for non-API routes.

test analysis:
tests/gui/api/test_app.py covers fallback for /some/unknown/path and partial UI builds, but it does not exercise an unknown /api/* path while the SPA mount is active.

suggested regression test:
Add a TestClient case with a real UI_BUILD_DIR and assert GET /api/not-a-real-route returns 404 rather than index.html.

minimum fix scope:
src/niamoto/gui/api/app.py plus the focused app test.

repro:
Create a temporary UI_BUILD_DIR with index.html, call create_app(), then GET /api/does-not-exist with TestClient. The mounted SPA handler will serve index.html instead of returning an API 404.

## medium: Spatial operations run without normalizing CRS

id: fnd_sig-feat-library-a8c20fbb8f-921a_95ed344163
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/geospatial (feat_library_a8c20fbb8f)
next: clawpatch show --finding fnd_sig-feat-library-a8c20fbb8f-921a_95ed344163

evidence:
- src/niamoto/core/plugins/transformers/geospatial/raster_stats.py:185-190 (RasterStats.transform)
- src/niamoto/core/plugins/transformers/geospatial/raster_stats.py:275-289 (RasterStats._extract_raster_data)
- src/niamoto/core/plugins/transformers/geospatial/shape_processor.py:468-471 (ShapeProcessor._process_layer)
- tests/core/plugins/transformers/geospatial/test_raster_stats.py:32-59 (simple_polygon_gdf/temp_raster)
- tests/core/plugins/transformers/geospatial/test_shape_processor.py:36-76 (TestShapeProcessor.setUp)

RasterStats passes the input geometry directly to rasterio.mask, which expects geometries in the raster CRS. ShapeProcessor similarly clips loaded layers against the shape GeoDataFrame without first aligning layer_gdf.crs and shape_gdf.crs. Real datasets commonly mix CRS between rasters, shape tables, and imported layers; these paths will either fail with no overlap or, worse, compute against the wrong coordinates.

recommendation:
Carry the geometry CRS into raster extraction and reproject the mask geometry to src.crs before calling rasterio.mask. In ShapeProcessor._process_layer, compare CRS and reproject either the layer or shape GeoDataFrame before gpd.clip, failing clearly when one side has no CRS and alignment cannot be guaranteed.

test analysis:
The raster and shape processor fixtures all use EPSG:4326, so the tests only exercise already-aligned inputs. VectorOverlay has a CRS-mismatch transform test, but these two owned paths do not.

suggested regression test:
Add one RasterStats test with a raster in a projected CRS and a WGS84 input shape, plus one ShapeProcessor layer test where the layer CRS differs from the shape CRS, asserting successful reprojection and non-empty results.

minimum fix scope:
Update RasterStats.transform/_extract_raster_data and ShapeProcessor._process_layer to normalize CRS before mask/clip operations.

repro:
Use a shape GeoDataFrame in EPSG:4326 with a raster or layer stored in EPSG:3857. RasterStats will send degree coordinates directly to rasterio.mask for the projected raster, and ShapeProcessor will clip the projected layer against the unprojected shape.

## medium: Stable hierarchy ID test would pass with order-dependent IDs

id: fnd_sig-feat-test-suite-5496f416d9-6_de68690124
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/imports#2 (feat_test-suite_5496f416d9)
next: clawpatch show --finding fnd_sig-feat-test-suite-5496f416d9-6_de68690124

evidence:
- tests/core/imports/test_hierarchy_builder.py:110-122 (test_stable_ids_reproducibility)

The test runs the same extraction twice against the same table order and compares only the ID series. That would still pass if the hash strategy accidentally became sequence-based or otherwise depended on deterministic query ordering. The intended guarantee for hash IDs is stability by hierarchy identity, not just repeatability in one unchanged result order.

recommendation:
Compare `full_path -> id` mappings across two source tables or query results with different row ordering, and assert every hierarchy path keeps the same ID regardless of source order.

test analysis:
All current evidence for stable IDs comes from two identical calls on the same fixture, so it cannot detect row-order-sensitive ID assignment.

suggested regression test:
Build the hierarchy once from the existing fixture, then replace or create a second source table with the same rows reversed/shuffled and assert `dict(zip(full_path, id))` is identical for both outputs.

minimum fix scope:
Strengthen `test_stable_ids_reproducibility` in `tests/core/imports/test_hierarchy_builder.py`.

## medium: Stacked area schema advertises pivot/unpivot transforms that are ignored

id: fnd_sig-feat-library-5ba560319a-8e41_8666076171
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: Python source src/niamoto/core/plugins/widgets#2 (feat_library_5ba560319a)
next: clawpatch show --finding fnd_sig-feat-library-5ba560319a-8e41_8666076171

evidence:
- src/niamoto/core/plugins/widgets/stacked_area_plot.py:95-105 (StackedAreaPlotParams.transform)
- src/niamoto/core/plugins/widgets/stacked_area_plot.py:157-208 (StackedAreaPlotWidget._apply_transform)
- src/niamoto/core/plugins/widgets/stacked_area_plot.py:231-256 (StackedAreaPlotWidget.render)
- tests/core/plugins/widgets/test_stacked_area_plot.py:195-218 (TestStackedAreaPlotWidget.test_render_dict_extract_series_transform)

The public params schema offers 'unpivot' and 'pivot', so GUI/config users can select them. The render path only special-cases 'extract_series'; _apply_transform does not implement 'unpivot' or 'pivot', so those selections silently fall through to generic conversion and can render the wrong shape or 'No data available'.

recommendation:
Either implement the advertised 'pivot' and 'unpivot' transformations with clear transform_params schemas, or remove them from json_schema_extra until supported. Return an explicit configuration error for unknown transform values instead of silently ignoring them.

test analysis:
Current tests cover direct DataFrame input, generic dict conversion, and extract_series only. There are no tests for the advertised pivot/unpivot transform options.

suggested regression test:
Add separate tests for transform='unpivot' and transform='pivot' using representative dict/list inputs, asserting the generated traces receive the transformed x/y series.

minimum fix scope:
src/niamoto/core/plugins/widgets/stacked_area_plot.py and tests/core/plugins/widgets/test_stacked_area_plot.py

repro:
Use StackedAreaPlotParams(transform='unpivot', transform_params={...}) with data that requires unpivoting from long form to x/y series. The transform is not applied; render proceeds as if no unpivot support exists.

## medium: Stale NC source labels create contradictory training labels

id: fnd_sig-feat-library-05b198d086-a5ae_7b34861e42
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source ml/scripts/data (feat_library_05b198d086)
next: clawpatch show --finding fnd_sig-feat-library-05b198d086-a5ae_7b34861e42

evidence:
- ml/scripts/data/build_gold_set.py:167-172 (NC_FULL_OCC_LABELS)
- ml/scripts/data/build_gold_set.py:232-240 (NC_OCC_LABELS)
- ml/scripts/data/build_gold_set.py:969-985 (SOURCES)
- ml/scripts/data/build_gold_set.py:2315-2328 (extract_from_source)

The nc_niamoto occurrence CSV in the repository has the NC full occurrence schema, not the older Gabon-style NC_OCC schema. Because the script feeds that file through NC_OCC_LABELS, it emits a gold record where plot_name is identifier.plot, while the same NC schema is also emitted via NC_FULL_OCC_LABELS as location.locality. This gives the trainer contradictory labels for the same header/data shape and silently drops most nc_occ columns from that source.

recommendation:
Point nc_occ at the correct label map for its actual schema, or remove the duplicate nc_occ/nc_plots entries if nc_niamoto is intentionally the same dataset as test-instance/niamoto-nc. Keep only one authoritative mapping for plot_name.

test analysis:
tests/ml/scripts/data/test_build_gold_set.py monkeypatches SOURCES with a tiny synthetic CSV, so it verifies the extraction contract but never checks that the checked-in source definitions match the checked-in CSV headers or that duplicate sources do not disagree on concepts.

suggested regression test:
Add a source-definition integrity test that loads each checked-in source header with its configured separator and asserts expected critical mappings for nc_niamoto, including plot_name -> location.locality, plus a check that no same source/header sample is emitted with conflicting concepts.

minimum fix scope:
Update the nc_occ/nc_plots source definitions or their label maps, then regenerate ml/data/gold_set.json if it is tracked as a produced artifact.

repro:
Run ./.venv/bin/python -c 'from ml.scripts.data import build_gold_set as b; [print(s["name"], len(b.extract_from_source(s)), [r["column_name"] for r in b.extract_from_source(s)][:10]) for s in b.SOURCES if s["name"] in {"nc_occ","nc_full_occ"}]' and observe nc_occ extracts only plot_name/geo_pt, while nc_full_occ extracts the full NC schema.

## medium: Startup recovery can leave an orphaned job permanently running when the PID was reused

id: fnd_sig-feat-library-da3046e57f-4cca_4feb6421f7
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/services (feat_library_da3046e57f)
next: clawpatch show --finding fnd_sig-feat-library-da3046e57f-4cca_4feb6421f7

evidence:
- src/niamoto/gui/api/services/job_file_store.py:56-60 (JobFileStore.create_job)
- src/niamoto/gui/api/services/job_file_store.py:319-324 (JobFileStore.recover_on_startup)

recover_on_startup treats any live PID as proof that the stored non-terminal job is still owned by the API. After a crash or reboot, OS PIDs can be reused by unrelated processes, so active_job.json can remain in status running forever. Because create_job rejects any non-terminal active job, that stale file blocks all later jobs for the project until manual cleanup.

recommendation:
Record enough process identity to distinguish the original API process from PID reuse, or combine the PID check with a heartbeat/updated_at staleness threshold. If the active job has not been updated recently, mark it interrupted even when the PID currently exists.

test analysis:
tests/gui/api/services/test_job_file_store.py covers dead PIDs and same-process jobs, but not PID reuse or a stale non-terminal job whose PID belongs to another live process.

suggested regression test:
Add a JobFileStore recovery test that writes a running active_job.json with a different pid, monkeypatches _is_pid_alive to return True, sets an old updated_at, and asserts recover_on_startup archives it as interrupted and allows create_job().

minimum fix scope:
src/niamoto/gui/api/services/job_file_store.py recovery metadata and recovery decision logic, plus the focused recovery test.

repro:
Create .niamoto/active_job.json with status "running" and a pid that is different from os.getpid() but for which _is_pid_alive returns True, then call recover_on_startup(); it returns None and leaves active_job.json running, so create_job() raises "Un job est déjà en cours".

## medium: Streamed API responses are read without a size cap or consistent close

id: fnd_sig-feat-route-d59e00f58a-5fde82_48e4bbac8a
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /test-api (feat_route_d59e00f58a)
next: clawpatch show --finding fnd_sig-feat-route-d59e00f58a-5fde82_48e4bbac8a

evidence:
- src/niamoto/gui/api/routers/files.py:247-254 (_get_with_pinned_public_dns)
- src/niamoto/gui/api/routers/files.py:523-526 (test_api_connection)
- src/niamoto/gui/api/routers/files.py:536-548 (test_api_connection)
- tests/gui/api/routers/test_files.py:239-409

The route accepts a user-supplied public URL, requests it with stream=True, then calls response.json() for 200 responses and response.text[:200] for non-200 responses. Both operations can materialize the entire response body before returning, so a large or endless public response can consume substantial memory despite this being only a connection test. The response is explicitly closed only on the peer-address rejection path; redirect-validation returns and normal/error returns do not use a finally block to close the streamed response. The existing tests use small mocked responses and do not exercise large bodies or response lifecycle cleanup.

recommendation:
Introduce a maximum response body size for this endpoint, reject or stop reading when Content-Length or streamed bytes exceed it, parse JSON from the capped bytes, and close the response in a finally block for every path after requests.get returns.

test analysis:
The route tests mock small response.json(), response.text, and redirect responses; they never simulate a large streamed body or assert close() on all return paths.

suggested regression test:
Add tests with a fake streamed response whose iter_content exceeds a configured cap and verify the endpoint returns a failure without reading beyond the cap, plus tests that close() is called for success, invalid JSON, redirects, and non-200 responses.

minimum fix scope:
Update test_api_connection to manage the response with try/finally, replace response.json()/response.text with capped reads, and add focused route tests for oversized and cleanup cases.

repro:
Point POST /api/files/test-api at a public endpoint that returns a very large 200 JSON payload, or a very large 500 text payload. The handler will attempt to read the full body through response.json() or response.text before producing the small ApiTestResponse.

## medium: Sunburst branchvalues='remainder' renders incorrect totals

id: fnd_sig-feat-library-5ba560319a-88c9_e147eb6c43
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/widgets#2 (feat_library_5ba560319a)
next: clawpatch show --finding fnd_sig-feat-library-5ba560319a-88c9_e147eb6c43

evidence:
- src/niamoto/core/plugins/widgets/sunburst_chart.py:72-75 (SunburstChartWidgetParams.branchvalues)
- src/niamoto/core/plugins/widgets/sunburst_chart.py:185-189 (SunburstChartWidget.render)
- src/niamoto/core/plugins/widgets/sunburst_chart.py:230-243 (SunburstChartWidget.render)
- tests/core/plugins/widgets/test_sunburst_chart.py:164-174 (TestSunburstChartWidget.test_render_with_different_branchvalues)

The widget exposes Plotly's 'remainder' mode, but it always sets category and root values to the sum of their children. In Plotly, 'total' means parent values are totals, while 'remainder' means parent values are the extra remainder outside children. Selecting 'remainder' therefore double-counts parent sectors and produces misleading percentages/areas instead of just changing interpretation safely.

recommendation:
Branch value construction on params.branchvalues. Keep summed parent values for 'total'; for 'remainder', set parent/root remainders deliberately, or reject 'remainder' unless explicit parent remainder values are supplied.

test analysis:
The existing test only asserts that both branchvalues modes produce a Plotly div; it never inspects the generated figure values or percentages.

suggested regression test:
Mock render_plotly_figure, render with branchvalues='remainder', and assert parent values are not populated with child sums unless explicit remainder data is provided.

minimum fix scope:
src/niamoto/core/plugins/widgets/sunburst_chart.py plus a focused assertion in tests/core/plugins/widgets/test_sunburst_chart.py

repro:
Patch render_plotly_figure to inspect the figure, then render {'habitat': {'forest': 800, 'savanna': 400}} with SunburstChartWidgetParams(branchvalues='remainder'). The category value is 1200 even though in remainder mode it should be the residual value, not the child sum.

## medium: Symlinked files directory can redefine the serving boundary

id: fnd_sig-feat-route-df13bf8a7d-4dc8bc_1b77f127c4
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /serve/{file_path:path} (feat_route_df13bf8a7d)
next: clawpatch show --finding fnd_sig-feat-route-df13bf8a7d-4dc8bc_1b77f127c4

evidence:
- src/niamoto/gui/api/routers/files.py:1172-1183 (serve_file)
- src/niamoto/gui/api/routers/files.py:1185-1202 (serve_file)
- tests/gui/api/routers/test_files.py:438-455 (test_read_export_file_rejects_symlinked_exports_root)

serve_file resolves both the requested path and the files directory through symlinks before checking containment. If the project has work_dir/files as a symlink to another directory inside the project, for example work_dir/config, then /api/files/serve/files/logo.svg resolves under that symlink target and passes full_path.relative_to(files_dir). That exposes image-extension files from a non-files project subtree despite the explicit 'outside files directory' boundary. The neighboring exports reader treats a symlinked root as invalid, but serve_file does not apply the same hardening.

recommendation:
Reject a symlinked files root before resolving it, and preferably reuse a no-follow path opener for served files so each path component is opened beneath the literal work_dir/files directory. Keep the image extension allowlist after the no-follow containment check.

test analysis:
The included tests cover symlink rejection for /exports/read and regular serving of images, but they do not exercise GET /serve/{file_path:path} with a symlinked files root that points to another in-project directory.

suggested regression test:
Add a serve_file regression test where work_dir/files is a symlink to work_dir/config, config/secret.svg exists, and GET /api/files/serve/files/secret.svg must return 400 or 403.

minimum fix scope:
Update serve_file path resolution around the work_dir/files boundary and add one router test for symlinked files roots.

repro:
Create work_dir/config/secret.svg, make work_dir/files a symlink to work_dir/config, patch get_working_directory to work_dir, then GET /api/files/serve/files/secret.svg. The current code resolves both paths to work_dir/config/secret.svg and returns the file instead of rejecting the symlinked files root.

## medium: Taxonomy consistency ignores configured hierarchy columns

id: fnd_sig-feat-route-71bdbf03c2-f6834f_9703d2affa
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /taxonomy-consistency (feat_route_71bdbf03c2)
next: clawpatch show --finding fnd_sig-feat-route-71bdbf03c2-f6834f_9703d2affa

evidence:
- src/niamoto/gui/api/routers/stats.py:3170-3174 (get_taxonomy_consistency)
- src/niamoto/gui/api/routers/stats.py:3198-3223 (get_taxonomy_consistency)
- src/niamoto/gui/api/routers/stats.py:3320-3346 (get_taxonomy_consistency)
- src/niamoto/gui/api/routers/stats.py:666-765 (_detect_configured_hierarchy_metadata)
- tests/gui/api/routers/test_stats.py:896-944 (test_hierarchy_inspection_uses_configured_hierarchy_columns)

The route resolves the target from import.yml references, including configured hierarchical references, but then analyzes only hard-coded Niamoto column names (`rank_name`, `parent_id`, `level`) or flat rank columns (`family`, `genus`, `species`, etc.). The same router already has metadata detection that honors `schema.id_field`, `schema.name_field`, `hierarchy.parent_field`, and `hierarchy.rank_field`, and linked tests prove custom hierarchy columns such as `taxon_key`, `parent_key`, `rank_label`, and `display_label` are valid for the hierarchy API. For such a valid configured taxonomy, `/taxonomy-consistency` returns `total_taxa` but an empty or incorrect `levels`, `orphan_records`, and `hierarchy_depth`, so the dashboard silently reports false consistency data.

recommendation:
Reuse `_detect_configured_hierarchy_metadata(column_names, ref_cfg) or detect_hierarchy_metadata(column_names)` in `get_taxonomy_consistency`, and drive rank, parent, id, and name queries from the resolved metadata before falling back to the flat-column strategy.

test analysis:
The supplied context test `tests/cli/test_stats.py` covers the CLI stats module, not the FastAPI route. The route tests cover `rank_name` plus `parent_id`, and separately cover configured hierarchy columns for `/hierarchy/{reference_name}`, but there is no `/taxonomy-consistency` test using configured custom hierarchy fields.

suggested regression test:
Add a GUI API test mirroring `test_hierarchy_inspection_uses_configured_hierarchy_columns` that calls `/api/stats/taxonomy-consistency?entity=custom_taxons` and asserts family/genus levels, correct hierarchy_depth, and orphan detection through the configured parent/id fields.

minimum fix scope:
Update `get_taxonomy_consistency` to resolve and use hierarchy metadata for hierarchical references; add one targeted route regression test for configured hierarchy fields.

repro:
Create an import.yml hierarchical reference with `hierarchy.rank_field: rank_label`, `hierarchy.parent_field: parent_key`, and `schema.name_field: display_label`, then create `entity_custom_taxons(taxon_key, parent_key, rank_label, display_label)` with family/genus rows. `GET /api/stats/taxonomy-consistency?entity=custom_taxons` will not enter the `rank_name` path and the flat-column fallback will not count `rank_label`, so levels come back empty despite valid hierarchy data.

## medium: Template preview has no size limit for markdown preview input

id: fnd_sig-feat-route-3cb4790eb7-0c01d0_ce2129bd70
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /preview-template (feat_route_3cb4790eb7)
next: clawpatch show --finding fnd_sig-feat-route-3cb4790eb7-0c01d0_ce2129bd70

evidence:
- src/niamoto/gui/api/routers/site.py:38 (MAX_MARKDOWN_PREVIEW_SIZE_BYTES)
- src/niamoto/gui/api/routers/site.py:1423-1431 (preview_template)
- tests/gui/api/routers/test_site.py:480-487 (test_preview_markdown_rejects_oversized_content)
- tests/gui/api/routers/test_site.py:1090-1122 (test_preview_template_sanitizes_markdown_html)

The standalone markdown preview endpoint enforces a 2 MiB input limit and has a regression test for 413 responses, but POST /preview-template accepts user-controlled context.content_markdown and runs preprocessing, markdown conversion, sanitization, and template rendering without any equivalent size check. A network caller can submit a very large markdown string to consume CPU and memory in the API process. The existing preview-template tests cover sanitization and path traversal, but they do not exercise oversized content.

recommendation:
Apply the same MAX_MARKDOWN_PREVIEW_SIZE_BYTES validation in preview_template before preprocessing content_markdown. Consider also bounding content_source reads before read_text() so project files cannot bypass the same preview rendering limit.

test analysis:
The only oversized-content test targets /preview-markdown. The preview-template tests at lines 1090-1122 verify HTML sanitization but never submit content_markdown above the configured limit.

suggested regression test:
Add a preview-template test that posts context.content_markdown with MAX_MARKDOWN_PREVIEW_SIZE_BYTES + 1 bytes and asserts HTTP 413 with a clear detail message.

minimum fix scope:
Add size validation to preview_template's content_markdown branch and, if content_source markdown is intended to share the same safety envelope, guard file size before reading.

repro:
POST /api/site/preview-template with template=page.html and context.content_markdown set to a payload far larger than MAX_MARKDOWN_PREVIEW_SIZE_BYTES. The handler proceeds into markdown conversion instead of rejecting it with 413.

## medium: Transformer integration behavior is effectively untested

id: fnd_sig-feat-test-suite-a112b39058-8_1faa4ef6ab
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/services (feat_test-suite_a112b39058)
next: clawpatch show --finding fnd_sig-feat-test-suite-a112b39058-8_1faa4ef6ab

evidence:
- tests/core/services/test_transformer.py:124-128 (mock_to_sql)
- tests/core/services/test_transformer.py:1029-1034 (TestTransformerServiceWorkflow)
- tests/core/services/test_parallel_equivalence.py:46-72 (_run_transform/_load_transform_tables)
- tests/core/services/test_parallel_equivalence.py:125-136 (test_export_html_is_stable_across_independent_runs)

The transformer tests explicitly stub out DataFrame.to_sql, use mocked database/plugin layers, and even document that the workflow tests are not real integration tests. The only nearby parallel-equivalence file defines transform helpers but the actual test only runs exports and compares HTML, so transformer persistence/output equivalence is not exercised. A regression where TransformerService produces incorrect database rows, fails with real DuckDB writes, or diverges across independent transform runs could pass this suite.

recommendation:
Add an integration test that copies or stages a subset project, runs the real transformer against a real DuckDB database with real plugins, then reads the generated transform tables and asserts stable expected rows or equivalence across two independent runs.

test analysis:
The included transformer tests replace the persistence and plugin boundaries with mocks, while the parallel-equivalence test never invokes the transform helpers it defines.

suggested regression test:
Extend `tests/core/services/test_parallel_equivalence.py` with a test that calls `_run_transform` for two copied projects, loads tables via `_load_transform_tables`, and asserts the resulting table payloads are equal and non-empty.

minimum fix scope:
Add one real DuckDB transformer integration/equivalence test; production code changes are not required for this finding.

repro:
Static inspection: `rg -n "_run_transform|_load_transform_tables" tests/core/services` shows those helpers are only defined, not called.

## medium: Transformer schema route ignores param_schema-only plugins

id: fnd_sig-feat-route-5a552b833a-a20eb6_87f432fc05
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route GET /transformer-schema/{plugin_name} (feat_route_5a552b833a)
next: clawpatch show --finding fnd_sig-feat-route-5a552b833a-a20eb6_87f432fc05

evidence:
- src/niamoto/gui/api/routers/recipes.py:645-663 (_get_transformer_schema)
- src/niamoto/gui/api/routers/recipes.py:331-337 (_get_transformer_params_validation_model)
- tests/gui/api/routers/test_recipes.py:382-388 (test_save_recipe_rejects_missing_required_plugin_params)
- tests/gui/api/routers/test_recipes.py:360-369 (test_recipes_transformer_schema_route_returns_plugin_params)

The schema endpoint builds transformer params only from a same-module class named after the plugin class or from config_model. Other code in the same router treats transformer param_schema as the authoritative validation model, and the tests include a transformer whose required params exist only through param_schema. For such a registered transformer, GET /api/recipes/transformer-schema/{plugin_name} returns 200 with an empty params object, so the GUI cannot render required fields even though save/validate later rejects the recipe.

recommendation:
In _get_transformer_schema, prefer getattr(plugin_class, "param_schema", None) before _find_params_model, matching _get_transformer_params_validation_model. Keep the existing config_model fallback for legacy plugins.

test analysis:
The transformer-schema route test only exercises time_series_analysis, whose params are discoverable by the current naming convention. The param_schema-only transformer appears in a save validation test, not in a schema route test.

suggested regression test:
Add a route test that registers a fake transformer with only param_schema, calls /api/recipes/transformer-schema/{name}, and asserts required param fields and required=true are returned.

minimum fix scope:
Update transformer schema extraction in src/niamoto/gui/api/routers/recipes.py and add one focused regression test in tests/gui/api/routers/test_recipes.py.

repro:
Register a transformer class with param_schema = RequiredTransformerParams, no config_model, and a params model that is local/imported rather than discoverable as {PluginClassName}Params on the module. Request /api/recipes/transformer-schema/required_transformer; the response params will be {} instead of containing source.

## medium: Trendline rendering is allowed to pass as an error

id: fnd_sig-feat-test-suite-b2806023db-0_0ef8802b2b
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/widgets#2 (feat_test-suite_b2806023db)
next: clawpatch show --finding fnd_sig-feat-test-suite-b2806023db-0_0ef8802b2b

evidence:
- tests/core/plugins/widgets/test_scatter_plot.py:153-160 (TestScatterPlotWidget.test_render_with_trendline)

The trendline test accepts either a rendered Plotly chart or a statsmodels import error. That means the test suite can pass without ever exercising successful trendline rendering, even though ScatterPlotParams exposes trendline support and the test name claims to verify rendering with a trendline.

recommendation:
Split this into explicit cases: one test that requires or mocks the successful trendline path and asserts no error, and a separate dependency-error test if missing statsmodels is an intended supported failure mode.

test analysis:
The current conditional treats the failure mode as success, so missing or broken trendline support does not fail the suite.

suggested regression test:
Add a test that ensures trendline='ols' renders successfully when the required dependency is available, or patch plotly.express.scatter and assert it is called with trendline='ols' without accepting an error response.

minimum fix scope:
Tighten test_render_with_trendline so the success path is mandatory, and move the missing-dependency behavior into its own targeted test if needed.

## medium: Uncaught config validation errors can make the list endpoint return 500

id: fnd_sig-feat-route-9bba88aee2-8b73e3_a709963d40
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET  (feat_route_9bba88aee2)
next: clawpatch show --finding fnd_sig-feat-route-9bba88aee2-8b73e3_a709963d40

evidence:
- src/niamoto/gui/api/routers/standard_profiles.py:292-296 (list_standard_profiles)
- src/niamoto/gui/api/routers/standard_profiles.py:134-138 (_profile_store)
- src/niamoto/gui/api/routers/standard_profiles.py:149-154 (_validation_service)

The GET /api/standard-profiles handler performs config loading and per-profile validation without catching ValueError or other configuration validation failures. Because those helpers load user-editable import/transform/export YAML, a malformed transform.yml or validation failure can bubble out as an unhandled exception and produce a 500 response instead of a controlled 400-style API error. Neighboring endpoints in this router generally wrap validation/service ValueError into HTTPException, so this list route has inconsistent and brittle error handling.

recommendation:
Wrap the store/service construction and profile validation loop in try/except ValueError and raise HTTPException(status_code=400, detail=str(exc)). Keep HTTPException passthrough if added around broader exceptions.

test analysis:
The existing list tests cover legacy hints and refreshed validation status with valid configuration only; they do not exercise malformed import/transform/export config while listing profiles.

suggested regression test:
Add a test for GET /api/standard-profiles with config/transform.yml containing a dict instead of a list, asserting a 400 response with a useful detail rather than an internal server error.

minimum fix scope:
Update list_standard_profiles error handling and add one router test for invalid transform configuration.

repro:
Write a non-list value to config/transform.yml, for example '{}', then request GET /api/standard-profiles. load_transform_config raises ValueError before the route can return a typed error response.

## medium: Unvalidated upstream status codes can crash the feedback route

id: fnd_sig-feat-route-2defe347ef-0ab148_0cebf1f22a
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /submit (feat_route_2defe347ef)
next: clawpatch show --finding fnd_sig-feat-route-2defe347ef-0ab148_0cebf1f22a

evidence:
- src/niamoto/gui/api/routers/feedback.py:93 (_forward_feedback)
- src/niamoto/gui/api/routers/feedback.py:133 (submit_feedback)

The route mirrors the worker's raw status code into FastAPI's JSONResponse. If the upstream worker returns an invalid HTTP status value, the API can fail while constructing or sending the response instead of returning a controlled relay error. Because this route proxies a network service, the upstream status should be treated as untrusted before being used in the public API response.

recommendation:
Validate the upstream status code before constructing JSONResponse. For values outside the valid HTTP status range, return a 502 with a generic relay error body.

test analysis:
Existing tests cover successful proxying, invalid/private configured URLs, DNS revalidation, and screenshot size limits, but no test simulates an upstream response with an invalid status code.

suggested regression test:
Add a route-level test that monkeypatches _forward_feedback to return (700, {"error": "bad upstream"}) and asserts the API returns a controlled 502 response rather than raising.

minimum fix scope:
Validate status_code in submit_feedback before passing it to JSONResponse.

repro:
Mock _forward_feedback to return (700, {"error": "bad upstream"}), then POST /api/feedback/submit with configured environment variables. The handler attempts JSONResponse(status_code=700, ...) instead of mapping the bad upstream response to a stable error.

## medium: Updating a transform widget crashes when widgets_data is null

id: fnd_sig-feat-library-9282ce0cc6-af4b_e9d6ceb053
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/routers#1 (feat_library_9282ce0cc6)
next: clawpatch show --finding fnd_sig-feat-library-9282ce0cc6-af4b_e9d6ceb053

evidence:
- src/niamoto/gui/api/routers/config.py:1859-1865 (update_transform_widget)
- src/niamoto/gui/api/routers/config.py:1907-1915 (delete_transform_widget)
- tests/common/test_config.py:90-113 (test_transform_widget_route_handles_null_widgets_data)

Read/delete paths normalize null widgets_data, and included tests establish null widgets_data as a supported legacy/stubbed shape for reads. The update path only handles a missing key, not an explicit null, then indexes None and returns a 500 instead of creating the widget mapping.

recommendation:
Normalize widgets_data in update_transform_widget as well. Treat None as {}, reject non-object values with the same 400 contract used elsewhere, then assign the new widget.

test analysis:
Included tests only assert GET behavior for null widgets_data; they do not exercise PUT against the same configuration shape.

suggested regression test:
Add a PUT test with widgets_data: null that expects 200 and verifies transform.yml is saved with widgets_data containing the new widget.

minimum fix scope:
Replace the presence check in update_transform_widget with a call to _normalize_widgets_data, then write the normalized dict back onto the group before mutation.

repro:
Use transform.yml containing [{"group_by": "plots", "widgets_data": null}] and PUT /api/config/transform/plots/widgets/foo with a valid plugin payload. group["widgets_data"] is None, so item assignment raises TypeError and is wrapped as a 500.

## medium: Valid BibTeX titles with deeper protected braces are dropped

id: fnd_sig-feat-route-ee6ca0e128-a8aab9_4b5207eb9d
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /import-bibtex (feat_route_ee6ca0e128)
next: clawpatch show --finding fnd_sig-feat-route-ee6ca0e128-a8aab9_4b5207eb9d

evidence:
- src/niamoto/gui/api/routers/site.py:2720-2728 (_parse_bibtex_entry)
- src/niamoto/gui/api/routers/site.py:2840-2845 (import_bibtex)
- tests/gui/api/routers/test_site.py:141-145 (test_import_bibtex_resolves_string_macros)

The field regex only handles a brace-delimited value with at most one nested brace level. BibTeX commonly uses nested protected braces for capitalization, for example title = {A {{DNA} barcode} study}. For that valid input the title field does not match, so the parser builds a reference with an empty title and the route reports the entry as missing a title instead of importing it.

recommendation:
Replace the field-value regex with a small BibTeX field scanner that tracks nested braces and quoted strings, or use a BibTeX parser library. Ensure values with arbitrary balanced braces are captured before title validation runs.

test analysis:
The current import tests cover a simple braced title, a simple string macro, oversized uploads, missing titles, and malformed entries, but they do not include valid nested-brace title values used for protected capitalization.

suggested regression test:
Add a route test posting a .bib file with title = {A {{DNA} barcode} study} and assert the response imports one entry with that title rather than returning a missing-title error.

minimum fix scope:
Update the BibTeX field parsing used by import_bibtex and add a focused regression test in tests/gui/api/routers/test_site.py.

repro:
Upload a .bib file containing @article{dna, title = {A {{DNA} barcode} study}, author = {Doe, Jane}, year = {2024}} to POST /api/site/import-bibtex; the parser fails to populate title and the route drops the entry with a missing-title error.

## medium: Valid DirectReference ref_key join path is not covered

id: fnd_sig-feat-test-suite-9f184bc103-d_77292e0af4
category: test-gap
confidence: high
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/loaders (feat_test-suite_9f184bc103)
next: clawpatch show --finding fnd_sig-feat-test-suite-9f184bc103-d_77292e0af4

evidence:
- tests/core/plugins/loaders/test_direct_reference.py:86-93 (TestDirectReferenceLoader.test_load_data_success)
- tests/core/plugins/loaders/test_direct_reference.py:132-136 (TestDirectReferenceLoader.test_load_data_success)
- tests/core/plugins/loaders/test_loader_sql_identifiers.py:38-53 (test_direct_reference_rejects_unsafe_ref_key_before_read_sql)

The positive DirectReference load test only covers the simple path where the data foreign key is compared directly to the group id. The only ref_key-specific coverage is a negative SQL identifier rejection case. That leaves the valid ref_key branch, which should join the reference table and match through an alternate reference identifier, untested. A regression in that branch could pass the current suite while breaking configurations that use external reference identifiers.

recommendation:
Add a positive DirectReferenceLoader test with params.ref_key set to a safe field such as external_id, reference table columns including id and external_id, and assert the generated SQL joins the reference table and filters by the reference id field.

test analysis:
Existing success coverage omits ref_key, and the only ref_key test stops before read_sql by using an unsafe identifier.

suggested regression test:
Create test_load_data_success_with_ref_key that configures key='taxon_ref' and ref_key='external_id', mocks columns for both tables, returns a DataFrame from pandas.read_sql, and asserts the SQL contains JOIN "ref_group_table" r ON m."taxon_ref" = r."external_id" and WHERE r."id" = :id.

minimum fix scope:
One new focused test in tests/core/plugins/loaders/test_direct_reference.py.

## medium: Validator accepts dataset links to non-existent references

id: fnd_sig-feat-route-e65a1a6f8b-58391f_33ce726392
category: api-contract
confidence: high
triage: contract-mismatch
status: open
feature: FastAPI route POST /import/v2/validate (feat_route_e65a1a6f8b)
next: clawpatch show --finding fnd_sig-feat-route-e65a1a6f8b-58391f_33ce726392

evidence:
- src/niamoto/gui/api/routers/config.py:1517-1525 (validate_import_v2)
- src/niamoto/gui/api/routers/config.py:1572-1593 (validate_import_v2)

The route advertises validation of entity links and references, but after Pydantic shape validation it only checks that at least one entity exists and that entity keys match a snake_case pattern. A YAML config can declare a dataset link whose `entity` points to a reference that is not present under `entities.references`; this endpoint will still return `valid: true`, allowing the UI or save flow to accept an import config that cannot be resolved semantically.

recommendation:
After `GenericImportConfig.model_validate`, build the set of declared reference names and validate each dataset link target against it. Return an entity-scoped error such as `dataset.<name>` when a link references an unknown entity.

test analysis:
The current route tests cover valid config, empty entities, invalid entity key format, and reference kind variants, but do not include a dataset link that targets a missing reference.

suggested regression test:
Add a `/api/config/import/v2/validate` test with one dataset link to an undeclared reference and assert `valid` is false with a `dataset.<name>` error.

minimum fix scope:
Only `validate_import_v2` semantic validation and its route tests need to change.

repro:
POST /api/config/import/v2/validate with a dataset containing `links: [{entity: missing_reference, field: taxon_id, target_field: id}]` and no `entities.references.missing_reference`. The current semantic validation has no branch that can add an error for that case.

## medium: WKT polygons with interior rings are parsed incorrectly or dropped

id: fnd_sig-feat-library-da3046e57f-8050_dc75a12d2e
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/services (feat_library_da3046e57f)
next: clawpatch show --finding fnd_sig-feat-library-da3046e57f-8050_dc75a12d2e

evidence:
- src/niamoto/gui/api/services/preview_utils.py:314-327 (parse_wkt_to_geojson)
- src/niamoto/gui/api/services/preview_utils.py:329-338 (parse_wkt_to_geojson)

The POLYGON branch captures only characters up to the first closing parenthesis, so a valid WKT polygon with holes silently loses every interior ring. The MULTIPOLYGON branch flattens one captured coordinate string into a single ring and its regex does not handle nested rings, so valid multipolygons with holes can be returned as None. That makes preview/map GeoJSON geometrically wrong for common GIS shapes such as islands, excluded areas, or administrative boundaries with enclaves.

recommendation:
Use a real WKT parser such as shapely/wellknown if available, or implement ring-aware parsing that preserves all rings for Polygon and all polygon/ring groups for MultiPolygon. Invalid WKT should return None without silently corrupting valid geometry.

test analysis:
tests/gui/api/services/test_preview_utils.py only asserts POINT, a single-ring POLYGON, and a MULTIPOLYGON with one exterior ring per polygon; it never exercises interior rings.

suggested regression test:
Add parse_wkt_to_geojson tests for POLYGON with an interior ring and MULTIPOLYGON containing a polygon with an interior ring, asserting the GeoJSON coordinates preserve the nested ring structure.

minimum fix scope:
src/niamoto/gui/api/services/preview_utils.py WKT parsing plus focused geometry parser tests.

repro:
parse_wkt_to_geojson("POLYGON ((0 0, 4 0, 4 4, 0 0), (1 1, 2 1, 1 1))") returns a Polygon with only the exterior ring instead of two rings; a MULTIPOLYGON with the same inner ring pattern is not parsed into valid GeoJSON.

## medium: ZIP extraction can follow a pre-existing symlinked archive directory outside imports

id: fnd_sig-feat-route-96e0fef7ce-dbbe46_b3246cd7bd
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /upload-files (feat_route_96e0fef7ce)
next: clawpatch show --finding fnd_sig-feat-route-96e0fef7ce-dbbe46_b3246cd7bd

evidence:
- src/niamoto/gui/api/routers/smart_config.py:581-587 (_handle_zip_upload)
- src/niamoto/gui/api/routers/smart_config.py:609-621 (_handle_zip_upload)

The ZIP handler accepts an existing imports/<zip-stem> directory without checking whether that directory is a symlink. If imports/data is a symlink to a directory outside the project, uploading data.zip writes temporary files and final extracted members through that symlink. The current relative_to check compares destinations to shapefile_dir.resolve(), so it validates containment inside the symlink target rather than inside the project imports directory.

recommendation:
Reject symlinked extraction directories and ensure the resolved extraction directory remains under the resolved project imports directory before writing any ZIP member. Consider applying the same resolved-containment check to imports_dir itself.

test analysis:
The symlink test covers an existing symlinked component file, but not a symlinked parent extraction directory or imports directory.

suggested regression test:
Create imports/data as a symlink to a tmp_path outside the working directory, upload data.zip, and assert the request returns an error and no external file is created.

minimum fix scope:
Add resolved path validation for imports_dir and shapefile_dir before ZIP extraction writes files.

repro:
Create imports/data as a symlink to an external writable directory, then POST data.zip containing file1.csv. The extracted file is written into the external directory while the response reports path imports/data/file1.csv.

## medium: A partial spatial config suppresses fallback discovery of other shape tables

id: fnd_sig-feat-route-ab5f280e83-4500dd_47ed61e1f6
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route GET /geo-coverage (feat_route_ab5f280e83)
next: clawpatch show --finding fnd_sig-feat-route-ab5f280e83-4500dd_47ed61e1f6

evidence:
- src/niamoto/gui/api/routers/stats.py:1997-2004 (_resolve_spatial_reference_tables)
- src/niamoto/gui/api/routers/stats.py:2070-2087 (_resolve_spatial_reference_tables)
- src/niamoto/gui/api/routers/stats.py:4115-4173 (get_geo_coverage)

The helper advertises fallback discovery for partial import.yml metadata, but it only scans tables when no configured spatial reference was appended at all. If import.yml contains one spatial reference whose table currently lacks a geometry column, any other unconfigured geometry tables are skipped. GET /geo-coverage then reports no analyzable shapes and ready_for_analysis false even though a usable shape table exists in the database.

recommendation:
Run fallback geometry scanning for tables not already seen when configured spatial references are missing geometry, or more generally merge config-derived spatial tables with unconfigured geometry-table discoveries while deduplicating by table name.

test analysis:
The included CLI stats tests do not hit this route. Existing GUI helper tests cover all-configured and no-config fallback modes separately, but not the partial-config case where at least one configured spatial reference exists and fallback still needs to find additional geometry tables.

suggested regression test:
Add a _resolve_spatial_reference_tables or GET /geo-coverage test with one configured spatial table without geometry plus one unconfigured geometry table, asserting both are considered and ready_for_analysis can become true.

minimum fix scope:
Adjust _resolve_spatial_reference_tables fallback condition and add a partial-config regression test.

repro:
Use an occurrence table with valid geometry, configure one spatial reference that resolves to a table without geometry, and also keep an unconfigured table such as zones with a geom or geometry column. GET /api/stats/geo-coverage will only list the configured non-geometry table and will not discover zones.

## medium: Analyze response is not upload-equivalent and drops class names

id: fnd_sig-feat-route-6801ba1857-04b58f_2a36de7e17
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: FastAPI route GET /{reference_name}/analyze/{source_name} (feat_route_6801ba1857)
next: clawpatch show --finding fnd_sig-feat-route-6801ba1857-04b58f_2a36de7e17

evidence:
- src/niamoto/gui/api/routers/sources.py:50-55 (ClassObjectInfo)
- src/niamoto/gui/api/routers/sources.py:409-413 (upload_precalc_source)
- src/niamoto/gui/api/routers/sources.py:730-731 (analyze_existing_source)
- src/niamoto/gui/api/routers/sources.py:777-784 (analyze_existing_source)

The route advertises upload-equivalent analysis, and the upload contract includes each class object's class_names. The analyze route hand-builds a response without a response_model and omits class_names, so a client that analyzes an already configured source gets less information than it got immediately after upload. That breaks consumers that need category labels for mapping or display after reload.

recommendation:
Add a response model for analyze_existing_source or reuse a shared analysis response model, and include class_names (and any other intentionally shared fields such as columns/success if the endpoint is meant to match upload).

test analysis:
The discovered sources router test for analyze only covers rejecting paths outside imports; it does not exercise a successful analyze response or compare it with the upload response contract.

suggested regression test:
Add a positive test for GET /api/sources/{reference}/analyze/{source} using a configured CSV with class_name values and assert each class_objects item includes class_names matching ClassObjectAnalyzer output.

minimum fix scope:
Update analyze_existing_source response serialization and add focused route coverage for the successful response contract.

repro:
Upload or configure a CSV with a class_object that has non-empty class_name values, then GET /api/sources/{reference}/analyze/{source}; the class_objects entries include cardinality but not the class_names returned by the upload endpoint.

## medium: Batch-preloaded occurrences can be dropped when taxon IDs are stringified

id: fnd_sig-feat-library-955a2fdc3a-e408_b1a152c737
category: bug
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/plugins/transformers/formats (feat_library_955a2fdc3a)
next: clawpatch show --finding fnd_sig-feat-library-955a2fdc3a-e408_b1a152c737

evidence:
- src/niamoto/core/plugins/transformers/formats/niamoto_to_dwc_occurrence.py:202-214 (NiamotoDwCTransformer.prepare_batch)
- src/niamoto/core/plugins/transformers/formats/niamoto_to_dwc_occurrence.py:437-441 (NiamotoDwCTransformer._fetch_occurrences_batch_from_db)
- src/niamoto/core/plugins/transformers/formats/niamoto_to_dwc_occurrence.py:160-165 (NiamotoDwCTransformer.transform)
- tests/core/plugins/transformers/formats/test_niamoto_to_dwc_occurrence.py:353-375 (TestNiamotoDwCTransformer.test_prepare_batch_uses_preloaded_occurrences)

prepare_batch preserves the original taxon ID type from transformed rows, while the batch SQL result groups by the database t.id value type. If input rows contain a numeric ID as a string, prepared_taxon_ids contains "123", but the fetched rows are stored under integer key 123. transform then sees "123" in prepared_taxon_ids and uses the preloaded cache, but get("123", []) returns an empty list, so valid occurrences are silently omitted. The linked batch test only covers integer IDs, so it does not contradict this failure mode.

recommendation:
Normalize taxon IDs consistently across prepare_batch, _fetch_occurrences_batch_from_db grouping, and transform cache lookup. For example, keep a requested-ID-to-database-ID map or cast fetched _taxon_id keys to the same canonical representation used by _get_taxon_id_from_data before storing and looking up cached occurrences.

test analysis:
Existing batch tests use integer taxon IDs throughout, so the cache key type matches the database result key type.

suggested regression test:
Add a prepare_batch/transform test where the input taxon id is "123" but the batch result key is integer 123, and assert the preloaded occurrence is still returned without falling back to a single fetch.

minimum fix scope:
Update the Darwin Core transformer's batch cache key normalization and add one focused regression test in tests/core/plugins/transformers/formats/test_niamoto_to_dwc_occurrence.py.

repro:
Prepare a batch with data {"id": "123"} and mock _fetch_occurrences_batch_from_db behavior equivalent to rows containing _taxon_id=123. The preload map will hold records under 123, while transform({"id": "123"}, same_config) looks up "123" and returns [].

## medium: Blocking analyzers run inline on the FastAPI event loop

id: fnd_sig-feat-route-536a72b579-372aeb_88f6d686f1
category: performance
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /analyze (feat_route_536a72b579)
next: clawpatch show --finding fnd_sig-feat-route-536a72b579-372aeb_88f6d686f1

evidence:
- src/niamoto/gui/api/routers/files.py:353-371 (analyze_file)
- src/niamoto/gui/api/routers/files.py:647-648 (analyze_shape)
- src/niamoto/gui/api/routers/files.py:793-794 (analyze_excel)
- tests/gui/api/routers/test_files.py:115-131 (test_analyze_file_rejects_oversized_upload)

The route is declared async, but after reading the upload it awaits analyzer coroutines that perform synchronous CPU and file I/O work inline: geopandas reads spatial files, pandas reads Excel workbooks, and CSV parsing loops over the full upload. Because those analyzer coroutines contain no offload points, a large allowed upload can monopolize the event loop for that worker and delay unrelated GUI API requests. The 50 MB upload cap and 100 MB ZIP expansion cap reduce the blast radius but still allow expensive parsing operations.

recommendation:
Run the blocking analyzer work in a threadpool, for example by making the analyzers synchronous and dispatching them with run_in_threadpool from analyze_file, or by wrapping each blocking pandas/geopandas parse call in run_in_threadpool.

test analysis:
The current tests assert routing, size limits, and analyzer results, but they do not exercise concurrent requests or verify that heavy parsing is offloaded from the event loop.

suggested regression test:
Add an async route-level test with a patched analyzer that performs blocking sleep and verify a concurrent lightweight request can still complete promptly after analyze_file dispatches analyzer work through run_in_threadpool.

minimum fix scope:
Change POST /analyze dispatch so CSV, Excel, and spatial analysis execute off the event loop.

repro:
Send a large but allowed .xlsx or shapefile ZIP to /api/files/analyze while issuing another lightweight API request to the same single-worker server; the second request can be delayed until pandas/geopandas parsing completes.

## medium: Combined widget configs can return null export plugins

id: fnd_sig-feat-route-66e52a2d79-c8526b_6b03396c9d
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: FastAPI route POST /generate-config (feat_route_66e52a2d79)
next: clawpatch show --finding fnd_sig-feat-route-66e52a2d79-c8526b_6b03396c9d

evidence:
- src/niamoto/gui/api/routers/templates.py:451-468 (generate_transform_config)
- src/niamoto/gui/api/routers/templates.py:708-712 (_build_export_config)
- tests/gui/api/routers/test_templates.py:407-426 (test_generate_config_rejects_malformed_combined_config)

The combined-config branch only validates that transformer and widget are objects. If the widget object omits plugin or sets it to null, generate-config returns export_override.plugin as null. The later export builder treats the presence of the plugin key as authoritative, so its fallback mapping is not used and save-config can write an export widget with plugin: null. The existing malformed-combined test covers a non-object transformer, but not missing required keys inside the widget section.

recommendation:
Validate combined configs require non-empty string widget.plugin and transformer params shaped as an object, or omit export_override.plugin when absent so _build_export_config can fall back to map_transformer_to_widget.

test analysis:
The current malformed combined test checks section type validation only; it does not assert required fields within otherwise object-shaped combined configs.

suggested regression test:
Add a generate-config test for combined config with widget missing plugin and assert 422, plus a valid combined config test that confirms export_override.plugin is a string.

minimum fix scope:
Tighten validation in the combined-config branch and extend the router tests for missing widget plugin.

repro:
POST /api/templates/generate-config with a template config like {"transformer":{"plugin":"time_series_analysis","params":{}},"widget":{"params":{}}}. The response contains widgets_data[template_id].export_override.plugin = null; passing that response to save-config reaches _build_export_config and keeps plugin null.

## medium: Concurrent publication requests can race on the same output artifacts

id: fnd_sig-feat-route-abe96db467-b3b7fb_b0d42843e8
category: concurrency
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /{profile_name}/outputs/{output_type} (feat_route_abe96db467)
next: clawpatch show --finding fnd_sig-feat-route-abe96db467-b3b7fb_b0d42843e8

evidence:
- src/niamoto/gui/api/routers/standard_profiles.py:397-404 (execute_standard_profile_output)
- src/niamoto/gui/api/routers/standard_profiles.py:421-429 (execute_standard_profile_output_draft)

The publication route dispatches output generation to the threadpool without any per-profile/output serialization, while the adjacent draft route explicitly serializes generation for the same profile/output key. The output service writes deterministic files for a configured profile output, so two POSTs to the publication endpoint can run in parallel against the same target artifacts and temporary filenames, causing failed requests or last-writer-wins output depending on timing.

recommendation:
Reuse the same per-workdir/profile/output locking strategy for publication output generation, or add a dedicated publication-output lock that wraps the run_in_threadpool call without blocking the event loop while waiting for the lock.

test analysis:
No linked tests were provided for this feature. The local route tests cover successful single-request execution and threadpool dispatch, but not overlapping POSTs to the same publication output.

suggested regression test:
Add an async/concurrent route test that monkeypatches _output_service().execute_profile to block while tracking active calls, fires two POSTs for the same profile/output, and asserts the second call cannot enter execute_profile until the first has exited.

minimum fix scope:
Update execute_standard_profile_output to serialize generation per workdir/profile_name/output_type and cover the route behavior with a concurrency regression test.

repro:
Send two overlapping POST requests to /api/standard-profiles/dwc_occurrences/outputs/api_json for a profile whose output writes to the default or configured publication directory; both requests enter execute_profile concurrently because there is no route-level lock.

## medium: CSS widget dependencies are emitted as script tags

id: fnd_sig-feat-route-618ee42618-788650_223678d1d2
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route GET /render-widget/{group_by}/{entity_id}/{transform_key} (feat_route_618ee42618)
next: clawpatch show --finding fnd_sig-feat-route-618ee42618-788650_223678d1d2

evidence:
- src/niamoto/gui/api/routers/entities.py:501-505 (render_widget)
- src/niamoto/gui/api/routers/entities.py:521-524 (render_widget)

The route treats every widget dependency as JavaScript and emits only script tags. Widget dependencies can include stylesheets, so a CSS dependency would be requested as a script instead of loaded with a stylesheet link, leaving the rendered widget unstyled or producing browser MIME errors in the preview.

recommendation:
Split dependencies by type before rendering the head. Emit <link rel="stylesheet" href="..."> for CSS assets and <script src="..."></script> for JavaScript assets, preserving the existing safety checks for both href and src attributes.

test analysis:
The linked render-widget tests cover escaping a missing widget message, rejecting one unsafe JavaScript-like dependency, and read-only database access. They do not include any stylesheet dependency or assert the generated head markup for CSS assets.

suggested regression test:
Add a render_widget test with a fake widget returning ['/assets/css/widget.css', '/assets/js/widget.js'] and assert that the response contains a stylesheet link for the CSS dependency and a script tag for the JS dependency.

minimum fix scope:
Update dependency rendering in src/niamoto/gui/api/routers/entities.py and add a focused test in tests/gui/api/routers/test_entities.py.

repro:
Use a widget whose get_dependencies() returns ['/assets/css/widget.css']; GET /api/entities/render-widget/taxon/1/richness returns <script src="/api/site/assets/css/widget.css"></script> rather than a <link rel="stylesheet">, so the CSS is not applied.

## medium: Database validation SQL path is not covered by the security tests

id: fnd_sig-feat-test-suite-0b8bb8d338-f_21f849d12e
category: test-gap
confidence: medium
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/transformers/aggregation (feat_test-suite_0b8bb8d338)
next: clawpatch show --finding fnd_sig-feat-test-suite-0b8bb8d338-f_21f849d12e

evidence:
- tests/core/plugins/transformers/aggregation/test_database_aggregator.py:67-88 (TestDatabaseAggregatorPlugin.test_sql_security_validation)
- tests/core/plugins/transformers/aggregation/test_database_aggregator.py:205-239 (TestDatabaseAggregatorPlugin.test_transform_rejects_malicious_template_param_before_execution)
- tests/core/plugins/transformers/aggregation/test_database_aggregator.py:370-378 (TestDatabaseAggregatorPlugin.test_get_example_config)

The suite verifies direct SQL validation and one malicious template parameter, but the validation configuration path is only checked for presence in the example config. That leaves the required_tables validation path untested even though it executes its own SQL before query execution. A regression or injection bug in that preflight path would not be caught by the current security-focused tests.

recommendation:
Add a DatabaseAggregator transform test with validation.required_tables set to an unsafe table identifier and assert the plugin rejects it before executing any SQL; also add a positive required_tables test for a safe table name.

test analysis:
The existing malicious cases exercise _validate_sql_security through direct queries/templates, not the separate validation.required_tables preflight path.

suggested regression test:
Configure validation.required_tables with a value like "taxon_ref; DROP TABLE occurrences; --" and assert transform raises without calling session.execute for that value.

minimum fix scope:
Extend test_database_aggregator.py with targeted required_tables validation tests; implementation may also need identifier validation depending on the test result.

## medium: Direct CSV path support lacks path escape coverage

id: fnd_sig-feat-test-suite-9f184bc103-1_2fc92b1b21
category: test-gap
confidence: medium
triage: test-gap
status: open
feature: Python test suite tests/core/plugins/loaders (feat_test-suite_9f184bc103)
next: clawpatch show --finding fnd_sig-feat-test-suite-9f184bc103-1_2fc92b1b21

evidence:
- tests/core/plugins/loaders/test_stats_loader.py:366-405 (TestStatsLoader.test_load_data_csv_direct_path)

The StatsLoader tests intentionally cover direct CSV path auto-detection and assert that a relative path is resolved and read. There is no companion test for absolute paths or parent-directory traversal such as ../secrets.csv. Because this loader reads files from configuration, that boundary matters: a future or current implementation could allow reading outside the project instance and this suite would still pass.

recommendation:
Add tests that pass absolute and parent-directory CSV paths and assert the loader rejects them before pandas.read_csv. If direct absolute paths are intentionally allowed, document that contract in the test name and cover the allowed base directories explicitly.

test analysis:
The only direct-path test is a happy path with imports/raw_shape_stats.csv; file-not-found and parse-error tests use configured import sources rather than escape-style direct paths.

suggested regression test:
Add test_load_data_csv_direct_path_rejects_parent_traversal with data='../outside.csv' and assert DataLoadError plus pandas.read_csv.assert_not_called(). Add the same for an absolute path if the intended contract is project-relative only.

minimum fix scope:
One or two focused StatsLoader direct-path tests.

## medium: Duplicate YAML entity keys are accepted and collapsed before validation

id: fnd_sig-feat-route-e65a1a6f8b-91ca7c_21e0e91df4
category: data-loss
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /import/v2/validate (feat_route_e65a1a6f8b)
next: clawpatch show --finding fnd_sig-feat-route-e65a1a6f8b-91ca7c_21e0e91df4

evidence:
- src/niamoto/gui/api/routers/config.py:1521 (validate_import_v2)
- src/niamoto/gui/api/routers/config.py:1534-1537 (validate_import_v2)
- src/niamoto/gui/api/routers/config.py:1581-1593 (validate_import_v2)

The endpoint claims to validate unique entity names, but it parses YAML with `yaml.safe_load` before any uniqueness check. Standard PyYAML loading keeps only the last value for duplicate mapping keys, so duplicate dataset or reference names are collapsed before the later loop sees them. The validator can therefore return `valid: true` for input containing duplicate entity definitions; the related save route re-loads and writes the parsed dict, which would persist only one of the duplicates.

recommendation:
Use a YAML loader that rejects duplicate mapping keys for this endpoint, or pre-parse with duplicate-key detection before `safe_load`. Return a validation error scoped to the duplicated entity path.

test analysis:
The route tests check snake_case entity names but do not include YAML with duplicate dataset or reference keys, so they do not exercise the promised uniqueness validation.

suggested regression test:
Add a validation test that posts YAML with duplicate dataset keys and asserts `valid` is false with an error mentioning the duplicate entity key.

minimum fix scope:
Add duplicate-key-aware YAML parsing for `validate_import_v2` and cover it in the import v2 route tests.

repro:
Submit YAML with two `entities.datasets.observations` keys containing different connector paths. After `yaml.safe_load`, only the last `observations` mapping remains, so the uniqueness check has no duplicate to inspect.

## medium: Enrichment preview tests do not cover private URL rejection

id: fnd_sig-feat-test-suite-7937c9eeaa-0_fd0203cf5a
category: test-gap
confidence: medium
triage: test-gap
status: open
feature: Python test suite tests/gui/api/routers#1 (feat_test-suite_7937c9eeaa)
next: clawpatch show --finding fnd_sig-feat-test-suite-7937c9eeaa-0_fd0203cf5a

evidence:
- tests/gui/api/routers/test_data_explorer.py:473-538 (test_preview_enrichment_preserves_structured_profile_config)
- tests/gui/api/routers/test_data_explorer.py:500-502 (test_preview_enrichment_preserves_structured_profile_config)
- tests/gui/api/routers/test_deploy.py:386-406 (test_health_rejects_private_url_without_outbound_request)
- tests/gui/api/routers/test_deploy.py:447-483 (test_health_revalidates_url_immediately_before_request)

The suite has strong SSRF-style checks for deploy health URLs, including localhost rejection and DNS rebinding prevention before an outbound request. The enrichment preview tests also exercise an endpoint that invokes a loader with a configured api_url, but they only use public HTTPS fixtures and mocked successful loader calls. There is no analogous test proving a private or rebound api_url is rejected before the loader runs.

recommendation:
Add a negative enrichment preview test with import.yml api_url set to localhost/private IP and a run_in_threadpool monkeypatch that fails if invoked. If DNS validation is expected, add a rebinding-style test similar to the deploy health route.

test analysis:
Current enrichment preview tests assert config pass-through and successful loader behavior; the private URL and no-outbound-request assertions exist only for /api/deploy/health, not /api/data/enrichment/preview.

suggested regression test:
Create import.yml with taxonomy.api_enrichment.api_url: http://127.0.0.1/metadata, monkeypatch run_in_threadpool to raise if called, POST /api/data/enrichment/preview, and assert 400 plus no loader invocation.

minimum fix scope:
tests/gui/api/routers/test_data_explorer.py, with shared URL validation wired into the enrichment preview route if the new test exposes the gap.

## medium: Failed thread startup leaves an orphaned active job

id: fnd_sig-feat-route-8ed7dff139-904c97_9003a9db30
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /auto-configure/jobs (feat_route_8ed7dff139)
next: clawpatch show --finding fnd_sig-feat-route-8ed7dff139-904c97_9003a9db30

evidence:
- src/niamoto/gui/api/routers/smart_config.py:146-168 (_AutoConfigureJobStore._prune_locked)
- src/niamoto/gui/api/routers/smart_config.py:175-179 (_AutoConfigureJobStore._active_jobs_for_project_locked)
- src/niamoto/gui/api/routers/smart_config.py:808-818 (start_auto_configure_job)

The route stores a pending job before starting the background thread, but there is no cleanup or failure transition if thread.start() raises. Because pruning only removes terminal jobs and pending jobs count against the per-project active-job limit, a thread-start failure can leave the project permanently unable to start another auto-config job until process restart or manual store mutation.

recommendation:
Wrap thread.start() in a try/except and either remove the just-created job from the store or mark it failed with a terminal event before returning a 503/500. Prefer adding a small store method for delete/fail-on-startup so the cleanup stays under the store lock.

test analysis:
The job tests cover successful completion, active-job rejection, project scoping, and event streaming, but they do not simulate a background thread startup failure.

suggested regression test:
Add a test that monkeypatches threading.Thread.start to raise, asserts the route returns an error, then restores start and verifies a new POST for the same project is not rejected as an already-active job.

minimum fix scope:
src/niamoto/gui/api/routers/smart_config.py: add startup failure cleanup around thread.start(), plus one focused router test.

repro:
Monkeypatch threading.Thread.start to raise RuntimeError, POST /api/smart/auto-configure/jobs with a valid imports file, then POST the same route again. The first request fails after creating the pending job; the second request returns 409 because the orphaned pending job still counts as active.

## medium: Filtered /execute requests can complete successfully without running the requested work

id: fnd_sig-feat-route-bf87481f7f-dcbce5_8123b78c7e
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: FastAPI route POST /execute (feat_route_bf87481f7f)
next: clawpatch show --finding fnd_sig-feat-route-bf87481f7f-dcbce5_8123b78c7e

evidence:
- src/niamoto/gui/api/routers/transform.py:190-215 (execute_transform_background)
- src/niamoto/gui/api/routers/transform.py:222-235 (execute_transform_background)
- src/niamoto/gui/api/routers/transform.py:272-289 (execute_transform_background)

The worker validates missing group filters, but it never validates missing transformation filters. If a caller posts transformations containing only unknown widget names, every group is dropped and the job is marked completed with zero metrics. The same zero-work success can happen for a supported default group shape because available_groups maps a missing group_by to "default", while normalize_group compares the requested group against None. In both cases a user-requested transform job can look successful even though none of the requested work was selected or executed.

recommendation:
Distinguish an intentionally empty transform config from a user-supplied filter that matched nothing. If group_by/group_bys/transformations were supplied and no expected transformations remain, fail the job with a clear not-found error before completing. Normalize missing group_by consistently, either by rejecting such configs or by treating them as "default" throughout filtering and execution.

test analysis:
The included CLI tests cover CLI group handling, not POST /execute. The route tests I inspected cover unknown groups and valid qualified widget filters, but not an unknown transformations filter or the missing-group_by/default-group path.

suggested regression test:
Add route-level or direct background-worker tests that assert transformations=["missing"] fails the job, and that group_by="default" either executes a no-group config consistently or is rejected explicitly.

minimum fix scope:
Update execute_transform_background selection validation and default group normalization in src/niamoto/gui/api/routers/transform.py, plus focused FastAPI route/background tests.

repro:
Call execute_transform_background with a config containing one widget and transformations=["missing_widget"]. The filtering at lines 206-215 produces no prepared groups, and lines 274-289 complete the job with total_transformations=0 instead of failing the invalid request.

## medium: Fusion training can publish a degraded model when required branch models are missing

id: fnd_sig-feat-library-c6e9398720-ecd7_053f7d9933
category: build-release
confidence: medium
triage: risk
status: open
feature: Python source ml/scripts/train (feat_library_c6e9398720)
next: clawpatch show --finding fnd_sig-feat-library-c6e9398720-ecd7_053f7d9933

evidence:
- ml/scripts/train/train_fusion.py:71-84 (load_branch_models)
- ml/scripts/train/train_fusion.py:450-458 (main)
- ml/scripts/train/train_fusion.py:544-561 (main)

The fusion model is meant to combine header and value branch probabilities, but missing branch model files only produce warnings. The script then extracts features with None branch models, which produces zero probability vectors, fits LogisticRegression, and writes fusion_model.joblib successfully. A mistyped model path or incomplete retrain can therefore create and release a fusion artifact that lacks the intended branch signal while exiting as success.

recommendation:
Fail fast when required branch model files are missing or malformed, unless an explicit option such as --allow-missing-branches is provided for experiments. Also validate that at least one nonzero branch probability is present before saving the final model.

test analysis:
No linked tests cover train_fusion.py main-path release behavior or missing branch model inputs.

suggested regression test:
Add a CLI/main-level test using a small valid gold set and missing branch model paths that asserts the command exits nonzero and does not create fusion_model.joblib.

minimum fix scope:
Change load_branch_models/main in ml/scripts/train/train_fusion.py to enforce required branch artifacts before final training and saving.

repro:
Run train_fusion.py with a valid gold set and --header-model/--value-model paths that do not exist. The script warns, trains with missing branch probabilities, and writes the output model instead of failing.

## medium: GET /api/collections leaves catalog errors unhandled

id: fnd_sig-feat-route-b627500d12-368e7a_4ba235e209
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route GET  (feat_route_b627500d12)
next: clawpatch show --finding fnd_sig-feat-route-b627500d12-368e7a_4ba235e209

evidence:
- src/niamoto/gui/api/routers/collections.py:91-97 (_raise_catalog_error)
- src/niamoto/gui/api/routers/collections.py:100-103 (list_collections)
- tests/gui/api/routers/test_collections.py:15-29 (test_list_collections_returns_reviewable_candidates)

The router already centralizes ValueError-to-HTTP mapping for catalog operations, but the GET collection list route calls the catalog service directly. The catalog service validates collection metadata while building the catalog, so user-editable invalid metadata such as an unknown source, invalid role, or invalid review_status can escape as an unhandled exception and become a 500 instead of a client-facing 400/404. The associated route test only covers the valid happy path.

recommendation:
Wrap list_collections in the same ValueError handling policy used by create/update, or add a read-specific mapper that returns an appropriate 400/404 without leaking an internal 500.

test analysis:
The included GET /api/collections test only asserts the successful catalog response for valid fixture data and does not exercise invalid user-edited collection metadata.

suggested regression test:
Add a router test that writes invalid metadata.collections config before GET /api/collections and asserts a non-500 response with a useful detail message.

minimum fix scope:
Update src/niamoto/gui/api/routers/collections.py list_collections error handling and add a focused test in tests/gui/api/routers/test_collections.py.

repro:
Create an import.yml metadata.collections entry with an invalid role or unknown source, then request GET /api/collections; the handler has no local ValueError mapping around the service call.

## medium: GET /data-content can block the FastAPI event loop while reading and parsing arbitrary project JSON

id: fnd_sig-feat-route-53287c8347-f4f49a_40c95c0809
category: performance
confidence: medium
triage: risk
status: open
feature: FastAPI route GET /data-content (feat_route_53287c8347)
next: clawpatch show --finding fnd_sig-feat-route-53287c8347-f4f49a_40c95c0809

evidence:
- src/niamoto/gui/api/routers/site.py:2310-2311 (get_data_content)
- src/niamoto/gui/api/routers/site.py:2338-2340 (get_data_content)
- tests/gui/api/routers/test_site.py:1415-1452

The route is declared async, so its synchronous file read and full in-memory JSON parse run on the event loop. Because the client controls the project-relative path within allowed data roots and there is no file-size guard, a large JSON file under data/ or files/data/ can stall unrelated GUI API requests until read_text/json.loads and response serialization finish. This is an availability risk for a network-facing FastAPI endpoint, even though path confinement is otherwise enforced.

recommendation:
Either make this route a synchronous def so Starlette runs it in a threadpool, or explicitly offload the read/parse to a worker thread. Add a maximum data-content file size before reading, ideally aligned with the existing upload/preview caps, and return 413 for oversized files.

test analysis:
The linked tests cover malformed JSON shapes only; they do not exercise large files, concurrent requests, or a maximum-size contract for GET /data-content.

suggested regression test:
Add a test that monkeypatches a small MAX_DATA_CONTENT_SIZE_BYTES, writes a larger data/items.json, and asserts GET /api/site/data-content returns 413 without parsing the file.

minimum fix scope:
Change get_data_content file loading/parsing behavior and add a route-level size-limit test.

repro:
Place a large valid array-of-objects file at data/large.json, then request /api/site/data-content?path=data/large.json while issuing another GUI API request; the second request can be delayed while the event loop handles the blocking read and parse.

## medium: Home URL aliases are not rewritten when links include fragments or query strings

id: fnd_sig-feat-route-98d87aef9c-749391_6dbc094e51
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route PUT /config (feat_route_98d87aef9c)
next: clawpatch show --finding fnd_sig-feat-route-98d87aef9c-749391_6dbc094e51

evidence:
- src/niamoto/gui/api/routers/site.py:126-138 (_normalize_link_url)
- src/niamoto/gui/api/routers/site.py:820-835 (update_site_config)
- tests/gui/api/routers/test_site.py:791-828 (test_update_site_config_normalizes_home_output_and_links)

PUT /config intentionally normalizes a root index page from a legacy output such as Home.html to index.html and rewrites navigation/footer aliases. The link rewrite uses the entire URL string as the alias key, so natural links such as /Home.html#team or /Home.html?lang=fr do not match the Home.html alias and are persisted unchanged. After the static page output is saved as index.html, those links point at the old output path instead of the normalized home page, which can leave navigation/footer links broken or stale.

recommendation:
Parse URLs into path plus suffix before alias lookup, rewrite only the path component, and append the original query/fragment suffix. Keep external URLs and non-page schemes unchanged.

test analysis:
The existing route test verifies alias rewriting only for the exact URL /Home.html, so the exact-match behavior passes while URLs with fragments or query strings are untested.

suggested regression test:
Add a PUT /api/site/config test with navigation and footer URLs like /Home.html#intro and Home.html?lang=fr, then assert they are saved as /index.html#intro and index.html?lang=fr.

minimum fix scope:
Update _normalize_link_url and add focused coverage in tests/gui/api/routers/test_site.py.

repro:
Send PUT /api/site/config with a static page {"template":"index.html","output_file":"Home.html"} and navigation URL "/Home.html#intro". The saved static_pages output becomes "index.html", but the saved navigation URL remains "/Home.html#intro" instead of "/index.html#intro".

## medium: Join table loader validates reference metadata but never uses it in the query

id: fnd_sig-feat-library-1ec3b98877-b67a_f2dbeb5708
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: Python source src/niamoto/core/plugins/loaders (feat_library_1ec3b98877)
next: clawpatch show --finding fnd_sig-feat-library-1ec3b98877-b67a_f2dbeb5708

evidence:
- src/niamoto/core/plugins/loaders/join_table.py:41-50 (JoinTableParams)
- src/niamoto/core/plugins/loaders/join_table.py:149-166 (JoinTableLoader.load_data)
- src/niamoto/core/plugins/loaders/join_table.py:169-174 (JoinTableLoader.load_data)
- tests/core/plugins/test_plugin_samples.py:145-149 (TestSampleLoaders.test_join_table_loader)

The config requires key as the reference-table key and exposes grouping, but load_data never resolves or joins the grouping table and never uses params.key. It also hard-codes m.id as the data-table join column. As a result, valid-looking configs that need to translate group_id through a reference table key or use a non-id data primary key validate successfully but produce incorrect SQL.

recommendation:
Either simplify the public contract by removing unused grouping/key fields, or implement the advertised relationship by resolving the grouping table, joining it through params.key, and using registry metadata or a parameter for the data-table id column instead of hard-coded m.id.

test analysis:
The included join-table sample only checks that read_sql is called; it does not inspect the SQL or exercise reference-key translation/non-id source identifiers.

suggested regression test:
Create main, grouping, and join tables where the reference table has an external key distinct from id and the main table uses a non-id identifier; assert load_data returns the expected rows and the SQL uses the configured reference key and source key semantics.

minimum fix scope:
Clarify and implement JoinTableParams semantics in JoinTableLoader.load_data, then add SQL/behavior tests for non-trivial key mappings.

repro:
Use a join table whose reference column stores an external plot code while group_id is the internal reference row id, and set key to the reference table's plot-code column. The loader still compares the join-table reference column directly to :id and never consults the reference table key.

## medium: JSON file logging can fail on non-serializable error context

id: fnd_sig-feat-library-4035506fee-a4bc_77a1d251d3
category: bug
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/common/utils (feat_library_4035506fee)
next: clawpatch show --finding fnd_sig-feat-library-4035506fee-a4bc_77a1d251d3

evidence:
- src/niamoto/common/utils/logging_utils.py:21-45 (JsonFormatter.format)
- src/niamoto/common/utils/logging_utils.py:139-150 (log_error)

log_error accepts arbitrary Dict[str, Any] as additional_info and NiamotoError.details can also contain arbitrary values, then JsonFormatter serializes the resulting record with json.dumps without a default serializer or sanitization. If callers pass common context values such as Path, datetime, Decimal, set, or another exception, the file handler raises TypeError while handling an error log. That can drop the original diagnostic and emit a logging failure during exception handling.

recommendation:
Normalize extra error context before attaching it to the LogRecord, or call json.dumps(log_data, default=str) so logging remains best-effort and never fails on diagnostic metadata.

test analysis:
tests/common/utils/test_logging_utils.py only checks string-only dictionaries for error_details and additional_info, and the file logging test uses no non-serializable context.

suggested regression test:
Add a setup_logging file-output test that calls log_error with additional_info containing a pathlib.Path or datetime and asserts the JSON log line is written with a stringified value.

minimum fix scope:
Update JsonFormatter.format or log_error in src/niamoto/common/utils/logging_utils.py and add one focused regression test in tests/common/utils/test_logging_utils.py.

repro:
Configure file logging with setup_logging(enable_console=False), then call log_error(logger, ValueError('boom'), {'path': Path('x')}); JsonFormatter.format reaches json.dumps(log_data) and raises TypeError because PosixPath is not JSON serializable.

## medium: Layer listing lacks symlink containment coverage

id: fnd_sig-feat-test-suite-630d864e8e-8_a8001c882a
category: test-gap
confidence: medium
triage: test-gap
status: open
feature: Python test suite tests/gui/api/routers#2 (feat_test-suite_630d864e8e)
next: clawpatch show --finding fnd_sig-feat-test-suite-630d864e8e-8_a8001c882a

evidence:
- tests/gui/api/routers/test_layers.py:17-21 (test_list_layers_returns_sorted_relative_paths_without_metadata)
- tests/gui/api/routers/test_layers.py:154-166 (test_get_layer_info_rejects_paths_outside_imports)

The layers tests cover regular files in `imports/` and a direct `../` escape for the detail endpoint, but they do not cover symlinks inside `imports/`. Because layer endpoints enumerate and inspect filesystem paths, a symlink regression could expose metadata or content from outside the project while these tests still pass.

recommendation:
Add layer router tests that create symlinks under `imports/` pointing outside the project and assert list/detail endpoints skip or reject them consistently.

test analysis:
The existing path security test only exercises an encoded parent-directory escape; the listing test only uses regular files and directories.

suggested regression test:
Create `imports/linked.geojson -> ../secret.geojson` and verify `/api/layers?include_metadata=false` does not return it, and `/api/layers/imports/linked.geojson` returns a 403 or 400 without reading the target.

minimum fix scope:
Tests in `tests/gui/api/routers/test_layers.py`; implementation hardening may be needed if the new regression exposes a failure.

## medium: Malformed semantic profiles become 500 responses

id: fnd_sig-feat-route-f7fab64f46-666081_c22208a370
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route GET /{entity_name} (feat_route_f7fab64f46)
next: clawpatch show --finding fnd_sig-feat-route-f7fab64f46-666081_c22208a370

evidence:
- src/niamoto/gui/api/routers/transformer_suggestions.py:367-374 (get_transformer_suggestions)
- src/niamoto/gui/api/routers/transformer_suggestions.py:377-391 (get_transformer_suggestions)

The route handles a completely missing semantic_profile as a user-facing 404, but then directly indexes required keys such as columns, transformer_suggestions, and analyzed_at. If an entity has an older, partial, or corrupted semantic_profile record, KeyError or Pydantic validation errors fall into the generic exception handler and return a 500. That turns persisted user/project data shape drift into an internal server error instead of a clear unavailable/invalid analysis response.

recommendation:
Validate the semantic_profile shape before conversion, and return a clear 404 or 422-style HTTPException for missing/invalid analysis fields. Prefer using a Pydantic model for the stored semantic profile or guarded .get() checks with explicit errors.

test analysis:
No linked tests were provided for this route, and the owned file contains no regression coverage for partial semantic_profile payloads.

suggested regression test:
Add an API test for an entity with semantic_profile present but missing transformer_suggestions/analyzed_at, asserting a non-500 response with a stable error detail.

minimum fix scope:
Update get_transformer_suggestions to validate required semantic_profile keys and handle validation errors explicitly; add targeted route tests for missing profile, partial profile, and valid profile.

repro:
Create or load an entity whose metadata.config contains {'semantic_profile': {'columns': []}} without transformer_suggestions or analyzed_at, then request GET /api/transformer-suggestions/{entity_name}; the handler raises before building the response and returns HTTP 500.

## medium: Markdown preview sanitizer allows arbitrary positioning CSS

id: fnd_sig-feat-route-eae6189540-39b2b2_7a6cbfde59
category: security
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /preview-markdown (feat_route_eae6189540)
next: clawpatch show --finding fnd_sig-feat-route-eae6189540-39b2b2_7a6cbfde59

evidence:
- src/niamoto/gui/api/routers/site.py:1184-1189 (_sanitize_markdown_html)
- src/niamoto/gui/api/routers/site.py:1202-1206 (_sanitize_markdown_html)
- src/niamoto/gui/api/routers/site.py:1274-1279 (preview_markdown)
- tests/gui/api/routers/test_site.py:455-477 (test_preview_markdown_sanitizes_user_controlled_html)

The endpoint is explicitly sanitizing user-controlled markdown before returning HTML, but the style allowlist accepts any CSS made from common punctuation unless it contains url, expression, or javascript. Raw HTML such as a span with position:fixed, inset:0, z-index, and background survives sanitization. If the GUI injects this preview HTML into the app DOM, a crafted preview can cover or spoof the interface even though script URLs and event handlers are removed. The current tests verify script and javascript URL removal but do not constrain dangerous CSS properties.

recommendation:
Replace the character-based style filter with a property-level allowlist. Permit only the styles needed for generated markdown image previews, such as max-width on img and the exact flex alignment/margin properties emitted by _preprocess_markdown_images; reject positioning, z-index, display overrides on arbitrary spans, background, opacity, transform, pointer-events, and similar UI-redress primitives.

test analysis:
The existing preview markdown sanitizer test covers script tags, event handlers, and javascript: URLs, but it never submits benign-looking CSS that can still alter the surrounding UI when rendered.

suggested regression test:
Add a preview-markdown test that posts a span or div with style="position:fixed;inset:0;z-index:9999;background:red" and asserts those properties are stripped, while keeping a separate assertion that the generated image alignment styles still render.

minimum fix scope:
Tighten _sanitize_markdown_html style handling and add one regression test in tests/gui/api/routers/test_site.py.

repro:
POST /api/site/preview-markdown with {"content":"<span style=\"display:block;position:fixed;inset:0;z-index:9999;background:red\">cover</span>"} returns 200 with <span style="display:block;position:fixed;inset:0;z-index:9999;background:red">cover</span> in html.

## medium: Missing API data_source silently falls back to source-table suggestions

id: fnd_sig-feat-route-3392f9beb8-a7a2d8_e1387d077e
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route GET /export/api-targets/{export_name}/groups/{group_by}/suggestions (feat_route_3392f9beb8)
next: clawpatch show --finding fnd_sig-feat-route-3392f9beb8-a7a2d8_e1387d077e

evidence:
- src/niamoto/gui/api/routers/config.py:3438-3450 (suggest_api_export_index_fields)
- src/niamoto/gui/api/routers/config.py:268-274 (_api_export_table_candidates)
- src/niamoto/gui/api/routers/config.py:5097-5105 (suggest_index_fields)
- src/niamoto/gui/api/routers/config.py:5158-5182 (suggest_index_fields)

For an API export group with a configured data_source, the suggestions route is expected to suggest fields from that API export table. The helper narrows candidates to only that data_source, but if the table does not exist it leaves transformed_table unset and then falls into the generic source-table/schema inference path. That produces a successful suggestions response for a different data shape instead of surfacing the bad data_source, so users can save index/detail mappings that do not exist in the configured API export output.

recommendation:
When data_source is provided and none of its candidate tables exists, return a 404 or 422 identifying the missing API export data_source. Only use the source-table inference fallback when no data_source is configured.

test analysis:
The provided tests/common/test_config.py does not exercise this route. The route-specific coverage present in tests/gui/api/routers/test_config_api_exports.py monkeypatches suggest_index_fields, so it verifies that data_source is passed through but never executes the missing-table fallback behavior.

suggested regression test:
Add a FastAPI route test or suggest_index_fields test where a group has data_source='missing_stats', the normal source table exists, and assert the suggestions endpoint returns an error instead of source-derived fields.

minimum fix scope:
Update suggest_index_fields to distinguish an explicit data_source from the default candidate search and fail before the source-table inference branch when the explicit table is unavailable.

repro:
Configure export.yml with json_api_exporter group {'group_by': 'taxons', 'data_source': 'missing_stats'} while transform.yml and the source table for taxons exist, then GET /api/config/export/api-targets/json_api/groups/taxons/suggestions. The route will return suggestions inferred from the source/transform config instead of rejecting the missing API data_source.

## medium: Missing exporter fallback can reorder the wrong export block before the HTML exporter

id: fnd_sig-feat-route-8fbddb1946-04489e_ea0b523020
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /{group_by}/reorder (feat_route_8fbddb1946)
next: clawpatch show --finding fnd_sig-feat-route-8fbddb1946-04489e_ea0b523020

evidence:
- src/niamoto/gui/api/routers/recipes.py:1576-1584 (reorder_widgets)
- src/niamoto/gui/api/routers/recipes.py:1623-1624 (reorder_widgets)
- tests/gui/api/routers/test_recipes.py:789-813 (test_reorder_widgets_leaves_non_web_exporters_unchanged)

The route treats any export with a missing exporter as eligible for widget reordering, then stops at the first matching group. That supports the legacy web_pages fixture, but it is not constrained by export name or by the presence of a later real html_page_exporter. If an export block before web_pages lacks an exporter field and has the same group_by, the endpoint will reorder that block and leave the actual HTML page widgets unchanged while still returning success.

recommendation:
When exporter is missing, only treat the block as the legacy web page export if its name is web_pages, or first prefer an explicit html_page_exporter before applying the legacy fallback.

test analysis:
The non-web regression test only covers a non-web export that explicitly declares exporter: json_api_exporter, so it exercises the continue path. The missing-exporter case is only tested with name: web_pages, which does not catch an earlier non-web or malformed legacy block without exporter.

suggested regression test:
Add a reorder test where a first export named json_api has no exporter field and a later web_pages export has exporter: html_page_exporter. Assert the json_api widgets stay unchanged and the web_pages widgets are reordered.

minimum fix scope:
Update the export selection predicate in reorder_widgets and add the focused regression test in tests/gui/api/routers/test_recipes.py.

repro:
Use an export.yml with exports[0] named json_api, no exporter field, group_by taxons, widgets alpha/beta, followed by exports[1] named web_pages with exporter html_page_exporter and the same group. POST /api/recipes/taxons/reorder with widget_ids ["beta", "alpha"]. The first block is reordered and the html_page_exporter block is not reached.

## medium: Plural plot and locality names are not recognized as domain entities

id: fnd_sig-feat-library-6703e8e4d3-bf00_535b6b1fb2
category: bug
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core (feat_library_6703e8e4d3)
next: clawpatch show --finding fnd_sig-feat-library-6703e8e4d3-bf00_535b6b1fb2

evidence:
- src/niamoto/core/domain_vocabulary.py:14-28 (STABLE_ENTITY_SYNONYMS)
- src/niamoto/core/domain_vocabulary.py:157-160 (matches_entity_name)
- tests/core/test_domain_vocabulary.py:14-18 (test_matches_entity_name_supports_domain_synonyms)

The matcher only accepts an exact normalized synonym or an exact token. Occurrence explicitly includes the plural "occurrences", but plot and locality only include singular forms, so common source names like "plots", "localities", or "locations" are not recognized. That makes infer_entity_token and file/profile heuristics miss common plural reference-table names while still correctly rejecting substrings such as "subplot_metrics".

recommendation:
Add explicit plural synonyms for stable entities, or add conservative plural normalization to token matching while keeping the existing token-boundary behavior that prevents substring matches like "subplot".

test analysis:
The tests cover a plural occurrence name and an underscored plot token, but they do not cover bare plural plot/locality file or entity names.

suggested regression test:
Add assertions that matches_entity_name("plots", "plot"), matches_entity_name("localities", "locality"), and infer_entity_token("locations", allowed=("plot", "taxon", "locality")) return the expected entity tokens while "subplot_metrics" remains false.

minimum fix scope:
Update domain vocabulary synonyms or token normalization in src/niamoto/core/domain_vocabulary.py and extend tests/core/test_domain_vocabulary.py.

repro:
matches_entity_name("plots", "plot") returns False, and infer_entity_token("locations", allowed=("plot", "taxon", "locality")) returns None.

## medium: POST /analyze-file can analyze project CSVs outside imports/

id: fnd_sig-feat-route-3f5bee0ffd-0348b5_eb78922cda
category: security
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /analyze-file (feat_route_3f5bee0ffd)
next: clawpatch show --finding fnd_sig-feat-route-3f5bee0ffd-0348b5_eb78922cda

evidence:
- src/niamoto/gui/api/routers/smart_config.py:674-679 (analyze_file_smart)
- src/niamoto/gui/api/routers/smart_config.py:266-286 (_validate_import_file_paths)
- src/niamoto/gui/api/routers/smart_config.py:779-783 (auto_configure)
- tests/gui/api/routers/test_smart_config.py:657-665 (TestAnalyzeFile.test_analyze_file_rejects_path_outside_project)

The route forwards the client-supplied filepath directly to AutoConfigService without applying the imports/ scoping helper used by the related auto-config endpoints. AutoConfigService only constrains paths to the project root, so any CSV under the project, including files outside imports/, can be probed through this network endpoint for columns, row count, hierarchy, and metadata. The tests prove outside-project traversal is rejected, but they do not establish that /analyze-file is limited to import inputs like the rest of this workflow.

recommendation:
Apply _validate_import_file_paths(work_dir, [request.filepath]) in analyze_file_smart before constructing AutoConfigService, or add an explicit documented allowlist if non-import project files are intentionally supported.

test analysis:
The existing route test only checks ../../etc/passwd is rejected as outside the project. All successful analyze-file tests use imports/... paths, and there is no test for a project-relative CSV outside imports/.

suggested regression test:
Add a test that creates working_directory / "private.csv" and asserts POST /api/smart/analyze-file with filepath "private.csv" returns 400 with an outside imports/project imports error.

minimum fix scope:
Route-level validation in analyze_file_smart plus one regression test.

repro:
Create a CSV such as <project>/private.csv, then POST /api/smart/analyze-file with {"filepath":"private.csv"}. The route will pass the path to analyze_file instead of rejecting it as outside imports/.

## medium: POST /save ignores export groups stored under params.groups

id: fnd_sig-feat-route-a38daf3424-162db5_6e401cff3c
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /save (feat_route_a38daf3424)
next: clawpatch show --finding fnd_sig-feat-route-a38daf3424-162db5_6e401cff3c

evidence:
- src/niamoto/gui/api/routers/recipes.py:1255-1265 (_export_widget_id_exists)
- src/niamoto/gui/api/routers/recipes.py:1468-1483 (save_widget_recipe)
- tests/gui/api/routers/test_recipes.py:462-480 (test_validate_recipe_rejects_duplicate_export_widget_id)

The route's validation helper treats html_page_exporter groups under either top-level groups or params.groups as existing export widgets, but save_widget_recipe only searches and writes top-level web_export["groups"]. For an export.yml that already has the target group under params.groups, POST /save will not update that existing group; it will append a new top-level group instead, leaving two divergent group definitions for the same group_by/widget id. That can make the saved recipe appear missing to code paths reading params.groups, or silently leave stale widget configuration in place.

recommendation:
Use a single helper for locating/creating html_page_exporter groups that mirrors the supported read locations. If params.groups is still supported, update the matched params.groups entry in place; otherwise remove params.groups support from duplicate detection and migration paths so save/validate have one contract.

test analysis:
The duplicate-id test only builds export groups at the top level, and the save rollback tests use an empty exports list, so no test exercises POST /save against an existing html_page_exporter group under params.groups.

suggested regression test:
Add a POST /api/recipes/save test with load_export_config returning {'exports': [{'exporter': 'html_page_exporter', 'params': {'groups': [{'group_by': 'taxons', 'widgets': [{'plugin': 'bar_plot', 'data_source': 'richness'}]}]}}]}. Assert the saved config updates that existing params.groups widget and does not create a top-level groups duplicate.

minimum fix scope:
src/niamoto/gui/api/routers/recipes.py group lookup/creation in save_widget_recipe, plus a focused regression in tests/gui/api/routers/test_recipes.py.

repro:
Configure load_export_config to return an html_page_exporter with params.groups containing group_by='taxons' and a widget data_source='richness', then POST /api/recipes/save with widget_id='richness'. The saved export_config will contain a new top-level groups entry instead of updating the existing params.groups widget.

## medium: PUT /data-content accepts unbounded JSON payloads for disk writes

id: fnd_sig-feat-route-6c8536c8db-bf48f3_feda2d2e9c
category: security
confidence: medium
triage: risk
status: open
feature: FastAPI route PUT /data-content (feat_route_6c8536c8db)
next: clawpatch show --finding fnd_sig-feat-route-6c8536c8db-bf48f3_feda2d2e9c

evidence:
- src/niamoto/gui/api/routers/site.py:2303-2307 (DataFileUpdate)
- src/niamoto/gui/api/routers/site.py:2390-2392 (update_data_content)
- src/niamoto/gui/api/routers/site.py:2447-2450 (update_file_content)

The route is a network-exposed file writer for user-controlled JSON, but DataFileUpdate has no item-count or serialized-size limit and update_data_content dumps and writes the full payload. Nearby upload and file-content endpoints enforce explicit byte limits, so this route is an outlier that can consume memory during parsing/serialization and fill project storage with a large request.

recommendation:
Add a maximum serialized byte size and/or maximum row count for data-content updates, return 413 when exceeded, and ideally enforce request body size before full parsing if the GUI API has shared middleware for that.

test analysis:
There are oversize tests for uploads, markdown preview, and file-content, but no PUT /data-content size-limit test in the included route tests.

suggested regression test:
Add a PUT /api/site/data-content test that monkeypatches a small MAX_DATA_CONTENT_SIZE_BYTES, sends data whose serialized JSON exceeds it, expects 413, and verifies any existing file is unchanged and no temp files remain.

minimum fix scope:
Introduce data-content size limits in site.py and add targeted tests for rejection and preservation of the existing file.

repro:
PUT /api/site/data-content with path data/items.json and a very large data array; the route will serialize and write it instead of returning 413.

## medium: Queued dataset imports can run against a different project than the request that created them

id: fnd_sig-feat-route-4b1f55c125-ebfa79_a06766d0bd
category: data-loss
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /execute/dataset/{entity_name} (feat_route_4b1f55c125)
next: clawpatch show --finding fnd_sig-feat-route-4b1f55c125-ebfa79_a06766d0bd

evidence:
- src/niamoto/gui/api/routers/imports.py:435-470 (execute_import_dataset)
- src/niamoto/gui/api/routers/imports.py:1103-1111 (process_generic_import_entity)
- src/niamoto/gui/api/context.py:47-59 (get_working_directory)
- src/niamoto/gui/api/context.py:226-274 (reload_project_from_desktop_config)

The route captures the request's resolved working directory and uses it for conflict detection and job metadata, but the background worker ignores that captured value and re-reads the mutable global GUI working directory when it starts. If the desktop project is reloaded or changed after the POST response is queued but before the background task resolves its config, the job can import the requested entity name into another project's database. With reset_table=true this can drop or overwrite tables in the wrong project. The stored job metadata would still claim the original working_directory, making the corruption difficult to diagnose.

recommendation:
Bind the background task to the request-time project. Pass the resolved work_dir or config_dir/database_path into process_generic_import_entity, or have the worker reconstruct Path(job["working_directory"]) and use that instead of calling get_working_directory(). Apply the same pattern to any follow-up cache invalidation that must target the same project.

test analysis:
The route-level dataset success test monkeypatches process_generic_import_entity to a no-op and only asserts that a job was created with the expected entity metadata. There is no test that changes get_working_directory between job creation and background processing, and there is no test asserting the worker uses the job's stored working_directory.

suggested regression test:
Add a test that creates a job while get_working_directory returns project A, changes the mocked working directory to project B before running process_generic_import_entity, and asserts Config/ImporterService are constructed from project A, not project B.

minimum fix scope:
Update execute_import_dataset/process_generic_import_entity to carry and use the captured working directory for the dataset job; add a focused regression test in tests/gui/api/routers/test_imports.py.

repro:
Create a dataset import job for project A, then switch/reload the desktop project to project B before process_generic_import_entity reaches get_working_directory(); the worker builds Config from project B and calls ImporterService for project B while the job record still identifies project A.

## medium: Reference imports can run while dependent dataset imports are still active

id: fnd_sig-feat-route-bb991c7401-712d6a_04a3b1b258
category: concurrency
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /execute/reference/{entity_name} (feat_route_bb991c7401)
next: clawpatch show --finding fnd_sig-feat-route-bb991c7401-712d6a_04a3b1b258

evidence:
- src/niamoto/gui/api/routers/imports.py:240-263 (_raise_if_import_conflicts)
- src/niamoto/gui/api/routers/imports.py:374-409 (execute_import_reference)
- src/niamoto/gui/api/routers/imports.py:841-855 (process_generic_import_all)
- tests/gui/api/routers/test_imports.py:230-294

The import-all path preserves dependency ordering by importing datasets before derived references, but POST /execute/reference/{entity_name} only blocks an active all-import or the exact same reference job. A user can therefore start a reference import while a dataset import for the same working directory is pending or running. For derived references, that can read a missing or partially refreshed source table and either fail spuriously or materialize stale/partial reference data.

recommendation:
Serialize import jobs per working directory, or at minimum reject reference imports when any active dataset job exists for the same working directory if the reference is derived from that dataset. Return 409 with the blocking job_id, matching the existing conflict response style.

test analysis:
The included tests assert conflicts for active import-all jobs and for the same target, but they never seed an active dataset or different-entity job before calling /execute/reference/{entity_name}.

suggested regression test:
Add a GUI router test that seeds imports.import_jobs with a running dataset job in the same working directory, posts /api/imports/execute/reference/taxons, and asserts a 409 with the dataset job_id and no new job creation.

minimum fix scope:
Update _raise_if_import_conflicts and the reference route's conflict policy, then add focused tests in tests/gui/api/routers/test_imports.py.

repro:
Start /api/imports/execute/dataset/occurrences and, before that background job completes, POST /api/imports/execute/reference/taxons where taxons is a derived reference sourced from occurrences. The second request is accepted because the active dataset job does not match import_type='reference' and entity_name='taxons'.

## medium: References response can emit lossy or fabricated transform relations

id: fnd_sig-feat-route-2454f2f91c-42ddd3_b9a5aa25ff
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: FastAPI route GET /references (feat_route_2454f2f91c)
next: clawpatch show --finding fnd_sig-feat-route-2454f2f91c-42ddd3_b9a5aa25ff

evidence:
- src/niamoto/gui/api/routers/transformer_suggestions.py:84-94 (RelationConfig)
- src/niamoto/gui/api/routers/transformer_suggestions.py:227-236 (get_available_references.build_relation_config)
- src/niamoto/gui/api/routers/transformer_suggestions.py:254-255 (get_available_references.build_relation_config)

The route advertises `relation` as the default transform.yml relation, but the response model has no `dataset` field and the explicit import.yml relation handling only copies `foreign_key` and `reference_key`. For projects with multiple datasets, callers cannot know which dataset this relation applies to. Separately, when no safe key is found, the route invents `<reference>_id`, so it can return a relation that does not exist in the source data. Both cases can lead clients to generate broken transform sources from a 200 response.

recommendation:
Add the relation dataset to the API model and populate it from `import.yml`; only return a relation when `foreign_key` or another safe, schema-backed key is available. Otherwise set `relation` to null so callers can ask for or detect a relation instead of using a fabricated one.

test analysis:
The current router tests cover a single-dataset happy path, an explicit key/ref_key pair, and spatial references without relation. They do not assert preservation of `relation.dataset`, multi-dataset behavior, or the no-safe-key fallback path.

suggested regression test:
Add a router test with two datasets and an explicit `relation.dataset` and assert it is present in the response; add another test where a non-spatial reference has no relation/id field and assert `relation` is null.

minimum fix scope:
Update `RelationConfig`, `build_relation_config`, and the `/api/transformer-suggestions/references` contract tests.

repro:
Create an import.yml with two datasets and a reference relation containing `dataset: occurrences`, `foreign_key: plot_name`, and `reference_key: plot`; GET `/api/transformer-suggestions/references` returns the key/ref_key but drops the dataset association. For a generic reference with no relation and no schema id field, the same endpoint returns `key: <name>_id` despite no evidence that column exists.

## medium: Required-table validation interpolates untrusted identifiers into SQL

id: fnd_sig-feat-library-1f08a771ef-6dfa_df077e02aa
category: security
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/plugins/transformers/aggregation (feat_library_1f08a771ef)
next: clawpatch show --finding fnd_sig-feat-library-1f08a771ef-6dfa_df077e02aa

evidence:
- src/niamoto/core/plugins/transformers/aggregation/database_aggregator.py:156-157 (ValidationConfig.required_tables)
- src/niamoto/core/plugins/transformers/aggregation/database_aggregator.py:342-347 (DatabaseAggregatorPlugin._validate_database_state)
- tests/core/plugins/transformers/aggregation/test_database_aggregator.py:205-239 (TestDatabaseAggregatorPlugin.test_transform_rejects_malicious_template_param_before_execution)

The direct query path validates SQL with _validate_sql_security before execution, and tests assert malicious template parameters do not reach the database. The required_tables path is also config-controlled but bypasses that validation and interpolates table names directly into a SQL string. A crafted table value can alter the validation query, and on drivers that accept stacked statements this can bypass the SELECT-only guard entirely.

recommendation:
Validate required table names with the same SQL identifier rules used elsewhere, resolve logical entity names through the registry if needed, and quote identifiers instead of f-stringing raw config values.

test analysis:
The existing malicious SQL regression covers template_params flowing through _execute_query, but there is no equivalent test for validation.required_tables.

suggested regression test:
Add a test that sets validation.required_tables to "taxon_ref; DROP TABLE occurrences; --" and asserts transform raises before session.execute is called.

minimum fix scope:
DatabaseAggregatorPlugin._validate_database_state and tests for required_tables validation.

repro:
Set validation.required_tables to a value such as "taxon_ref; DROP TABLE occurrences; --". _validate_database_state builds "SELECT 1 FROM taxon_ref; DROP TABLE occurrences; -- LIMIT 1" before any identifier validation.

## medium: Save route can persist non class-object CSV sources

id: fnd_sig-feat-route-e8da76bed1-8fb169_c0b1cad55c
category: bug
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /{reference_name}/save (feat_route_e8da76bed1)
next: clawpatch show --finding fnd_sig-feat-route-e8da76bed1-8fb169_c0b1cad55c

evidence:
- src/niamoto/gui/api/routers/sources.py:335-346 (upload_precalc_source)
- src/niamoto/gui/api/routers/sources.py:541-549 (save_source_config)
- src/niamoto/gui/api/routers/sources.py:557-570 (save_source_config)
- src/niamoto/gui/api/routers/sources.py:582-592 (save_source_config)

The feature is specifically for pre-calculated class_object CSV sources, and upload validates that shape before returning a path to save. The save route, however, only checks that the CSV has some header and that the selected entity column exists, then writes a stats_loader source. A direct save request can therefore persist a CSV missing class_object, class_name, or class_value; later class-object widgets and suggestions will see a configured stats source that cannot satisfy their expected data shape.

recommendation:
Before writing transform.yml, validate that the normalized CSV header includes class_object, class_name, and class_value, or reuse ClassObjectAnalyzer and reject when analysis.is_valid is false.

test analysis:
The save tests cover empty CSVs, blank headers, paths outside imports, unknown references, and source collisions, but not a CSV with an entity column that lacks the required class_object fields.

suggested regression test:
Add a save-route test with a CSV header like 'taxon_id,value' and assert 400 with no transform.yml mutation.

minimum fix scope:
Add header-level class_object required-column validation in save_source_config before detect_relation_fields and before acquiring the write lock.

repro:
Create imports/raw_bad.csv containing 'taxon_id,value\n1,5\n', then POST /api/sources/taxons/save with source_name 'bad_stats', file_path 'imports/raw_bad.csv', and entity_id_column 'taxon_id'. The route accepts and writes a stats_loader source despite the missing class_object columns.

## medium: Shapefile conversion overwrites existing GeoPackages without an explicit overwrite choice

id: fnd_sig-feat-library-a67705f9ea-6ea4_117092d787
category: data-loss
confidence: medium
triage: risk
status: open
feature: Python source scripts/_archive (feat_library_a67705f9ea)
next: clawpatch show --finding fnd_sig-feat-library-a67705f9ea-6ea4_117092d787

evidence:
- scripts/_archive/shp_to_gpkg.py:51-58 (convert_shapefile_to_gpkg)
- scripts/_archive/shp_to_gpkg.py:79-90 (convert_multiple_shapefiles)
- scripts/_archive/shp_to_gpkg.py:104-109 (convert_multiple_shapefiles)

The default output paths are deterministic and there is no existence check. Single-file conversion writes to <input>.gpkg, output-dir conversion writes to <stem>.gpkg, and merge mode always writes the first layer to merged.gpkg with mode='w'. Running the helper in a directory with existing GeoPackages can silently replace prior outputs or layers.

recommendation:
Before writing, fail if the target GeoPackage exists unless the user passes an explicit --force/--overwrite flag. For merge mode, consider requiring an explicit --output path or refusing to overwrite merged.gpkg by default.

test analysis:
The included tests are unrelated auto-detection and matcher tests; none exercise shp_to_gpkg.py or pre-existing output files.

suggested regression test:
Add tests for convert_shapefile_to_gpkg and merge mode that create an existing target file and assert conversion refuses to overwrite without an explicit overwrite option.

minimum fix scope:
scripts/_archive/shp_to_gpkg.py output path validation and CLI option handling.

repro:
Place an existing merged.gpkg in the output directory, then run python scripts/_archive/shp_to_gpkg.py <dir> --merge. The first written layer opens merged.gpkg with mode='w', replacing the existing package content.

## medium: Slow analysis blocks the async event loop

id: fnd_sig-feat-route-2d0780c4e2-e3b977_87cc9677df
category: concurrency
confidence: medium
triage: risk
status: open
feature: FastAPI route POST /geo-coverage/analyze (feat_route_2d0780c4e2)
next: clawpatch show --finding fnd_sig-feat-route-2d0780c4e2-e3b977_87cc9677df

evidence:
- src/niamoto/gui/api/routers/stats.py:4191-4201 (analyze_spatial_coverage)
- src/niamoto/gui/api/routers/stats.py:4305-4339 (analyze_spatial_coverage)
- src/niamoto/gui/api/routers/stats.py:4341-4383 (analyze_spatial_coverage)

FastAPI only offloads normal def handlers automatically. Because this route is async def but performs synchronous DuckDB/SQLAlchemy work directly, a large coverage analysis can monopolize the server event loop and delay unrelated API requests on the same worker.

recommendation:
Move the synchronous database/spatial work into a regular helper and call it with await run_in_threadpool(...), or make the route a synchronous def so FastAPI runs it in its threadpool. For very large projects, consider a background job with polling, but the minimum fix is offloading the blocking work.

test analysis:
The current tests validate returned payloads from small fixtures and do not exercise concurrent requests or event-loop responsiveness during long spatial queries.

suggested regression test:
Add an async API test that monkeypatches the analysis helper to block briefly, sends a concurrent lightweight request, and asserts the lightweight request is not held behind the analysis call after the route is offloaded.

minimum fix scope:
Change only the scheduling boundary for analyze_spatial_coverage and keep the current SQL behavior intact.

repro:
Run POST /api/stats/geo-coverage/analyze against a large occurrence table and issue another lightweight API request concurrently; the lightweight request can be delayed until the blocking spatial queries yield.

## medium: Spatial loader ignores its required key field and uses one geometry column for both tables

id: fnd_sig-feat-library-1ec3b98877-a336_fdf4ab86f6
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: Python source src/niamoto/core/plugins/loaders (feat_library_1ec3b98877)
next: clawpatch show --finding fnd_sig-feat-library-1ec3b98877-a336_fdf4ab86f6

evidence:
- src/niamoto/core/plugins/loaders/spatial.py:22-30 (SpatialParams)
- src/niamoto/core/plugins/loaders/spatial.py:91-103 (SpatialLoader.load_data)
- src/niamoto/core/plugins/loaders/spatial.py:105-120 (SpatialLoader.load_data)

SpatialParams requires a key, but load_data never uses params.key. Instead, params.geometry_field is used both to fetch the reference polygon and to test the main table geometry. Configurations where the reference shape column and the main point geometry column differ, which the separate parameters imply should be expressible, will query the wrong column or fail even though the config validates.

recommendation:
Define the contract explicitly and use separate quoted identifiers for the reference geometry column and the main geometry column. If key is intended to identify the main geometry field, use params.key in the m.<column> side of ST_Contains; otherwise remove or rename the required key field and add the missing parameter.

test analysis:
The included spatial sample only asserts that pandas.read_sql is called; it does not assert the generated SQL or cover differing geometry column names.

suggested regression test:
Add a SpatialLoader test with distinct reference and main geometry column names and assert the generated SQL selects the reference geometry column but calls ST_Contains(..., m."<main_geometry_column>").

minimum fix scope:
Adjust SpatialParams/SpatialLoader.load_data so the query uses the configured column for each side of the spatial relationship and add a focused SQL-generation test.

repro:
Configure a reference table with shape_geom and a main table with point_geom, setting key="point_geom" and geometry_field="shape_geom". The generated containment query will still use m."shape_geom" instead of the main-table key column.

## medium: SSH deployer embeds key_path and port into an unquoted rsync remote-shell string

id: fnd_sig-feat-library-6bfcb2751e-ed3d_67cb458674
category: security
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/plugins/deployers (feat_library_6bfcb2751e)
next: clawpatch show --finding fnd_sig-feat-library-6bfcb2751e-ed3d_67cb458674

evidence:
- src/niamoto/core/plugins/deployers/ssh.py:56-70 (SSHDeployer.deploy)
- tests/core/plugins/deployers/test_ssh.py:99-107 (test_ssh_deployer_streams_successful_rsync)

The deployer passes rsync a single remote-shell command string assembled directly from deployment config. Because rsync parses the -e command string to run ssh, spaces or shell metacharacters in key_path, and non-numeric content in port, can change the ssh command. This breaks legitimate key paths containing spaces and can become local command/option injection if a project or GUI-provided deployment config is not fully trusted.

recommendation:
Validate port as an integer in the allowed TCP range, reject key_path values with unsafe characters or quote them with shlex.quote when constructing the rsync -e string. Prefer a small helper that builds the remote-shell string and has tests for spaces and unsafe input.

test analysis:
The SSH tests only assert the default command without key_path and do not cover custom ports, key paths with spaces, or malicious/invalid values.

suggested regression test:
Add tests for key_path='/tmp/my key.pem' and port='22 -oProxyCommand=...' that assert either safe quoting is used or invalid values are rejected before create_subprocess_exec is called.

minimum fix scope:
src/niamoto/core/plugins/deployers/ssh.py command construction plus SSH deployer command-building tests.

repro:
Set extra.key_path to a path containing a space, or to a value containing additional ssh options; the constructed -e value becomes 'ssh -p 22 -i <raw value>' with no quoting or validation, so rsync/ssh does not receive the intended single identity-file argument.

## medium: Structured descriptor contracts are matched only by exact value equality

id: fnd_sig-feat-library-07569c8838-d24e_702b695fd9
category: bug
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/plugins/matching (feat_library_07569c8838)
next: clawpatch show --finding fnd_sig-feat-library-07569c8838-d24e_702b695fd9

evidence:
- src/niamoto/core/plugins/matching/matcher.py:216-225 (SmartMatcher._structure_match_score)
- src/niamoto/core/plugins/matching/matcher.py:284-300 (SmartMatcher._matching_keys / SmartMatcher._mismatched_keys)

The matcher treats descriptor values as opaque values and requires exact equality for every shared key. That works for simple string descriptors like "list", but it rejects structured descriptors such as column lists when a widget declares placeholders or a compatible shape rather than the transformer's exact emitted names. In the current plugin set, this causes otherwise compatible dataframe-style transformer/widget contracts to score 0.0, so auto-discovery can fail silently.

recommendation:
Define explicit semantics for structured descriptor values. For column-list descriptors, either match by shape/length and required metadata, add wildcard placeholder handling, or require plugins to use the exact same canonical column descriptors and validate that contract.

test analysis:
The matching tests exercise simple string descriptors and descriptor mismatches, but they do not cover list-valued descriptor compatibility or placeholder column descriptors.

suggested regression test:
Add a SmartMatcher test with a dataframe transformer output_structure containing a list-valued columns descriptor and a widget compatible_structures pattern that should be considered compatible under the intended dataframe contract.

minimum fix scope:
Update SmartMatcher descriptor comparison helpers and add targeted tests for structured descriptor values.

repro:
Define a transformer with output_structure={"_type":"dataframe","columns":["x","y"]} and a widget pattern {"_type":"dataframe","columns":["x_field","y_field"]}. _mismatched_keys returns {"columns"}, so _partial_match is skipped and no suggestion is produced.

## medium: Table view can render unsanitized cell HTML when escape is disabled

id: fnd_sig-feat-library-5ba560319a-4c71_391d6c7027
category: security
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/plugins/widgets#2 (feat_library_5ba560319a)
next: clawpatch show --finding fnd_sig-feat-library-5ba560319a-4c71_391d6c7027

evidence:
- src/niamoto/core/plugins/widgets/table_view.py:117-120 (TableViewParams.escape)
- src/niamoto/core/plugins/widgets/table_view.py:216-220 (TableViewWidget.render)
- tests/core/plugins/widgets/test_table_view.py:373-393 (TestTableViewWidget.test_render_with_escape_disabled)
- tests/core/plugins/widgets/test_table_view.py:395-415 (TestTableViewWidget.test_render_with_escape_enabled)

Widget data is rendered directly into HTML for preview/export. With escape=False, any HTML in DataFrame cells is emitted verbatim; if a dataset contains script-capable markup, this becomes stored HTML/script injection in the generated widget output. The tests show this is currently allowed intentionally for benign formatting, so confidence is medium rather than high, but the option lacks sanitization or a clearly separated trusted-HTML path.

recommendation:
Keep escaping mandatory for ordinary table data, or replace escape=False with an explicit trusted/sanitized HTML mode that strips scripts/event handlers and is clearly named. If raw HTML is truly required, isolate it behind a separate widget or trusted-only configuration path.

test analysis:
The tests assert that escape=False preserves benign tags, and only verify script escaping when escape=True. They do not cover dangerous attributes/tags under escape=False or document the trust boundary.

suggested regression test:
Add a test with escape=False and a script-capable payload such as an event-handler attribute, asserting it is escaped, sanitized, or rejected according to the chosen policy.

minimum fix scope:
src/niamoto/core/plugins/widgets/table_view.py and tests/core/plugins/widgets/test_table_view.py

repro:
Render TableViewWidget with data = pd.DataFrame({'name': ['<img src=x onerror=alert(1)>']}) and TableViewParams(escape=False). The returned table contains the raw img tag.

## medium: Unvalidated reference name can expose arbitrary extra_data tables

id: fnd_sig-feat-route-43b640eacb-622d7a_622c4d169f
category: security
confidence: medium
triage: risk
status: open
feature: FastAPI route GET /{reference_name}/enrichment-catalog (feat_route_43b640eacb)
next: clawpatch show --finding fnd_sig-feat-route-43b640eacb-622d7a_622c4d169f

evidence:
- src/niamoto/gui/api/routers/templates.py:418-421 (get_enrichment_catalog)
- src/niamoto/gui/api/routers/templates.py:98-107 (_reference_source_candidates)
- src/niamoto/gui/api/services/templates/suggestion_service.py:1139-1157 (get_reference_enrichment_catalog)
- src/niamoto/common/table_resolver.py:78-80 (resolve_reference_table)

The route accepts the network-controlled path parameter and passes it directly to the catalog service. Unlike the suggestions route path, it does not validate that reference_name is declared in import.yml. The downstream reference resolver falls back to convention-based table lookup, including an unprefixed physical table name, then reads extra_data samples and returns field sample values. A caller can therefore request a non-reference table that happens to have an extra_data column and receive catalog/sample data that was not intended to be exposed through this reference-scoped endpoint.

recommendation:
Validate reference_name against the configured import.yml references before calling get_reference_enrichment_catalog, or move that validation into the service. Unknown references should return 404 before any table fallback or SQL query runs.

test analysis:
tests/gui/api/routers/test_templates.py stubs get_reference_enrichment_catalog, so it only verifies serialization and threadpool dispatch. tests/gui/api/services/templates/test_suggestion_service.py covers the happy path for a configured plots reference, not an unknown reference resolving to an existing arbitrary table.

suggested regression test:
Add an API or service test with import.yml containing no users reference and a database table users/ entity_users with extra_data, then assert GET /api/templates/users/enrichment-catalog returns 404 and does not expose catalog fields.

minimum fix scope:
Add reference existence validation for this route/service and a focused regression test for unknown-reference rejection.

repro:
In a project whose import.yml does not declare a users reference, create a SQLite table named users or entity_users with an extra_data column containing api_enrichment payloads. Request GET /api/templates/users/enrichment-catalog. The resolver can select that table and the route returns a catalog instead of rejecting the unknown reference.

## medium: Widget schema generation failures are returned as successful empty schemas

id: fnd_sig-feat-route-e7527d6df8-178414_65f65e93a4
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: FastAPI route GET /widget-schema/{plugin_name} (feat_route_e7527d6df8)
next: clawpatch show --finding fnd_sig-feat-route-e7527d6df8-178414_65f65e93a4

evidence:
- src/niamoto/gui/api/routers/recipes.py:846-859 (_get_widget_schema)
- src/niamoto/gui/api/routers/recipes.py:1191-1194 (get_widget_schema)
- tests/gui/api/routers/test_recipes.py:281-323

For an existing widget, any exception while building the Pydantic JSON schema is logged and then ignored, so the route still returns 200 with the widget name and an empty params object. That violates the route contract of returning the parameter definitions and gives clients no way to distinguish a widget with no parameters from a schema-generation failure. The GUI can then render an incomplete form and produce invalid or incomplete recipe configuration.

recommendation:
Only treat a registry not-found error as a 404. Let schema-generation failures propagate to the route and return a 500, or raise an explicit HTTPException with a clear message such as "Unable to build widget schema".

test analysis:
The linked tests cover successful core widget discovery and arbitrary dict params, but they do not exercise a registered widget whose schema extraction fails.

suggested regression test:
Add a test that registers a widget with a param_schema.model_json_schema method that raises, calls /api/recipes/widget-schema/<name>, and asserts a 500 response rather than a 200 response with empty params.

minimum fix scope:
Update _get_widget_schema/get_widget_schema error handling and add one route-level regression test in tests/gui/api/routers/test_recipes.py.

repro:
Register a WidgetPlugin with a param_schema whose model_json_schema raises, or monkeypatch an existing widget param_schema.model_json_schema to raise RuntimeError, then request GET /api/recipes/widget-schema/<plugin>. The response will be 200 with params: {} instead of an error.

## medium: Widget suggestions still offer measurement widgets for stale identifier-like numeric fields

id: fnd_sig-feat-library-f782651b22-f464_afc73dbe8c
category: bug
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/imports#2 (feat_library_f782651b22)
next: clawpatch show --finding fnd_sig-feat-library-f782651b22-f464_afc73dbe8c

evidence:
- src/niamoto/core/imports/transformer_suggester.py:175-203 (TransformerSuggester._should_skip_measurement_transformer)
- tests/core/imports/test_transformer_suggester.py:129-152 (TestCategoryMapping.test_identifier_like_numeric_profile_skips_measurement_widgets)
- src/niamoto/core/imports/widget_generator.py:247-260 (WidgetGenerator._generate_for_column)
- src/niamoto/core/imports/widget_generator.py:779-796 (WidgetGenerator._calculate_confidence)

TransformerSuggester explicitly blocks binned_distribution and statistical_summary for identifier-like numeric profiles, and the tests document that stale identifier names must not get measurement-oriented transformers. The TemplateSuggester path uses WidgetGenerator instead, where the same fields are only penalized, not skipped. With a foreign-key numeric profile the confidence remains above TemplateSuggester.MIN_CONFIDENCE, so bogus histogram/gauge suggestions can leak into the UI.

recommendation:
Share the identifier-like skip predicate between TransformerSuggester and WidgetGenerator, or add an equivalent guard before creating measurement transformer suggestions.

test analysis:
The existing test asserts the stale identifier guard only on TransformerSuggester. The WidgetGenerator assertion covers only DataCategory.IDENTIFIER, not numeric profiles with identifier-like names or FK/PK purposes.

suggested regression test:
Add a WidgetGenerator or TemplateSuggester test using the idrb_n FOREIGN_KEY numeric profile from test_transformer_suggester and assert no binned_distribution or statistical_summary suggestions are returned.

minimum fix scope:
Add the guard in WidgetGenerator._generate_for_column and cover the stale numeric identifier case.

## medium: Wildcard conditional requests can return 304 before proving the preview exists

id: fnd_sig-feat-route-5f24573c94-66c232_f2ef483762
category: api-contract
confidence: medium
triage: contract-mismatch
status: open
feature: FastAPI route GET /preview/{template_id} (feat_route_5f24573c94)
next: clawpatch show --finding fnd_sig-feat-route-5f24573c94-66c232_f2ef483762

evidence:
- src/niamoto/gui/api/routers/preview.py:92-99 (_if_none_match_matches)
- src/niamoto/gui/api/routers/preview.py:139-143 (get_preview)
- tests/gui/api/routers/test_preview.py:84-101 (TestGetPreview.test_etag_304_accepts_weak_multi_value_and_wildcard)

The GET route treats If-None-Match: * as an unconditional match after computing an ETag from the request, and returns 304 without rendering or otherwise validating that the selected preview representation actually exists. HTTP wildcard matching is only valid when the selected representation exists; for an unknown or non-renderable template_id this can hide the real error behind a 304 and leave clients with stale or missing preview content. The current wildcard test locks in the render-skipping behavior only for a mock happy path, so it does not disprove this edge case.

recommendation:
Do not use the pre-render shortcut for wildcard requests unless the route first validates that the preview exists. The smallest safer change is to only allow exact ETag matches in the pre-render path and let If-None-Match: * fall through to render/validation.

test analysis:
The existing wildcard test uses a MagicMock engine with no missing-template behavior and explicitly asserts render is not called, so it only covers the valid-template cache-hit path.

suggested regression test:
Add a GET /api/preview/missing test with If-None-Match: * where the mock engine would return an error or raise if rendered, then assert the response is not 304 and validation/rendering is reached.

minimum fix scope:
Update _if_none_match_matches/get_preview conditional handling for wildcard ETags and adjust the wildcard test expectation for invalid templates.

repro:
Request GET /api/preview/<missing-template> with header If-None-Match: * while the engine would reject or return an error for that template during render. The route can return 304 before render is called.
