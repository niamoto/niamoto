/**
 * FileUploadZone - Reusable drag & drop upload component
 *
 * Extracted from WelcomeStep for reuse in Flow DataPanel
 */

import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Upload,
  FileText,
  Database,
  AlertCircle,
  X,
  Table2,
  Map,
  Globe,
  Loader2,
} from 'lucide-react'
import { uploadFiles, type UploadedFileInfo } from '@/lib/api/upload'

interface FileUploadZoneProps {
  onFilesReady: (files: UploadedFileInfo[], paths: string[]) => void
  onError?: (error: string) => void
  disabled?: boolean
  compact?: boolean
}

export function FileUploadZone({
  onFilesReady,
  onError,
  disabled = false,
  compact = false,
}: FileUploadZoneProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [existingFiles, setExistingFiles] = useState<string[]>([])
  const [showExistingDialog, setShowExistingDialog] = useState(false)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const files = Array.from(e.dataTransfer.files)
    setSelectedFiles((prev) => [...prev, ...files])
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      setSelectedFiles((prev) => [...prev, ...files])
    }
  }, [])

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const clearFiles = () => {
    setSelectedFiles([])
    setError(null)
  }

  const handleUpload = async (overwrite: boolean = false) => {
    if (selectedFiles.length === 0) return

    try {
      setUploading(true)
      setError(null)
      setUploadProgress(0)

      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 10, 90))
      }, 200)

      const result = await uploadFiles(selectedFiles, overwrite)

      clearInterval(progressInterval)
      setUploadProgress(100)

      // Check if files already exist
      if (!overwrite && result.existing_files && result.existing_files.length > 0) {
        setExistingFiles(result.existing_files)
        setShowExistingDialog(true)
        setUploading(false)
        return
      }

      if (result.success) {
        const filePaths = result.uploaded_files.map((f: UploadedFileInfo) => f.path)
        onFilesReady(result.uploaded_files, filePaths)
        setSelectedFiles([])
      } else {
        const errMsg = result.errors.join(', ') || 'Upload failed'
        setError(errMsg)
        onError?.(errMsg)
      }
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Upload failed'
      setError(errMsg)
      onError?.(errMsg)
    } finally {
      setUploading(false)
    }
  }

  const handleUseExistingFiles = () => {
    const filePaths = existingFiles.map((filename) => `imports/${filename}`)
    const uploadedFiles = existingFiles.map((filename) => ({
      filename,
      path: `imports/${filename}`,
      size: 0,
      size_mb: 0,
      type: filename.split('.').pop() || '',
      category: 'csv' as const,
    }))

    setShowExistingDialog(false)
    setSelectedFiles([])
    onFilesReady(uploadedFiles, filePaths)
  }

  const handleReplaceAll = async () => {
    setShowExistingDialog(false)
    await handleUpload(true)
  }

  const getFileIcon = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'csv':
        return <FileText className="h-4 w-4 text-blue-500" />
      case 'gpkg':
      case 'geojson':
        return <Database className="h-4 w-4 text-green-500" />
      case 'tif':
      case 'tiff':
        return <Database className="h-4 w-4 text-purple-500" />
      default:
        return <FileText className="h-4 w-4 text-gray-500" />
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} Ko`
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`
  }

  const groupedFiles = selectedFiles.reduce(
    (acc, file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || 'other'
      const category =
        ext === 'csv'
          ? 'csv'
          : ['gpkg', 'geojson'].includes(ext)
            ? 'gpkg'
            : ['tif', 'tiff'].includes(ext)
              ? 'tif'
              : 'other'
      if (!acc[category]) acc[category] = []
      acc[category].push(file)
      return acc
    },
    {} as Record<string, File[]>
  )

  const minHeight = compact ? 'min-h-[100px]' : 'min-h-[150px]'

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      {selectedFiles.length === 0 && (
        <div
          className={`flex ${minHeight} cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 transition-colors ${
            dragActive
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/50'
          } ${disabled ? 'pointer-events-none opacity-50' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-upload-zone')?.click()}
        >
          <Upload className={`mb-2 ${compact ? 'h-8 w-8' : 'h-10 w-10'} text-muted-foreground`} />
          <p className="mb-1 text-sm font-medium">Glissez-deposez vos fichiers</p>
          <p className="text-xs text-muted-foreground">CSV, GeoPackage, GeoJSON, TIFF</p>
          <input
            type="file"
            multiple
            accept=".csv,.gpkg,.geojson,.tif,.tiff,.zip"
            onChange={handleFileInput}
            className="hidden"
            id="file-upload-zone"
            disabled={disabled}
          />
        </div>
      )}

      {/* Selected files list */}
      {selectedFiles.length > 0 && (
        <div className="space-y-3">
          {Object.entries(groupedFiles).map(([category, files]) => (
            <div key={category} className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground">
                {category === 'csv' && (
                  <>
                    <Table2 className="h-3 w-3 text-blue-500" />
                    Fichiers CSV
                  </>
                )}
                {category === 'gpkg' && (
                  <>
                    <Map className="h-3 w-3 text-green-500" />
                    GeoPackage/GeoJSON
                  </>
                )}
                {category === 'tif' && (
                  <>
                    <Globe className="h-3 w-3 text-purple-500" />
                    Fichiers TIFF
                  </>
                )}
                {category === 'other' && (
                  <>
                    <FileText className="h-3 w-3 text-gray-500" />
                    Autres fichiers
                  </>
                )}
              </div>

              {files.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 rounded-md border bg-muted/30 p-2"
                >
                  {getFileIcon(file)}
                  <span className="flex-1 truncate text-sm">{file.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(file.size)}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeFile(selectedFiles.indexOf(file))
                    }}
                    disabled={uploading}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          ))}

          {/* Upload progress */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Telechargement...
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          {!uploading && (
            <div className="flex items-center justify-between pt-2">
              <Button variant="outline" size="sm" onClick={clearFiles}>
                Annuler
              </Button>
              <Button onClick={() => handleUpload()} disabled={uploading || disabled}>
                <Upload className="mr-2 h-4 w-4" />
                Telecharger {selectedFiles.length} fichier
                {selectedFiles.length > 1 ? 's' : ''}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Dialog for existing files */}
      <AlertDialog open={showExistingDialog} onOpenChange={setShowExistingDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fichiers existants</AlertDialogTitle>
            <AlertDialogDescription>
              {existingFiles.length} fichier{existingFiles.length !== 1 ? 's' : ''} existe
              {existingFiles.length !== 1 ? 'nt' : ''} deja. Que souhaitez-vous faire ?
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="my-4 max-h-48 overflow-y-auto rounded-lg bg-muted p-4">
            <ul className="space-y-1 text-sm">
              {existingFiles.map((filename, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-500" />
                  <span className="font-mono">{filename}</span>
                </li>
              ))}
            </ul>
          </div>

          <AlertDialogFooter className="flex-col gap-2 sm:flex-row">
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <Button variant="outline" onClick={handleUseExistingFiles}>
              Utiliser les existants
            </Button>
            <AlertDialogAction onClick={handleReplaceAll}>Remplacer tout</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
