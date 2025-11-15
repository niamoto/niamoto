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
import { Loader2, FileText, Database, AlertCircle, Sparkles, Upload, X, CheckCircle2, Table2, Map, Globe } from 'lucide-react'
import { uploadFiles, type UploadedFileInfo } from '@/lib/api/upload'
import type { WizardState } from '../QuickSetupWizard'

interface WelcomeStepProps {
  wizardState: WizardState
  updateState: (updates: Partial<WizardState>) => void
  onNext: () => void
}

export default function WelcomeStep({ updateState, onNext }: WelcomeStepProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([])
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
    setSelectedFiles(prev => [...prev, ...files])
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      setSelectedFiles(prev => [...prev, ...files])
    }
  }, [])

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async (overwrite: boolean = false) => {
    if (selectedFiles.length === 0) return

    try {
      setUploading(true)
      setError(null)
      setUploadProgress(0)

      // Simulate progress (real progress needs backend streaming support)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const result = await uploadFiles(selectedFiles, overwrite)

      clearInterval(progressInterval)
      setUploadProgress(100)

      // Check if files already exist (and we're not overwriting)
      if (!overwrite && result.existing_files && result.existing_files.length > 0) {
        setExistingFiles(result.existing_files)
        setShowExistingDialog(true)
        setUploading(false)
        return
      }

      if (result.success) {
        setUploadedFiles(result.uploaded_files)

        // Update wizard state with uploaded file paths
        const filePaths = result.uploaded_files.map(f => f.path)
        updateState({
          selectedFiles: filePaths,
          scannedFiles: result.uploaded_files
        })

        if (result.errors.length > 0) {
          setError(`Uploaded ${result.uploaded_count} files with ${result.errors.length} errors: ${result.errors.join(', ')}`)
        }
      } else {
        setError(result.errors.join(', ') || 'Upload failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleUseExistingFiles = () => {
    // Use existing files - construct paths and skip to auto-config
    const filePaths = existingFiles.map(filename => `imports/${filename}`)
    updateState({
      selectedFiles: filePaths,
      scannedFiles: []  // Empty since we're not uploading
    })

    // Close dialog and mark as uploaded
    setShowExistingDialog(false)
    setUploadedFiles(existingFiles.map(filename => ({
      filename,
      path: `imports/${filename}`,
      size: 0,
      size_mb: 0,
      type: filename.split('.').pop() || '',
      category: 'csv'  // Will be corrected by backend
    })))
  }

  const handleReplaceAll = async () => {
    setShowExistingDialog(false)
    await handleUpload(true)  // Re-upload with overwrite=true
  }

  const getFileIcon = (file: File | UploadedFileInfo) => {
    const name = 'name' in file ? file.name : file.filename
    const ext = name.split('.').pop()?.toLowerCase()

    switch (ext) {
      case 'csv':
        return <FileText className="w-5 h-5 text-blue-500" />
      case 'gpkg':
      case 'geojson':
        return <Database className="w-5 h-5 text-green-500" />
      case 'tif':
      case 'tiff':
        return <Database className="w-5 h-5 text-purple-500" />
      default:
        return <FileText className="w-5 h-5 text-gray-500" />
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const groupedFiles = selectedFiles.reduce((acc, file) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || 'other'
    const category = ext === 'csv' ? 'csv' : ['gpkg', 'geojson'].includes(ext) ? 'gpkg' : ['tif', 'tiff'].includes(ext) ? 'tif' : 'other'
    if (!acc[category]) acc[category] = []
    acc[category].push(file)
    return acc
  }, {} as Record<string, File[]>)

  return (
    <div className="space-y-6">
      {/* Welcome message */}
      <div className="text-center pb-4 border-b">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
          <Sparkles className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Welcome to Niamoto!</h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Upload all your data files at once. We'll analyze them and automatically configure your import.
        </p>
      </div>

      {/* Upload area */}
      {uploadedFiles.length === 0 && (
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive ? 'border-primary bg-primary/5' : 'border-border'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-lg font-semibold mb-2">Drag and drop files here</h3>
          <p className="text-sm text-muted-foreground mb-4">
            or click to browse
          </p>
          <input
            type="file"
            multiple
            accept=".csv,.gpkg,.geojson,.tif,.tiff,.zip"
            onChange={handleFileInput}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload">
            <Button variant="outline" asChild>
              <span>Browse Files</span>
            </Button>
          </label>
          <p className="text-xs text-muted-foreground mt-4">
            Supported: CSV, GeoPackage (.gpkg), GeoJSON, TIFF, ZIP (shapefiles)
          </p>
        </div>
      )}

      {/* Selected files preview */}
      {selectedFiles.length > 0 && uploadedFiles.length === 0 && (
        <div className="space-y-4">
          <h3 className="font-semibold flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Selected Files ({selectedFiles.length})
          </h3>

          {Object.entries(groupedFiles).map(([category, files]) => (
            <div key={category} className="space-y-2">
              <div className="text-sm font-medium text-muted-foreground uppercase flex items-center gap-2">
                {category === 'csv' && (
                  <>
                    <Table2 className="w-4 h-4 text-blue-500" />
                    CSV Files (Datasets)
                  </>
                )}
                {category === 'gpkg' && (
                  <>
                    <Map className="w-4 h-4 text-green-500" />
                    GeoPackage Files (Shapes/Layers)
                  </>
                )}
                {category === 'tif' && (
                  <>
                    <Globe className="w-4 h-4 text-purple-500" />
                    TIFF Files (Raster Layers)
                  </>
                )}
                {category === 'other' && (
                  <>
                    <FileText className="w-4 h-4 text-gray-500" />
                    Other Files
                  </>
                )}
              </div>

              <div className="space-y-2">
                {files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 p-3 border rounded-lg hover:bg-accent"
                  >
                    {getFileIcon(file)}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{file.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(selectedFiles.indexOf(file))}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Upload progress */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <div
                  className="bg-primary h-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="w-4 h-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {/* Uploaded files summary */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle2 className="w-6 h-6" />
            <h3 className="font-semibold text-lg">
              Upload Complete! ({uploadedFiles.length} files)
            </h3>
          </div>

          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold text-blue-500">
                {uploadedFiles.filter(f => f.category === 'csv').length}
              </div>
              <div className="text-sm text-muted-foreground">CSV Files</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-500">
                {uploadedFiles.filter(f => f.category === 'gpkg').length}
              </div>
              <div className="text-sm text-muted-foreground">GeoPackage</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold text-purple-500">
                {uploadedFiles.filter(f => f.category === 'tif').length}
              </div>
              <div className="text-sm text-muted-foreground">TIFF Layers</div>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between items-center pt-4 border-t">
        <div>
          {uploadedFiles.length === 0 && selectedFiles.length > 0 && (
            <Button variant="outline" onClick={() => setSelectedFiles([])}>
              Clear All
            </Button>
          )}
        </div>

        <div className="flex gap-2">
          {uploadedFiles.length === 0 && selectedFiles.length > 0 && (
            <Button
              onClick={() => handleUpload()}
              disabled={uploading}
              size="lg"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  Upload {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''}
                  <Upload className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          )}

          {uploadedFiles.length > 0 && (
            <Button onClick={onNext} size="lg">
              Continue with {uploadedFiles.length} file{uploadedFiles.length !== 1 ? 's' : ''}
              <Sparkles className="w-4 h-4 ml-2" />
            </Button>
          )}
        </div>
      </div>

      {/* Dialog for existing files */}
      <AlertDialog open={showExistingDialog} onOpenChange={setShowExistingDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Files Already Exist</AlertDialogTitle>
            <AlertDialogDescription>
              {existingFiles.length} file{existingFiles.length !== 1 ? 's' : ''} already exist in the imports directory. What would you like to do?
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="my-4 p-4 bg-muted rounded-lg max-h-48 overflow-y-auto">
            <ul className="space-y-1 text-sm">
              {existingFiles.map((filename, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-500" />
                  <span className="font-mono">{filename}</span>
                </li>
              ))}
            </ul>
          </div>

          <AlertDialogFooter className="flex-col sm:flex-row gap-2">
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <Button variant="outline" onClick={handleUseExistingFiles}>
              Use Existing Files
            </Button>
            <AlertDialogAction onClick={handleReplaceAll}>
              Replace All
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
