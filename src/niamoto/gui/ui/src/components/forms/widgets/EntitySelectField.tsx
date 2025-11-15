// src/components/forms/widgets/EntitySelectField.tsx

import React, { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Loader2 } from 'lucide-react';

interface EntitySelectFieldProps {
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
  kind?: 'dataset' | 'reference';  // Optional filter
  groupBy?: string;
}

interface EntityListResponse {
  datasets: string[];
  references: string[];
  all: Array<{
    name: string;
    kind: string;
    entity_type: string;
  }>;
}

const EntitySelectField: React.FC<EntitySelectFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder = 'Select an entity...',
  required = false,
  disabled = false,
  error,
  className = '',
  kind,
  groupBy  // Reserved for future use: filter entities by group context
}) => {
  const [entities, setEntities] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Note: groupBy parameter is available for future enhancement
  // to filter entities based on transform group context
  void groupBy;

  useEffect(() => {
    const fetchEntities = async () => {
      try {
        setLoading(true);
        setLoadError(null);

        // Build URL with optional kind filter
        const url = kind
          ? `/api/entities/available?kind=${kind}`
          : `/api/entities/available`;

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Failed to fetch entities: ${response.statusText}`);
        }

        const data: EntityListResponse = await response.json();

        // Determine which list to use based on filter
        let entityList: string[] = [];
        if (kind === 'dataset') {
          entityList = data.datasets;
        } else if (kind === 'reference') {
          entityList = data.references;
        } else {
          // No filter - combine all entities
          entityList = [...data.datasets, ...data.references];
        }

        setEntities(entityList);
      } catch (err) {
        console.error('Error fetching entities:', err);
        setLoadError(err instanceof Error ? err.message : 'Failed to load entities');
        setEntities([]);
      } finally {
        setLoading(false);
      }
    };

    fetchEntities();
  }, [kind]);

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Select
        value={value}
        onValueChange={onChange}
        disabled={disabled || loading}
      >
        <SelectTrigger id={name} className={error || loadError ? 'border-red-500' : ''}>
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-muted-foreground">Loading entities...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {entities.length === 0 && !loading && (
            <div className="p-2 text-sm text-muted-foreground text-center">
              {loadError ? 'Error loading entities' : 'No entities available'}
            </div>
          )}
          {entities.map((entityName) => (
            <SelectItem key={entityName} value={entityName}>
              {entityName}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {description && !error && !loadError && (
        <FormDescription>{description}</FormDescription>
      )}
      {(error || loadError) && (
        <FormMessage className="text-red-500">{error || loadError}</FormMessage>
      )}
    </FormItem>
  );
};

export default EntitySelectField;
