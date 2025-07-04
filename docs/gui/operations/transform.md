# Transform Operation - GUI Documentation

## Overview

The Transform operation in Niamoto allows users to configure data transformations and statistical calculations on imported data. It provides a visual interface for creating transformation pipelines that generate derived datasets and statistics.

## Concept

Transformations in Niamoto are plugin-based operations that:
- Calculate statistics (e.g., species richness, diversity indices)
- Generate spatial analyses (e.g., distribution maps, density calculations)
- Create aggregated data (e.g., by region, elevation bands)
- Produce derived metrics for visualization

## Planned Interface Design

### Main Layout Concept

```
┌─────────────────────────────────────────────────────┐
│                Transform Pipeline                    │
├───────────────┬─────────────────────────────────────┤
│ Available     │ Pipeline Canvas                     │
│ Transforms    │                                     │
│               │  ┌─────────┐     ┌─────────┐       │
│ 📊 Statistics │  │ Input   │     │Transform│       │
│ 🗺️  Spatial   │  │ Data    │ ──→ │ Plugin  │ ──→   │
│ 📈 Analysis   │  └─────────┘     └─────────┘       │
│ 🔄 Aggregate  │                                     │
│               │ [Drag transforms here to build]      │
└───────────────┴─────────────────────────────────────┘
```

### Transform Categories

1. **Statistical Transforms**
   - Species richness calculation
   - Shannon diversity index
   - Simpson's index
   - Abundance calculations
   - Top N species analysis

2. **Spatial Transforms**
   - Distribution mapping
   - Density calculations
   - Hotspot analysis
   - Buffer analysis
   - Spatial joins

3. **Aggregation Transforms**
   - Group by taxonomy level
   - Aggregate by geographic region
   - Temporal aggregations
   - Custom groupings

4. **Data Quality Transforms**
   - Duplicate detection
   - Outlier identification
   - Completeness checks
   - Validation reports

## Implementation Plan

### Phase 1: Basic Transform List

```typescript
interface Transform {
  id: string
  name: string
  category: 'statistics' | 'spatial' | 'aggregation' | 'quality'
  description: string
  icon: string
  parameters: Parameter[]
  inputs: InputRequirement[]
  outputs: OutputDefinition[]
}

interface TransformListProps {
  transforms: Transform[]
  onSelect: (transform: Transform) => void
}
```

### Phase 2: Visual Pipeline Builder

```typescript
interface TransformNode {
  id: string
  transformId: string
  position: { x: number; y: number }
  parameters: Record<string, any>
  connections: {
    inputs: Connection[]
    outputs: Connection[]
  }
}

interface Pipeline {
  nodes: TransformNode[]
  connections: Connection[]
  metadata: {
    name: string
    description: string
    created: Date
    modified: Date
  }
}
```

### Phase 3: Parameter Configuration

```
┌─────────────────────────────────────┐
│ Configure: Species Richness         │
├─────────────────────────────────────┤
│ Input Data:                         │
│ ○ All occurrences                  │
│ ● Filtered by: [Select filter]     │
│                                     │
│ Group By:                           │
│ ☑ Plot                             │
│ ☐ Shape (Province)                 │
│ ☐ Elevation band                   │
│                                     │
│ Options:                            │
│ ☑ Include rare species             │
│ ☐ Weight by abundance              │
│                                     │
│ Output Name: species_richness_plot │
└─────────────────────────────────────┘
```

## API Design

### Transform Listing
```python
GET /api/transforms
Response: {
    transforms: [
        {
            id: "species_richness",
            name: "Species Richness",
            category: "statistics",
            description: "Calculate species richness by group",
            parameters: [
                {
                    name: "group_by",
                    type: "select",
                    options: ["plot", "shape", "elevation"]
                }
            ]
        }
    ]
}
```

### Pipeline Execution
```python
POST /api/transform/execute
Body: {
    pipeline: Pipeline,
    options: {
        preview: boolean,
        limit: number
    }
}
Response: Stream of progress and results
```

## UI Components to Build

### 1. TransformCatalog
- Searchable list of available transforms
- Category filters
- Drag source for pipeline builder

### 2. PipelineCanvas
- Visual node editor
- Drag and drop support
- Connection drawing
- Pan and zoom

### 3. TransformNode
- Visual representation of transform
- Input/output ports
- Status indicators
- Quick parameter access

### 4. ParameterPanel
- Dynamic form generation
- Validation
- Help tooltips
- Preview of effect

### 5. ResultsPreview
- Sample output data
- Statistics summary
- Visualization preview

## User Workflow

1. **Select Input Data**
   - Choose from imported datasets
   - Apply filters if needed
   - Preview input statistics

2. **Add Transforms**
   - Browse transform catalog
   - Drag to pipeline canvas
   - Connect transforms

3. **Configure Parameters**
   - Click transform to configure
   - Set parameters
   - Validate configuration

4. **Preview Results**
   - Run preview on sample
   - Check output format
   - Adjust if needed

5. **Execute Pipeline**
   - Run full transformation
   - Monitor progress
   - Save results

## Design Suggestions

### 1. Smart Transform Recommendations
```
Based on your data, we recommend:
• Species Accumulation Curves (you have temporal data)
• Elevation Analysis (you have altitude data)
• Endemic Species Summary (matches your taxonomy)
```

### 2. Transform Templates
- Pre-built pipelines for common analyses
- Community-shared transforms
- Export/import pipeline definitions

### 3. Interactive Preview
- Live preview as parameters change
- Sample size selector
- Before/after comparison

### 4. Visual Feedback
```
┌─────────┐
│Transform│ ← ⚠️ Missing required input
├─────────┤
│ ██░░░░░ │ ← Progress: 25%
└─────────┘

✓ Validated and ready
⚡ Currently executing
❌ Error in configuration
```

## Technical Considerations

### State Management
```typescript
interface TransformStore {
    availableTransforms: Transform[]
    currentPipeline: Pipeline
    executionStatus: ExecutionStatus
    results: TransformResult[]

    addNode: (transform: Transform) => void
    updateNode: (nodeId: string, params: any) => void
    connectNodes: (from: string, to: string) => void
    executePipeline: () => Promise<void>
}
```

### Performance Optimization
- Lazy loading of transform definitions
- Streaming results for large datasets
- Client-side caching of previews
- WebWorker for heavy computations

### Error Handling
- Graceful degradation for failed nodes
- Partial pipeline execution
- Clear error messages with fixes
- Rollback capabilities

## Future Enhancements

1. **AI-Assisted Pipeline Building**
   - Natural language to pipeline
   - Automatic optimization
   - Anomaly detection in results

2. **Collaborative Pipelines**
   - Share pipelines between users
   - Version control
   - Comments and documentation

3. **Custom Transform Development**
   - In-browser Python editor
   - Transform testing framework
   - Publishing to catalog

4. **Real-time Transforms**
   - Live data connections
   - Streaming transformations
   - Incremental updates

5. **Advanced Visualizations**
   - Integrated chart builder
   - Map visualizations
   - 3D representations

## Integration Points

### With Import Operation
- Use imported data as inputs
- Transform during import
- Validation transforms

### With Export Operation
- Export transformed data
- Include in static site
- API endpoints for results

### With Visualization
- Direct visualization of results
- Interactive exploration
- Dashboard integration
