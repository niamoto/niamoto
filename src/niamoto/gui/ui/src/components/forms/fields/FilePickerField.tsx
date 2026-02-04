// src/components/forms/fields/FilePickerField.tsx

import React, { useState, useEffect } from 'react';
// Select components removed - using custom file browser instead
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, FolderOpen, File, ChevronRight, Home } from 'lucide-react';

interface FileInfo {
  name: string;
  type: 'file' | 'directory';
  path: string;
  size: number | null;
}

interface BrowseResponse {
  type: 'file' | 'directory';
  path: string;
  items?: FileInfo[];
}

type FileType = 'raster' | 'vector' | 'csv' | 'all';

interface FilePickerFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  accept?: FileType;          // Filter by file type
  basePath?: string;          // Base path (default: imports/)
}

// File type extensions mapping
const FILE_EXTENSIONS: Record<FileType, string[]> = {
  raster: ['.tif', '.tiff', '.asc', '.img', '.vrt', '.nc'],
  vector: ['.gpkg', '.shp', '.geojson', '.json', '.kml', '.gml'],
  csv: ['.csv', '.tsv', '.txt'],
  all: []
};

const formatFileSize = (bytes: number | null): string => {
  if (bytes === null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const FilePickerField: React.FC<FilePickerFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder = 'Select a file...',
  required = false,
  disabled = false,
  error,
  className = '',
  accept = 'all',
  basePath = 'imports/'
}) => {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [currentPath, setCurrentPath] = useState<string>(basePath);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);

  // Filter files by type
  const filterFiles = (items: FileInfo[]): FileInfo[] => {
    if (accept === 'all') return items;

    const extensions = FILE_EXTENSIONS[accept];
    return items.filter(item => {
      if (item.type === 'directory') return true;
      const ext = item.name.toLowerCase().slice(item.name.lastIndexOf('.'));
      return extensions.includes(ext);
    });
  };

  // Fetch files from API
  const fetchFiles = async (path: string) => {
    try {
      setLoading(true);
      setFetchError(null);

      const response = await fetch(`/api/files/browse?path=${encodeURIComponent(path)}`);
      if (!response.ok) {
        if (response.status === 404) {
          setFetchError('Path not found');
        } else {
          throw new Error(`Failed to fetch: ${response.statusText}`);
        }
        setFiles([]);
        return;
      }

      const data: BrowseResponse = await response.json();
      if (data.items) {
        setFiles(filterFiles(data.items));
        setCurrentPath(data.path);
      }
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  // Load files when browser is opened
  useEffect(() => {
    if (showBrowser) {
      fetchFiles(currentPath);
    }
  }, [showBrowser]);

  // Navigate to a directory
  const navigateTo = (path: string) => {
    fetchFiles(path);
  };

  // Go up one directory
  const goUp = () => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '.';
    fetchFiles(parentPath);
  };

  // Select a file
  const selectFile = (file: FileInfo) => {
    if (file.type === 'directory') {
      navigateTo(file.path);
    } else {
      // Convert absolute path to relative path from project root
      const relativePath = file.path.includes('/imports/')
        ? file.path.slice(file.path.indexOf('/imports/') + 1)
        : file.name;
      onChange?.(relativePath);
      setShowBrowser(false);
    }
  };

  // Get file icon based on type
  const getFileIcon = (file: FileInfo) => {
    if (file.type === 'directory') {
      return <FolderOpen className="h-4 w-4 text-blue-500" />;
    }
    return <File className="h-4 w-4 text-gray-500" />;
  };

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}

      <div className="flex gap-2">
        <Input
          id={name}
          value={value || ''}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={`flex-1 ${error ? 'border-red-500' : ''}`}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={() => setShowBrowser(!showBrowser)}
          disabled={disabled}
        >
          <FolderOpen className="h-4 w-4" />
        </Button>
      </div>

      {/* File browser */}
      {showBrowser && (
        <div className="mt-2 border rounded-md p-2 bg-background max-h-64 overflow-y-auto">
          {/* Breadcrumb / Navigation */}
          <div className="flex items-center gap-1 mb-2 text-sm text-muted-foreground border-b pb-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 px-2"
              onClick={() => navigateTo(basePath)}
            >
              <Home className="h-3 w-3" />
            </Button>
            <ChevronRight className="h-3 w-3" />
            <span className="truncate">{currentPath}</span>
            {currentPath !== basePath && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 ml-auto"
                onClick={goUp}
              >
                Go up
              </Button>
            )}
          </div>

          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-sm text-muted-foreground">Loading...</span>
            </div>
          )}

          {/* Error state */}
          {fetchError && !loading && (
            <div className="text-sm text-red-500 py-2">{fetchError}</div>
          )}

          {/* File list */}
          {!loading && !fetchError && (
            <div className="space-y-1">
              {files.length === 0 ? (
                <div className="text-sm text-muted-foreground py-2">
                  No {accept !== 'all' ? accept : ''} files found
                </div>
              ) : (
                files.map((file) => (
                  <button
                    key={file.path}
                    type="button"
                    className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-muted text-left"
                    onClick={() => selectFile(file)}
                  >
                    {getFileIcon(file)}
                    <span className="flex-1 truncate text-sm">{file.name}</span>
                    {file.size !== null && (
                      <span className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)}
                      </span>
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default FilePickerField;
