# Binary Distribution Guide

This guide explains how Niamoto can be distributed as standalone binaries for multiple platforms.

## 🎯 Overview

Niamoto can be packaged as a single executable file that includes:
- Python runtime
- All dependencies (FastAPI, DuckDB, pandas, geopandas, etc.)
- React GUI (pre-built)
- ML models
- Core plugins

**No Python installation required for end users!**

## 📦 Supported Platforms

| Platform | Architecture | Binary Name | Size |
|----------|--------------|-------------|------|
| macOS | Apple Silicon (M1/M2/M3/M4) | `niamoto` | ~135 MB |
| macOS | Intel (x86_64) | `niamoto` | ~135 MB |
| Linux | x86_64 | `niamoto` | ~135 MB |
| Windows | x86_64 | `niamoto.exe` | ~135 MB |

## 🏗️ Build Methods

### Method 1: Local Build (Single Platform)

Build for your current platform:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the binary
pyinstaller build_scripts/niamoto.spec --clean --noconfirm

# Result in dist/niamoto (or dist/niamoto.exe on Windows)
```

**Use case**: Testing, development, or distribution on a single platform.

### Method 2: GitHub Actions (All Platforms)

Automated cross-platform builds on every release:

```bash
# 1. Update version
vim src/niamoto/__version__.py  # Change to new version

# 2. Commit and tag
git add src/niamoto/__version__.py
git commit -m "chore: bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z

# 3. GitHub Actions automatically:
#    - Builds for all 4 platforms
#    - Creates GitHub Release
#    - Uploads all binaries
```

**Use case**: Production releases, multi-platform distribution.

See [.github/RELEASE.md](../.github/RELEASE.md) for detailed release instructions.

## 🚀 Usage

### For End Users

**macOS / Linux**:
```bash
# Download the binary
curl -L https://github.com/niamoto/niamoto/releases/download/v0.7.4/niamoto-macos-arm64.tar.gz -o niamoto.tar.gz

# Extract
tar -xzf niamoto.tar.gz

# Make executable
chmod +x niamoto

# Run
./niamoto gui --instance my-project/
```

**Windows**:
```powershell
# Download and extract niamoto-windows-x86_64.zip

# Run
.\niamoto.exe gui --instance my-project\
```

### Available Commands

All standard Niamoto CLI commands work:

```bash
# Start GUI
./niamoto gui --instance my-project/ --port 8080

# Import data
./niamoto import --instance my-project/

# Transform data
./niamoto transform --instance my-project/

# Export static site
./niamoto export --instance my-project/

# Initialize new project
./niamoto init my-new-project/
```

## 🔧 Technical Details

### How It Works

1. **PyInstaller** bundles:
   - Python interpreter
   - All Python packages
   - Data files (models, UI)
   - Into a single executable

2. **On Launch**:
   - Binary extracts to temporary directory (`/tmp/_MEI...`)
   - Runs the Niamoto CLI with all dependencies
   - Cleans up on exit

3. **Bundle Structure**:
   ```
   niamoto (executable)
   └─ Contains:
      ├─ Python 3.11 runtime
      ├─ niamoto/ (package)
      ├─ models/ (ML models)
      ├─ niamoto/gui/ui/dist/ (React build)
      └─ All dependencies
   ```

### Build Configuration

The build is configured in `build_scripts/niamoto.spec`:

- **Entry point**: `src/niamoto/__main__.py`
- **Hidden imports**: Listed in `hiddenimports` array
- **Data files**: Automatically collected from patterns
- **Optimization**: UPX compression enabled
- **Console mode**: Enabled (for CLI output)

### Platform-Specific Details

**macOS**:
- Code-signed (SDK version normalized)
- Universal binaries possible with `lipo`
- Runs on macOS 11+ (Big Sur and later)

**Linux**:
- Built on Ubuntu 22.04 (glibc 2.35)
- Compatible with most modern Linux distros
- May require older glibc for older systems

**Windows**:
- Requires Windows 10/11
- WebView2 not needed (Niamoto uses browser)
- Antivirus may flag initially (false positive)

## 📊 Size Optimization

Current binary size: **~135 MB** (uncompressed)

Compressed (tar.gz/zip): **~50-60 MB**

### Future Optimizations

Potential size reductions:
- Remove unused stdlib modules: -20 MB
- Switch to Polars instead of pandas: -30 MB
- Remove matplotlib if unused: -20 MB
- Use DuckDB Spatial instead of GeoPandas: -100 MB

**Trade-off**: Complexity vs size. Current approach prioritizes simplicity.

## 🔐 Security Considerations

### Code Signing

**macOS**: Binaries should be signed with Apple Developer certificate:
```bash
codesign --sign "Developer ID Application: Your Name" dist/niamoto
```

**Windows**: Binaries should be signed with Authenticode certificate.

### Distribution

Recommended distribution methods:
1. ✅ GitHub Releases (public, auditable)
2. ✅ Direct download from official website
3. ⚠️ Package managers (require additional setup)

### Verification

Users can verify downloads with checksums:
```bash
# Generate checksums during release
sha256sum niamoto > niamoto.sha256

