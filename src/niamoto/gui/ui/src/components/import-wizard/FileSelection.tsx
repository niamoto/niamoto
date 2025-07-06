import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { ImportType } from './ImportWizard'

interface FileSelectionProps {
  importType: ImportType
  onFileSelected: (file: File, analysis: any) => void
}

const acceptedFormats: Record<ImportType, Record<string, string[]>> = {
  taxonomy: {
    'text/csv': ['.csv'],
  },
  plots: {
    'text/csv': ['.csv'],
    'application/geopackage+sqlite3': ['.gpkg'],
    'application/x-shapefile': ['.shp'],
  },
  occurrences: {
    'text/csv': ['.csv'],
  },
  shapes: {
    'application/geopackage+sqlite3': ['.gpkg'],
    'application/x-shapefile': ['.shp'],
    'application/json': ['.json', '.geojson'],
    'application/zip': ['.zip'],
  },
}

export function FileSelection({ importType, onFileSelected }: FileSelectionProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const analyzeFile = useCallback(async (file: File) => {
    setIsAnalyzing(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('import_type', importType)

      const response = await fetch('/api/files/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to analyze file')
      }

      const result = await response.json()
      setAnalysis(result)
      onFileSelected(file, result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze file')
    } finally {
      setIsAnalyzing(false)
    }
  }, [importType, onFileSelected])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      setSelectedFile(file)
      await analyzeFile(file)
    }
  }, [analyzeFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFormats[importType],
    multiple: false,
  })

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Select File</h2>

      {!selectedFile ? (
        <div
          {...getRootProps()}
          className={cn(
            "cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors",
            isDragActive
              ? "border-primary bg-primary/10"
              : "border-gray-300 hover:border-gray-400"
          )}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          {isDragActive ? (
            <p className="text-sm font-medium">Drop the file here...</p>
          ) : (
            <>
              <p className="text-sm font-medium">
                Drag and drop your {importType} file here, or click to browse
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Supported formats: {Object.values(acceptedFormats[importType]).flat().join(', ')}
                {importType === 'shapes' && (
                  <span className="block mt-1 text-amber-600">
                    Note: For shapefiles, please upload a ZIP containing all required files (.shp, .shx, .dbf, etc.)
                  </span>
                )}
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3">
                <FileText className="mt-1 h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(selectedFile.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSelectedFile(null)
                  setAnalysis(null)
                  setError(null)
                }}
              >
                Change
              </Button>
            </div>
          </div>

          {isAnalyzing && (
            <div className="rounded-lg border bg-muted/50 p-4">
              <div className="flex items-center space-x-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <p className="text-sm">Analyzing file...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <div className="flex items-start space-x-2">
                <AlertCircle className="mt-0.5 h-4 w-4 text-destructive" />
                <div>
                  <p className="text-sm font-medium text-destructive">Analysis Failed</p>
                  <p className="text-sm text-destructive/80">{error}</p>
                </div>
              </div>
            </div>
          )}

          {analysis && (
            <div className="rounded-lg border bg-accent/50 p-4">
              <div className="flex items-start space-x-2">
                <Check className="mt-0.5 h-4 w-4 text-primary" />
                <div className="flex-1">
                  <p className="text-sm font-medium">File Analysis Complete</p>
                  <FileAnalysisDetails analysis={analysis} importType={importType} />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface FileAnalysisDetailsProps {
  analysis: any
  importType: ImportType
}

function FileAnalysisDetails({ analysis }: FileAnalysisDetailsProps) {
  if (!analysis) return null

  return (
    <div className="mt-2 space-y-1 text-sm text-muted-foreground">
      {analysis.row_count && (
        <p>• {analysis.row_count.toLocaleString()} rows</p>
      )}
      {analysis.columns && (
        <p>• {analysis.columns.length} columns detected</p>
      )}
      {analysis.feature_count && (
        <p>• {analysis.feature_count.toLocaleString()} features</p>
      )}
      {analysis.geometry_types && analysis.geometry_types.length > 0 && (
        <p>• Geometry types: {analysis.geometry_types.join(', ')}</p>
      )}
      {analysis.analysis?.has_lat_lon && (
        <p>• ✓ Coordinate columns detected</p>
      )}
      {analysis.analysis?.has_geometry && (
        <p>• ✓ Geometry column detected</p>
      )}
    </div>
  )
}
