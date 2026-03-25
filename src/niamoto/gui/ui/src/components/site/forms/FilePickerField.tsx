/**
 * FilePickerField - File selector with upload capability
 *
 * Allows selecting existing files from a folder or uploading new ones
 */

import { useRef, useState } from 'react'
import { Upload, FolderOpen, Link, Loader2, File, X } from 'lucide-react'
import { toast } from 'sonner'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import { useProjectFiles, useUploadFile } from '@/features/site/hooks/useSiteConfig'

interface FilePickerFieldProps {
  value: string
  onChange: (path: string) => void
  folder?: string // Default: 'files/data'
  placeholder?: string
  accept?: string // File input accept attribute
  className?: string
}

// Format file size
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Get file extension
function getExtension(filename: string): string {
  const parts = filename.split('.')
  return parts.length > 1 ? parts.pop()?.toUpperCase() || '' : ''
}

export function FilePickerField({
  value,
  onChange,
  folder = 'files/data',
  placeholder = 'Selectionner ou uploader un fichier',
  accept,
  className,
}: FilePickerFieldProps) {
  const [open, setOpen] = useState(false)
  const [externalUrl, setExternalUrl] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch files from folder
  const { data: filesData, isLoading, refetch } = useProjectFiles(folder)
  const uploadMutation = useUploadFile()

  const files = filesData?.files || []

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await uploadMutation.mutateAsync({ file, folder })
      await refetch()
      onChange(result.path)
      toast.success('File uploaded', {
        description: result.filename,
      })
      setOpen(false)
    } catch (err) {
      toast.error('Upload error', {
        description: err instanceof Error ? err.message : 'Upload failed',
      })
    }
    e.target.value = ''
  }

  // Handle external URL
  const handleExternalUrl = () => {
    if (externalUrl.trim()) {
      onChange(externalUrl.trim())
      setExternalUrl('')
      setOpen(false)
    }
  }

  // Get display name for current value
  const displayName = value
    ? value.split('/').pop() || value
    : placeholder

  return (
    <div className={cn('flex gap-2', className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="flex-1 justify-start font-normal"
          >
            {value ? (
              <span className="flex items-center gap-2 truncate">
                <File className="h-4 w-4 shrink-0" />
                <span className="truncate">{displayName}</span>
              </span>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-96 p-0" align="start">
          <Tabs defaultValue="files" className="w-full">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="files" className="gap-2">
                <FolderOpen className="h-4 w-4" />
                Fichiers existants
              </TabsTrigger>
              <TabsTrigger value="external" className="gap-2">
                <Link className="h-4 w-4" />
                URL externe
              </TabsTrigger>
            </TabsList>

            <TabsContent value="files" className="p-2 space-y-2">
              {/* Upload button */}
              <div className="flex gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={accept}
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadMutation.isPending}
                >
                  {uploadMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="mr-2 h-4 w-4" />
                  )}
                  Uploader un fichier
                </Button>
              </div>

              {/* Files list */}
              <ScrollArea className="h-48">
                {isLoading ? (
                  <div className="flex items-center justify-center p-4">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : files.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    Aucun fichier dans {folder}/
                  </div>
                ) : (
                  <div className="space-y-1">
                    {files.map((file) => (
                      <button
                        key={file.path}
                        type="button"
                        onClick={() => {
                          onChange(file.path)
                          setOpen(false)
                        }}
                        className={cn(
                          'w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted',
                          value === file.path && 'bg-primary/10 text-primary'
                        )}
                      >
                        <File className="h-4 w-4 shrink-0" />
                        <span className="flex-1 truncate text-left">{file.name}</span>
                        <span className="text-xs text-muted-foreground shrink-0">
                          {getExtension(file.name)}
                        </span>
                        {file.size && (
                          <span className="text-xs text-muted-foreground shrink-0">
                            {formatFileSize(file.size)}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="external" className="p-2 space-y-2">
              <p className="text-xs text-muted-foreground">
                Entrez l'URL d'une ressource externe
              </p>
              <div className="flex gap-2">
                <Input
                  value={externalUrl}
                  onChange={(e) => setExternalUrl(e.target.value)}
                  placeholder="https://example.com/data.csv"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleExternalUrl()
                    }
                  }}
                />
                <Button
                  size="sm"
                  onClick={handleExternalUrl}
                  disabled={!externalUrl.trim()}
                >
                  OK
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </PopoverContent>
      </Popover>

      {/* Clear button */}
      {value && (
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0"
          onClick={() => onChange('')}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}

export default FilePickerField
