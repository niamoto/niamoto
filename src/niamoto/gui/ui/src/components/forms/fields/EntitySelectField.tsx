// src/components/forms/widgets/EntitySelectField.tsx

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Loader2 } from 'lucide-react';
import { mergeOptionValue } from '../formSchemaUtils';

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

const entityListCache = new Map<string, EntityListResponse>();
const entityListRequests = new Map<string, Promise<EntityListResponse>>();

async function loadEntityList(): Promise<EntityListResponse> {
  const cacheKey = 'all';
  const cached = entityListCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const inflight = entityListRequests.get(cacheKey);
  if (inflight) {
    return inflight;
  }

  const request = (async () => {
    const response = await fetch(`/api/entities/available`, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Failed to fetch entities: ${response.statusText}`);
    }

    const data: EntityListResponse = await response.json();
    entityListCache.set(cacheKey, data);
    return data;
  })().finally(() => {
    entityListRequests.delete(cacheKey);
  });

  entityListRequests.set(cacheKey, request);
  return request;
}

async function loadEntityOptions(kind?: 'dataset' | 'reference'): Promise<string[]> {
  const data = await loadEntityList();
  return kind === 'dataset'
    ? data.datasets
    : kind === 'reference'
      ? data.references
      : [...data.datasets, ...data.references];
}

const EntitySelectField: React.FC<EntitySelectFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder,
  required = false,
  disabled = false,
  error,
  className = '',
  kind,
  groupBy  // Reserved for future use: filter entities by group context
}) => {
  const { t } = useTranslation('common');
  const [entities, setEntities] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Note: groupBy parameter is available for future enhancement
  // to filter entities based on transform group context
  void groupBy;

  const resolvedPlaceholder = placeholder ?? t('placeholders.selectOption');
  const resolvedEntities = mergeOptionValue(entities, value);

  useEffect(() => {
    let cancelled = false;

    const fetchEntities = async () => {
      try {
        setLoading(true);
        setLoadError(null);

        const entityList = await loadEntityOptions(kind);
        if (!cancelled) {
          setEntities(entityList);
        }
      } catch (err) {
        console.error('Error fetching entities:', err);
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Failed to load entities');
          setEntities([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchEntities();

    return () => {
      cancelled = true;
    };
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
	              <span className="text-muted-foreground">{t('status.loading')}</span>
	            </div>
	          ) : (
	            <SelectValue placeholder={resolvedPlaceholder} />
	          )}
	        </SelectTrigger>
	        <SelectContent>
	          {resolvedEntities.length === 0 && !loading && (
	            <div className="p-2 text-sm text-muted-foreground text-center">
	              {loadError ? t('status.error') : t('empty.noData')}
	            </div>
	          )}
	          {resolvedEntities.map((entityName) => (
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
