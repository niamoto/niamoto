# clawpatch report

findings: 12

## high: Arbitrary data_source lets callers sample unrelated database tables

id: fnd_sig-feat-route-dc3b2c2d15-11d89f_a4305f9c3e
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /export/{group_by}/index-generator/suggestions (feat_route_dc3b2c2d15)
next: clawpatch show --finding fnd_sig-feat-route-dc3b2c2d15-11d89f_a4305f9c3e

evidence:
- src/niamoto/gui/api/routers/config.py:5010-5013 (suggest_index_fields)
- src/niamoto/gui/api/routers/config.py:5097-5104 (suggest_index_fields)
- src/niamoto/gui/api/routers/config.py:5121-5132 (suggest_index_fields)
- src/niamoto/gui/api/routers/config.py:4293-4303 (_build_index_field_suggestion)

FastAPI exposes the non-path scalar parameter data_source as a query parameter on the public suggestions route. When supplied, the handler uses that value as the only transformed-table candidate, checks only that the table exists, then reads SELECT * from it and serializes inferred field metadata including sample_values. There is no validation that the table belongs to the requested group or to a saved API export group, so a caller who knows any table name in the project database can request /export/{valid_group}/index-generator/suggestions?data_source=<table> and receive sampled values from unrelated tables.

recommendation:
Do not expose data_source on the public route. Split the implementation into a private helper that accepts data_source, and keep the /export/{group_by}/index-generator/suggestions route limited to the default group-derived candidates. For API export suggestions, continue passing the saved group data_source through the wrapper route, but validate it against export.yml or an allowlist of tables owned by that group before reading it.

test analysis:
The provided context test file exercises Config loading and an unrelated transform widget route, not attacker-controlled data_source on this endpoint. Existing route coverage found in the repo checks normal suggestions behavior and saved API export data_source plumbing, but does not assert that an arbitrary query-string data_source is rejected.

suggested regression test:
Create a project fixture with a valid transform group and an unrelated table containing a distinctive value, then assert GET /api/config/export/{group}/index-generator/suggestions?data_source=<unrelated_table> returns 400/404 and does not include that table's field names or sample values.

minimum fix scope:
Route boundary and table selection validation inside src/niamoto/gui/api/routers/config.py, plus a focused FastAPI TestClient regression for arbitrary query data_source rejection.

repro:
With any valid transform group such as taxons and an additional table named private_notes in the configured DuckDB database, call GET /api/config/export/taxons/index-generator/suggestions?data_source=private_notes. If the table exists, the response is built from private_notes columns and sample values instead of the taxons export table.

## high: Concurrent API tests can leave global DNS resolution pinned

id: fnd_sig-feat-route-d59e00f58a-784c32_f98dba42bf
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /test-api (feat_route_d59e00f58a)
next: clawpatch show --finding fnd_sig-feat-route-d59e00f58a-784c32_f98dba42bf

evidence:
- src/niamoto/gui/api/routers/files.py:225-227 (_get_with_pinned_public_dns)
- src/niamoto/gui/api/routers/files.py:244-256 (_get_with_pinned_public_dns)
- tests/gui/api/routers/test_files.py:239-276 (test_test_api_connection_uses_requests_stack)

The original socket.getaddrinfo is captured before acquiring the lock, then restored after the monkeypatch. If a second request enters this function while the first request has socket.getaddrinfo patched, the second request captures the first request's pinned resolver as its original resolver. When the second request finishes, it restores that stale pinned resolver globally, corrupting DNS resolution for the whole process. The linked tests exercise the requests path sequentially and do not create overlapping /test-api calls, so they cannot catch this race.

recommendation:
Capture original_getaddrinfo only after acquiring _PINNED_DNS_REQUEST_LOCK, immediately before assigning socket.getaddrinfo. Prefer replacing the process-wide monkeypatch with a per-request transport/resolver if feasible.

test analysis:
The current tests patch socket.getaddrinfo and requests.get in single-threaded request flows; none overlap two calls while the global resolver is patched.

suggested regression test:
Add a concurrency test that blocks the first _get_with_pinned_public_dns call after it patches socket.getaddrinfo, starts a second call, releases both, and asserts socket.getaddrinfo is restored to the real original function.

minimum fix scope:
Move the original resolver capture inside the locked section in _get_with_pinned_public_dns and add an overlapping-call regression test.

