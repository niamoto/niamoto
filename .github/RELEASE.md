# Release Process

This document explains how to create a new Niamoto release with cross-platform binaries.

## 🚀 Quick Release

### 1. Update Version

Update the version in `src/niamoto/__version__.py`:

```python
__version__ = "0.7.5"  # New version
```

### 2. Commit and Tag

```bash
# Commit version bump
git add src/niamoto/__version__.py
git commit -m "chore: bump version to 0.7.5"

# Create and push tag
git tag v0.7.5
git push origin main
git push origin v0.7.5
```

### 3. Automated Build

Once the tag is pushed, GitHub Actions will automatically:

1. ✅ Build React UI
2. ✅ Build binaries for all platforms:
   - macOS Apple Silicon (arm64)
   - macOS Intel (x86_64)
   - Linux x86_64
   - Windows x86_64
3. ✅ Create GitHub Release with all binaries
4. ✅ Generate release notes

### 4. Monitor Progress

Visit: https://github.com/niamoto/niamoto/actions

The build takes approximately:
- React UI: ~2-3 minutes
- Each binary: ~5-10 minutes
- **Total: ~15-20 minutes**

## 📦 What Gets Released

Each release includes 4 binaries:

| File | Platform | Size |
|------|----------|------|
| `niamoto-macos-arm64.tar.gz` | macOS M1/M2/M3/M4 | ~50-60 MB |
| `niamoto-macos-x86_64.tar.gz` | macOS Intel | ~50-60 MB |
| `niamoto-linux-x86_64.tar.gz` | Linux x86_64 | ~50-60 MB |
| `niamoto-windows-x86_64.zip` | Windows 10/11 | ~50-60 MB |

**Uncompressed binaries are ~130-140 MB each**

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
- [ ] React UI builds: `cd src/niamoto/gui/ui && npm run build`

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

- **macOS-14**: Latest Apple Silicon runner (arm64)
- **macOS-13**: Latest Intel runner (x86_64)
- **ubuntu-22.04**: Ubuntu 22.04 LTS (glibc 2.35)
- **windows-latest**: Windows Server 2022

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
