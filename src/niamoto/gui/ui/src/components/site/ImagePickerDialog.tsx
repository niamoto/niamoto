/**
 * ImagePickerDialog - Dialog for selecting or uploading images
 *
 * Features:
 * - Browse existing images in files/images/ folder
 * - Upload new images
 * - Multi-selection support for gallery creation
 * - Preview before selection
 * - Returns selected paths for markdown insertion
 */

import { useState, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { useProjectFiles, useUploadFile, type ProjectFile } from '@/hooks/useSiteConfig'
import { Upload, Image as ImageIcon, Check, Loader2, FolderOpen, Images } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// Selected image with alt text
export interface SelectedImage {
  path: string
  altText: string
}

interface ImagePickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (images: SelectedImage[]) => void
}

// Supported image extensions
const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']

function isImageFile(file: ProjectFile): boolean {
  return IMAGE_EXTENSIONS.some((ext) => file.extension.toLowerCase() === ext)
}

export function ImagePickerDialog({ open, onOpenChange, onSelect }: ImagePickerDialogProps) {
  const [selectedFiles, setSelectedFiles] = useState<ProjectFile[]>([])
  const [isUploading, setIsUploading] = useState(false)

  // Fetch images from files/images/ folder
  const { data: filesData, isLoading, refetch } = useProjectFiles('files/images')
  const uploadMutation = useUploadFile()

  // Filter to only show images
  const imageFiles = filesData?.files.filter(isImageFile) || []

  // Check if file is selected
  const isSelected = (file: ProjectFile) => selectedFiles.some((f) => f.path === file.path)

  // Toggle file selection
  const toggleSelection = (file: ProjectFile) => {
    setSelectedFiles((prev) => {
      if (isSelected(file)) {
        return prev.filter((f) => f.path !== file.path)
      }
      return [...prev, file]
    })
  }

  // Handle file upload
  const handleUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files
      if (!files || files.length === 0) return

      setIsUploading(true)
      const uploadedFiles: ProjectFile[] = []

      try {
        // Upload all selected files
        for (const file of Array.from(files)) {
          // Validate file type
          const isImage = file.type.startsWith('image/')
          if (!isImage) {
            toast.error('Type de fichier invalide', {
              description: `${file.name} n'est pas une image`,
            })
            continue
          }

          const result = await uploadMutation.mutateAsync({ file, folder: 'files/images' })
          uploadedFiles.push({
            name: result.filename,
            path: result.path,
            size: file.size,
            extension: result.filename.split('.').pop() || '',
            modified: new Date().toISOString(),
          })
        }

        if (uploadedFiles.length > 0) {
          toast.success('Images uploadees', {
            description: `${uploadedFiles.length} image(s) ajoutee(s)`,
          })
          // Refresh file list
          await refetch()
          // Auto-select the uploaded files
          setSelectedFiles((prev) => [...prev, ...uploadedFiles])
        }
      } catch (err) {
        toast.error("Erreur d'upload", {
          description: err instanceof Error ? err.message : 'Echec',
        })
      } finally {
        setIsUploading(false)
        // Reset input
        event.target.value = ''
      }
    },
    [uploadMutation, refetch]
  )

  // Handle selection confirmation
  const handleConfirm = useCallback(() => {
    if (selectedFiles.length === 0) return

    // Convert to SelectedImage format (use filename without extension as alt)
    const images: SelectedImage[] = selectedFiles.map((file) => ({
      path: file.path,
      altText: file.name.replace(/\.[^.]+$/, ''),
    }))

    onSelect(images)
    // Reset state
    setSelectedFiles([])
    onOpenChange(false)
  }, [selectedFiles, onSelect, onOpenChange])

  // Handle dialog close
  const handleClose = useCallback(() => {
    setSelectedFiles([])
    onOpenChange(false)
  }, [onOpenChange])

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Get selection index for ordering badge
  const getSelectionIndex = (file: ProjectFile): number => {
    return selectedFiles.findIndex((f) => f.path === file.path) + 1
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {selectedFiles.length > 1 ? (
              <Images className="h-5 w-5" />
            ) : (
              <ImageIcon className="h-5 w-5" />
            )}
            {selectedFiles.length > 1
              ? `Inserer ${selectedFiles.length} images (galerie)`
              : 'Inserer une image'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Upload section */}
          <div className="flex items-center gap-4">
            <label
              htmlFor="image-upload"
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-4 py-2 transition-colors hover:bg-muted',
                isUploading && 'pointer-events-none opacity-50'
              )}
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              <span>Uploader des images</span>
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handleUpload}
                disabled={isUploading}
              />
            </label>
            <span className="text-sm text-muted-foreground">
              Cliquez pour selectionner plusieurs images
            </span>
          </div>

          {/* Selection info */}
          {selectedFiles.length > 1 && (
            <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2">
              <Images className="h-4 w-4 text-primary" />
              <span className="text-sm">
                {selectedFiles.length} images selectionnees - elles seront inserees comme galerie
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto h-7 text-xs"
                onClick={() => setSelectedFiles([])}
              >
                Tout deselectionner
              </Button>
            </div>
          )}

          {/* File browser */}
          <div className="rounded-md border">
            <div className="flex items-center gap-2 border-b bg-muted/50 px-3 py-2">
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">files/images/</span>
              <span className="text-sm text-muted-foreground">
                ({imageFiles.length} image{imageFiles.length !== 1 ? 's' : ''})
              </span>
            </div>

            <ScrollArea className="h-64">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : imageFiles.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <ImageIcon className="mb-2 h-8 w-8" />
                  <p className="text-sm">Aucune image dans files/images/</p>
                  <p className="text-xs">Uploadez une image pour commencer</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-2 p-2">
                  {imageFiles.map((file) => {
                    const selected = isSelected(file)
                    const selectionIndex = getSelectionIndex(file)

                    return (
                      <button
                        key={file.path}
                        onClick={() => toggleSelection(file)}
                        className={cn(
                          'group relative flex flex-col items-center rounded-md border p-2 transition-colors hover:bg-muted',
                          selected && 'border-primary bg-primary/5'
                        )}
                      >
                        {/* Selection badge */}
                        {selected && selectedFiles.length > 1 && (
                          <Badge
                            className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-[10px]"
                            variant="default"
                          >
                            {selectionIndex}
                          </Badge>
                        )}

                        {/* Thumbnail */}
                        <div className="relative mb-1 h-16 w-full overflow-hidden rounded bg-muted">
                          <img
                            src={`/api/site/${file.path}`}
                            alt={file.name}
                            className="h-full w-full object-contain"
                            onError={(e) => {
                              // Hide broken images
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                          {selected && (
                            <div className="absolute inset-0 flex items-center justify-center bg-primary/20">
                              <Check className="h-6 w-6 text-primary" />
                            </div>
                          )}
                        </div>
                        {/* File name */}
                        <span className="w-full truncate text-center text-xs" title={file.name}>
                          {file.name}
                        </span>
                        <span className="text-xs text-muted-foreground">{formatSize(file.size)}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Annuler
          </Button>
          <Button onClick={handleConfirm} disabled={selectedFiles.length === 0}>
            {selectedFiles.length > 1 ? (
              <>
                <Images className="mr-2 h-4 w-4" />
                Inserer {selectedFiles.length} images
              </>
            ) : (
              'Inserer'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ImagePickerDialog
