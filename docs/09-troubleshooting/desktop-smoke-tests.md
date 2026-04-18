# Desktop Smoke Tests

Use this checklist before calling a desktop build healthy on macOS, Linux, or Windows.

## Current build matrix

The current CI workflow in `.github/workflows/build-tauri.yml` produces:

- macOS arm64
- Linux x86_64
- Linux arm64
- Windows x86_64

Windows ARM64 is only partially supported in code today:

- the Tauri runtime resolves the ARM64 sidecar target
- the CI workflow does not build or publish a Windows ARM64 artifact yet
- local ARM64 testing still depends on a native sidecar environment

## Startup

Check:

- the desktop app launches without a console window on Windows
- only one title bar is visible on Windows and Linux
- the startup screen progresses, then the main UI loads
- a startup failure shows the inline error screen instead of a blank window
- startup logs are written to the native desktop log directory

## Project selection

Check:

- opening an existing project works
- invalid recent projects are detected and can be removed
- creating a project rejects invalid names such as `CON`, `bad/name`, trailing dots, or trailing spaces
- switching projects updates the backend context without restarting the whole desktop app

## Core workflows

Check:

- import starts and reaches progress updates
- transform starts and reaches progress updates
- site export starts and reaches progress updates
- feedback submission either succeeds or fails with a useful local diagnostic
- updater can check, download, and install an update

## Platform-specific checks

### Windows

- no extra terminal window opens
- installer and updater both complete without leaving the UI stuck at `0%`
- project creation rejects Windows-reserved names
- opening external links works for `http`, `https`, and `mailto`, and rejects other schemes

### Linux

- updater handles the privileged install step cleanly
- PyInstaller bundle contains required native GIS dependencies
- native window decorations remain intact

### macOS

- overlay title bar still leaves enough drag area
- traffic lights remain accessible
- startup, project switching, and updater still work after the Tauri hardening passes
