// src/components/forms/fields/LayerSelectField.tsx

import React, { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Badge } from '@/components/ui/badge';
import { Loader2, Map, Layers, Database } from 'lucide-react';

type LayerType = 'raster' | 'vector' | 'all';

interface RasterMetadata {
  type: 'raster';
  path: string;
  name: string;
  size_bytes: number;
  crs: string | null;
  extent: { minx: number; miny: number; maxx: number; maxy: number } | null;
  width: number | null;
  height: number | null;
  bands: number | null;
  dtype: string | null;
}

interface VectorMetadata {
  type: 'vector';
  path: string;
  name: string;
  size_bytes: number;
  crs: string | null;
  extent: { minx: number; miny: number; maxx: number; maxy: number } | null;
  feature_count: number | null;
  geometry_type: string | null;
  columns: string[] | null;
}

type LayerMetadata = RasterMetadata | VectorMetadata;

interface LayersListResponse {
  raster: RasterMetadata[];
  vector: VectorMetadata[];
  base_path: string;
}

interface LayerSelectFieldProps {
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
  accept?: LayerType;  // Filter by layer type
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const LayerSelectField: React.FC<LayerSelectFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder = 'Select a layer...',
  required = false,
  disabled = false,
  error,
  className = '',
  accept = 'all'
}) => {
  const [layers, setLayers] = useState<LayerMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Fetch layers on mount
  useEffect(() => {
    const fetchLayers = async () => {
      try {
        setLoading(true);
        setFetchError(null);

        const response = await fetch(`/api/layers?type=${accept}&include_metadata=true`);
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.statusText}`);
        }

        const data: LayersListResponse = await response.json();

        // Combine raster and vector layers based on accept filter
        let allLayers: LayerMetadata[] = [];
        if (accept === 'all' || accept === 'raster') {
          allLayers = [...allLayers, ...data.raster];
        }
        if (accept === 'all' || accept === 'vector') {
          allLayers = [...allLayers, ...data.vector];
        }

        // Sort by name
        allLayers.sort((a, b) => a.name.localeCompare(b.name));
        setLayers(allLayers);
      } catch (err) {
        setFetchError(err instanceof Error ? err.message : 'Failed to load layers');
        setLayers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLayers();
  }, [accept]);

  // Get icon for layer type
  const getLayerIcon = (layer: LayerMetadata) => {
    if (layer.type === 'raster') {
      return <Map className="h-4 w-4 text-green-500" />;
    }
    return <Layers className="h-4 w-4 text-blue-500" />;
  };

  // Get layer info summary
  const getLayerInfo = (layer: LayerMetadata): string => {
    if (layer.type === 'raster') {
      const parts: string[] = [];
      if (layer.width && layer.height) {
        parts.push(`${layer.width}×${layer.height}`);
      }
      if (layer.bands) {
        parts.push(`${layer.bands} band${layer.bands > 1 ? 's' : ''}`);
      }
      return parts.join(' • ') || 'Raster';
    } else {
      const parts: string[] = [];
      if (layer.geometry_type) {
        parts.push(layer.geometry_type);
      }
      if (layer.feature_count !== null) {
        parts.push(`${layer.feature_count.toLocaleString()} features`);
      }
      return parts.join(' • ') || 'Vector';
    }
  };

  // Find selected layer
  const selectedLayer = layers.find(l => l.path === value);

  // Show loading state
  if (loading) {
    return (
      <FormItem className={className}>
        {label && (
          <Label>
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </Label>
        )}
        <div className="flex items-center gap-2 h-10 px-3 border rounded-md bg-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-muted-foreground">Loading layers...</span>
        </div>
      </FormItem>
    );
  }

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Select
        value={value || ''}
        onValueChange={(val) => onChange?.(val)}
        disabled={disabled || layers.length === 0}
      >
        <SelectTrigger id={name} className={error ? 'border-red-500' : ''}>
          <SelectValue placeholder={fetchError || (layers.length === 0 ? 'No layers found' : placeholder)}>
            {selectedLayer && (
              <div className="flex items-center gap-2">
                {getLayerIcon(selectedLayer)}
                <span>{selectedLayer.name}</span>
              </div>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {layers.map((layer) => (
            <SelectItem key={layer.path} value={layer.path}>
              <div className="flex items-center gap-3 py-1">
                {getLayerIcon(layer)}
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{layer.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2">
                    <span>{getLayerInfo(layer)}</span>
                    <span>•</span>
                    <span>{formatFileSize(layer.size_bytes)}</span>
                    {layer.crs && (
                      <>
                        <span>•</span>
                        <span>{layer.crs}</span>
                      </>
                    )}
                  </div>
                </div>
                <Badge variant="secondary" className="text-xs">
                  {layer.type}
                </Badge>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Show selected layer details */}
      {selectedLayer && (
        <div className="mt-2 p-2 bg-muted rounded-md text-xs space-y-1">
          <div className="flex items-center gap-2">
            <Database className="h-3 w-3" />
            <span className="text-muted-foreground">Path:</span>
            <span className="font-mono">{selectedLayer.path}</span>
          </div>
          {selectedLayer.crs && (
            <div className="flex items-center gap-2">
              <Map className="h-3 w-3" />
              <span className="text-muted-foreground">CRS:</span>
              <span>{selectedLayer.crs}</span>
            </div>
          )}
          {selectedLayer.type === 'vector' && selectedLayer.columns && (
            <div className="flex items-start gap-2">
              <Layers className="h-3 w-3 mt-0.5" />
              <span className="text-muted-foreground">Columns:</span>
              <span className="flex-1">{selectedLayer.columns.slice(0, 5).join(', ')}
                {selectedLayer.columns.length > 5 && ` +${selectedLayer.columns.length - 5} more`}
              </span>
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

export default LayerSelectField;
