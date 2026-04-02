# Cross-Platform Build & Test Strategy

**Date**: 2026-04-01
**Status**: Validated
**Scope**: Cross-platform build readiness, release gates, and smoke-test procedure
**Part of**: Tauri release readiness (4/4 - security, auto-updater, dependencies, cross-platform)

## Context

Niamoto Desktop has a cross-platform packaging pipeline on paper, but the current repository is not yet ready for a first public release on all targets.

The desktop stack has three packaging layers:

1. Tauri shell (Rust)
2. PyInstaller sidecar (Python / FastAPI)
3. Frontend assets (Vite / React)

Cross-platform failures can come from any of these layers, so the release strategy must validate all three together.

## Current Repo State

- A GitHub Actions workflow exists for macOS arm64, Linux x86_64, and Windows x86_64.
- Linux builds already run on Ubuntu 22.04, which is the correct baseline for better glibc compatibility.
- Tauri still bundles `targets: "all"`, so Linux AppImage is still part of the build output.
- The PyInstaller spec still uses `upx=True`.
- The FastAPI sidecar shutdown path still uses `process.kill()` only.
- macOS-only imports in Rust are correctly guarded with `#[cfg(target_os = "macos")]`, but the related crates still live in the shared dependency section of `Cargo.toml`.
- The desktop workflow installs frontend dependencies but does not run `pnpm build` before `tauri build`.
- The desktop workflow uses Node 18 even though the committed lockfile resolves Vite 7.3.1, which requires a newer Node runtime.

## Release Blockers

### 1. Desktop CI Build Contract Is Incomplete

**Problem**

The current desktop workflow is not aligned with the frontend toolchain:

- it installs frontend dependencies but never runs `pnpm build`
- Tauri expects `frontendDist` to exist
- the workflow still uses Node 18 while the locked Vite version requires Node 20.19+ or 22.12+

**Impact**

This is a more immediate blocker than most platform-specific runtime issues: the workflow can fail before we even reach packaging validation on Linux or Windows.

**Fix**

- Update the desktop workflow to use Node 20 or 22
- Run `pnpm install --frozen-lockfile`
- Run `pnpm build` before the Tauri step
- Treat the generated frontend bundle as part of the release contract

### 2. macOS Public Distribution Still Needs Signing and Notarization

**Problem**

Local macOS builds are not the same thing as a distributable macOS release. The current workflow does not yet model code signing or notarization.

**Impact**

Without signing and notarization, the first public macOS release will trigger Gatekeeper warnings or fail the normal download-and-open path.

**Fix**

- Add Apple signing credentials to the desktop release workflow
- Add notarization for the packaged macOS bundle
- Treat signed + notarized DMG output as a release gate, not a follow-up task

### 3. Sidecar Shutdown Is Not Process-Tree Aware

**Problem**

The Rust shell currently keeps the FastAPI sidecar handle and calls `process.kill()` on shutdown. That only handles the tracked child process, not a whole process tree.

This matters because the PyInstaller bundle can leave child processes behind, which would keep the local port bound and break the next launch.

**Fix**

- Implement platform-aware process-tree shutdown
- On Windows, terminate the full tree
- On Unix, launch the sidecar in its own process group or session first, then terminate that group
- Optionally add a graceful backend shutdown endpoint before the forced kill path

## High Priority Before First Public Release

### 4. Windows Antivirus Friction

**Problem**

The current PyInstaller spec still uses UPX compression. That is a common source of antivirus false positives, especially for one-file Python executables.

**Fix**

- Set `upx=False` in the PyInstaller spec
- Keep the generated sidecar unsigned only for internal testing
- For public distribution, expect Windows reputation and SmartScreen friction until code signing is in place

### 5. Geo / Native Runtime Data Must Be Verified in Packaged Builds

**Problem**

The current spec includes `pyproj`, `duckdb`, and `shapely` imports, but it does not explicitly collect all runtime data and native assets for every problematic package.

The most likely runtime risk is `pyproj` data such as `proj.db`. `duckdb` and `shapely` should be treated as verification targets rather than assumed failures.

**Fix**

- Add explicit `pyproj` data collection to the PyInstaller spec
- Verify DuckDB and Shapely inside packaged Windows and Linux builds
- Only escalate to `collect_all(...)` for those packages if smoke tests show missing native assets

### 6. Linux Distribution Policy Must Be Explicit

**Problem**

The repo still asks Tauri to build all Linux bundle targets, including AppImage, but the release policy for Linux is not decided.

