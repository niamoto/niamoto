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
        ├── ColumnMapper.tsx    # Visual field mapping interface
        ├── AdvancedOptions.tsx # Type-specific advanced settings
        └── ReviewImport.tsx    # Final review and execution
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

### Import Process Flow

1. **File Upload & Analysis**: Automatic detection of file type and structure
2. **Field Mapping**: Visual drag-and-drop with auto-suggestions
3. **Advanced Configuration**: Type-specific options for fine-tuning
4. **Validation**: Real-time validation with detailed feedback
5. **Asynchronous Execution**: Background processing with progress tracking

### Technical Workflow Example

```typescript
// 1. User selects import type
const config: ImportConfig = {
    importType: 'taxonomy'  // Note: uses importType, not type
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
// Returns: { filename, type, columns, column_types, row_count, sample_data, suggestions }

// 4. User maps fields
const mappings = {
    taxon_id: 'id_taxonref',
    full_name: 'scientific_name',
    family: 'family',
    genus: 'genus'
}

// 5. Configuration is generated
const finalConfig = {
    importType: 'taxonomy',
    file: file,
    fileAnalysis: analysis,
    fieldMappings: mappings,
    advancedOptions: {
        taxonomy: {  // Options are nested by import type
            useApiEnrichment: true,
            apiProvider: 'gbif',
            rateLimit: 2,
            extractFromOccurrences: false,
            updateExisting: true
        }
    }
}
```

## Current Features Implemented

### Advanced Options by Import Type

#### Taxonomy Options
- **API Enrichment**: GBIF or POWO integration with rate limiting
- **Extract from Occurrences**: Build taxonomy from occurrence data
- **Update Existing**: Option to update existing taxa records

#### Plots Options
- **Import Hierarchy**: Support for hierarchical plot structures
- **Hierarchy Delimiter**: Configurable delimiter for nested plots
- **Generate IDs**: Auto-generate plot identifiers with custom prefix
- **Validate Geometry**: Geometry validation before import

#### Occurrences Options
- **Link to Plots**: Automatic linking to existing plots
- **Create Missing Taxa**: Option to create taxa entries for unknown IDs
- **Validate Coordinates**: Coordinate validation
- **Duplicate Strategy**: Skip, update, or error on duplicates

#### Shapes Options
- **Simplify Geometry**: Reduce geometry complexity with tolerance
- **Calculate Area**: Auto-calculate shape areas
- **Calculate Perimeter**: Auto-calculate shape perimeters

### Import Execution Features

- **Asynchronous Processing**: Background job execution
- **Progress Tracking**: Real-time progress with polling
- **Validation Before Import**: Automatic validation on review step
- **Configuration Export**: Download import config as JSON
- **Error Handling**: Detailed error and warning messages

## Remaining Tasks

### High Priority
1. **Integration with Niamoto Core**
   - Connect to actual import engine
   - Real database operations
   - Proper error handling from backend

2. **Shapefile Support**
   - Multi-file upload for .shp/.shx/.dbf
   - Zip file extraction
   - Coordinate system detection

### Medium Priority
1. **Import History**
   - Persist job history in database
   - Show previous imports
   - Re-run functionality

2. **Batch Operations**
   - Import multiple files at once
   - Queue management interface

### Low Priority
1. **Configuration Templates**
   - Save/load import configurations
   - Share configurations between users
   - Template marketplace

2. **Advanced Transformations**
   - Custom field transformations
   - Data cleaning rules
   - Conditional mappings

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

## API Documentation

### Endpoints

The import functionality is powered by several API endpoints:

#### File Analysis
```
POST /api/files/analyze
Content-Type: multipart/form-data

FormData:
  - file: File
  - import_type: string

Response: {
  filename: string,
  type: "csv" | "excel" | "json" | "geojson" | "geopackage",
  columns: string[],
  column_types: Record<string, string>,
  row_count?: number,
  feature_count?: number,  // For spatial files
  sample_data: any[],
  suggestions: Record<string, string[]>,
  geometry_types?: string[],  // For spatial files
  crs?: string,  // For spatial files
  bounds?: number[]  // For spatial files
}
```

#### Import Validation
```
POST /api/imports/validate
Content-Type: multipart/form-data

FormData:
  - file: File
  - import_type: string
  - file_name: string
  - field_mappings: string (JSON)
  - advanced_options?: string (JSON)

Response: {
  valid: boolean,
  errors: string[],
  warnings: string[],
  summary: {
    import_type: string,
    file_name: string,
    mapped_fields: number,
    validation_errors: number,
    validation_warnings: number
  }
}
```

#### Import Execution
```
POST /api/imports/execute
Content-Type: multipart/form-data

FormData:
  - file: File
  - import_type: string
  - file_name: string
  - field_mappings: string (JSON)
  - advanced_options?: string (JSON)
  - validate_only?: boolean

Response: {
  job_id: string,
  status: "pending",
  created_at: string,
  message: string
}
```

#### Job Status
```
GET /api/imports/jobs/{job_id}

Response: {
  id: string,
  status: "pending" | "running" | "completed" | "failed",
  import_type: string,
  file_name: string,
  created_at: string,
  started_at?: string,
  completed_at?: string,
  progress: number,
  total_records: number,
  processed_records: number,
  errors: string[],
  warnings: string[]
}
```

#### List Jobs
```
GET /api/imports/jobs?limit=10&offset=0&status=completed

Response: {
  total: number,
  limit: number,
  offset: number,
  jobs: ImportJob[]
}
```

### Development Workflow

When developing the import interface, use the two-server setup:

1. **API Server** (port 8080):
   ```bash
   uv run python -m niamoto gui --no-browser
   ```

2. **React Dev Server** (port 5173):
   ```bash
   cd src/niamoto/gui/ui
   npm run dev
   ```

The Vite config includes a proxy that forwards `/api/*` requests to port 8080.

### Testing Tips

1. **Test Files**: Create small CSV files for quick testing
2. **API Testing**: Use FastAPI docs at http://localhost:8080/docs
3. **Network Tab**: Monitor API calls in browser DevTools
4. **State Debugging**: Use React DevTools to inspect component state

### Import Job Management

The import process uses asynchronous job execution with polling:

```typescript
// Start import job
const response = await axios.post('/api/imports/execute', formData)
const jobId = response.data.job_id

// Poll for job status
const pollInterval = setInterval(async () => {
  const job = await axios.get(`/api/imports/jobs/${jobId}`)

  if (job.data.status === 'completed') {
    clearInterval(pollInterval)
    // Handle success
  } else if (job.data.status === 'failed') {
    clearInterval(pollInterval)
    // Handle error
  }

  // Update progress UI
  setProgress(job.data.progress)
}, 1000)
```

The ReviewImport component handles this automatically, showing:
- Progress bar with percentage
- Record count (processed/total)
- Real-time error and warning accumulation
- Success/failure status

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
