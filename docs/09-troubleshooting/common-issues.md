# Common Issues

Use this page for the most common CLI, import, collections, publish, and desktop
startup failures.

## CLI or environment problems

If `niamoto` is not available, first confirm the active environment:

```bash
uv run niamoto --help
```

If that fails, check that the project environment is installed and active.

## Missing project or config files

If a command cannot find `config.yml`, `import.yml`, `transform.yml`, or
`export.yml`, make sure you are running from the project root and that the files
exist in the expected config directory.

## Import failures

Typical causes:

- wrong input paths
- mismatched identifiers
- columns that no longer match the config

Start with [Import workflow](../02-user-guide/import.md), then recheck
[configuration-guide.md](../06-reference/configuration-guide.md).

## Collections or transform failures

Typical causes:

- a plugin name changed
- a required parameter is missing
- a group references data that import never created

Start with [Collections](../02-user-guide/collections.md), then review
[plugin-api.md](../06-reference/plugin-api.md).

## Publish or export failures

Typical causes:

- export targets reference missing transformed data
- widget or template configuration drifted
- publish output paths are wrong

Start with [Publish](../02-user-guide/publish.md), then review
[api-export-guide.md](../06-reference/api-export-guide.md).

## Desktop startup issues

If the desktop app refuses to start or preview properly:

### macOS Gatekeeper

If macOS blocks the app on first launch:

1. right-click the app or installer and choose *Open*
2. if needed, open *System Settings -> Privacy & Security*
3. click *Open Anyway* for the blocked Niamoto build

### Windows startup or blank UI

If the app launches but the UI stays blank or fails early:

1. rerun the installer to restore the embedded runtime
2. make sure Windows is up to date so the bundled WebView2 runtime can start cleanly
3. check that the app reaches the main UI instead of stopping on a blank window

### Linux `.AppImage` and native dependencies

If the `.AppImage` does not start:

1. make sure it is executable:

   ```bash
   chmod +x niamoto_*_amd64.AppImage
   ./niamoto_*_amd64.AppImage
   ```

2. if startup still fails, verify that the host has the native GIS libraries the
   desktop bundle expects
3. compare the machine against the [desktop smoke tests](desktop-smoke-tests.md)

### Project path and writable directories

If startup succeeds but the app cannot open a project correctly:

1. check that the selected project path exists
2. confirm the app can write to `config/`, `db/`, `exports/`, and `logs/`
3. verify that the GUI backend can read the active instance

## Go to the code when

If the issue is clearly tied to a plugin implementation, API route, or service,
switch from docs to the relevant source directory under `src/niamoto/`.
