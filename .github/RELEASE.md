# Release Process

This document describes the current release contract for Niamoto.

## Quick Release

Inspect the release state and proposed bump:

```bash
uv run python scripts/build/niamoto_release.py
```

Cut a specific release:

```bash
uv run python scripts/build/niamoto_release.py 0.15.6 --yes
```

Cut the suggested release automatically:

```bash
uv run python scripts/build/niamoto_release.py --yes
```

Dry-run only:

```bash
uv run python scripts/build/niamoto_release.py --dry-run
```

## Release Contract

The release flow is intentionally split into two layers:

1. `scripts/build/niamoto_release.py` is the source of truth for the release cut.
   It inspects Git state, runs preflight checks, updates `CHANGELOG.md`, bumps
   versions, creates the release commit/tag, pushes `main`, and publishes the
   GitHub Release with `gh release create`.
2. GitHub Actions reacts to that published release:
   - `publish-pypi.yml` publishes the Python package
   - `build-tauri.yml` builds desktop bundles and finalizes the macOS artifacts
   - `build-binaries.yml` builds CLI archives on tag push and uploads them to the
     existing GitHub Release

The important rule is: **the GitHub Release is created locally, not from
`build-binaries.yml`**. This avoids the broken fan-out where release-triggered
workflows never start because the release was created from another workflow.

## What the Script Checks

Before mutating Git state, `niamoto_release.py` inspects:

- current branch
- dirty working tree
- last tag
- commits since the last tag
- suggested semantic version bump

With `--yes`, it also runs:

- `uv run pytest tests/ -x -q --tb=short`
- `uvx ruff check src/`
- `pnpm install --frozen-lockfile`
- `pnpm run build`
- `cargo audit` when Cargo is available
- local `build_desktop.sh` on macOS as a non-blocking warning step

## macOS Finalization

The macOS release path now relies on:

- `scripts/dev/verify_macos_distribution.sh`
- `scripts/build/finalize_macos_release.sh`

`build-tauri.yml` builds the raw bundle first, then the finalizer repairs the
embedded Python framework layout, re-signs the final bundle, notarizes it, and
rebuilds:

- `Niamoto_<arch>.app.tar.gz`
- `Niamoto_<arch>.app.tar.gz.sig`
- `Niamoto_<version>_<arch>.dmg`
- `latest.json`

## Manual Recovery

If the published release exists but macOS finalization fails, fix the workflow
or the finalizer and rerun `build-tauri.yml`. Do not move the tag unless the
release is still unreleased and you intentionally want to restart the version.

If the GitHub Release already exists and you only need to refresh its notes:

```bash
gh release edit v0.15.6 --title "Niamoto v0.15.6" --notes-file /tmp/release-notes.md
```

If you need to refinalize a downloaded macOS bundle locally:

```bash
bash scripts/build/finalize_macos_release.sh \
  --app path/to/Niamoto.app \
  --release-tag v0.15.6 \
  --output-dir /tmp/niamoto-release-fix
```

## Pre-Release Checklist

- `main` is checked out and clean
- GitHub CLI is authenticated
- Apple signing secrets are valid
- updater signing secrets are valid
- the new changelog section is accurate
- the version has not already been published to PyPI
