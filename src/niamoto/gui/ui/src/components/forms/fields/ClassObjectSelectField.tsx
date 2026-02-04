// src/components/forms/fields/ClassObjectSelectField.tsx

import React, { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Loader2 } from 'lucide-react';

interface ClassObjectInfo {
  name: string;
  cardinality: number;
  value_type: string;
  suggested_plugin: string;
  confidence: number;
}

interface ClassObjectSelectFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: string | string[];
  onChange?: (value: string | string[]) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  groupBy?: string;         // Group name (reference_name)
  source?: string;          // Source name to analyze
  multiple?: boolean;       // Allow multiple selection
}

const ClassObjectSelectField: React.FC<ClassObjectSelectFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder = 'Select class object...',
  required = false,
  disabled = false,
  error,
  className = '',
  groupBy,
  source,
  multiple = false
}) => {
  const [classObjects, setClassObjects] = useState<ClassObjectInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Fetch class objects when groupBy or source changes
  useEffect(() => {
    const fetchClassObjects = async () => {
      if (!groupBy || !source) {
        setClassObjects([]);
        return;
      }

      try {
        setLoading(true);
        setFetchError(null);

        const response = await fetch(`/api/sources/${groupBy}/analyze/${source}`);
        if (!response.ok) {
          if (response.status === 404) {
            setFetchError('Source not found');
          } else {
            throw new Error(`Failed to fetch: ${response.statusText}`);
          }
          setClassObjects([]);
          return;
        }

        const data = await response.json();
        setClassObjects(data.class_objects || []);
      } catch (err) {
        setFetchError(err instanceof Error ? err.message : 'Failed to load class objects');
        setClassObjects([]);
      } finally {
        setLoading(false);
      }
    };

    fetchClassObjects();
  }, [groupBy, source]);

  // Handle value change
  const handleChange = (newValue: string) => {
    if (multiple) {
      // For multiple selection, toggle the value
      const currentValues = Array.isArray(value) ? value : value ? [value] : [];
      const newValues = currentValues.includes(newValue)
        ? currentValues.filter(v => v !== newValue)
        : [...currentValues, newValue];
      onChange?.(newValues);
    } else {
      onChange?.(newValue);
    }
  };

  // Get display value
  const displayValue = Array.isArray(value) ? value.join(', ') : value;

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
          <span className="text-sm text-muted-foreground">Loading class objects...</span>
        </div>
      </FormItem>
    );
  }

  // Show error or empty state message
  const showMessage = !source
    ? 'Select a source first'
    : fetchError
      ? fetchError
      : classObjects.length === 0
        ? 'No class objects found in source'
        : null;

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Select
        value={typeof value === 'string' ? value : undefined}
        onValueChange={handleChange}
        disabled={disabled || !source || classObjects.length === 0}
      >
        <SelectTrigger id={name} className={error ? 'border-red-500' : ''}>
          <SelectValue placeholder={showMessage || placeholder}>
            {displayValue}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {classObjects.map((co) => (
            <SelectItem key={co.name} value={co.name}>
              <div className="flex items-center justify-between gap-4 w-full">
                <span>{co.name}</span>
                <span className="text-xs text-muted-foreground">
                  {co.cardinality} values • {co.value_type}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default ClassObjectSelectField;
