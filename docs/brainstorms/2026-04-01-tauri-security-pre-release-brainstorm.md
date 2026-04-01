# Tauri Security Pre-Release Hardening

**Date**: 2026-04-01
**Status**: Revised
**Scope**: Tauri shell hardening before first major release
**Part of**: Tauri release readiness (1/4 — security, auto-updater, dependencies, cross-platform)

## Context

Niamoto Desktop uses Tauri 2.9.2 as a desktop shell around a React 19 frontend served by a FastAPI backend on localhost.

Important architecture detail: the Tauri window boots the bundled shell, then navigates to `http://127.0.0.1:<port>`. That means Tauri security settings harden the bootstrap shell and the Tauri bridge, but they do not by themselves secure the FastAPI-served application pages after navigation.

This revision keeps the scope explicit so we do not overstate what the Tauri config actually protects.

## What We're Building

Two immediate shell hardening changes, plus one boundary clarification that should change how we talk about CSP and `freezePrototype`.

### 1. Content Security Policy for the Tauri Bootstrap Shell

**Problem**: `"csp": null` in `tauri.conf.json` — no CSP at all.

**Correction**: the original proposal was too permissive and mixed two different concerns:

- Tauri shell CSP
- FastAPI-served app CSP

`https://*` is not needed for the bootstrap shell. External images, embeds, and API calls are part of the application pages served by FastAPI, not part of the bundled Tauri shell that boots before `window.location.replace(...)`.

**Solution**: add a restrictive shell CSP in `src-tauri/tauri.conf.json`, and treat any CSP for the FastAPI-served UI as a separate backend topic.

```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:;
font-src 'self';
connect-src 'self' http://localhost:* http://127.0.0.1:*;
frame-src 'self' blob:;
object-src 'none';
base-uri 'self';
form-action 'self';
```

**Notes**:

- Keep Tauri's default CSP tightening behavior. Do not disable asset CSP modification.
- Add a separate `devCsp` if needed for Vite/HMR. Do not assume the release CSP will work unchanged in development.
- Do not claim this shell CSP secures the real app UI after the webview has navigated to FastAPI on localhost.

### 2. Disable Production Devtools by Removing the Cargo Feature

**Problem**: `features = ["devtools"]` in `Cargo.toml` makes devtools available in all builds including release.

**Solution**: Remove `"devtools"` from features list.

```toml
# Before
tauri = { version = "2.9.2", features = ["devtools"] }

# After
tauri = { version = "2.9.2", features = [] }
```

**Effect**: according to the Tauri docs, the inspector works in dev/debug builds by default and requires the `devtools` Cargo feature to be available in release builds. Removing the feature is the release hardening step that matters.

**Cleanup to decide separately**:

- `app.windows[].devtools: true` in `tauri.conf.json` is no longer useful once the release feature is removed, but leaving it there mainly affects developer ergonomics rather than release exposure.
- `core:webview:allow-internal-toggle-devtools` in `src-tauri/capabilities/default.json` should be removed if we want to stop advertising a devtools path entirely.

### 3. `freezePrototype` Is Not a Primary Mitigation in the Current Architecture

**Original claim**: add `"freezePrototype": true` and count it as a release blocker.

**Correction**: Tauri documents `freezePrototype` as protection used with the custom protocol. Niamoto Desktop does not keep the main app on the Tauri custom protocol; it navigates the main webview to `http://127.0.0.1:<port>`.

That means:

- enabling `freezePrototype` is still reasonable as defense-in-depth for the bootstrap shell
- it should not be presented as protection for the FastAPI-served application pages
- it is not one of the highest-leverage release blockers compared with shell CSP and devtools release gating

**Decision**: optional defense-in-depth, not the headline fix. If enabled, document it accurately.

## Key Decisions

- **No `https://*` in the Tauri shell CSP**: it weakens the policy without matching the actual bootstrap shell needs
- **Treat shell hardening and FastAPI hardening separately**: Tauri config does not automatically secure the localhost-served UI
- **Keep `script-src 'self'` strict**: all shell JS is local
- **Keep `style-src 'unsafe-inline'`**: the current frontend stack still relies on inline styles
- **Do not oversell `freezePrototype`**: useful only as shell defense-in-depth in this architecture
- **No capability refactor in this pass**: still not worth splitting the entire IPC surface before first release
- **Do not turn off `withGlobalTauri` in this pass**: current frontend code still relies on `window.__TAURI__`, so that needs a separate refactor if we want to reduce XSS blast radius later

## Files to Modify

1. `src-tauri/tauri.conf.json`
   - add release CSP for the bootstrap shell
   - add `devCsp` separately if needed for development
   - optionally remove explicit `devtools: true` as config cleanup
   - optionally add `freezePrototype: true` as defense-in-depth, but do not treat it as the main fix
2. `src-tauri/Cargo.toml`
   - remove the `devtools` Cargo feature
3. `src-tauri/capabilities/default.json`
   - optionally remove `core:webview:allow-internal-toggle-devtools` if we want to fully clean up the devtools path

## What We're NOT Doing

- Full capabilities refactoring before release
- A last-minute refactor away from `withGlobalTauri`
- Claiming that Tauri CSP secures the FastAPI-served UI after navigation
- Treating `freezePrototype` as a substitute for real CSP and bridge hardening
- Backend CSP/security headers for the localhost-served app in this Tauri-only note
- Dependency version alignment (separate topic)
- Code signing / notarization (separate topic)

## Next Steps

1. Implement the shell CSP in `src-tauri/tauri.conf.json` and keep development behavior explicit with `devCsp`.
2. Remove the `devtools` Cargo feature and decide whether to also clean up the explicit devtools config and capability entry.
3. Open a separate backend hardening note if we want CSP/security headers on the FastAPI-served desktop UI itself.
4. Continue with the remaining release-readiness topics:
   - auto-updater system
   - dependency audit and version alignment
   - cross-platform build and testing (Windows/Linux)
