# Tauri Auto-Updater System

**Date**: 2026-04-01
**Status**: Revised
**Scope**: In-app updater for published desktop releases via GitHub Releases
**Part of**: Tauri release readiness (2/4 — security, auto-updater, dependencies, cross-platform)

## Context

Niamoto Desktop currently has no updater. Users must manually download new installers from GitHub Releases.

The repo already has a desktop build workflow in `.github/workflows/build-tauri.yml`, but it is currently a manual build workflow, not a release workflow guaranteed to publish signed updater artifacts.

That distinction matters:

- `tauri-plugin-updater` can only install updates that have been built with updater artifacts enabled
- those artifacts must be signed
- they must be attached to a published GitHub Release
- the app must query a URL that actually serves the current `latest.json`

## What We're Building

A stable-channel updater for desktop builds using:

- `tauri-plugin-updater` for check, download, signature verification, and install
- `@tauri-apps/plugin-updater` for the React-side API
- `@tauri-apps/plugin-process` for relaunch after install
- GitHub Releases as the update distribution endpoint

No custom update server is needed for the first release.

## Architecture

```text
tagged release workflow
    -> signed updater artifacts + latest.json
        -> published GitHub Release
            -> updater plugin checks latest.json
                -> desktop banner in app shell
                    -> user installs update
                        -> app relaunches
```

## 1. Rust Plugin Setup

### `src-tauri/Cargo.toml`

Add the updater and process plugins:

```toml
tauri-plugin-updater = "2"
tauri-plugin-process = "2"
```

### `src-tauri/src/lib.rs`

Register `process` on the builder and register `updater` inside `setup`, which matches the official Tauri v2 updater setup pattern and fits the existing `setup(|app| { ... })` structure already used by Niamoto.

Sketch:

```rust
tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_process::init())
    .setup(|app| {
        #[cfg(desktop)]
        app.handle().plugin(tauri_plugin_updater::Builder::new().build())?;

        // existing startup logic...
        Ok(())
    })
```

### `src-tauri/capabilities/default.json`

Add:

```json
"updater:default",
"process:default"
```

Notes:

- `updater:default` covers check, download, install, and download-and-install
- `process:default` is needed if the frontend uses `relaunch()`
- no change is needed to the existing `remote.urls` scope for localhost; updater downloads are handled by the plugin, not by the webview fetch layer

## 2. Tauri Configuration

### `src-tauri/tauri.conf.json`

Add updater configuration:

```json
{
  "bundle": {
    "createUpdaterArtifacts": true
  },
  "plugins": {
    "updater": {
      "pubkey": "<GENERATED_PUBLIC_KEY>",
      "endpoints": [
        "https://github.com/niamoto/niamoto/releases/latest/download/latest.json"
      ],
      "windows": {
        "installMode": "passive"
      }
    }
  }
}
```

Why this shape:

- `createUpdaterArtifacts: true` tells Tauri to build updater bundles and signatures
- `pubkey` must contain the minisign public key content, not a file path
- `endpoints` can point directly at GitHub's static `latest.json`
- `windows.installMode: "passive"` is the best default for a user-facing updater

Important constraints:

- this endpoint only works for a published release, not a draft release
- if we later want beta or prerelease channels, `releases/latest/download/latest.json` is no longer enough by itself
- updater artifact signing is separate from platform code signing for macOS and Windows

## 3. CI/CD Changes

### Current State

The existing `.github/workflows/build-tauri.yml`:

- runs on `workflow_dispatch`
- builds desktop bundles
- uploads CI artifacts
- does not yet pass updater signing secrets to `tauri-action`
- does not yet clearly define the GitHub Release publishing behavior required for updater consumption

### Required Change

Turn this into a real release workflow for updater builds.

Recommended trigger:

```yaml
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
```

Recommended `tauri-action` configuration:

```yaml
- name: Build Tauri
  uses: tauri-apps/tauri-action@v0
  with:
    projectPath: src-tauri
    tagName: v__VERSION__
    releaseName: Niamoto v__VERSION__
    releaseBody: See the assets to download and install this version.
    releaseDraft: false
    prerelease: false
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    TAURI_SIGNING_PRIVATE_KEY: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}
    TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}
```

Why this is required:

- `latest.json` is only useful if a published GitHub Release actually contains it
- draft releases should not be used for the stable updater endpoint
- the updater artifacts are only signed if the signing key env vars are present during the build

