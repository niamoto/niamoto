# YAML Strategies

Keep YAML explicit. Reuse only the parts that are genuinely stable.

## Practical rules

- Prefer explicit, repetitive YAML over clever indirection when the audience is
  primarily domain experts.
- Reuse presets only when the repeated block is stable across several entities.
- Keep field names and group names close to the dataset vocabulary.
- Introduce comments only when a block would otherwise be misread.
- Validate one pipeline stage at a time after a config change.

## Related docs

- [configuration-guide.md](configuration-guide.md)
- [configuration-analysis.md](configuration-analysis.md)
- [Collections](../02-user-guide/collections.md)
