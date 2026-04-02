# Dependency Audit & Versioning Policy

**Date**: 2026-04-01
**Status**: Validated
**Scope**: Dependency health check + versioning strategy for release
**Part of**: Tauri release readiness (3/4 - security, auto-updater, dependencies, cross-platform)

## Context

This review is based on the manifests and committed lockfiles present in the repository on 2026-04-01.

It is meant to answer two questions:

1. Is there a dependency issue that must be fixed before the Tauri release?
2. What versioning policy should we follow after the release?

This note does not replace a fresh `pnpm audit` and `cargo audit` run before shipping.

## Current State

### Rust Dependencies (manifest vs lock)

| Package | Manifest | Resolved (lock) | Assessment |
|---------|----------|-----------------|------------|
| `tauri` | `2.9.2` | `2.9.3` | Normal patch drift |
| `tauri-build` | `2.5.1` | `2.5.2` | Normal patch drift |
| `tauri-plugin-log` | `2` | `2.7.1` | Expected broad major range |
| `tauri-plugin-dialog` | `2` | `2.4.2` | Expected broad major range |
| `window-vibrancy` | `0.7` | `0.7.1` direct + `0.6.0` transitive | Worth noting, not a release blocker by itself |

Key point: there is no evidence here of a broken Rust dependency graph. The previous note that described `tauri-build` as a "significant mismatch" was incorrect.

### JS Dependencies (manifest vs lock)

| Package | Manifest | Resolved (lock) | Assessment |
|---------|----------|-----------------|------------|
| `react` | `^19.1.0` | `19.2.4` | Locked install is already ahead of the floor |
| `react-dom` | `^19.1.0` | `19.2.4` | Same as `react` |
| `vite` | `^7.0.0` | `7.3.1` | Normal caret drift |
| `@monaco-editor/react` | `^4.7.0` | `4.7.0` | Stable |
| `monaco-editor` | `^0.55.1` | `0.55.1` | Stable |
| `dompurify` | transitive only | `3.2.7` | Current lock is already on a patched line |

Key point: the repo should be audited against `pnpm-lock.yaml`, not only against `package.json`. A manifest specifier is not the installed state.

### Security Notes

- The older note about "16 npm vulnerabilities" should not be treated as current state without rerunning `pnpm audit`.
- The Monaco/DOMPurify concern does not justify a package update by itself anymore: the current lock already resolves `monaco-editor` to `0.55.1` and `dompurify` to `3.2.7`.
- There is no committed `cargo audit` result in the repo today. If we want recurring Rust advisory coverage, we need a dedicated CI job for it.

## Immediate Actions (Pre-Release)

### 1. Do Not Widen Rust Dependency Ranges Right Before Release

Keep the current explicit requirements in `src-tauri/Cargo.toml`.

`tauri = "2.9.2"` and `tauri-build = "2.5.1"` already allow patch upgrades through Cargo's default caret semantics. Changing them to bare `"2"` would broaden the accepted range without solving a demonstrated problem.

### 2. Re-Run Audits From the Current Lockfiles

Before cutting the desktop release, rerun audits against the state that will actually ship:

```bash
cd src/niamoto/gui/ui && pnpm audit --prod
cd src-tauri && cargo audit
```

If `cargo audit` is not available locally, install it once or rely on CI. The important point is the audit result, not whether the tool is installed on one machine.

### 3. Add a Dedicated Rust Audit Workflow

Do not bolt `cargo audit` onto the existing Python matrix as a raw shell snippet. The current `.github/workflows/tests.yml` job does not set up a Rust toolchain and is not shaped for Tauri-specific checks.

Prefer a dedicated workflow or a dedicated Rust security job, for example:

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

This keeps the audit narrow, reproducible, and tied to the Rust lockfile.

## Versioning Policy

### Philosophy: Explicit Constraints + Committed Lockfiles

Use explicit manifest constraints, commit lockfiles, and let the resolver pick patch updates inside the declared compatibility window.

Do not widen version ranges unless we intentionally want to broaden what the project supports.

### By Ecosystem

| Ecosystem | Strategy | Example | Lockfile |
|-----------|----------|---------|----------|
| **Rust** | Explicit dependency requirements + committed lockfile | `tauri = "2.9.2"` or `tauri-plugin-log = "2"` when major-only is intentional | `Cargo.lock` |
| **JS** | Caret ranges + committed lockfile | `"react": "^19.1.0"` | `pnpm-lock.yaml` |
| **Python** | Minimum ranges, add upper bounds where compatibility is sensitive | `"pandas>=2.3.1,<3"` | `uv.lock` |
| **Release tooling** | Exact pin where reproducibility matters | `PyInstaller==...` in CI or release scripts | Workflow or script |

### Maintenance Cycle

- Before each desktop release: rerun `pnpm audit`, `cargo audit`, and review lockfile deltas.
- Quarterly: refresh minor and patch versions in a dedicated dependency pass.
- On runtime advisory: patch immediately.
- On dev-only advisory: batch with the next dependency pass unless the issue affects release tooling.
- On major upgrades: use a dedicated branch and a full validation cycle.

### What Not to Change Now

- Do not replace explicit Tauri requirements with bare `"2"` ranges.
- Do not update `monaco-editor` only because of the stale DOMPurify note; verify with a fresh audit first.
- Do not use manifest specifiers as the source of truth for a release audit; use the committed lockfiles.

## Files to Modify

1. `.github/workflows/dependency-audit.yml` (new) if we want a dedicated Rust audit workflow.
2. `.github/workflows/tests.yml` only if we intentionally decide to keep dependency audits inside the main CI pipeline.
3. No immediate manifest change is required in `src-tauri/Cargo.toml` or `src/niamoto/gui/ui/package.json` based on the current lockfiles alone.
