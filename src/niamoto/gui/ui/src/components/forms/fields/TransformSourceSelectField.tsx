// src/components/forms/widgets/TransformSourceSelectField.tsx

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Loader2 } from 'lucide-react';
import { mergeOptionValue } from '../formSchemaUtils';

interface TransformSourceSelectFieldProps {
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
  groupBy?: string;  // Optional: filter sources by group_by
  kind?: 'dataset' | 'reference';
}

interface TransformSourceInfo {
  name: string;
  type: 'dataset' | 'reference' | 'csv_stats';
}

interface TransformSourcesResponse {
  sources: TransformSourceInfo[];
}

const transformSourceCache = new Map<string, TransformSourcesResponse>();
const transformSourceRequests = new Map<string, Promise<TransformSourcesResponse>>();

async function loadTransformSources(groupBy?: string): Promise<TransformSourcesResponse> {
  if (!groupBy) {
    return { sources: [] };
  }

  const cacheKey = groupBy;
  const cached = transformSourceCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const inflight = transformSourceRequests.get(cacheKey);
  if (inflight) {
    return inflight;
  }

  const request = (async () => {
    const response = await fetch(`/api/recipes/sources/${groupBy}`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch sources: ${response.statusText}`);
    }

    const data: TransformSourcesResponse = await response.json();
    transformSourceCache.set(cacheKey, data);
    return data;
  })().finally(() => {
    transformSourceRequests.delete(cacheKey);
  });

  transformSourceRequests.set(cacheKey, request);
  return request;
}

async function loadTransformSourceOptions(
  groupBy?: string,
  kind?: 'dataset' | 'reference',
): Promise<string[]> {
  const data = await loadTransformSources(groupBy);
  return data.sources
    .filter((source) => !kind || source.type === kind)
    .map((source) => source.name)
    .filter((sourceName) => sourceName && sourceName.trim() !== '');
}

const TransformSourceSelectField: React.FC<TransformSourceSelectFieldProps> = ({
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
  groupBy,
  kind
}) => {
  const { t } = useTranslation('common');
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const resolvedPlaceholder = placeholder ?? t('placeholders.selectOption');
  const resolvedSources = mergeOptionValue(sources, value);

  useEffect(() => {
    let cancelled = false;

    const fetchSources = async () => {
      try {
        setLoading(true);
        setLoadError(null);

        if (!groupBy) {
          if (!cancelled) {
            setSources([]);
            setLoading(false);
          }
          return;
        }

        const sourceNames = await loadTransformSourceOptions(groupBy, kind);
        if (!cancelled) {
          setSources(sourceNames);
        }
      } catch (err) {
        console.error('Error fetching transform sources:', err);
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Failed to load sources');
          setSources([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchSources();

    return () => {
      cancelled = true;
    };
  }, [groupBy, kind]);

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
	          {resolvedSources.length === 0 && !loading && (
	            <div className="p-2 text-sm text-muted-foreground text-center">
	              {loadError ? t('status.error') : t('empty.noData')}
	            </div>
	          )}
	          {resolvedSources.map((sourceName) => (
	            <SelectItem key={sourceName} value={sourceName}>
	              {sourceName}
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

export default TransformSourceSelectField;
