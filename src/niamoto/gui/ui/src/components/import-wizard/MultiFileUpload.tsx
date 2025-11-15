import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import { Upload, AlertCircle, Loader2, Files } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface MultiFileUploadProps {
  onFilesSelect: (files: File[]) => void
  acceptedFormats: string[]
  isAnalyzing?: boolean
  maxSizeMB?: number
  error?: string | null
}

export function MultiFileUpload({
  onFilesSelect,
  acceptedFormats,
  isAnalyzing = false,
  maxSizeMB = 100,
  error
}: MultiFileUploadProps) {
  const { t } = useTranslation('common')

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      // Filter files by size
      const validFiles = acceptedFiles.filter(
        file => !maxSizeMB || file.size <= maxSizeMB * 1024 * 1024
      )

      if (validFiles.length > 0) {
        onFilesSelect(validFiles)
      }
    }
  }, [onFilesSelect, maxSizeMB])

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: acceptedFormats.reduce((acc, format) => {
      acc[format] = [format]
      return acc
    }, {} as Record<string, string[]>),
    multiple: true,
    maxSize: maxSizeMB * 1024 * 1024
  })

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "relative rounded-lg border-2 border-dashed p-8 text-center transition-colors cursor-pointer",
          isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50",
          isAnalyzing && "pointer-events-none opacity-50 cursor-not-allowed",
          acceptedFiles.length > 0 && !isAnalyzing && "border-green-500 bg-green-50/50 dark:bg-green-900/10"
        )}
      >
        <input {...getInputProps()} />

        {isAnalyzing ? (
          <div className="space-y-4">
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">{t('file.analyzing')}</p>
          </div>
        ) : acceptedFiles.length > 0 ? (
          <div className="space-y-4">
            <Files className="mx-auto h-12 w-12 text-green-600" />
            <div>
              <p className="font-medium">
                {acceptedFiles.length} file{acceptedFiles.length > 1 ? 's' : ''} selected
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {acceptedFiles.slice(0, 3).map(f => f.name).join(', ')}
                {acceptedFiles.length > 3 && `, and ${acceptedFiles.length - 3} more`}
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
                {isDragActive ? t('file.dropHere') : 'Drop shape files here, or click to select'}
              </p>
              <p className="text-sm text-muted-foreground">
                You can select multiple files at once
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
