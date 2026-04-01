---
title: Tauri Desktop Release Readiness
type: feat
date: 2026-04-01
---

# Tauri Desktop Release Readiness

## Overview

Prepare the Niamoto Tauri desktop app for its first public release across macOS, Windows, and Linux.

This plan consolidates 4 validated brainstorms into an execution order that is safe to follow:

- fix the desktop build contract first
- harden the Tauri shell without overselling what it protects
- stabilize the PyInstaller sidecar
- wire signing before any public updater release path
- validate the updater between two real packaged versions
- only then enable the public tag-based release flow

**Source brainstorms:**
- `docs/brainstorms/2026-04-01-tauri-security-pre-release-brainstorm.md`
- `docs/brainstorms/2026-04-01-tauri-auto-updater-brainstorm.md`
- `docs/brainstorms/2026-04-01-tauri-dependency-audit-brainstorm.md`
- `docs/brainstorms/2026-04-01-tauri-cross-platform-brainstorm.md`

## Architecture Reminder

```text
Tauri shell (Rust)
    -> spawns PyInstaller sidecar (Python/FastAPI) on localhost
    -> loads React frontend in WebView
    -> after boot, navigates to http://127.0.0.1:<port>
```

The Tauri shell CSP protects the bootstrap phase only. After navigation to localhost, the FastAPI-served pages are outside the Tauri custom-protocol security boundary.

## Release Rule

Do not enable the public tag-triggered release flow until:

1. signed desktop artifacts build successfully
2. macOS signing and notarization are working
3. the updater has been tested between two real packaged versions
4. VM smoke tests pass on the supported platforms

Public release cutover is the last phase of this plan, not the middle.

## Implementation Phases

### Phase 1: Fix Desktop CI Build Contract

The current desktop workflow is the first blocker:

- Node 18 is too old for the committed Vite lockfile
- frontend dependencies are installed, but `pnpm build` is never run before `tauri build`

Nothing else is worth validating until CI produces working artifacts on all target platforms.

#### 1.1 Update Node version in CI

**File:** `.github/workflows/build-tauri.yml`

```yaml
# Before
- uses: actions/setup-node@v6
  with:
    node-version: '18'

# After
- uses: actions/setup-node@v6
  with:
    node-version: '22'
```

Node 20 would also be acceptable. The point is to meet the Vite 7 lockfile requirement.

#### 1.2 Add frontend build step

**File:** `.github/workflows/build-tauri.yml`

Add after the frontend dependency install step:

```yaml
- name: Build frontend
  run: cd src/niamoto/gui/ui && pnpm run build
```

#### 1.3 Validate

Trigger the workflow manually on GitHub Actions.

**Acceptance criteria:**
- [ ] macOS-arm64 build succeeds
- [ ] Linux-x86_64 build succeeds
- [ ] Windows-x86_64 build succeeds
- [ ] artifacts are uploaded for all 3 matrix jobs

---

### Phase 2: Shell Security Hardening

This phase hardens the Tauri shell. It does not secure the FastAPI pages after navigation to localhost.

#### 2.1 Add restrictive shell CSP

**File:** `src-tauri/tauri.conf.json`

```json
"security": {
  "csp": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' http://localhost:* http://127.0.0.1:*; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'"
}
```

Notes:

- this CSP is for the bootstrap shell only
- do not add `https://*`
- if Vite HMR needs a different policy in development, add `devCsp` separately instead of weakening release CSP

#### 2.2 Remove the release devtools feature

**File:** `src-tauri/Cargo.toml`

```toml
# Before
tauri = { version = "2.9.2", features = ["devtools"] }

# After
tauri = { version = "2.9.2", features = [] }
```

This is the release hardening step that matters for devtools exposure.

#### 2.3 Optional cleanup: devtools capability and config

**Files:**
- `src-tauri/capabilities/default.json`
- `src-tauri/tauri.conf.json`

Optional cleanup, not a release blocker:

- remove `core:webview:allow-internal-toggle-devtools`
- remove explicit `app.windows[].devtools: true` if it is no longer useful

Only do this in the same PR if it does not slow down debugging or confuse local development.

#### 2.4 Optional defense-in-depth: freezePrototype

**File:** `src-tauri/tauri.conf.json`

If desired, add:

```json
"freezePrototype": true
```

Treat this as shell-only defense-in-depth. Do not present it as the main mitigation for the localhost-served app.

#### 2.5 Validate

```bash
cd src-tauri && cargo check
```

Then verify:

- `tauri dev` still launches in development
- the bootstrap shell still loads and navigates to the local app
- the release CSP does not break the boot path

