import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'
import { FolderOpen } from 'lucide-react'

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  className?: string
}

export function FileUpload({ onFilesSelected, className }: FileUploadProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      onFilesSelected(acceptedFiles)
    },
    [onFilesSelected]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/json': ['.json', '.geojson'],
      'application/x-shapefile': ['.shp'],
    },
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        'cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors',
        isDragActive
          ? 'border-primary bg-primary/10'
          : 'border-gray-300 hover:border-gray-400',
        className
      )}
    >
      <input {...getInputProps()} />
      <div className="space-y-2">
        <FolderOpen className="mx-auto h-12 w-12 text-muted-foreground" />
        {isDragActive ? (
          <p className="text-sm font-medium">Drop the files here...</p>
        ) : (
          <>
            <p className="text-sm font-medium">
              Drag and drop files here, or click to browse
            </p>
            <p className="text-xs text-muted-foreground">
              Supported formats: CSV, Excel, JSON, GeoJSON, Shapefile
            </p>
          </>
        )}
      </div>
    </div>
  )
}