repro:
Issue two overlapping POST /api/files/test-api requests to different hosts. Have the first request block inside requests.get while the second enters _get_with_pinned_public_dns and captures socket.getaddrinfo before it acquires _PINNED_DNS_REQUEST_LOCK. After both complete, socket.getaddrinfo may still be the first request's pinned resolver.

## high: Deploy command exits successfully after streamed deploy errors

id: fnd_sig-feat-cli-command-a6ee60742c-_e9a6ad9ddf
category: build-release
confidence: high
triage: risk
status: open
feature: Python source src/niamoto/cli/commands (feat_cli-command_a6ee60742c)
next: clawpatch show --finding fnd_sig-feat-cli-command-a6ee60742c-_e9a6ad9ddf

evidence:
- src/niamoto/cli/commands/deploy.py:166-167 (deploy_commands)
- src/niamoto/cli/commands/deploy.py:170-188 (_run_deploy)

The CLI deploy path ignores the outcome of the async deploy stream. `_run_deploy` prints `ERROR:` SSE messages but never records failure or raises, and `deploy_commands` does not inspect a return value. A deployer can emit `data: ERROR: ...` followed by `data: DONE`, and `niamoto deploy` will still exit 0, which makes CI/CD or shell scripts treat a failed release as successful.

recommendation:
Have `_run_deploy` return a success boolean or raise `CommandError` when any `ERROR:` message is seen. Then make `deploy_commands` fail the command after the stream ends if a deploy error occurred.

test analysis:
The deploy tests cover pre-flight validation failures that happen before `_run_deploy` is called, and they mock `_run_deploy` as successful for the happy path. There is no test for an `ERROR:` line emitted by the deployer stream itself.

suggested regression test:
Add a CLI test with a fake deployer yielding an `ERROR:` SSE line followed by `DONE`, assert the error is printed and `runner.invoke(deploy_commands).exit_code != 0`.

minimum fix scope:
`src/niamoto/cli/commands/deploy.py` plus one deploy CLI test.

repro:
Use a fake deployer whose `deploy()` async iterator yields `data: ERROR: upload failed\n\n` and then `data: DONE\n\n`; invoke `deploy_commands` with valid config and preflight passing. The output contains the error, but the Click result exits successfully because no exception is raised.

## high: Direct spatial upload filenames can escape the temporary directory

id: fnd_sig-feat-route-536a72b579-ac8466_338f9c4f8f
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /analyze (feat_route_536a72b579)
next: clawpatch show --finding fnd_sig-feat-route-536a72b579-ac8466_338f9c4f8f

evidence:
- src/niamoto/gui/api/routers/files.py:366-367 (analyze_file)
- src/niamoto/gui/api/routers/files.py:637-641 (analyze_shape)
- tests/gui/api/routers/test_files.py:174-197 (test_analyze_shape_zip_rejects_traversal_members)

For spatial uploads ending in .geojson or .gpkg, the route passes the client-controlled multipart filename directly into analyze_shape. analyze_shape then opens temp_path / filename for writing. pathlib discards temp_path for absolute filenames and honors .. segments for relative filenames, so a crafted filename such as /tmp/niamoto-overwrite.geojson or ../../target.gpkg can write or truncate files outside the temporary directory before geopandas reads the file. The tests validate traversal for ZIP member names, but they do not cover traversal through the top-level uploaded filename used by direct spatial uploads.

recommendation:
Reject uploaded filenames that are absolute or contain path separators/.. before passing them to analyzers, or ignore the supplied name for storage and write direct uploads to a fixed generated path using only a validated suffix.

test analysis:
The existing traversal test only exercises ZIP member paths inside _extract_zip_safely. The analyze_file route tests patch analyze_shape, and no test sends a direct .geojson or .gpkg upload with an absolute or parent-relative filename.

suggested regression test:
Add a TestClient test for POST /api/files/analyze with entity_type=shapes and filename='../escape.geojson' or an absolute temporary path, asserting a 400/403-style error and that no file is created or truncated outside the temporary extraction directory.

minimum fix scope:
Validate or replace file.filename for direct spatial uploads in analyze_file/analyze_shape before constructing file_path.

repro:
POST /api/files/analyze with entity_type=shapes and multipart file field using filename="/tmp/niamoto-overwrite.geojson" and valid GeoJSON bytes. The handler writes those bytes to /tmp/niamoto-overwrite.geojson from line 641.

## high: Draft output route can deadlock the event loop under concurrent requests

