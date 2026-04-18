# Templates and Hierarchy Patterns

Reusable templates help when a block stays stable across several entities or
widgets. Hierarchies stay easier to debug when identifiers and parent-child
relationships remain visible in configuration.

## Templates

Use shared templates or presets only when they remove stable duplication. If a
block still changes substantially from one entity or widget to another, keep it
explicit in the project config.

## Hierarchies

Hierarchy handling should remain visible in the configuration:

- reference imports define the identifiers and parent-child structure
- transforms describe how grouped outputs are computed on top of that structure
- widgets and exports consume the resulting grouped data

## Related docs

- [configuration-guide.md](configuration-guide.md)
- [Import workflow](../02-user-guide/import.md)
- [Collections](../02-user-guide/collections.md)
