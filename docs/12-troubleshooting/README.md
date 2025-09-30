# Troubleshooting

Solutions to common issues and problems.

## 📚 Documents in this Section

- **[Common Issues](common-issues.md)** - Frequently encountered problems and solutions

## 🔍 Quick Fixes

### Installation Issues

**Problem**: `pip install niamoto` fails
```bash
# Solution: Use uv instead
uv pip install niamoto
```

**Problem**: GUI won't start
```bash
# Check port availability
lsof -i :8080
# Use different port
niamoto gui --port 8081
```

### Import Errors

**Problem**: CSV import fails
- Check file encoding (UTF-8 required)
- Verify column headers match mapping
- Ensure no special characters in headers

**Problem**: GIS import error
- Install GDAL: `pip install gdal`
- Check projection system
- Verify file format support

### Database Issues

**Problem**: Database locked
```bash
# Find and kill process
fuser niamoto.db
# Or restart Niamoto
```

**Problem**: Migration errors
```bash
# Reset database
niamoto db reset
# Re-run migrations
niamoto db migrate
```

## 🐛 Debugging Tips

### Enable Debug Mode
```bash
# Set environment variable
export NIAMOTO_DEBUG=true
# Or in CLI
niamoto --debug import
```

### Check Logs
```bash
# View logs
tail -f ~/.niamoto/logs/niamoto.log
# Increase verbosity
niamoto -vvv import
```

### Validate Configuration
```bash
# Check YAML syntax
niamoto validate config/import.yml
# Test pipeline
niamoto test-pipeline
```

## 💬 Getting Help

1. Check [Common Issues](common-issues.md)
2. Search [GitHub Issues](https://github.com/niamoto/niamoto/issues)

## 🔗 Related Documentation

- [Getting Started](../01-getting-started/) - Initial setup
- [Configuration](../08-configuration/) - Config troubleshooting
- [Development](../11-development/) - Debug techniques

---
*Can't find your issue? Please report it on GitHub!*