id: fnd_sig-feat-route-8cf709f416-873f09_23cf595dcc
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /{profile_name}/outputs/{output_type}/draft (feat_route_8cf709f416)
next: clawpatch show --finding fnd_sig-feat-route-8cf709f416-873f09_23cf595dcc

evidence:
- src/niamoto/gui/api/routers/standard_profiles.py:365-371 (execute_standard_profile_output_draft)
- src/niamoto/gui/api/routers/standard_profiles.py:166-178 (_draft_output_lock)

The route acquires a blocking threading.Lock on the async event-loop thread and then awaits threadpool work while still holding that lock. If a second request for the same profile/output reaches `with lock:` while the first request is still awaiting, the second request blocks the event loop in the synchronous lock acquisition. The first request then cannot resume on the event loop to release the lock after its threadpool work completes, so the API can hang for that output and potentially stall unrelated requests handled by the same event loop.

recommendation:
Do not hold a synchronous `threading.Lock` across an `await`. Use an `asyncio.Lock` per draft key and `async with` around the await, or acquire/release the lock inside the worker thread by wrapping the entire synchronous output execution in one function passed to `run_in_threadpool`.

test analysis:
No linked tests were provided for this route, and this failure requires concurrent requests to the same draft endpoint; ordinary single-request handler tests would not expose the event-loop deadlock.

suggested regression test:
Add an async concurrency test that fires two draft-output requests for the same profile/output while stubbing `execute_profile` to block briefly, then asserts both complete within a timeout and execute serially.

minimum fix scope:
Change the draft-output locking implementation for `execute_standard_profile_output_draft` and its per-key lock storage so lock acquisition is non-blocking for the event loop or happens entirely inside the threadpool.

repro:
Start two concurrent POST requests to `/{profile_name}/outputs/{output_type}/draft` for the same existing profile and output type, with the output execution taking long enough for the second request to enter while the first is awaiting. The second request blocks on `threading.Lock.acquire()` in the event loop, preventing the first request from resuming and releasing the lock.

## high: POST /execute/all can run concurrently with active entity imports

id: fnd_sig-feat-route-583b6fcc12-22b7c9_2f1721ad57
category: concurrency
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route POST /execute/all (feat_route_583b6fcc12)
next: clawpatch show --finding fnd_sig-feat-route-583b6fcc12-22b7c9_2f1721ad57

evidence:
- src/niamoto/gui/api/routers/imports.py:306-315 (execute_import_all)
- src/niamoto/gui/api/routers/imports.py:852-856 (process_generic_import_all)
- tests/gui/api/routers/test_imports.py:230-260 (test_execute_import_reference_rejects_active_all_job_for_same_workdir)
- tests/gui/api/routers/test_imports.py:314-345 (test_execute_import_dataset_rejects_concurrent_job_for_same_target)

The all-import route only checks for another active import-all job in the same working directory before creating a new job. It does not reject active reference or dataset imports, even though the all-import worker builds an execution plan containing every configured dataset and reference and can pass reset_table into those imports. The entity routes already treat an active all-import and an active same-target entity import as conflicts, so the intended behavior is to avoid overlapping imports that mutate the same project database. This missing inverse check allows a user to start /execute/all while /execute/dataset/{name} or /execute/reference/{name} is still pending/running, causing duplicate imports or table resets against the same tables.

recommendation:
Make execute_import_all reject any active pending/running import job for the same working directory, not just active import-all jobs. Return 409 with the conflicting job id, matching the existing conflict behavior used by entity imports.

test analysis:
The tests cover duplicate all-import rejection and entity-import rejection while an all-import is active, plus same-target entity rejection. They do not cover the inverse case where an entity import is active and /execute/all is requested.

suggested regression test:
Add a test that seeds import_jobs with a running reference or dataset job for the current working directory, posts to /api/imports/execute/all, and asserts a 409 response with that job id and no new job creation.

minimum fix scope:
Update execute_import_all conflict detection in src/niamoto/gui/api/routers/imports.py and add a focused API router test.

repro:
Start a long-running POST /api/imports/execute/dataset/occurrences job for a working directory, then immediately POST /api/imports/execute/all for the same working directory. The second request passes the current conflict check because there is no active import_type == 'all' job, then its background task includes the active entity in its execution plan.

## high: Project-mutating GUI routers bypass desktop mutation auth

id: fnd_sig-feat-library-26b7b129a9-8718_c72707ad67
category: security
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/gui/api/routers#2 (feat_library_26b7b129a9)
next: clawpatch show --finding fnd_sig-feat-library-26b7b129a9-8718_c72707ad67

