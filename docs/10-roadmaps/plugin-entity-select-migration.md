# Plugin Migration to entity-select Widget

**Date**: 2025-10-22
**Phase**: 2.2 - Progressive Migration
**Goal**: Replace hardcoded `ui:options` with dynamic `entity-select` widget

---

## Summary

**10 plugins** need migration from hardcoded entity options to dynamic entity-select widget.

### Migration Pattern

**BEFORE (hardcoded)**:
```python
source: str = Field(
    default="occurrences",
    description="Data source table name",
    json_schema_extra={
        "ui:widget": "select",
        "ui:options": ["occurrences", "taxonomy", "plots"],
    },
)
```

**AFTER (dynamic)**:
```python
source: str = Field(
    default="occurrences",
    description="Data source entity name",
    json_schema_extra={
        "ui:widget": "entity-select",
        "ui:entity-filter": {"kind": "dataset"}  # Optional: filter by kind
    },
)
```

---

## Plugins to Migrate

### Group 1: General Transformers (3 plugins)
These reference any type of entity.

1. **transformers/aggregation/top_ranking.py**
   - Field: `source`
   - Current options: `["occurrences", "taxonomy", "plots", "shapes"]`
   - Migration: `entity-select` (no filter - all entities)

2. **transformers/aggregation/binary_counter.py**
   - Field: `source`
   - Current options: `["occurrences", "taxonomy", "plots"]`
   - Migration: `entity-select` with `kind: "dataset"` (datasets only)

3. **transformers/distribution/time_series_analysis.py**
   - Field: `source`
   - Current options: `["occurrences", "plots", "observations"]`
   - Migration: `entity-select` with `kind: "dataset"`

---

### Group 2: Class Object Transformers (7 plugins)
These work with shape statistics (intermediate computed data).

**Note**: These reference pre-computed stats tables (`raw_shape_stats`, `shape_stats`),
not direct entities. Current hardcoded options are actually correct since these
are internal transformation outputs, not user-defined entities.

**Decision**: These should probably NOT be migrated to entity-select, as they reference
intermediate data structures, not EntityRegistry entities.

4. transformers/class_objects/series_extractor.py
5. transformers/class_objects/series_matrix_extractor.py
6. transformers/class_objects/categories_extractor.py
7. transformers/class_objects/binary_aggregator.py
8. transformers/class_objects/series_by_axis_extractor.py
9. transformers/class_objects/series_ratio_aggregator.py
10. transformers/class_objects/field_aggregator.py

---

## Migration Plan

### Immediate Migration (Group 1 - 3 plugins)

These plugins should be migrated immediately:

- [x] `transformers/aggregation/top_ranking.py`
- [x] `transformers/aggregation/binary_counter.py`
- [x] `transformers/distribution/time_series_analysis.py`

### Future Consideration (Group 2 - 7 plugins)

These plugins reference intermediate stats tables, not entities.

**Options**:
1. **Leave as-is**: Keep hardcoded options since they're internal
2. **Create stats-select widget**: New widget for intermediate stats tables
3. **Document**: Add comment explaining why they're hardcoded

**Recommendation**: Option 3 - Document and leave hardcoded.

---

## Testing Strategy

After migration:

1. **Backend test**: Verify `/api/entities/available` returns entities
2. **Frontend test**: Open transform config, verify dropdown loads entities
3. **Integration test**: Configure plugin with custom entity, verify save/load
4. **E2E test**: Run full pipeline with migrated plugin

---

## Rollback Plan

If migration causes issues:

1. Git revert migration commit
2. Entity-select widget remains available for future use
3. Plugins fall back to hardcoded options

---

## Notes

- **Breaking change**: Users with custom configs referencing old entity names will need to update
- **Backward compatibility**: Old configs will still work if entity names match
- **Documentation**: Update plugin docs to explain entity-select usage
