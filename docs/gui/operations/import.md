# Import Operation - GUI Documentation

## Overview

The Import operation in Niamoto GUI provides a user-friendly interface for importing various types of ecological data into the database. It transforms the complex `import.yml` configuration into an intuitive multi-step wizard.

## Current Implementation

### User Interface Flow

The import process is structured as a 5-step wizard:

1. **Data Source Selection** - Choose the type of data to import
2. **File Selection & Analysis** - Upload files and preview their structure
3. **Field Mapping** - Map source columns to database fields
4. **Advanced Options** - Configure additional settings (API enrichment, hierarchies)
5. **Review & Import** - Preview configuration and execute import

### Components Architecture

```
src/niamoto/gui/ui/src/
├── pages/
│   └── import.tsx              # Main import page
└── components/
    └── import-wizard/
        ├── ImportWizard.tsx    # Main wizard container
        ├── FileSelection.tsx   # File upload with drag-and-drop
        └── ColumnMapper.tsx    # Visual field mapping interface
```

### Key Features Implemented

#### 1. Smart File Analysis
- Automatic file type detection (CSV, Excel, GeoJSON, GeoPackage)
- Column type inference
- Geometry detection (WKT, coordinates)
- Row count and sample data preview
- Smart field suggestions based on column names

#### 2. Visual Field Mapping
- Drag-and-drop interface for mapping columns
- Auto-suggestions for common field names
- Required field validation
- Real-time validation feedback

#### 3. Multi-Format Support
- **Taxonomy**: CSV files with hierarchical data
- **Plots**: CSV or spatial files (GeoPackage, Shapefile)
- **Occurrences**: CSV with species observations
- **Shapes**: GeoPackage, Shapefile, GeoJSON

### API Endpoints

```python
# File analysis endpoint
POST /api/files/analyze
Body: FormData {
    file: File,
    import_type: "taxonomy" | "plots" | "occurrences" | "shapes"
}
Response: {
    filename: string,
    type: string,
    columns: string[],
    column_types: Record<string, string>,
    row_count: number,
    sample_data: any[],
    suggestions: Record<string, string[]>
}
```

### Technical Workflow Example

```typescript
// 1. User selects import type
const config: ImportConfig = {
    type: 'taxonomy'
}

// 2. User uploads file
const file = new File(['...'], 'taxonomy.csv')
const formData = new FormData()
formData.append('file', file)
formData.append('import_type', 'taxonomy')

// 3. File is analyzed
const analysis = await fetch('/api/files/analyze', {
    method: 'POST',
    body: formData
}).then(r => r.json())

// 4. User maps fields
const mappings = {
    taxon_id: 'id_taxonref',
    full_name: 'scientific_name',
    family: 'family',
    genus: 'genus'
}

// 5. Configuration is generated
const finalConfig = {
    type: 'taxonomy',
    file: file,
    fileAnalysis: analysis,
    fieldMappings: mappings,
    advancedOptions: {
        api_enrichment: true
    }
}
```

## Remaining Tasks

### High Priority
1. **Advanced Options Component**
   - API enrichment configuration
   - Hierarchical import settings for plots
   - Source selection for taxonomy (file vs occurrence)
   - Rate limiting controls

2. **Review & Import Component**
   - Configuration preview
   - YAML generation preview
   - Import execution with progress tracking
   - Error handling and reporting

3. **Import Execution Endpoint**
   ```python
   POST /api/import/execute
   Body: ImportConfig
   Response: Stream of progress updates
   ```

### Medium Priority
1. **Data Preview Component**
   - Table view of sample data
   - Highlight mapped columns
   - Show data transformations

2. **Validation Endpoint**
   ```python
   POST /api/import/validate
   Body: ImportConfig
   Response: ValidationResult
   ```

3. **Progress Monitoring**
   - Real-time import progress
   - Record count updates
   - Error accumulation

### Low Priority
1. **Configuration Templates**
   - Save import configurations
   - Load previous configurations
   - Share configurations

2. **Batch Import**
   - Import multiple files at once
   - Queue management

## Design Suggestions

### 1. Enhanced File Analysis
- **Geometry Preview**: Show shapes on a map for spatial files
- **Data Quality Indicators**: Show completeness, duplicates, anomalies
- **Encoding Detection**: Handle various file encodings automatically

### 2. Improved Field Mapping
- **AI-Powered Suggestions**: Use ML to suggest mappings based on data patterns
- **Transformation Rules**: Allow simple transformations (uppercase, trim, etc.)
- **Conditional Mappings**: Map based on other column values

### 3. Advanced Options UI
```
┌─────────────────────────────────────┐
│ Advanced Options                     │
├─────────────────────────────────────┤
│ ☑ Enable API Enrichment             │
│   ├─ API: endemia.nc               │
│   ├─ Rate limit: 2 req/sec         │
│   └─ Cache results                 │
│                                     │
│ ☐ Hierarchical Import (Plots)       │
│   ├─ Levels: Country > Plot        │
│   └─ Aggregate geometry            │
│                                     │
│ ☐ Extract from Occurrences (Tax)    │
│   └─ Generate missing ranks        │
└─────────────────────────────────────┘
```

### 4. Import History
- Track all imports with timestamps
- Show success/failure statistics
- Allow re-running previous imports
- Rollback functionality

### 5. Layout Improvements

#### Split View for Large Datasets
```
┌─────────────┬─────────────────────┐
│ Source Data │ Target Schema       │
├─────────────┼─────────────────────┤
│ CSV Preview │ Database Preview    │
│             │                     │
│ id_taxon    │ taxon_ref          │
│ name     ──→│ ├─ id              │
│ family      │ ├─ full_name       │
│             │ └─ family          │
└─────────────┴─────────────────────┘
```

#### Responsive Mobile View
- Stack wizard steps vertically on mobile
- Simplified field mapping for touch devices
- Progressive disclosure of advanced options

## Code Structure

### Frontend State Management
```typescript
// Using Zustand for import state
interface ImportStore {
    configs: ImportConfig[]
    currentConfig: ImportConfig | null
    setConfig: (config: ImportConfig) => void
    addConfig: (config: ImportConfig) => void
    executeImport: () => Promise<void>
}
```

### Component Hierarchy
```
ImportPage
└── ImportWizard
    ├── StepIndicator
    ├── StepContent
    │   ├── SourceSelection
    │   ├── FileSelection
    │   ├── ColumnMapper
    │   ├── AdvancedOptions
    │   └── ReviewImport
    └── NavigationControls
```

### Error Handling Pattern
```typescript
try {
    const result = await importService.execute(config)
    showSuccess(`Imported ${result.recordCount} records`)
} catch (error) {
    if (error instanceof ValidationError) {
        showValidationErrors(error.errors)
    } else if (error instanceof ImportError) {
        showImportError(error.message, error.details)
    } else {
        showGenericError('Import failed')
    }
}
```

## Future Enhancements

1. **Real-time Collaboration**
   - Multiple users can work on same import
   - Comments and annotations
   - Approval workflow

2. **Import Scheduling**
   - Schedule recurring imports
   - Watch folders for new files
   - Automated imports from APIs

3. **Data Transformation Pipeline**
   - Visual transformation builder
   - Custom Python/SQL transformations
   - Preview transformations before import

4. **Integration with External Systems**
   - Direct database connections
   - API integrations
   - Cloud storage support (S3, Google Drive)

5. **Advanced Validation Rules**
   - Custom validation scripts
   - Cross-file validation
   - Reference data validation
