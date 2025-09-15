import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import { Upload, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  accept?: string
  maxSize?: number
  multiple?: boolean
  className?: string
}

export function FileUpload({
  onFileSelect,
  accept = '*',
  maxSize = 10 * 1024 * 1024, // 10MB default
  multiple = false,
  className
}: FileUploadProps) {
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError(null)

    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0]
      if (rejection.errors[0]?.code === 'file-too-large') {
        setError(t('import.fileUpload.errorTooLarge', 'File is too large'))
      } else if (rejection.errors[0]?.code === 'file-invalid-type') {
        setError(t('import.fileUpload.errorInvalidType', 'Invalid file type'))
      } else {
        setError(t('import.fileUpload.errorGeneral', 'Error uploading file'))
      }
      return
    }

    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect, t])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: accept === '*' ? undefined : { [accept]: [] },
    maxSize,
    multiple,
    noClick: false,
    noKeyboard: false
  })

  return (
    <div className={cn('space-y-2', className)}>
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-muted-foreground/50',
          error && 'border-destructive/50 bg-destructive/5'
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          <Upload className={cn(
            'h-8 w-8',
            isDragActive ? 'text-primary' : 'text-muted-foreground'
          )} />
          <div>
            <p className="text-sm font-medium">
              {isDragActive
                ? t('import.fileUpload.dropHere', 'Drop file here')
                : t('import.fileUpload.dragDrop', 'Drag & drop or click to select')
              }
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {accept !== '*' && (
                <>
                  {t('import.fileUpload.acceptedTypes', 'Accepted types')}: {accept}
                  <br />
                </>
              )}
              {t('import.fileUpload.maxSize', 'Max size')}: {(maxSize / 1024 / 1024).toFixed(0)}MB
            </p>
          </div>
        </div>
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
