// src/components/forms/widgets/FieldSelectField.tsx

import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Database } from 'lucide-react';

interface FieldSelectFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: string;
  onChange?: (value: string) => void;
  availableFields: string[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  allowMultiple?: boolean;
}

const FieldSelectField: React.FC<FieldSelectFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  availableFields,
  placeholder = 'Select a field...',
  required = false,
  disabled = false,
  error,
  className = '',
  allowMultiple: _allowMultiple = false // unused but kept for future enhancement
}) => {
  // Group fields by table/source if they contain dots
  const groupedFields = React.useMemo(() => {
    const groups: Record<string, string[]> = {};
    const standalone: string[] = [];

    availableFields.forEach(field => {
      if (field.includes('.')) {
        const [table, ...rest] = field.split('.');
        if (!groups[table]) {
          groups[table] = [];
        }
        groups[table].push(rest.join('.'));
      } else {
        standalone.push(field);
      }
    });

    return { groups, standalone };
  }, [availableFields]);

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          <Database className="inline-block h-3 w-3 mr-1" />
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Select
        value={value}
        onValueChange={onChange}
        disabled={disabled}
      >
        <SelectTrigger id={name} className={error ? 'border-red-500' : ''}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {/* Standalone fields */}
          {groupedFields.standalone.length > 0 && (
            <>
              {groupedFields.standalone.map(field => (
                <SelectItem key={field} value={field}>
                  <span className="font-mono text-sm">{field}</span>
                </SelectItem>
              ))}
              {Object.keys(groupedFields.groups).length > 0 && (
                <div className="my-1 h-px bg-gray-200" />
              )}
            </>
          )}

          {/* Grouped fields */}
          {Object.entries(groupedFields.groups).map(([table, fields]) => (
            <div key={table}>
              <div className="px-2 py-1 text-xs font-semibold text-gray-500">
                {table}
              </div>
              {fields.map(field => (
                <SelectItem key={`${table}.${field}`} value={`${table}.${field}`}>
                  <span className="font-mono text-sm ml-2">{field}</span>
                </SelectItem>
              ))}
            </div>
          ))}

          {availableFields.length === 0 && (
            <div className="px-2 py-1 text-sm text-gray-500">
              No fields available
            </div>
          )}
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

export default FieldSelectField;
