# Import Dependencies and Order

The Niamoto GUI enforces the proper import order to maintain data integrity. This document explains the import dependencies and how they are enforced in the interface.

## Import Order

The following import order must be respected:

1. **Taxonomy** - Must be imported first (or extracted from occurrences)
2. **Occurrences** - Requires taxonomy (foreign key: `taxon_ref_id`)
3. **Plots** - Can be imported independently
4. **Shapes** - Can be imported independently

## Dependency Enforcement

### Visual Indicators

The import page shows the status of each import type:
- ✅ Green badge with record count for completed imports
- ❌ Red badge showing missing dependencies
- ⚠️ Gray badge for pending imports

### Import Restrictions

- Import buttons are disabled for types with unmet dependencies
- Clear error messages explain which imports must be completed first
- The wizard shows a warning alert if prerequisites are not met

### Status Checking

The GUI queries the database to check:
- Table existence (`taxon_ref`, `occurrences`, `plot_ref`, `shapes`)
- Row counts for each table
- Dependency requirements based on foreign key constraints

## API Endpoints

### `/api/imports/status`

Returns the current import status:

```json
{
  "taxonomy": {
    "import_type": "taxonomy",
    "is_imported": true,
    "row_count": 1500,
    "dependencies_met": true,
    "missing_dependencies": []
  },
  "occurrences": {
    "import_type": "occurrences",
    "is_imported": false,
    "row_count": 0,
    "dependencies_met": true,
    "missing_dependencies": []
  },
  "plots": {
    "import_type": "plots",
    "is_imported": false,
    "row_count": 0,
    "dependencies_met": true,
    "missing_dependencies": []
  },
  "shapes": {
    "import_type": "shapes",
    "is_imported": false,
    "row_count": 0,
    "dependencies_met": true,
    "missing_dependencies": []
  }
}
```

## User Experience

1. **First-time Users**: See a helpful alert explaining the import order
2. **Progress Tracking**: Visual progress bars show overall import completion
3. **Re-imports**: Users can re-import data with a clear indication of existing data
4. **Guided Workflow**: "Start here" badge on taxonomy for new instances

## Technical Implementation

- React hook `useImportStatus` fetches and caches import status
- Import page checks dependencies before allowing navigation to wizard
- Wizard validates prerequisites at each step
- Real-time status updates after successful imports