**Acceptance criteria:**
- [ ] `cargo check` passes
- [ ] `tauri dev` still works
- [ ] shell bootstrap still loads and hands off to localhost correctly
- [ ] release build no longer depends on the `devtools` Cargo feature

---

### Phase 3: PyInstaller and Sidecar Robustness

Fix the packaging issues that are most likely to break packaged builds or leave the desktop app in a bad state after close.

#### 3.1 Disable UPX compression

**File:** `build_scripts/niamoto.spec`

```python
# Before
upx=True,

# After
upx=False,
```

This reduces a common source of Windows antivirus false positives.

#### 3.2 Add explicit pyproj data collection

**File:** `build_scripts/niamoto.spec`

Update imports:

```python
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
```

Then add after the metadata block:

```python
# Include pyproj coordinate reference data such as proj.db
datas += collect_data_files('pyproj')
```

#### 3.3 Set a shorter Windows runtime temp directory

**File:** `build_scripts/niamoto.spec`

```python
# Before
runtime_tmpdir=None,

# After
runtime_tmpdir=None if sys.platform != 'win32' else os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'niamoto'),
```

#### 3.4 Implement process-tree-aware shutdown

**File:** `src-tauri/src/lib.rs`

Replace the current close handler with platform-aware shutdown logic.

Implementation requirements:

- Windows: kill the full process tree
- Unix: launch the sidecar in its own process group or session, then terminate that group
- keep a final fallback `kill()` path if the graceful or grouped shutdown fails

If using Unix process-group signaling, update `launch_fastapi_server` so the sidecar is started in its own group before relying on negative-PID kills.

#### 3.5 Optional manifest cleanup: move macOS-only crates

**File:** `src-tauri/Cargo.toml`

Move these from shared dependencies to a target-specific section:

```toml
[target.'cfg(target_os = "macos")'.dependencies]
window-vibrancy = "0.7"
cocoa = "0.26"
objc = "0.2"
```

This is mainly a clarity improvement. The runtime code is already guarded with `#[cfg(target_os = "macos")]`.

#### 3.6 Validate

```bash
cd src-tauri && cargo check
uv run pyinstaller build_scripts/niamoto.spec --clean --noconfirm
```

**Acceptance criteria:**
- [ ] `cargo check` passes
- [ ] PyInstaller build succeeds
- [ ] packaged sidecar starts and stops cleanly
- [ ] coordinate transforms work in packaged mode

---

### Phase 4: Release Credentials and Signed Build Foundations

Before enabling the updater in a public release flow, wire the credentials and CI inputs needed for signed builds.

Do not add a public tag-triggered release in this phase.

#### 4.1 Generate updater signing keys

```bash
cargo tauri signer generate -w ~/.tauri/niamoto.key
```

Then:

1. store the private key securely
2. add `TAURI_SIGNING_PRIVATE_KEY` to GitHub repo secrets
3. add `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` to GitHub repo secrets
4. keep the public key content for `tauri.conf.json`

Losing the private key means installed apps will not trust future updates.

#### 4.2 Prepare Apple signing and notarization secrets

Add the Apple credentials needed by Tauri signing/notarization to GitHub secrets:

- `APPLE_CERTIFICATE`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_SIGNING_IDENTITY`
- `APPLE_ID`
- `APPLE_PASSWORD`
- `APPLE_TEAM_ID`

#### 4.3 Pass signing secrets to the desktop workflow

**File:** `.github/workflows/build-tauri.yml`

Update the `tauri-action` environment so manual builds already run with the signing inputs:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
  TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}
  APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
  APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
  APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
  APPLE_ID: ${{ secrets.APPLE_ID }}
  APPLE_PASSWORD: ${{ secrets.APPLE_PASSWORD }}
  APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
```

#### 4.4 Keep release publication manual for now

Stay on `workflow_dispatch` while implementing and testing.

Do not enable:

- `push.tags`
- `releaseDraft: false`
- a public updater-dependent stable release flow

That cutover happens in Phase 7, after smoke tests and updater validation.

#### 4.5 Validate

Run the desktop workflow manually with signing secrets in place.

**Acceptance criteria:**
- [ ] manual desktop build still succeeds on all target platforms
- [ ] updater signing inputs are accepted by CI
- [ ] macOS artifact is signed
- [ ] macOS notarization path is working or clearly identified as the remaining blocker

---

### Phase 5: Auto-Updater Implementation and Staged Validation

This phase depends on:

- Phase 1: working desktop CI artifacts
- Phase 2: shell hardening in place
- Phase 4: updater signing keys and signing-capable workflow

#### 5.1 Add Rust dependencies

**File:** `src-tauri/Cargo.toml`

```toml
tauri-plugin-updater = "2"
tauri-plugin-process = "2"
```

