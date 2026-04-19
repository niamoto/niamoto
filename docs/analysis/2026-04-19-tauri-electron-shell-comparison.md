# Tauri vs Electron Shell Comparison

Date: 2026-04-19
Status: provisional after the initial parallel-shell spike

## What is implemented

- the renderer no longer depends directly on Tauri APIs for its core desktop flows
- desktop runtime detection now reports both `mode` and `shell`
- an experimental Electron shell exists under [electron/](/Users/julienbarbe/Dev/clients/niamoto/electron)
- Electron now mirrors the current desktop startup contract:
  - shared desktop project config
  - Python sidecar on loopback
  - authenticated `/api/health` probe
  - loading state before navigation
  - graceful child-process shutdown
- dedicated local scripts now exist for:
  - development: [scripts/dev/dev_electron.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/dev/dev_electron.sh)
  - packaging: [scripts/build/build_electron.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/build/build_electron.sh)

## Current observations

### 1. Renderer cleanliness improved regardless of the final shell choice

This is already a concrete gain.

- the frontend now targets a shell-neutral desktop bridge
- Tauri-specific updater/runtime code is isolated behind Tauri-only providers
- Electron can reuse the same renderer surface instead of forcing a second UI
  integration path

Current answer to the gate question "Is the renderer materially cleaner once
the desktop bridge exists?": **yes**.

### 2. Electron does not simplify the backend architecture

Electron does not remove the core desktop complexity in Niamoto.

- the app still needs the same Python sidecar
- the shell still needs to resolve a staged sidecar path
- the shell still needs the same authenticated readiness probe
- project switching still depends on the same FastAPI reload endpoint

The complexity moves from Rust/Tauri into Node/Electron. It does not disappear.

Current answer to the gate question "Did Electron reduce startup-path
complexity?": **no clear reduction so far**.

### 3. Electron increases shell and packaging surface area

The repo now carries extra shell-specific work for Electron:

- `main` process code
- `preload` bridge code
- Electron-only package metadata and builder config
- a second development script
- a second packaging script

That is acceptable for a spike. It would become a maintenance cost if both
shells remained first-class for too long.

### 4. The main product question is still only partially answered

Electron was considered because of cross-platform shell uniformity and maturity.
This spike has made Electron operationally plausible, but it has **not yet**
proven the full product case.

What is verified:

- targeted Electron shell unit tests pass locally
- the renderer bridge works without direct Tauri coupling
- the Electron shell can express the same startup contract in code

What is not yet verified in this document:

- stability comparison against the current Tauri build in real packaged runs
- updater parity
- Windows and Linux validation

Current answer to the gate question "Is the Electron shell operationally
credible?": **yes on the initial macOS packaged validation, still incomplete
for broader release confidence**.

## Packaged macOS validation

An actual packaged Electron app was built locally on macOS arm64 from:

- [scripts/build/build_electron.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/build/build_electron.sh)
- [electron/package.json](/Users/julienbarbe/Dev/clients/niamoto/electron/package.json)

The resulting app bundle was:

- [Niamoto Electron.app](/Users/julienbarbe/Dev/clients/niamoto/electron/dist/mac-arm64/Niamoto%20Electron.app)

Observed packaged behavior:

- the packaged Electron executable launched successfully
- the packaged sidecar was started from `Contents/Resources/sidecar/.../niamoto`
- the authenticated desktop health probe returned the expected
  `x-niamoto-desktop-token`
- `/api/health/runtime-mode` returned `{"mode":"desktop","shell":"electron",...}`
- the startup log showed real frontend asset traffic and backend API traffic
  through the packaged loopback server

Measured packaged size after correcting ML model inclusion in the PyInstaller
spec:

- full macOS arm64 app bundle: `644 MB`
- packaged sidecar: `394 MB`
- Electron frameworks: `249 MB`

Corrected Tauri measurement with the same PyInstaller spec:

- full macOS arm64 app bundle: `539 MB`
- packaged DMG: `208 MB`
- sidecar copied before Tauri bundling: `394 MB`
- sidecar inside the final `.app`: `520 MB`

Important correction:

- an earlier `603 MB` Electron measurement was understated because the build was
  still missing the trained ML models from `ml/models`
- the shared PyInstaller spec now packages those models into `ml/models/` in
  the sidecar bundle
- the Tauri bundle expands several sidecar symlinks into real files during
  packaging, notably for `libgdal*`, `libproj*`, `Python`, and `libsqlite3*`
- Electron preserves those symlinks in the packaged app, which keeps the
  packaged sidecar materially smaller on disk than the Tauri-bundled copy of
  the same source sidecar

Concrete local evidence captured during the run:

- startup log:
  [desktop-startup-81874-1776617242271.log](/Users/julienbarbe/Library/Application%20Support/com.niamoto.desktop.electron/logs/desktop-startup-81874-1776617242271.log)
- runtime endpoint returned `shell = electron`
- the probe endpoint returned the desktop token header as expected
- the corrected Tauri app was produced at
  [Niamoto.app](/Users/julienbarbe/Dev/clients/niamoto/src-tauri/target/release/bundle/macos/Niamoto.app)

One runtime warning did appear from the packaged sidecar:

- `Warning 3: Cannot find gdalvrt.xsd (GDAL_DATA is not defined)`

That warning did not prevent the packaged app from loading and serving real UI
and API traffic, but it is worth tracking as a packaging-hardening item for the
geospatial stack.

## Provisional recommendation

At this stage:

- keep Tauri as the production shell
- keep Electron as an experimental parallel shell only
- treat the renderer bridge refactor as a durable improvement either way
- treat the initial macOS packaged startup validation as passed
- require a second hardening pass before any stronger migration recommendation

## Open decision gate

Questions still requiring explicit evidence:

1. Does Electron reduce cross-platform shell-specific uncertainty enough to
   justify its extra runtime and packaging burden?
2. Does packaged Electron startup behave more predictably than packaged Tauri
   on the target desktop OS?
3. Is the additional shell/tooling surface acceptable for a team that still
   has a very large Python sidecar to optimize?

Until those questions are answered with packaged evidence, the sensible default
remains: **Tauri in production, Electron as research**.