evidence:
- src/niamoto/gui/api/desktop_auth.py:11-19 (require_desktop_mutation_auth)
- src/niamoto/gui/api/routers/imports.py:291-299 (execute_import_all)
- tests/gui/api/routers/test_imports.py:297-311 (test_execute_import_dataset_rejects_missing_desktop_auth_before_job_creation)
- src/niamoto/gui/api/routers/site.py:774-840 (update_site_config)
- src/niamoto/gui/api/routers/site.py:2423-2475 (update_file_content)
- src/niamoto/gui/api/routers/smart_config.py:892-957 (create_entities_bulk)
- src/niamoto/gui/api/routers/sources.py:503-633 (save_source_config)
- src/niamoto/gui/api/routers/recipes.py:1395-1424 (save_widget_recipe)
- src/niamoto/gui/api/routers/standard_profiles.py:460-477 (create_standard_profile)

The desktop token is the established guard for GUI mutation endpoints when NIAMOTO_DESKTOP_AUTH_TOKEN is configured, and included tests verify that import and preview mutations reject missing tokens. Several owned routers perform the same class of project mutations without accepting Request or calling require_desktop_mutation_auth: they rewrite export.yml/import.yml/transform.yml, edit content files, upload files, and create/delete publication profiles. With a token configured, unauthenticated requests to these endpoints can still alter project configuration or project files, bypassing the intended desktop-shell mutation boundary.

recommendation:
Add Request parameters or FastAPI dependencies to every project-mutating endpoint in these routers and call require_desktop_mutation_auth before any filesystem/config/database mutation. Keep read-only preview/validation endpoints separate if they are intentionally unauthenticated.

test analysis:
The included auth tests cover imports and preview only. The included sources, recipes, site, layout, smart_config, and standard profile tests exercise successful mutations without setting NIAMOTO_DESKTOP_AUTH_TOKEN, so they do not assert that missing tokens are rejected.

suggested regression test:
For each mutating router, set NIAMOTO_DESKTOP_AUTH_TOKEN, call one representative write endpoint without x-niamoto-desktop-token, assert 401, and assert the target config/file remains unchanged; add a matching valid-token test for one endpoint per router.

minimum fix scope:
Guard the write endpoints in src/niamoto/gui/api/routers/site.py, smart_config.py, sources.py, layout.py, recipes.py, and standard_profiles.py with desktop mutation auth, then add focused auth regression tests for those routers.

repro:
Set NIAMOTO_DESKTOP_AUTH_TOKEN=desktop-secret and start the GUI API. Send PUT /api/site/config, PUT /api/site/file-content, POST /api/smart/management/entities/bulk, POST /api/sources/{reference}/save, POST /api/recipes/save, or POST /api/standard-profiles without x-niamoto-desktop-token. The handlers have no auth dependency and proceed to write project files instead of returning 401.

## high: Raster-based transformers mask and rasterize with geometries in the input GeoDataFrame CRS instead of the raster CRS

id: fnd_sig-feat-library-7e7ea31318-146d_7473dcb3aa
category: bug
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/plugins/transformers/ecological (feat_library_7e7ea31318)
next: clawpatch show --finding fnd_sig-feat-library-7e7ea31318-146d_7473dcb3aa

evidence:
- src/niamoto/core/plugins/transformers/ecological/elevation_profile.py:147-150 (ElevationProfile.transform)
- src/niamoto/core/plugins/transformers/ecological/forest_elevation.py:204-211 (ForestElevationAnalysis.transform)
- src/niamoto/core/plugins/transformers/ecological/forest_holdridge.py:171-175 (ForestHoldridgeAnalysis.transform)

These transformers read a raster and immediately pass the input GeoDataFrame geometry to rasterio.mask. They only reproject vector overlay layers to data.crs later, but never reproject the analysis geometry or rasterized overlay geometries to src.crs. When an AOI GeoDataFrame and DEM/Holdridge raster use different CRSs, rasterio interprets coordinates in the raster CRS, producing empty masks or silently wrong elevation/zone distributions.

recommendation:
Inside each rasterio.open block, compare data.crs to src.crs and reproject the analysis geometry to src.crs before mask. Any vector layer that is rasterized onto mask_transform should also be clipped/rasterized in the raster CRS, while returned metadata can still reference the original analysis CRS as needed.