#### 5.2 Register plugins in Rust

**File:** `src-tauri/src/lib.rs`

Register the process plugin in the builder chain and the updater plugin during setup.

#### 5.3 Add capabilities

**File:** `src-tauri/capabilities/default.json`

Add:

```json
"updater:default",
"process:default"
```

#### 5.4 Configure updater in Tauri config

**File:** `src-tauri/tauri.conf.json`

Add:

```json
"bundle": {
  "createUpdaterArtifacts": true
}
```

And:

```json
"plugins": {
  "updater": {
    "pubkey": "<PUBLIC_KEY_FROM_PHASE_4.1>",
    "endpoints": [
      "https://github.com/niamoto/niamoto/releases/latest/download/latest.json"
    ],
    "windows": {
      "installMode": "passive"
    }
  }
}
```

#### 5.5 Add frontend dependencies

```bash
cd src/niamoto/gui/ui && pnpm add @tauri-apps/plugin-updater @tauri-apps/plugin-process
```

#### 5.6 Implement desktop updater UI

Create:

- `src/niamoto/gui/ui/src/shared/desktop/updater/useAppUpdater.ts`
- `src/niamoto/gui/ui/src/shared/desktop/updater/UpdateBanner.tsx`

Mount the banner in:

- `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`

Implementation requirements:

- no-op in web mode
- check for updates after a short delay, then on an interval
- display update availability, download progress, and error state
- relaunch after successful install

#### 5.7 Validate updater code locally

**Acceptance criteria:**
- [ ] `cargo check` passes
- [ ] updater plugin registers without startup errors
- [ ] banner renders only in desktop mode
- [ ] web mode is unaffected

#### 5.8 Run one staged end-to-end updater test

Before enabling the public release flow, validate the updater between two real packaged versions.

Recommended approach:

1. produce a first signed packaged build and install it on a test machine
2. publish a newer signed packaged build to a staging destination or temporary non-production release path
3. verify the app detects the newer version
4. verify download, install, and relaunch
5. verify the app opens correctly after the update

The exact staging mechanism can be:

- a temporary test release sequence in the main repo before public announcement
- or a separate staging repository / endpoint if one is available

The important point is that updater validation must happen before the stable public release path is enabled.

**Acceptance criteria:**
- [ ] an installed older build detects a newer signed build
- [ ] download and install complete successfully
- [ ] app relaunches successfully after install
- [ ] the updated app opens and works normally

---

### Phase 6: Dependency Audit and Security CI

This phase can run in parallel with Phase 5 once the base desktop build is healthy.

#### 6.1 Create a dedicated Rust audit workflow

**File:** `.github/workflows/dependency-audit.yml` (new)

```yaml
name: Rust Dependency Audit

on:
  pull_request:
    paths:
      - "src-tauri/Cargo.toml"
      - "src-tauri/Cargo.lock"
  push:
    branches: [main]
    paths:
      - "src-tauri/Cargo.toml"
      - "src-tauri/Cargo.lock"

jobs:
  rust-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - uses: actions-rust-lang/audit@v1
        with:
          workingDirectory: src-tauri
```

#### 6.2 Re-run audits from lockfiles

Before release, run:

```bash
cd src/niamoto/gui/ui && pnpm audit --prod
cd src-tauri && cargo audit
```

Use lockfile state as the source of truth. Do not change manifest versions based on stale notes.

**Acceptance criteria:**
- [ ] Rust audit workflow triggers on Cargo changes
- [ ] no critical runtime vulnerabilities in `pnpm audit --prod`
- [ ] no critical advisories in `cargo audit`

---

### Phase 7: Distribution Policy, Smoke Tests, and Public Release Cutover

This is the final gate. It depends on all earlier phases.

#### 7.1 Set Linux public distribution policy

For v1:

- support Linux x86_64 as `.deb`
- remove AppImage from the public release path

**File:** `src-tauri/tauri.conf.json`

Update bundle targets to drop AppImage while keeping the Windows installer formats needed for evaluation:

```json
"targets": ["dmg", "app", "deb", "msi", "nsis"]
```

Also update the artifact upload step in `.github/workflows/build-tauri.yml` to stop publishing `*.AppImage` in the main release path.

#### 7.2 Make an explicit Windows installer decision

Before public release, choose one supported Windows installer format for v1.

Use VM validation to compare:

- install success
- updater behavior
- antivirus / reputation friction
- user-facing installation experience

Until that decision is made, building both `msi` and `nsis` for internal validation is acceptable. Public support should name one format, not both by accident.

#### 7.3 Run packaged smoke tests on supported platforms

Use GitHub Actions artifacts as the source of truth for release builds.

Suggested test project:

