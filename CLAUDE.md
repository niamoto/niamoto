# Niamoto Development

Ecological data platform: **Import → Transform → Export** via plugins.
Test instance: `test-instance/niamoto-test/`

**Golden Rule**: If a field botanist understands it in 2 minutes, it's the right solution.

## Ask Before Implementing When It Changes Semantics

Clarify with the user when the change affects one of these boundaries:
- **Layer choice**: import.yml (data loading), transform.yml (statistics), export.yml (visualization)
- **Plugin scope**: Creating new plugin vs modifying existing one
- **Architecture trade-offs**: Performance vs simplicity, DuckDB native vs Pandas
- **Data expectations**: Input format, output structure, error handling strategy

If the answer is already discoverable from the code or config, prefer checking first instead of asking.

## Skills

Use repo-local skills only when they are available in the current environment and clearly help with the task.

## Commands

Typical validation workflow:

```bash
uv run pytest
uvx ruff check src/ --fix
uvx ruff format src/
```

Frontend work:

```bash
cd src/niamoto/gui/ui
pnpm build
```

GUI dev workflow reference:

```bash
./scripts/dev_gui.sh test-instance/niamoto-nc
```

More commands:

```bash
docs/development-commands.md
```

## Critical Rules

### Genericity First — No Hardcoding

Niamoto is a **generic ecological data platform**, not a New Caledonia-specific tool. Code must work for any dataset, any taxonomy, any field names.

**NEVER hardcode:**
- Table names (`dataset_occurrences`, `taxon`, etc.) → Use `EntityRegistry.get(name).table_name`
- Field names (`id_taxonref`, `dbh`, `height`, etc.) → Read from config or schema
- Entity names (`occurrences`, `plots`, etc.) → Use `EntityRegistry.list_entities()`
- Domain values (`endemic`, `native`, etc.) → Read from data or config

**Allowed exceptions:**
- Well-known API standards (Darwin Core fields like `scientificName`, `decimalLatitude`)
- Internal metadata tables (`niamoto_metadata_*`)
- Framework conventions (Pydantic `model_config`, plugin `config_model`)

**Pattern to follow:**
```python
# BAD - hardcoded
for table in ["dataset_occurrences", "occurrences"]:
    cols = get_columns(table)

# GOOD - generic via EntityRegistry
registry = EntityRegistry(db)
for entity in registry.list_entities(kind=EntityKind.DATASET):
    cols = get_columns(entity.table_name)
```

When tempted to hardcode, ask: "Would this work for a forest inventory in Madagascar? A coral reef study in Indonesia?"

### Other Rules

- Database access via **services only**, never directly in plugins
- Plugins define `config_model` (Pydantic) for validation
- Use `Database(path, read_only=True)` when another process locks the DB
- Register plugins with `@register("name", PluginType.TRANSFORMER)`
- **Linting**: use `uvx ruff` (never `ruff` alone) — ruff is not installed globally
- **Commits**: always in English (conventional commits format)
- Keep GUI docs and README files in English
- The frontend architecture now follows `src/app`, `src/features`, and `src/shared`

## References

- Plugin development: `docs/04-plugin-development/`
- Architecture decisions: `docs/09-architecture/`
- GUI documentation: `docs/06-gui/`
- GUI code-level docs:
  - `src/niamoto/gui/README.md`
  - `src/niamoto/gui/ui/README.md`
