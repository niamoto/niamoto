# Configuration Analysis

Use this checklist when reviewing a complex configuration change.

## Checklist

1. Keep import, transform, and export responsibilities separate.
2. Prefer explicit identifiers and group names over inferred behavior.
3. Confirm that plugin parameters match the plugin family that consumes them.
4. Check whether repeated blocks should stay explicit or become a shared preset.
5. Verify that the same concept is not defined twice across YAML files.

## Related docs

- [configuration-guide.md](configuration-guide.md)
- [yaml-strategies.md](yaml-strategies.md)
- [templates-hierarchy.md](templates-hierarchy.md)
