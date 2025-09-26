# Niamoto GUI Architecture

## Overview

The Niamoto GUI is a modern web application built with React and FastAPI, providing a visual interface for configuring and managing ecological data pipelines. This document outlines the technical architecture, design patterns, and development standards.

## Technology Stack

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS v4** - Utility-first styling
- **shadcn/ui** - Component library
- **Lucide React** - Icon library
- **React Router v6** - Client-side routing
- **Zustand** - State management
- **React Query** - Server state management
- **React Dropzone** - File uploads

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **SQLAlchemy** - ORM
- **GeoAlchemy2** - Spatial extensions
- **GeoPandas** - Spatial data processing
- **Pandas** - Data manipulation

## Project Structure

```
src/niamoto/gui/
├── api/                    # FastAPI backend
│   ├── app.py             # Application setup
│   └── routers/           # API endpoints
│       ├── config.py      # Configuration endpoints
│       └── files.py       # File management
├── ui/                    # React frontend
│   ├── src/
│   │   ├── components/    # Reusable components
│   │   │   ├── ui/       # Base UI components
│   │   │   └── import-wizard/  # Feature components
│   │   ├── pages/        # Route pages
│   │   ├── lib/          # Utilities
│   │   └── App.tsx       # Main app component
│   └── dist/             # Production build
└── README.md             # GUI documentation
```

## Architecture Patterns

### Frontend Architecture

#### Component Hierarchy
```
App
├── MainLayout
│   ├── Sidebar
│   │   ├── SidebarHeader
│   │   ├── SidebarNav
│   │   └── SidebarFooter
│   └── Main Content (Outlet)
│       ├── ImportPage
│       ├── TransformPage
│       ├── ExportPage
│       └── VisualizePage
```

#### State Management Pattern
```typescript
// Global state with Zustand
const useImportStore = create<ImportStore>((set) => ({
  configs: [],
  currentConfig: null,
  setConfig: (config) => set({ currentConfig: config }),
  addConfig: (config) => set((state) => ({
    configs: [...state.configs, config]
  })),
}))

// Server state with React Query
const { data, isLoading, error } = useQuery({
  queryKey: ['fileAnalysis', file],
  queryFn: () => analyzeFile(file),
  enabled: !!file,
})
```

#### Component Patterns
```typescript
// Compound Components
<ImportWizard>
  <ImportWizard.Steps />
  <ImportWizard.Content />
  <ImportWizard.Navigation />
</ImportWizard>

// Render Props
<FileUpload
  render={({ isDragging, files }) => (
    <DropZone active={isDragging}>
      {files.map(file => <FileItem key={file.name} file={file} />)}
    </DropZone>
  )}
/>

// Custom Hooks
function useFileAnalysis(file: File) {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (file) analyzeFile(file).then(setAnalysis)
  }, [file])

  return { analysis, loading }
}
```

### Backend Architecture

#### API Structure
```python
# Modular router organization
app = FastAPI()
app.include_router(config.router, prefix="/api/config")
app.include_router(files.router, prefix="/api/files")
app.include_router(import.router, prefix="/api/import")
app.include_router(transform.router, prefix="/api/transform")
app.include_router(export.router, prefix="/api/export")
```

#### Request/Response Pattern
```python
# Pydantic models for validation
class FileAnalysisRequest(BaseModel):
    file: UploadFile
    import_type: ImportType

class FileAnalysisResponse(BaseModel):
    filename: str
    columns: List[str]
    row_count: int
    suggestions: Dict[str, List[str]]

# Endpoint implementation
@router.post("/analyze", response_model=FileAnalysisResponse)
async def analyze_file(request: FileAnalysisRequest):
    # Process file
    # Return structured response
```

#### Service Layer Pattern
```python
class ImportService:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.plot_importer = PlotImporter(self.db)

    async def import_taxonomy(self, config: ImportConfig):
        # Validate configuration
        # Execute import
        # Return results
```

## Communication Patterns

### API Communication Flow
```
Frontend                    Backend                     Database
    |                          |                           |
    |-- POST /api/analyze ---> |                           |
    |                          |-- Analyze file --------> |
    |                          |<-- Return schema -------- |
    |<-- Suggestions ---------- |                           |
    |                          |                           |
    |-- POST /api/import ----> |                           |
    |                          |-- Import data ---------> |
    |                          |-- Stream progress -----> |
    |<-- Progress updates ----- |                           |
    |<-- Final result --------- |<-- Confirmation -------- |
```

