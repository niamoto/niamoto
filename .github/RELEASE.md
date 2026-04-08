# Release Process

This document explains how to create a new Niamoto release with cross-platform binaries.

## 🚀 Quick Release

### 1. Update Version (Automated with bump2version)

**Recommended approach** - Updates all files automatically:

```bash
# Patch version (0.7.4 → 0.7.5)
uv run bump2version patch

# Minor version (0.7.5 → 0.8.0)
uv run bump2version minor

# Major version (0.8.0 → 1.0.0)
uv run bump2version major
```

This automatically:
- ✅ Updates version in `pyproject.toml`, `docs/conf.py`, `src/niamoto/__version__.py`
- ✅ Creates a commit: "Bump version: X.X.X → Y.Y.Y"
- ✅ Creates a git tag `vY.Y.Y`

### 2. Push Release

```bash
# Push commit and tag
git push && git push origin v0.7.5
```

### 3. Publish to PyPI (automated)

PyPI publication is automated via GitHub Actions (Trusted Publishers / OIDC).
Creating a GitHub Release triggers the `publish-pypi.yml` workflow which:
- ✅ Builds React UI
- ✅ Creates wheel (with GUI) and sdist (without GUI)
- ✅ Publishes to PyPI via OIDC (no token needed)

### 4. Automated Binary Build

Once the tag is pushed, GitHub Actions will automatically:

1. ✅ Build React UI
2. ✅ Build binaries for all platforms:
   - macOS Apple Silicon (arm64)
   - macOS Intel (x86_64)
   - Linux x86_64
   - Linux arm64
   - Windows x86_64
3. ✅ Create GitHub Release with all binaries
4. ✅ Generate release notes

### 5. Monitor Progress

Visit: https://github.com/niamoto/niamoto/actions

The build takes approximately:
- React UI: ~2-3 minutes
- Each binary: ~5-10 minutes
- **Total: ~10-15 minutes**

## 📦 What Gets Released

Each release includes 5 CLI binaries and matching desktop bundles:

| File | Platform | Size |
|------|----------|------|
| `niamoto-macos-arm64.tar.gz` | macOS Apple Silicon (M1/M2/M3/M4) | ~50-60 MB |
| `niamoto-macos-x86_64.tar.gz` | macOS Intel (2019-2020 MacBooks) | ~50-60 MB |
| `niamoto-linux-x86_64.tar.gz` | Linux x86_64 | ~50-60 MB |
| `niamoto-linux-arm64.tar.gz` | Linux arm64 (Pi, Ampere, Graviton) | ~50-60 MB |
| `niamoto-windows-x86_64.zip` | Windows 10/11 x86_64 | ~50-60 MB |

Desktop bundles (`.dmg`, `.deb`, `.msi`) are produced for every platform above
(except Windows arm64) by the `build-tauri.yml` workflow and attached to the
same GitHub Release.

**Uncompressed binaries are ~130-140 MB each**

## 🏷️ Managing Git Tags

### Move/Recreate a Tag

If you need to move a tag to a different commit (e.g., after fixing a build issue):

```bash
# Delete local tag
git tag -d v0.7.5

# Delete remote tag
git push origin :refs/tags/v0.7.5

# Create new tag at current commit
git tag v0.7.5

# Push new tag
git push origin v0.7.5
```

**⚠️ Warning**: Only recreate tags for unreleased versions or if critical issue. Released tags should generally not be moved.

### List All Tags

```bash
# List all tags
git tag -l

# List tags with pattern
git tag -l "v0.7.*"

# Show tag details
git show v0.7.5
```

### Delete a Tag

```bash
# Delete local tag
git tag -d v0.7.5

# Delete remote tag
git push origin --delete v0.7.5
# or
git push origin :refs/tags/v0.7.5
```

### Tag a Specific Commit

```bash
# Tag a specific commit
git tag v0.7.5 <commit-hash>
git push origin v0.7.5

# Tag with annotation
git tag -a v0.7.5 -m "Release version 0.7.5"
git push origin v0.7.5
```

## 🔧 Manual Trigger

You can also trigger a build manually without creating a release:

1. Go to https://github.com/niamoto/niamoto/actions/workflows/build-binaries.yml
2. Click "Run workflow"
3. Select branch
4. Click "Run workflow"

This will build binaries but won't create a release.

## 🐛 Troubleshooting

### Build Fails on One Platform

If a build fails on one platform (e.g., Windows), the other platforms will continue building thanks to `fail-fast: false`.

Check the logs for the failed platform to identify the issue.

### PyInstaller Errors

Common issues:
- **Missing dependency**: Add to `hiddenimports` in `build_scripts/niamoto.spec`
- **Missing data file**: Add to `datas` pattern in `niamoto.spec`
- **Import error**: Check that the dependency is in `pyproject.toml`

### React Build Missing

If the binary doesn't include the React UI:
1. Check that `src/niamoto/gui/ui/dist/` exists
2. Verify the build-react job succeeded
3. Check the artifact download step

## 📝 Release Notes Customization

The workflow auto-generates release notes. To customize:

Edit `.github/workflows/build-binaries.yml` in the "Create Release Notes" step.

## 🔐 Permissions

The workflow requires `contents: write` permission to create releases.

This is already configured in the workflow file.

## ✅ Pre-Release Checklist

Before creating a release:

- [ ] All tests pass: `pytest`
- [ ] Version bumped in `__version__.py`
- [ ] CHANGELOG updated (if you have one)
- [ ] Documentation updated
- [ ] Local build works: `pyinstaller build_scripts/niamoto.spec`
- [ ] React UI builds: `cd src/niamoto/gui/ui && pnpm run build`

## 🎯 Version Numbering

Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Examples:
- `v0.7.4` → `v0.7.5` (bug fix)
- `v0.7.5` → `v0.8.0` (new feature)
- `v0.8.0` → `v1.0.0` (breaking change / stable release)

## 📊 Build Matrix Details

The workflow builds on:

- **macOS-14**: Apple Silicon runner for native arm64 binaries
- **macOS-13**: Intel runner for native x86_64 macOS binaries
- **ubuntu-22.04**: Ubuntu 22.04 LTS for Linux x86_64 binaries
- **ubuntu-22.04-arm**: Ubuntu 22.04 arm64 runner for Linux arm64 binaries
- **windows-latest**: Windows Server 2022 for Windows x86_64 binaries

**Note:** Intel macOS builds are included again to provide native binaries for
2019-2020 MacBooks and other x86_64 systems. Apple Silicon users continue to
receive native arm64 binaries.

## 🔄 Updating the Workflow

To modify the build process:

1. Edit `.github/workflows/build-binaries.yml`
2. Test locally if possible
3. Or create a test tag: `git tag v0.0.0-test && git push origin v0.0.0-test`
4. Check the build, then delete the test tag

## 📚 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [Semantic Versioning](https://semver.org/)