test analysis:
Existing tests use matching CRS for the raster mask path, or mock rasterio.mask without asserting CRS conversion. The elevation profile tests cover forest vector CRS mismatch, but not raster CRS mismatch.

suggested regression test:
Create an AOI in EPSG:4326 and a small DEM/Holdridge raster in a projected CRS over the equivalent area. Assert the transformer reprojects the AOI and returns the same bin/zone counts as a pre-projected AOI.

minimum fix scope:
Update ElevationProfile, ForestElevationAnalysis, and ForestHoldridgeAnalysis raster masking/rasterization paths to operate in raster CRS.

## high: Read-only SQL endpoint can read local server files through DuckDB table functions

id: fnd_sig-feat-route-cfa70199e4-d114ff_c15245808f
category: security
confidence: high
triage: confirmed-bug
status: open
feature: FastAPI route GET /query (feat_route_cfa70199e4)
next: clawpatch show --finding fnd_sig-feat-route-cfa70199e4-d114ff_c15245808f

evidence:
- src/niamoto/gui/api/routers/database.py:427-451 (execute_query)
- src/niamoto/gui/api/routers/database.py:459-466 (execute_query)
- tests/gui/api/routers/test_database_routes.py:327-400 (test_query_endpoint_rejects_mutation_and_multistatement_sql_before_opening_db)

The route treats a query as safe when it starts with SELECT/WITH and does not contain mutation keywords or comment/multistatement tokens, then executes it as raw SQL. On DuckDB, read-only database mode prevents database writes but does not prevent SELECT table functions such as read_csv_auto('/path') from reading process-readable local files. I verified the same SELECT * FROM (...) LIMIT wrapper accepts read_csv_auto('/etc/hosts'), so a network caller can exfiltrate local files while passing the current safety checks.

recommendation:
Do not expose unrestricted SQL here. Replace the endpoint with a structured allow-listed query API, or parse/validate SQL against an allow-list of project tables, columns, and harmless expressions. Explicitly reject DuckDB table/file/network functions and other external-access statements, and prefer engine-level settings that disable external access where available.

test analysis:
The route tests cover mutation keywords, multistatement/comment rejection, and that DuckDB is opened read-only. They do not test safe-looking SELECT statements that access files through DuckDB table functions; tests/common/test_database.py only exercises the lower-level Database wrapper.

suggested regression test:
Add a GUI route test that submits SELECT * FROM read_csv_auto('<tmp secret file>') with limit=1 and asserts the endpoint rejects it before returning file contents.

minimum fix scope:
Harden execute_query validation/authorization and add targeted route regression tests for DuckDB external file-access functions.

repro:
GET /api/database/query?query=SELECT%20*%20FROM%20read_csv_auto('/etc/hosts')&limit=1 returns local file content on a DuckDB-backed project.

## high: reset_table can drop an existing reference before validating the replacement source

id: fnd_sig-feat-library-14deaaa145-0d9a_0edf608bcc
category: data-loss
confidence: high
triage: confirmed-bug
status: open
feature: Python source src/niamoto/core/services (feat_library_14deaaa145)
next: clawpatch show --finding fnd_sig-feat-library-14deaaa145-0d9a_0edf608bcc

evidence:
- src/niamoto/core/services/importer.py:103-106 (ImporterService.import_reference)
- src/niamoto/core/services/importer.py:173-184 (ImporterService.import_reference)
- tests/core/services/test_importer.py:116-153

For direct file references, import_reference drops the existing target table as soon as reset_table is true, before checking that connector.path is present and that the replacement file exists. A stale or mistyped path therefore deletes the existing reference table and then raises FileReadError, leaving the project without its prior data. The dataset path validates the file before dropping, so this is an inconsistent and avoidable data-loss path. The same early drop also affects derived and multi-feature references before their prerequisites are validated.

recommendation:
Move the reset drop until after connector-specific validation succeeds. For direct references, validate connector.path and source_path.exists() first; for derived references, resolve the source entity first; for multi-feature references, validate/resolve source files first. Then drop immediately before invoking the import engine.

test analysis:
The linked tests cover reset_table with a valid file and missing-file handling without reset_table, but they never combine reset_table=True with an invalid replacement source.

suggested regression test:
Add a test where service.db.has_table returns True, the reference source path is missing, and reset_table=True; assert FileReadError is raised and service.db.execute_sql is not called.

minimum fix scope:
Reorder validation and table reset inside ImporterService.import_reference.

repro:
Configure a direct reference whose existing table entity_sites exists, call import_reference('sites', config_with_missing_path, reset_table=True), and observe DROP TABLE is executed before FileReadError is raised.