### WebSocket for Real-time Updates
```typescript
// Frontend
const ws = new WebSocket('ws://localhost:8080/ws')
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data)
  updateProgress(progress)
}

// Backend
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async for progress in import_progress():
        await websocket.send_json(progress)
```

## Error Handling

### Frontend Error Boundaries
```typescript
class ErrorBoundary extends Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
    this.setState({ hasError: true })
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />
    }
    return this.props.children
  }
}
```

### Backend Error Handling
```python
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )
```

## Performance Optimization

### Frontend Optimizations
- **Code Splitting**: Dynamic imports for large components
- **Lazy Loading**: React.lazy for route components
- **Memoization**: useMemo and React.memo for expensive computations
- **Virtual Scrolling**: For large data lists
- **Debouncing**: For search and filter inputs

### Backend Optimizations
- **Streaming Responses**: For large file downloads
- **Caching**: Redis for frequently accessed data
- **Pagination**: For large datasets
- **Background Tasks**: Celery for long-running operations
- **Connection Pooling**: For database connections

## Security Considerations

### Authentication & Authorization
```python
# JWT token validation
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
```

### Input Validation
- File type validation
- Size limits
- Content scanning
- SQL injection prevention
- XSS protection

## Development Workflow

### Local Development
```bash
# Backend
cd src/niamoto/gui
uvicorn api.app:app --reload

# Frontend
cd src/niamoto/gui/ui
npm run dev
```

### Testing Strategy
```typescript
// Component Testing
describe('ImportWizard', () => {
  it('should advance to next step when valid', () => {
    const { getByText } = render(<ImportWizard />)
    fireEvent.click(getByText('Next'))
    expect(getByText('File Selection')).toBeInTheDocument()
  })
})

// API Testing
def test_file_analysis():
    response = client.post("/api/files/analyze", files={"file": ...})
    assert response.status_code == 200
    assert "columns" in response.json()
```

### Build Process
```bash
# Frontend build
npm run build

# Docker image
docker build -t niamoto-gui .
```

## Deployment Architecture

### Container Structure
```yaml
version: '3.8'
services:
  frontend:
    image: niamoto-gui-frontend
    ports:
      - "80:80"

  backend:
    image: niamoto-gui-backend
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://...

  database:
    image: postgis/postgis
    volumes:
      - db-data:/var/lib/postgresql/data
```

### Scaling Considerations
- Horizontal scaling with load balancer
- CDN for static assets
- Database read replicas
- Caching layer (Redis)
- Message queue for async tasks

## Monitoring & Logging

### Frontend Monitoring
```typescript
// Error tracking with Sentry
Sentry.init({
  dsn: "YOUR_SENTRY_DSN",
  integrations: [new BrowserTracing()],
  tracesSampleRate: 1.0,
})

// Performance monitoring
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    analytics.track('performance', {
      name: entry.name,
      duration: entry.duration,
    })
  }
})
```

### Backend Logging
```python
# Structured logging
import structlog

logger = structlog.get_logger()

@router.post("/import")
async def import_data(config: ImportConfig):
    logger.info("import_started", config=config.dict())
    try:
        result = await import_service.execute(config)
        logger.info("import_completed", records=result.count)
        return result
    except Exception as e:
        logger.error("import_failed", error=str(e))
        raise
```

## Best Practices

### Code Style
- **TypeScript**: Strict mode enabled
- **Python**: Black formatter, mypy type checking
- **Components**: Functional components with hooks
- **Naming**: Clear, descriptive names

### Git Workflow
- Feature branches
- Conventional commits
- PR reviews required
- CI/CD pipeline

### Documentation
- Component documentation with JSDoc
- API documentation with OpenAPI
- README files for each module
- Architecture decision records

## Future Considerations

### Microservices Architecture
- Separate services for import, transform, export
- API Gateway
- Service mesh
- Event-driven communication

### Performance Enhancements
- GraphQL for efficient data fetching
- Server-side rendering with Next.js
- Edge computing for global distribution
- WebAssembly for compute-intensive tasks

### Advanced Features
- Plugin system for custom components
- Multi-tenancy support
- Real-time collaboration
- Machine learning integration
