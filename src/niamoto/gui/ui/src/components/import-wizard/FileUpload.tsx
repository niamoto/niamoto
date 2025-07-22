import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  acceptedFormats: string[]
  isAnalyzing?: boolean
  maxSizeMB?: number
  error?: string | null
}

export function FileUpload({
  onFileSelect,
  acceptedFormats,
  isAnalyzing = false,
  maxSizeMB = 100,
  error
}: FileUploadProps) {
  const { t } = useTranslation('common')
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]

      // Check file size
      if (maxSizeMB && file.size > maxSizeMB * 1024 * 1024) {
        return
      }

      onFileSelect(file)
    }
  }, [onFileSelect, maxSizeMB])

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: acceptedFormats.reduce((acc, format) => {
      acc[format] = [format]
      return acc
    }, {} as Record<string, string[]>),
    maxFiles: 1,
    maxSize: maxSizeMB * 1024 * 1024
  })

  const selectedFile = acceptedFiles[0]

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "relative rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25",
          isAnalyzing && "pointer-events-none opacity-50",
          selectedFile && !isAnalyzing && "border-green-500 bg-green-50/50 dark:bg-green-900/10"
        )}
      >
        <input {...getInputProps()} />

        {isAnalyzing ? (
          <div className="space-y-4">
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">{t('file.analyzing')}</p>
          </div>
        ) : selectedFile ? (
          <div className="space-y-4">
            <FileText className="mx-auto h-12 w-12 text-green-600" />
            <div>
              <p className="font-medium">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} {t('units.mb')}
              </p>
            </div>
            <p className="text-sm text-muted-foreground">
              {t('file.dropzoneReplace')}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <div>
              <p className="font-medium">
                {isDragActive ? t('file.dropHere') : t('file.dropzone')}
              </p>
              <p className="text-sm text-muted-foreground">
                {t('file.dropzoneOr')}
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('file.acceptedFormats', { formats: acceptedFormats.join(', ') })} {t('file.maxSize', { size: maxSizeMB })}
            </p>
          </div>
        )}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