## high: Delete can drop the wrong table when dataset and reference share a name

id: fnd_sig-feat-route-52ffc99d21-9f4595_0e716b481d
category: data-loss
confidence: medium
triage: risk
status: open
feature: FastAPI route DELETE /entities/{entity_type}/{entity_name} (feat_route_52ffc99d21)
next: clawpatch show --finding fnd_sig-feat-route-52ffc99d21-9f4595_0e716b481d

evidence:
- src/niamoto/gui/api/routers/imports.py:590-604 (delete_entity)
- src/niamoto/gui/api/routers/imports.py:606-613 (delete_entity)
- tests/gui/api/routers/test_imports.py:701-755 (test_delete_dataset_fallback_drops_dataset_table_not_reference_collision)

The route trusts the registry table name for entity_name before considering the requested entity_type. If import.yml contains both a dataset and a reference with the same name, and the registry entry for that name points at the other kind's table, DELETE /entities/dataset/plots?delete_table=true will drop the registry table first and stop before reaching the dataset-specific fallback. The included fallback collision test shows the intended behavior is to avoid dropping the reference table when deleting the dataset, but it only covers the no-registry path.

recommendation:
Only use registry metadata when entity_meta.kind matches the requested entity_type. If it does not match, ignore that registry table for this deletion and fall back to the type-specific table names, or change registry lookup to be keyed by both name and kind.

test analysis:
The current tests cover the same-name dataset/reference collision only when registry lookup is absent, so they do not exercise the higher-priority registry table path that can point at the wrong kind.

suggested regression test:
Add a delete_entity test with both dataset and reference named 'plots', a fake registry returning kind=EntityKind.REFERENCE/table_name='reference_plots', and fake DB tables for both names. Assert deleting the dataset drops only 'dataset_plots' and leaves the reference config entry intact.

minimum fix scope:
Update delete_entity table-name selection in src/niamoto/gui/api/routers/imports.py and add one focused API/router regression test.

repro:
Create import.yml with both entities.datasets.plots and entities.references.plots. Make the registry return kind=reference, table_name='reference_plots' for name 'plots', and have both reference_plots and dataset_plots exist. Call delete_entity(..., 'dataset', 'plots', delete_table=True). The current code drops reference_plots and removes only the dataset config entry.

## high: Filtered HTML exports can delete an unowned group directory

id: fnd_sig-feat-library-db85b6eec6-946b_ef0364dd47
category: data-loss
confidence: medium
triage: risk
status: open
feature: Python source src/niamoto/core/plugins/exporters (feat_library_db85b6eec6)
next: clawpatch show --finding fnd_sig-feat-library-db85b6eec6-946b_ef0364dd47

evidence:
- src/niamoto/core/plugins/exporters/html_page_exporter.py:465-483 (HtmlPageExporter.export)
- src/niamoto/core/plugins/exporters/html_page_exporter.py:1413-1423 (HtmlPageExporter._process_groups)
- tests/core/plugins/exporters/test_html_page_exporter.py:1528-1547 (test_export_with_group_filter_no_clear)

Full HTML exports validate an existing output directory with an ownership marker before recursive deletion, but filtered exports skip that validation and later delete output_dir/group_by directly when the filtered group matches. Because export creates the root marker before _process_groups, an arbitrary configured output_dir can become marked during a filtered run and then have a pre-existing group-named subdirectory removed without proving that subdirectory was produced by Niamoto. The linked test only proves a sibling file in the root survives; it does not cover the targeted group directory deletion path.

recommendation:
Apply the same ownership check before clearing a filtered group directory, or create/check a per-group ownership marker before allowing shutil.rmtree. At minimum, refuse filtered clearing unless the export root was already marked before the current run and the target group directory is inside that marked root.

test analysis:
The existing group-filter test asserts that a root-level file is preserved, but it does not create a populated group subdirectory and verify it is protected when unowned.

suggested regression test:
Create output_dir/taxon/important.txt without a group ownership marker, run HtmlPageExporter.export with group_filter="taxon", and assert a ProcessError is raised and the file still exists.

minimum fix scope:
HTML exporter filtered group-directory clearing logic.

repro:
Configure an HTML export with output_dir pointing at an existing directory that contains a non-Niamoto subdirectory named like the group, for example output/taxon, then run export(..., group_filter="taxon"). _process_groups will call shutil.rmtree(output/taxon).
