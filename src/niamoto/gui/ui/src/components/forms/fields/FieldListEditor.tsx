// src/components/forms/fields/FieldListEditor.tsx

import React, { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2, GripVertical, ChevronDown, ChevronUp } from 'lucide-react';
import TagsField from './TagsField';

interface FieldConfig {
  source?: string | null;
  class_object: string | string[];
  target: string;
  units?: string | null;
  format?: 'range' | 'number' | 'text' | null;
}

interface FieldListEditorProps {
  name: string;
  label?: string;
  description?: string;
  value?: FieldConfig[];
  onChange?: (value: FieldConfig[]) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  groupBy?: string;
  source?: string;          // Default source for new fields
  minItems?: number;
  maxItems?: number;
}

const emptyField: FieldConfig = {
  class_object: '',
  target: '',
  units: null,
  format: null
};

const FieldListEditor: React.FC<FieldListEditorProps> = ({
  name: _name,
  label,
  description,
  value = [],
  onChange,
  required = false,
  disabled = false,
  error,
  className = '',
  minItems = 0,
  maxItems
}) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  // Add a new field
  const handleAdd = () => {
    if (maxItems && value.length >= maxItems) return;
    const newFields = [...value, { ...emptyField }];
    onChange?.(newFields);
    setExpandedIndex(newFields.length - 1);
  };

  // Remove a field
  const handleRemove = (index: number) => {
    if (value.length <= minItems) return;
    const newFields = value.filter((_, i) => i !== index);
    onChange?.(newFields);
    if (expandedIndex === index) {
      setExpandedIndex(newFields.length > 0 ? Math.min(index, newFields.length - 1) : null);
    } else if (expandedIndex !== null && expandedIndex > index) {
      setExpandedIndex(expandedIndex - 1);
    }
  };

  // Update a field
  const handleFieldChange = (index: number, key: keyof FieldConfig, fieldValue: FieldConfig[keyof FieldConfig]) => {
    const newFields = [...value];
    newFields[index] = { ...newFields[index], [key]: fieldValue };
    onChange?.(newFields);
  };

  // Handle class_object change (can be string or string[])
  const handleClassObjectChange = (index: number, newValue: string | string[]) => {
    handleFieldChange(index, 'class_object', newValue);
  };

  // Move field up/down
  const moveField = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= value.length) return;

    const newFields = [...value];
    [newFields[index], newFields[newIndex]] = [newFields[newIndex], newFields[index]];
    onChange?.(newFields);
    setExpandedIndex(newIndex);
  };

  // Toggle expand/collapse
  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  // Get display label for a field
  const getFieldLabel = (field: FieldConfig, index: number): string => {
    if (field.target) return field.target;
    if (typeof field.class_object === 'string' && field.class_object) return field.class_object;
    if (Array.isArray(field.class_object) && field.class_object.length > 0) {
      return field.class_object.join(', ');
    }
    return `Field ${index + 1}`;
  };

  return (
    <FormItem className={className}>
      {label && (
        <div className="flex items-center justify-between mb-2">
          <Label>
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAdd}
            disabled={disabled || (maxItems !== undefined && value.length >= maxItems)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add field
          </Button>
        </div>
      )}

      <div className="space-y-2">
        {value.map((field, index) => (
          <Card key={index} className="border">
            {/* Header - always visible */}
            <CardHeader
              className="py-2 px-3 cursor-pointer hover:bg-muted/50"
              onClick={() => toggleExpand(index)}
            >
              <div className="flex items-center gap-2">
                <GripVertical className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-sm font-medium flex-1">
                  {getFieldLabel(field, index)}
                </CardTitle>
                {field.units && (
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    {field.units}
                  </span>
                )}
                {field.format && (
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    {field.format}
                  </span>
                )}
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => { e.stopPropagation(); moveField(index, 'up'); }}
                    disabled={disabled || index === 0}
                  >
                    <ChevronUp className="h-3 w-3" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => { e.stopPropagation(); moveField(index, 'down'); }}
                    disabled={disabled || index === value.length - 1}
                  >
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground hover:text-destructive"
                    onClick={(e) => { e.stopPropagation(); handleRemove(index); }}
                    disabled={disabled || value.length <= minItems}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </CardHeader>

            {/* Content - collapsible */}
            {expandedIndex === index && (
              <CardContent className="pt-0 pb-3 px-3 space-y-3">
                {/* Class Object */}
                <div>
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    Class Object(s)
                  </Label>
                  <TagsField
                    name={`${_name}.${index}.class_object`}
                    value={Array.isArray(field.class_object) ? field.class_object : field.class_object ? [field.class_object] : []}
                    onChange={(tags) => handleClassObjectChange(index, tags.length === 1 ? tags[0] : tags)}
                    placeholder="Enter class object names..."
                    disabled={disabled}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Single value or multiple for ranges
                  </p>
                </div>

                {/* Target */}
                <div>
                  <Label className="text-xs text-muted-foreground mb-1 block">
                    Target Field Name
                  </Label>
                  <Input
                    value={field.target || ''}
                    onChange={(e) => handleFieldChange(index, 'target', e.target.value)}
                    placeholder="Output field name..."
                    disabled={disabled}
                  />
                </div>

                {/* Units and Format in a row */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs text-muted-foreground mb-1 block">
                      Units (optional)
                    </Label>
                    <Input
                      value={field.units || ''}
                      onChange={(e) => handleFieldChange(index, 'units', e.target.value || null)}
                      placeholder="e.g., ha, m, mm/an"
                      disabled={disabled}
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground mb-1 block">
                      Format (optional)
                    </Label>
                    <Select
                      value={field.format || 'none'}
                      onValueChange={(v) => handleFieldChange(index, 'format', v === 'none' ? null : v)}
                      disabled={disabled}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select format" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        <SelectItem value="range">Range (min-max)</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                        <SelectItem value="text">Text</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            )}
          </Card>
        ))}

        {value.length === 0 && (
          <div className="text-sm text-muted-foreground text-center py-4 border rounded-md border-dashed">
            No fields configured. Click "Add field" to start.
          </div>
        )}
      </div>

      {description && !error && (
        <FormDescription className="mt-2">{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500 mt-2">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default FieldListEditor;
