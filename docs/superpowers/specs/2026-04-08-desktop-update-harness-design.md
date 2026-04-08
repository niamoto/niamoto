# Desktop Update Harness

## Goal

Add a reusable local harness to validate the real desktop auto-update flow on macOS:

- build a source app version
- build a newer target app version
- expose a local Tauri updater endpoint for the target version
- launch the source app against that local endpoint
- verify whether the app reaches the expected final version after update

The harness is meant to answer one concrete question reliably: does a desktop update succeed end-to-end, including the relaunch step?

## Problem Summary

The current repository can build desktop artifacts and can launch the app in development mode, but it cannot easily reproduce the actual updater workflow locally.

`cargo tauri dev` and [scripts/dev/dev_desktop.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/dev/dev_desktop.sh) do not test:

- updater version detection
- updater artifact download
- installation of a newer bundle
- app relaunch after installation

This leaves regressions in the update flow hard to confirm. The recent `Importing a module script failed` error during relaunch is exactly the kind of issue that needs a real update harness, not a dev-mode restart.

## Chosen Direction

Build a macOS-only semi-automatic harness under [scripts/dev](/Users/julienbarbe/Dev/clients/niamoto/scripts/dev):

- it prepares isolated `from` and `to` build workspaces
- it overrides version numbers and updater endpoint only inside those temporary workspaces
- it builds two real desktop artifacts
- it serves the target updater metadata and signed artifact from a local HTTP server
- it launches the source app and tells the operator when to click `Install`
- it records enough output to confirm whether the app ended up on the target version

The harness intentionally stops short of UI automation. The install click remains manual in the first version.

## Rejected Alternatives

### Reusing `cargo tauri dev`

Rejected because it does not exercise the updater plugin or the post-install relaunch path.

### Full UI automation

Rejected for the first version because it is much more fragile than the underlying updater test. The first goal is to validate the update pipeline itself, not automate every click.

### Editing tracked repo files in place

Rejected because it would create unnecessary churn in versioned config files and make failures harder to clean up. The harness should operate in isolated temporary workspaces.

## Scope

### In Scope

- macOS local update testing
- source and target desktop builds created by the harness
- local updater endpoint
- source app launch
- final version verification
- saved logs and artifacts for debugging

### Out of Scope

- Windows or Linux update harness support
- GitHub release publication
- fully automated UI clicking
- notarization or distribution concerns outside local testing

## User Workflow

The intended flow is:

1. Run a script such as [scripts/dev/test_desktop_update.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/dev/test_desktop_update.sh).
2. Provide `from` and `to` versions, or accept defaults such as `0.13.0-test` and `0.13.1-test`.
3. Let the harness build both app versions in isolated directories.
4. Let the harness start a small local HTTP server that exposes the target updater manifest and artifact.
5. The harness launches the source app.
6. The operator clicks `Install` in the app when the update is offered.
7. The harness reports:
   - whether the update was detected
   - whether the app relaunch reached the target version
   - where to find logs and generated artifacts

## Architecture

### Temporary Workspaces

The harness creates two isolated workspaces under `/tmp`:

- `from-workspace`
- `to-workspace`

Each workspace is a copy of the repository or a minimized build-ready tree. Version overrides and updater endpoint overrides happen only there.

This avoids mutating tracked files in the main checkout.

### Version Overrides

The harness updates at least:

- [src-tauri/tauri.conf.json](/Users/julienbarbe/Dev/clients/niamoto/src-tauri/tauri.conf.json)
- [pyproject.toml](/Users/julienbarbe/Dev/clients/niamoto/pyproject.toml)

inside the temporary workspaces so both builds expose distinct app versions.

The source workspace points its updater endpoint to the local harness server, not GitHub Releases.

### Build Outputs

The harness builds:

- a source `.app`
- a target updater artifact plus local updater metadata

The exact artifact names are not assumed in the design. The script should discover them from Tauri build outputs rather than hardcode platform-specific filenames more than necessary.

### Local Updater Server

The harness serves the target updater metadata and artifact from a local HTTP server bound to `127.0.0.1` on a chosen port.

The server only needs to expose:

- updater manifest
- signed artifact file
- signature file if required by the manifest format

This keeps the harness close to the real updater contract while staying entirely local.

## Verification Strategy

The first version of the harness verifies success through observable version state, not UI automation.

Primary success criterion:

- after the install flow and relaunch, the running app reports the target version

Secondary indicators:

- update becomes available in the source app
- target version is present in served metadata
- logs do not show updater download or relaunch errors

The harness should print a clear summary with pass/fail checkpoints.

## Logging and Artifacts

The harness should retain:

- local server logs
- build logs for `from` and `to`
- resolved updater metadata path
- generated artifact paths
- source app launch logs when available

All paths should be printed at the end so failures can be debugged without rerunning blindly.

## Failure Modes

The harness should fail early and explicitly when:

- the source build fails
- the target build fails
- updater metadata cannot be found or generated
- the local server cannot start
- the source app cannot launch
- the final version cannot be observed within the expected window

Each failure should point to the relevant log path.

## Implementation Notes

- Keep the first version as a shell script plus small helper snippets if that is sufficient.
- Prefer existing repo tooling and current Tauri build outputs over inventing a separate build system.
- Keep macOS-specific assumptions explicit inside the script rather than hiding them behind generic names.
- Make the harness safe to rerun by cleaning up or isolating ports and temp directories predictably.

## Testing

### Manual

- run the harness end-to-end on macOS
- confirm the source app sees the local update
- click `Install`
- confirm the app relaunches to the target version

### Automated

At minimum:

- basic smoke test for script argument validation if helper logic is extracted
- documentation update for how to use the harness

The harness itself is primarily an integration tool, so the real validation remains the end-to-end local run.
