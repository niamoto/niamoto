// src/components/forms/widgets/DirectorySelectField.tsx

import React, { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Folder, FolderOpen, ChevronRight, File } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface DirectorySelectFieldProps {
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
  fileMode?: boolean; // true for file selection, false for directory
  extensions?: string[]; // for file mode, filter by extensions
}

interface FileItem {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number;
}

const DirectorySelectField: React.FC<DirectorySelectFieldProps> = ({
  name,
  label,
  description,
  value = '',
  onChange,
  placeholder = 'Select a directory...',
  required = false,
  disabled = false,
  error,
  className = '',
  fileMode = false,
  extensions = []
}) => {
  const [showDialog, setShowDialog] = useState(false);
  const [currentPath, setCurrentPath] = useState('/');
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [_selectedPath, setSelectedPath] = useState(value);

  const fetchDirectory = async (path: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/files/list?path=${encodeURIComponent(path)}`);
      if (response.ok) {
        const data = await response.json();
        let items = data.files || [];

        // Filter by extensions if in file mode
        if (fileMode && extensions.length > 0) {
          items = items.filter((item: FileItem) => {
            if (item.is_directory) return true;
            return extensions.some(ext => item.name.endsWith(ext));
          });
        }

        setFiles(items);
      }
    } catch (err) {
      console.error('Failed to fetch directory:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (showDialog) {
      fetchDirectory(currentPath);
    }
  }, [currentPath, showDialog]);

  const handleItemClick = (item: FileItem) => {
    if (item.is_directory) {
      setCurrentPath(item.path);
    } else if (fileMode) {
      setSelectedPath(item.path);
      onChange?.(item.path);
      setShowDialog(false);
    }
  };

  const handleSelectDirectory = () => {
    if (!fileMode) {
      setSelectedPath(currentPath);
      onChange?.(currentPath);
      setShowDialog(false);
    }
  };

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {fileMode ? <File className="inline-block h-3 w-3 mr-1" /> : <Folder className="inline-block h-3 w-3 mr-1" />}
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <div className="flex gap-2">
        <Input
          id={name}
          name={name}
          type="text"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={error ? 'border-red-500' : ''}
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => setShowDialog(true)}
          disabled={disabled}
        >
          Browse
        </Button>
      </div>
      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {fileMode ? 'Select a File' : 'Select a Directory'}
            </DialogTitle>
            <DialogDescription>
              Current path: {currentPath}
            </DialogDescription>
          </DialogHeader>
          <div className="border rounded p-2 h-96 overflow-auto">
            {loading ? (
              <div className="text-center py-4">Loading...</div>
            ) : (
              <div className="space-y-1">
                {currentPath !== '/' && (
                  <button
                    className="w-full text-left px-2 py-1 hover:bg-gray-100 rounded flex items-center gap-2"
                    onClick={() => {
                      const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
                      setCurrentPath(parentPath);
                    }}
                  >
                    <Folder className="h-4 w-4" />
                    ..
                  </button>
                )}
                {files.map((item) => (
                  <button
                    key={item.path}
                    className="w-full text-left px-2 py-1 hover:bg-gray-100 rounded flex items-center gap-2"
                    onClick={() => handleItemClick(item)}
                  >
                    {item.is_directory ? (
                      <>
                        <FolderOpen className="h-4 w-4 text-blue-500" />
                        <span className="font-medium">{item.name}</span>
                        <ChevronRight className="h-4 w-4 ml-auto text-gray-400" />
                      </>
                    ) : (
                      <>
                        <File className="h-4 w-4 text-gray-500" />
                        <span>{item.name}</span>
                        {item.size && (
                          <span className="ml-auto text-xs text-gray-500">
                            {(item.size / 1024).toFixed(1)} KB
                          </span>
                        )}
                      </>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
          {!fileMode && (
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSelectDirectory}>
                Select This Directory
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </FormItem>
  );
};

export default DirectorySelectField;