# Users verify
sha256sum -c niamoto.sha256
```

## 🐛 Troubleshooting

### Binary Doesn't Start

**Symptoms**: Binary runs but nothing happens, or immediate crash.

**Solutions**:
1. Check permissions: `chmod +x niamoto`
2. Run from terminal to see error messages
3. Check if all resources are included: Look for "FileNotFoundError"

### Missing Dependencies

**Symptoms**: `ImportError` or `ModuleNotFoundError`

**Solution**: Add to `hiddenimports` in `build_scripts/niamoto.spec`:
```python
hiddenimports = [
    'your_missing_module',
]
```

### UI Doesn't Load

**Symptoms**: Server starts but browser shows 404.

**Solution**: Verify React build is included:
```bash
# Check the spec file includes UI dist
# Should see: "✓ Including React build from .../dist"
# Should see: "Added XX files from React build"
```

### Platform-Specific Issues

**macOS "damaged" warning**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine niamoto
```

**Linux "permission denied"**:
```bash
chmod +x niamoto
```

**Windows SmartScreen warning**:
- Click "More info" → "Run anyway"
- Better: Code-sign the binary

## 📚 Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [Release Process Guide](../.github/RELEASE.md)
- [Build Scripts README](../build_scripts/README.md)
- [GitHub Actions Workflow](../.github/workflows/build-binaries.yml)

## 🔄 Update Process

For end users to update:

1. Download new version binary
2. Replace old binary
3. Done!

No dependency management, no pip install, no virtual environments.

## 💡 Best Practices

### For Developers

- ✅ Test binary locally before releasing
- ✅ Keep `niamoto.spec` updated with new dependencies
- ✅ Document breaking changes in release notes
- ✅ Use semantic versioning

### For Users

- ✅ Download from official GitHub Releases only
- ✅ Verify checksums when available
- ✅ Keep one version per project (avoid conflicts)
- ✅ Use `--instance` flag to specify project directory

## 🎯 Use Cases

### Research Teams

**Scenario**: Share analysis tools with field researchers.

**Solution**: USB drive with binary + data:
```
/USB/
├── niamoto (binary)
├── field-data/ (instance)
│   ├── imports/
│   ├── config/
│   └── db/
└── run.sh (./niamoto gui --instance field-data/)
```

### Production Servers

**Scenario**: Deploy to server without Python.

**Solution**: Single binary deployment:
```bash
# Copy binary to server
scp niamoto user@server:/opt/niamoto/

# Run as service
./niamoto gui --instance /data/niamoto-prod --port 8080 --no-browser
```

### Workshops/Training

**Scenario**: 20 participants, all different OS.

**Solution**: Provide 3 binaries (macOS, Linux, Windows):
- No setup time
- No dependency hell
- Works offline
- Identical experience

## ✨ Advantages

✅ **No Python required** - Users don't need Python installed
✅ **No pip install** - No dependency resolution issues
✅ **Consistent environment** - Same versions everywhere
✅ **Offline capable** - Works without internet
✅ **Simple distribution** - Just download and run
✅ **Version control** - Easy to have multiple versions
✅ **Fast startup** - Pre-compiled, optimized

## ⚠️ Limitations

❌ **Large file size** - 135 MB (vs ~50 MB source)
❌ **Platform-specific** - Need separate binary per OS
❌ **Update size** - Full binary download (not incremental)
❌ **Not modifiable** - Can't edit code (by design)
❌ **Startup extraction** - First run slower (creates temp dir)

## 🔮 Future Enhancements

Potential improvements:
- **Auto-update**: Check for new versions, download automatically
- **Plugins**: Load external plugins from user directories
- **Config UI**: GUI to generate instance configs
- **Binary diff updates**: Download only changed parts
- **Signed binaries**: Proper code signing for all platforms
