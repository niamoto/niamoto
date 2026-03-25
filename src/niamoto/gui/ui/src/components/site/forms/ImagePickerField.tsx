/**
 * ImagePickerField - Image selector with upload capability and preview
 *
 * Allows selecting existing images from a folder or uploading new ones
 */

import { useRef, useState } from 'react'
import { Upload, FolderOpen, Link, Loader2, Image as ImageIcon, X } from 'lucide-react'
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

interface ImagePickerFieldProps {
  value: string
  onChange: (path: string) => void
  folder?: string // Default: 'files/team'
  placeholder?: string
  className?: string
}

// Image extensions
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']

export function ImagePickerField({
  value,
  onChange,
  folder = 'files/team',
  placeholder = 'Selectionner une image',
  className,
}: ImagePickerFieldProps) {
  const [open, setOpen] = useState(false)
  const [externalUrl, setExternalUrl] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch files from folder
  const { data: filesData, isLoading, refetch } = useProjectFiles(folder)
  const uploadMutation = useUploadFile()

  // Filter only images
  const images = (filesData?.files || []).filter((f) =>
    IMAGE_EXTENSIONS.includes(f.extension.toLowerCase())
  )

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await uploadMutation.mutateAsync({ file, folder })
      await refetch()
      onChange(result.path)
      toast.success('Image uploaded', {
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

  // Get image URL for display
  const getImageUrl = (path: string) => {
    if (path.startsWith('http')) return path
    return `/api/site/${path}`
  }

  return (
    <div className={cn('flex gap-2', className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="flex-1 h-auto min-h-9 justify-start font-normal p-2"
          >
            {value ? (
              <div className="flex items-center gap-2">
                <img
                  src={getImageUrl(value)}
                  alt=""
                  className="h-8 w-8 rounded object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none'
                  }}
                />
                <span className="truncate text-sm">
                  {value.split('/').pop()}
                </span>
              </div>
            ) : (
              <span className="flex items-center gap-2 text-muted-foreground">
                <ImageIcon className="h-4 w-4" />
                {placeholder}
              </span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0" align="start">
          <Tabs defaultValue="gallery" className="w-full">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="gallery" className="gap-2">
                <FolderOpen className="h-4 w-4" />
                Galerie
              </TabsTrigger>
              <TabsTrigger value="external" className="gap-2">
                <Link className="h-4 w-4" />
                URL externe
              </TabsTrigger>
            </TabsList>

            <TabsContent value="gallery" className="p-2 space-y-2">
              {/* Upload button */}
              <div className="flex gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
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
                  Uploader une image
                </Button>
              </div>

              {/* Images grid */}
              <ScrollArea className="h-48">
                {isLoading ? (
                  <div className="flex items-center justify-center p-4">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : images.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    Aucune image dans {folder}/
                  </div>
                ) : (
                  <div className="grid grid-cols-4 gap-1">
                    {images.map((file) => (
                      <button
                        key={file.path}
                        type="button"
                        onClick={() => {
                          onChange(file.path)
                          setOpen(false)
                        }}
                        className={cn(
                          'relative aspect-square rounded overflow-hidden border-2 transition-colors hover:border-primary/50',
                          value === file.path
                            ? 'border-primary'
                            : 'border-transparent'
                        )}
                        title={file.name}
                      >
                        <img
                          src={getImageUrl(file.path)}
                          alt={file.name}
                          className="h-full w-full object-cover"
                        />
                      </button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="external" className="p-2 space-y-2">
              <p className="text-xs text-muted-foreground">
                Entrez l'URL d'une image externe
              </p>
              <div className="flex gap-2">
                <Input
                  value={externalUrl}
                  onChange={(e) => setExternalUrl(e.target.value)}
                  placeholder="https://example.com/photo.jpg"
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

export default ImagePickerField