AppImage may still be worth keeping later, but it should not be part of the initial public release unless it is tested and intentionally supported.

**Decision for v1**

- Linux public release target: `.deb`
- AppImage: optional follow-up, not part of the first supported release unless it passes VM validation

**Fix**

- If we defer AppImage, stop building and uploading it in the main release workflow
- Keep Ubuntu 22.04 as the Linux build baseline
- Document runtime expectations for manual installs separately from build dependencies

### 7. Windows WebView2 Policy Should Be Explicit, Not Alarmist

**Problem**

WebView2 is not the main blocker for a Windows 10/11 release. The default Tauri installer behavior is acceptable for connected environments, and modern Windows versions already include the runtime in most supported configurations.

The real question is whether offline installation matters for v1.

**Decision for v1**

- Default path: keep the standard bootstrapper behavior
- If offline installs become a release requirement, switch to `offlineInstaller` or a fixed runtime later

## Platform Notes

### macOS

- macOS-specific runtime code is already behind `#[cfg(target_os = "macos")]`
- The manifest can still be cleaned up by moving `cocoa`, `objc`, and `window-vibrancy` to target-specific dependencies
- Public release quality depends on signing and notarization, not just local success

### Windows

- Main risks are sidecar process cleanup, antivirus reputation, and unsigned distribution warnings
- WebView2 is a policy choice, not the primary release blocker

### Linux

- Ubuntu 22.04 is the correct CI base for now
- `.deb` should be the supported package for v1
- Runtime documentation should talk about user-facing runtime packages, not `-dev` packages used only to build the app

## Smoke Test Checklist

Run this on each supported platform using packaged artifacts, not just local `tauri dev`.

### All Platforms

- [ ] App launches and shows the loading screen
- [ ] FastAPI sidecar starts and answers the health endpoint
- [ ] Existing project opens from the file dialog
- [ ] Main data table renders
- [ ] Plotly charts render
- [ ] Leaflet / map views render
- [ ] CSV import works
- [ ] A transform can be started successfully
- [ ] HTML export completes
- [ ] Window resize and maximize work
- [ ] App closes cleanly and the sidecar does not remain alive

### Windows

- [ ] Installer runs successfully
- [ ] App launches after install
- [ ] Paths with spaces work
- [ ] Paths with accented characters work
- [ ] Coordinate transforms work in packaged mode
- [ ] Restart after close does not fail because of an orphaned backend process

### Linux

- [ ] `.deb` installs cleanly
- [ ] App launches without missing library errors
- [ ] File dialog works
- [ ] Coordinate transforms work in packaged mode
- [ ] No crash from macOS-only desktop code paths

### macOS

- [ ] Vibrancy effect works
- [ ] Overlay title bar works
- [ ] DMG installs cleanly
- [ ] Signed app opens normally
- [ ] Notarized app opens normally after download

## Testing Environment

- Use GitHub Actions artifacts as the source of truth for release builds
- Validate Windows and Linux inside fresh VMs
- Use a real packaged test project, not only trivial launch checks
- Record failures with screenshots and short notes so packaging fixes can be tied to concrete regressions

Suggested procedure:

1. Trigger the desktop build workflow
2. Download packaged artifacts for each target
3. Install in a fresh VM or test machine
4. Copy a known-good sample project
5. Run the smoke checklist
6. Record platform-specific failures

## Files to Modify (Pre-Release)

1. `.github/workflows/build-tauri.yml`
   Update Node version, run `pnpm build`, and add macOS signing/notarization inputs.
2. `build_scripts/niamoto.spec`
   Set `upx=False` and add explicit `pyproj` data collection. Only add broader `collect_all(...)` rules if packaged runtime tests prove they are needed.
3. `src-tauri/src/lib.rs`
   Implement process-tree-aware sidecar shutdown.
4. `src-tauri/tauri.conf.json`
   Narrow Linux bundle targets if AppImage is deferred, and set Windows installer policy only if offline support becomes required.
5. `src-tauri/Cargo.toml`
   Optionally move macOS-only crates to target-specific dependencies for clarity.
6. Desktop installation docs
   Document supported Linux package format and runtime requirements for end users.

## Decision Summary

For the first public release, the practical support target should be:

- macOS arm64, signed and notarized
- Windows x86_64 with documented signing limitations until code signing is in place
- Linux x86_64 as `.deb`

AppImage support can be added later, but it should not stay in the default release path unless it is explicitly tested and supported.