The current `actions/upload-artifact` step can stay for CI convenience, but it is not what the updater consumes.

## 4. Frontend Integration

### Dependencies

Add to `src/niamoto/gui/ui/package.json`:

- `@tauri-apps/plugin-updater`
- `@tauri-apps/plugin-process`

### File Placement

Do not add a new root-level `src/components/UpdateBanner.tsx`.

This updater UI is desktop-only and cross-feature, so it fits better under `src/shared`.

Recommended structure:

1. `src/niamoto/gui/ui/src/shared/desktop/updater/useAppUpdater.ts`
2. `src/niamoto/gui/ui/src/shared/desktop/updater/UpdateBanner.tsx`

### Mount Point

Mount the banner from `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`, above `TopBar`.

Reason:

- it appears globally in the desktop app shell
- it does not show on the welcome screen before desktop initialization is complete
- it follows the current layout architecture instead of bypassing it

### Runtime Detection

Use `useRuntimeMode().isDesktop`, not a new raw `window.__TAURI__` check in the component.

### Behavior

Recommended behavior:

- wait briefly after layout mount before first check
- check every 4 hours while the app is open
- show nothing when no update is available
- show a dismissible banner when an update is available
- show download progress during install
- relaunch automatically after successful install on platforms where that is appropriate

Reference JS flow:

```ts
import { check } from '@tauri-apps/plugin-updater'
import { relaunch } from '@tauri-apps/plugin-process'

const update = await check()

if (update) {
  await update.downloadAndInstall((event) => {
    // Started / Progress / Finished
  })

  await relaunch()
}
```

Platform note:

- on Windows, the application is automatically exited during install due to installer limitations
- immediate relaunch is still a reasonable default on macOS and Linux

## 5. Key Generation and Secret Handling

Generate updater signing keys manually:

```bash
cargo tauri signer generate -w ~/.tauri/niamoto.key
```

Then:

1. copy the public key into `src-tauri/tauri.conf.json`
2. add the private key content or path to `TAURI_SIGNING_PRIVATE_KEY`
3. add the password to `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`

Important:

- updater signing cannot be disabled
- losing the private key means installed apps cannot trust future updates signed by a different key
- `.env` files are not sufficient for the build step; the secrets must be present in the actual CI environment

## Key Decisions

- **GitHub Releases over custom update server**: simplest first-release path, no extra infrastructure
- **Published stable release only**: required for the `releases/latest/download/latest.json` endpoint to behave predictably
- **Banner in app shell, not modal dialog**: visible but low-friction
- **Mount from `MainLayout`**: matches current frontend architecture
- **Use `plugin-process` and relaunch**: cleaner install flow than “updated, please reopen manually”
- **Keep updater checks desktop-only**: no-op in web mode
- **No release-channel system yet**: stable only for now

## Files to Create or Modify

1. `src-tauri/Cargo.toml`
   - add `tauri-plugin-updater`
   - add `tauri-plugin-process`
2. `src-tauri/src/lib.rs`
   - register process plugin
   - register updater plugin in `setup`
3. `src-tauri/tauri.conf.json`
   - add updater config
   - enable `createUpdaterArtifacts`
   - set Windows install mode
4. `src-tauri/capabilities/default.json`
   - add `updater:default`
   - add `process:default`
5. `src/niamoto/gui/ui/package.json`
   - add `@tauri-apps/plugin-updater`
   - add `@tauri-apps/plugin-process`
6. `src/niamoto/gui/ui/src/shared/desktop/updater/useAppUpdater.ts`
   - updater state and polling logic
7. `src/niamoto/gui/ui/src/shared/desktop/updater/UpdateBanner.tsx`
   - UI for available, downloading, error states
8. `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`
   - mount the banner in the desktop shell
9. `.github/workflows/build-tauri.yml`
   - publish on version tags
   - pass signing secrets
   - publish a non-draft release suitable for updater use

## What We're NOT Doing

- Custom update server
- Release channels or beta updater feeds
- Delta updates
- Changelog rendering inside the banner
- Silent background installs without user action
- Custom Rust commands for updater orchestration
- Solving macOS and Windows platform code signing in this note

## Next Steps

1. Convert `build-tauri.yml` into a release workflow that publishes signed updater artifacts.
2. Add updater and process plugins on the Rust side.
3. Add the desktop-only updater UI under `src/shared/desktop/updater`.
4. Mount the banner from `MainLayout`.
5. Test one full update cycle against a real published GitHub Release before calling the feature ready.
