/**
 * Upload Zone - Specialized single-file CSV uploader
 *
 * This component is intentionally narrower than FileUploadZone:
 * it is only used by AddSourceDialog for precomputed auxiliary CSV sources.
 * The main import workflow uses FileUploadZone.
 */

import { useCallback, useState } from 'react'
import { Upload, FileSpreadsheet, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface UploadZoneProps {
  onFileSelect: (file: File) => void
  isUploading?: boolean
  error?: string | null
}

export function UploadZone({ onFileSelect, isUploading, error }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragOver(false)

      const files = e.dataTransfer.files
      if (files.length > 0) {
        const file = files[0]
        if (file.name.endsWith('.csv')) {
          onFileSelect(file)
        }
      }
    },
    [onFileSelect]
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        onFileSelect(files[0])
      }
      // Reset input so same file can be selected again
      e.target.value = ''
    },
    [onFileSelect]
  )

  return (
    <div className="space-y-3">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'relative flex min-h-[120px] flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors',
          isDragOver
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-muted-foreground/50',
          isUploading && 'pointer-events-none opacity-50'
        )}
      >
        <input
          type="file"
          accept=".csv"
          onChange={handleFileInput}
          className="absolute inset-0 cursor-pointer opacity-0"
          disabled={isUploading}
        />

        {isUploading ? (
          <>
            <div className="mb-2 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">Analyse en cours...</p>
          </>
        ) : (
          <>
            <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="mb-1 text-sm font-medium">
              Glissez un fichier CSV ici
            </p>
            <p className="text-xs text-muted-foreground">
              ou cliquez pour parcourir
            </p>
          </>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Format Help */}
      <div className="rounded-md bg-muted/50 p-3 text-xs">
        <div className="mb-2 flex items-center gap-1.5 font-medium text-foreground">
          <FileSpreadsheet className="h-3.5 w-3.5" />
          Format attendu
        </div>
        <div className="space-y-1 text-muted-foreground">
          <p>
            <span className="font-mono text-foreground">class_object</span> - Type de statistique
          </p>
          <p>
            <span className="font-mono text-foreground">class_name</span> - Categorie ou valeur
          </p>
          <p>
            <span className="font-mono text-foreground">class_value</span> - Valeur numerique
          </p>
          <p className="mt-1.5 text-[10px]">
            + colonne d'entite : plot_id, shape_id, taxon_id, id...
          </p>
        </div>
      </div>
    </div>
  )
}
