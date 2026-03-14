/**
 * ImagePickerDialog - Dialog for selecting or uploading images
 *
 * Features:
 * - Browse existing images in files/ folder (recursively)
 * - Filter by subfolder
 * - Upload new images
 * - Multi-selection support for gallery creation
 * - Preview before selection
 * - Returns selected paths for markdown insertion
 */

import { useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
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
import { Upload, Image as ImageIcon, Check, Loader2, FolderOpen, Images, Search } from 'lucide-react'
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

// Extract subfolder from file path (e.g., "files/img/methodes/pic.png" → "img/methodes")
function getSubfolder(file: ProjectFile): string {
  const parts = file.path.split('/')
  // Remove "files/" prefix and filename
  if (parts.length <= 2) return '' // root of files/
  return parts.slice(1, -1).join('/')
}

export function ImagePickerDialog({ open, onOpenChange, onSelect }: ImagePickerDialogProps) {
  const { t } = useTranslation(['site', 'common'])
  const [selectedFiles, setSelectedFiles] = useState<ProjectFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [activeFolder, setActiveFolder] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch ALL images from files/ folder (recursive via API rglob)
  const { data: filesData, isLoading, refetch } = useProjectFiles('files')
  const uploadMutation = useUploadFile()

  // Filter to only show images
  const allImageFiles = useMemo(
    () => filesData?.files.filter(isImageFile) || [],
    [filesData]
  )

  // Extract unique subfolders for folder tabs
  const subfolders = useMemo(() => {
    const folders = new Set<string>()
    for (const file of allImageFiles) {
      const sf = getSubfolder(file)
      if (sf) folders.add(sf)
    }
    return Array.from(folders).sort()
  }, [allImageFiles])

  // Filter images by active folder and search query
  const imageFiles = useMemo(() => {
    let filtered = allImageFiles
    if (activeFolder !== null) {
      if (activeFolder === '') {
        // Root: files directly in files/ (no subfolder)
        filtered = filtered.filter((f) => getSubfolder(f) === '')
      } else {
        filtered = filtered.filter((f) => getSubfolder(f) === activeFolder)
      }
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter((f) => f.name.toLowerCase().includes(q))
    }
    return filtered
  }, [allImageFiles, activeFolder, searchQuery])

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
        for (const file of Array.from(files)) {
          const isImage = file.type.startsWith('image/')
          if (!isImage) {
            toast.error(t('imagePicker.invalidFileType'), {
              description: t('imagePicker.notAnImage', { name: file.name }),
            })
            continue
          }

          const result = await uploadMutation.mutateAsync({ file, folder: 'files' })
          uploadedFiles.push({
            name: result.filename,
            path: result.path,
            size: file.size,
            extension: result.filename.split('.').pop() || '',
            modified: new Date().toISOString(),
          })
        }

        if (uploadedFiles.length > 0) {
          toast.success(t('imagePicker.imagesUploaded'), {
            description: t('imagePicker.imagesAdded', { count: uploadedFiles.length }),
          })
          await refetch()
          setSelectedFiles((prev) => [...prev, ...uploadedFiles])
        }
      } catch (err) {
        toast.error(t('imagePicker.uploadError'), {
          description: err instanceof Error ? err.message : t('imagePicker.uploadFailed'),
        })
      } finally {
        setIsUploading(false)
        event.target.value = ''
      }
    },
    [uploadMutation, refetch, t]
  )

  // Handle selection confirmation
  const handleConfirm = useCallback(() => {
    if (selectedFiles.length === 0) return

    const images: SelectedImage[] = selectedFiles.map((file) => ({
      path: file.path,
      altText: file.name.replace(/\.[^.]+$/, ''),
    }))

    onSelect(images)
    setSelectedFiles([])
    onOpenChange(false)
  }, [selectedFiles, onSelect, onOpenChange])

  // Handle dialog close
  const handleClose = useCallback(() => {
    setSelectedFiles([])
    setActiveFolder(null)
    setSearchQuery('')
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
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {selectedFiles.length > 1 ? (
              <Images className="h-5 w-5" />
            ) : (
              <ImageIcon className="h-5 w-5" />
            )}
            {selectedFiles.length > 1
              ? t('imagePicker.insertImages', { count: selectedFiles.length })
              : t('imagePicker.insertImage')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          {/* Upload + Search row */}
          <div className="flex items-center gap-3">
            <label
              htmlFor="image-upload"
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-1.5 text-sm transition-colors hover:bg-muted',
                isUploading && 'pointer-events-none opacity-50'
              )}
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              <span>{t('imagePicker.uploadImages')}</span>
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
            <div className="flex flex-1 items-center gap-2 rounded-md border px-3 py-1.5">
              <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <input
                type="text"
                placeholder={t('imagePicker.searchPlaceholder', { defaultValue: 'Filtrer par nom...' })}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full border-none outline-none bg-transparent text-sm"
              />
            </div>
          </div>

          {/* Selection info */}
          {selectedFiles.length > 1 && (
            <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2">
              <Images className="h-4 w-4 text-primary" />
              <span className="text-sm">
                {t('imagePicker.imagesSelected', { count: selectedFiles.length })}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto h-7 text-xs"
                onClick={() => setSelectedFiles([])}
              >
                {t('imagePicker.deselectAll')}
              </Button>
            </div>
          )}

          {/* Folder tabs */}
          {subfolders.length > 0 && (
            <div className="flex flex-wrap gap-1">
              <Button
                variant={activeFolder === null ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setActiveFolder(null)}
              >
                {t('imagePicker.allImages', { defaultValue: 'Tout' })} ({allImageFiles.length})
              </Button>
              <Button
                variant={activeFolder === '' ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setActiveFolder('')}
              >
                files/ ({allImageFiles.filter((f) => getSubfolder(f) === '').length})
              </Button>
              {subfolders.map((sf) => (
                <Button
                  key={sf}
                  variant={activeFolder === sf ? 'default' : 'outline'}
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setActiveFolder(sf)}
                >
                  {sf}/ ({allImageFiles.filter((f) => getSubfolder(f) === sf).length})
                </Button>
              ))}
            </div>
          )}

          {/* File browser */}
          <div className="rounded-md border">
            <div className="flex items-center gap-2 border-b bg-muted/50 px-3 py-2">
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">
                files/{activeFolder !== null ? (activeFolder ? activeFolder + '/' : '') : ''}
              </span>
              <span className="text-sm text-muted-foreground">
                ({imageFiles.length} image{imageFiles.length !== 1 ? 's' : ''})
              </span>
            </div>

            <ScrollArea className="h-72">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : imageFiles.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <ImageIcon className="mb-2 h-8 w-8" />
                  <p className="text-sm">{t('imagePicker.noImagesInFolder')}</p>
                  <p className="text-xs">{t('imagePicker.uploadToStart')}</p>
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-2 p-2">
                  {imageFiles.map((file) => {
                    const selected = isSelected(file)
                    const selectionIndex = getSelectionIndex(file)
                    const subfolder = getSubfolder(file)

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
                        <span className="w-full truncate text-center text-xs" title={file.path}>
                          {file.name}
                        </span>
                        {/* Show subfolder if browsing all */}
                        {activeFolder === null && subfolder && (
                          <span className="w-full truncate text-center text-[10px] text-muted-foreground">
                            {subfolder}/
                          </span>
                        )}
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
            {t('common:actions.cancel')}
          </Button>
          <Button onClick={handleConfirm} disabled={selectedFiles.length === 0}>
            {selectedFiles.length > 1 ? (
              <>
                <Images className="mr-2 h-4 w-4" />
                {t('imagePicker.insertImages', { count: selectedFiles.length })}
              </>
            ) : (
              t('imagePicker.insert')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ImagePickerDialog
