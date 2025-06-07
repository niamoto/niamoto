# Template Not Found: group_index.html

## Problem Description

You may encounter an error like:
```
jinja2.exceptions.TemplateNotFound: group_index.html
```

This error typically occurs in the `IndexGeneratorPlugin` when Jinja2 cannot find the `group_index.html` template.

## Root Cause

This issue was resolved in commit `35af102` (June 2, 2025) where templates were reorganized:
- **Before**: Templates were located in `_layouts/` subdirectory (e.g., `_layouts/group_index.html`)
- **After**: Templates were moved to the root templates directory (e.g., `group_index.html`)

## Solutions

### 1. Update Your Configuration

If you have custom configuration files that reference old template paths:

**Old (deprecated):**
```yaml
index_generator:
  template: "_layouts/group_index.html"
```

**New (correct):**
```yaml
index_generator:
  template: "group_index.html"
```

### 2. Automatic Migration

The system now automatically detects and converts legacy template paths:
- Legacy paths like `_layouts/group_index.html` are automatically converted to `group_index.html`
- A deprecation warning is issued to help you update your configuration

### 3. Verify Template Availability

The system now provides better error messages when templates are not found:
- Lists all available templates in the error message
- Shows both user-defined and default Niamoto templates

### 4. Template Search Order

Niamoto uses a `ChoiceLoader` that searches templates in this order:
1. **User templates**: Your project's template directory (specified in `template_dir`)
2. **Default templates**: Niamoto's built-in templates

## Debugging Steps

If you're still experiencing template issues:

1. **Check your configuration**:
   ```bash
   # Verify your export.yml uses the correct template paths
   grep -r "_layouts" config/export.yml
   ```

2. **Enable debug logging** to see available templates:
   ```bash
   # The system will log available templates when debug logging is enabled
   uv run niamoto export web_pages
   ```

3. **Verify template directory**:
   ```bash
   # Check that your template directory exists and is accessible
   ls -la templates/
   ```

## Prevention

To avoid this issue in the future:
- Always use the simplified template names (e.g., `group_index.html`)
- Avoid referencing the `_layouts/` subdirectory
- Keep your Niamoto installation up to date

## Related Files

- `src/niamoto/publish/templates/group_index.html` - Default template
- `src/niamoto/core/plugins/exporters/index_generator.py` - Template loading logic
- `src/niamoto/core/plugins/models.py` - Configuration validation with auto-migration
