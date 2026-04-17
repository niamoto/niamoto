# Configuration Guide

Niamoto splits configuration by pipeline stage so each file answers one
question.

## Main files

- `config.yml`: runtime settings such as paths and shared services
- `import.yml`: raw sources, entity definitions, and import rules
- `transform.yml`: grouped statistics and reusable computed outputs
- `export.yml`: website export and machine-readable outputs
- `deploy.yml`: deployment targets and platform settings, when present

## Boundary rules

- `import.yml` answers: where does the data come from?
- `transform.yml` answers: what do we compute from it?
- `export.yml` answers: how do we publish it?
- `deploy.yml` answers: where do published outputs go?

If a change spans more than one of these questions, document the boundary
explicitly instead of hiding it in one large config block.

## Related docs

- [Import workflow](../02-user-guide/import.md)
- [Transform workflow](../02-user-guide/transform.md)
- [Export workflow](../02-user-guide/export.md)
- [plugin-api.md](plugin-api.md)