- `test-instance/niamoto-test/`

For each supported platform:

1. download the packaged artifact from CI
2. install it on a fresh VM or test machine
3. copy a known-good test project
4. run the smoke checklist
5. record failures with screenshots and short notes

**All platforms:**
- [ ] app launches and shows the loading screen
- [ ] FastAPI sidecar starts and health endpoint responds
- [ ] test project opens from the file dialog
- [ ] data table renders
- [ ] Plotly chart renders
- [ ] map view renders
- [ ] CSV import works
- [ ] transform executes
- [ ] HTML export completes
- [ ] window resize/maximize works
- [ ] app closes cleanly and the sidecar does not remain alive

**Windows:**
- [ ] chosen installer format installs successfully
- [ ] paths with spaces work
- [ ] paths with accented characters work
- [ ] coordinate transforms work in packaged mode
- [ ] restart after close does not fail because of an orphaned backend process

**Linux:**
- [ ] `.deb` installs cleanly
- [ ] no missing library errors
- [ ] file dialog works
- [ ] coordinate transforms work in packaged mode

**macOS:**
- [ ] signed app opens normally
- [ ] notarized app opens normally after download
- [ ] vibrancy and overlay title bar work

#### 7.4 Confirm updater behavior on the supported release path

If Phase 5 used a temporary staging destination, repeat one final updater test using the same release path shape that production will use.

**Acceptance criteria:**
- [ ] updater works on the final supported release path
- [ ] all supported-platform smoke tests pass
- [ ] one Windows installer format is explicitly chosen for v1

#### 7.5 Enable public release cutover

Only after all previous checks pass:

1. add the public tag trigger to `.github/workflows/build-tauri.yml`
2. configure `tauri-action` to publish non-draft releases
3. publish the first stable release

Recommended trigger and release behavior:

```yaml
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
```

And in the `tauri-action` step:

```yaml
with:
  projectPath: src-tauri
  tagName: v__VERSION__
  releaseName: Niamoto v__VERSION__
  releaseBody: See the assets to download and install this version.
  releaseDraft: false
  prerelease: false
```

Do not make this change earlier in the plan.

---

## Phase Dependencies

```text
Phase 1 (CI build) ----------┬----------- Phase 2 (Shell security)
                             ├----------- Phase 3 (Sidecar robustness)
                             └----------- Phase 4 (Signing foundations)

Phase 2 + Phase 4 + Phase 1  ------------ Phase 5 (Updater)
Phase 1 --------------------------------- Phase 6 (Audit)

Phase 1 + 2 + 3 + 4 + 5 + 6 ------------ Phase 7 (Final release gate)
```

Key dependency rules:

- Phase 1 unblocks everything else
- Phase 4 must happen before updater validation becomes meaningful
- Phase 5 must include an end-to-end updater test before public release cutover
- Phase 7 is the only place where the public tag-triggered release flow is enabled

## Files Modified (Summary)

| File | Phases | Changes |
|------|--------|---------|
| `.github/workflows/build-tauri.yml` | 1, 4, 7 | Node update, frontend build, signing env, final release cutover |
| `.github/workflows/dependency-audit.yml` | 6 | new file |
| `src-tauri/tauri.conf.json` | 2, 5, 7 | shell CSP, optional freezePrototype, updater config, bundle targets |
| `src-tauri/Cargo.toml` | 2, 3, 5 | remove devtools feature, optional macOS target deps, updater/process deps |
| `src-tauri/capabilities/default.json` | 2, 5 | optional devtools cleanup, updater/process permissions |
| `src-tauri/src/lib.rs` | 3, 5 | process-tree shutdown, plugin registration |
| `build_scripts/niamoto.spec` | 3 | `upx=False`, `pyproj` data, `runtime_tmpdir` |
| `src/niamoto/gui/ui/package.json` | 5 | updater/process frontend deps |
| `src/niamoto/gui/ui/src/shared/desktop/updater/useAppUpdater.ts` | 5 | new file |
| `src/niamoto/gui/ui/src/shared/desktop/updater/UpdateBanner.tsx` | 5 | new file |
| `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx` | 5 | mount updater UI |

## Manual Steps Required

1. Generate updater signing keys with `cargo tauri signer generate`
2. Add updater signing secrets to GitHub
3. Export Apple signing material and add Apple secrets to GitHub
4. Run the staged updater test between two packaged versions
5. Run VM smoke tests on the supported platforms
6. Choose one Windows installer format for v1

## What This Plan Does Not Cover

- FastAPI-side CSP or backend security headers
- refactoring away from `withGlobalTauri`
- delta updates or beta channels
- Windows code signing certificate unless Windows reputation issues force it into v1
- macOS x86_64 builds
