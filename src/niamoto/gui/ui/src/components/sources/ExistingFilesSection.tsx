/**
 * ExistingFilesSection - Shows existing files in imports/ for re-import
 *
 * Allows users to re-run auto-config + import without uploading again
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import {
  FileText,
  Database,
  FolderOpen,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { scanImportsDirectory, type FileInfo, type DirectoryInfo } from '@/lib/api/smart-config'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

interface ExistingFilesSectionProps {
  onFilesSelected: (paths: string[]) => void
  disabled?: boolean
}

export function ExistingFilesSection({ onFilesSelected, disabled = false }: ExistingFilesSectionProps) {
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set())

  const {
    data: scanResult,
    isLoading,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ['imports-scan'],
    queryFn: scanImportsDirectory,
    staleTime: 30000,
  })

  const toggleFile = (path: string) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const toggleDir = (dirPath: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev)
      if (next.has(dirPath)) {
        next.delete(dirPath)
      } else {
        next.add(dirPath)
      }
      return next
    })
  }

  const selectAllInDir = (dir: DirectoryInfo) => {
    // This would require nested file listing - for now just toggle the dir
    toggleDir(dir.path)
  }

  const handleReconfigure = () => {
    if (selectedPaths.size > 0) {
      onFilesSelected(Array.from(selectedPaths))
    }
  }

  const getFileIcon = (file: FileInfo) => {
    switch (file.extension) {
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

  const formatSize = (sizeMb: number) => {
    if (sizeMb < 1) {
      return `${Math.round(sizeMb * 1024)} Ko`
    }
    return `${sizeMb.toFixed(1)} Mo`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!scanResult?.exists || scanResult.summary.total_files === 0) {
    return null // Don't show if no existing files
  }

  const importableFiles = scanResult.files.filter((f) => f.importable)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="flex items-center gap-2 text-sm font-medium">
          <FolderOpen className="h-4 w-4" />
          Fichiers existants
          <Badge variant="secondary" className="text-xs">
            {scanResult.summary.importable_files}
          </Badge>
        </h4>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          disabled={isRefetching}
        >
          <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      <div className="max-h-48 space-y-1 overflow-y-auto rounded-md border p-2">
        {/* Directories */}
        {scanResult.directories.map((dir) => (
          <Collapsible
            key={dir.path}
            open={expandedDirs.has(dir.path)}
            onOpenChange={() => toggleDir(dir.path)}
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent">
              {expandedDirs.has(dir.path) ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <FolderOpen className="h-4 w-4 text-amber-500" />
              <span className="flex-1 text-left font-medium">{dir.name}/</span>
              <Badge variant="outline" className="text-xs">
                {dir.file_count} fichiers
              </Badge>
            </CollapsibleTrigger>
            <CollapsibleContent className="ml-6 space-y-1 py-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-full justify-start text-xs"
                onClick={() => selectAllInDir(dir)}
              >
                Selectionner le dossier
              </Button>
            </CollapsibleContent>
          </Collapsible>
        ))}

        {/* Root files */}
        {importableFiles.map((file) => (
          <label
            key={file.path}
            className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent"
          >
            <Checkbox
              checked={selectedPaths.has(file.full_path)}
              onCheckedChange={() => toggleFile(file.full_path)}
              disabled={disabled}
            />
            {getFileIcon(file)}
            <span className="flex-1 truncate text-sm">{file.name}</span>
            <span className="text-xs text-muted-foreground">{formatSize(file.size_mb)}</span>
          </label>
        ))}
      </div>

      {selectedPaths.size > 0 && (
        <Button
          className="w-full"
          onClick={handleReconfigure}
          disabled={disabled}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Reconfigurer {selectedPaths.size} fichier{selectedPaths.size > 1 ? 's' : ''}
        </Button>
      )}
    </div>
  )
}
