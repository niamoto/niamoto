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
    const fetchSources = async () => {
      try {
        setLoading(true);
        setLoadError(null);

        // Build URL with optional group_by filter
        const url = groupBy
          ? `/api/recipes/sources/${groupBy}`
          : null;

        if (!url) {
          setSources([]);
          return;
        }

        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Failed to fetch sources: ${response.statusText}`);
        }

        const data: TransformSourcesResponse = await response.json();
        const sourceNames = data.sources
          .filter((source) => !kind || source.type === kind)
          .map((source) => source.name)
          .filter((sourceName) => sourceName && sourceName.trim() !== '');
        setSources(sourceNames);
      } catch (err) {
        console.error('Error fetching transform sources:', err);
        setLoadError(err instanceof Error ? err.message : 'Failed to load sources');
        setSources([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSources();
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
