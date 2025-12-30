// src/components/forms/widgets/ArrayField.tsx

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Plus, X, GripVertical, ChevronDown, ChevronRight } from 'lucide-react';
import TextField from './TextField';
import NumberField from './NumberField';
import SelectField from './SelectField';
import CheckboxField from './CheckboxField';
import FieldSelectField from './FieldSelectField';
import ObjectField from './ObjectField';

interface ArrayFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: any[];
  onChange?: (value: any[]) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  itemType?: string;
  itemSchema?: any;
  minItems?: number;
  maxItems?: number;
  availableFields?: string[];
}

const ArrayField: React.FC<ArrayFieldProps> = ({
  name,
  label,
  description,
  value = [],
  onChange,
  required = false,
  disabled = false,
  error,
  className = '',
  itemType = 'text',
  itemSchema,
  minItems = 0,
  maxItems,
  availableFields = []
}) => {
  const handleAddItem = () => {
    const newValue = [...value];
    let defaultValue: any;

    if (itemType === 'number') {
      defaultValue = 0;
    } else if (itemType === 'checkbox') {
      defaultValue = false;
    } else if (itemType === 'select' && itemSchema?.enum) {
      defaultValue = itemSchema.enum[0];
    } else if (itemType === 'object') {
      // For objects, create a default object with all required fields
      defaultValue = {};
      if (itemSchema?.properties) {
        Object.entries(itemSchema.properties).forEach(([key, prop]: [string, any]) => {
          if (prop.default !== undefined) {
            defaultValue[key] = prop.default;
          } else if (prop.type === 'string') {
            defaultValue[key] = '';
          } else if (prop.type === 'number') {
            defaultValue[key] = 0;
          } else if (prop.type === 'boolean') {
            defaultValue[key] = false;
          } else if (prop.type === 'array') {
            defaultValue[key] = [];
          } else if (prop.type === 'object') {
            defaultValue[key] = {};
          }
        });
      }
      // Handle $ref to definitions
      else if (itemSchema?.$ref) {
        // Start with empty object, will be populated by the form
        defaultValue = {};
      }
    } else {
      defaultValue = '';
    }

    newValue.push(defaultValue);
    onChange?.(newValue);
  };

  const handleRemoveItem = (index: number) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange?.(newValue);
  };

  const handleItemChange = (index: number, itemValue: any) => {
    const newValue = [...value];
    newValue[index] = itemValue;
    onChange?.(newValue);
  };

  const handleMoveItem = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === value.length - 1) return;

    const newValue = [...value];
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    [newValue[index], newValue[newIndex]] = [newValue[newIndex], newValue[index]];
    onChange?.(newValue);
  };

  // State to track which items are collapsed
  const [collapsedItems, setCollapsedItems] = useState<Set<number>>(new Set());

  const toggleItemCollapse = (index: number) => {
    const newCollapsed = new Set(collapsedItems);
    if (newCollapsed.has(index)) {
      newCollapsed.delete(index);
    } else {
      newCollapsed.add(index);
    }
    setCollapsedItems(newCollapsed);
  };

  const getItemSummary = (item: any, index: number) => {
    // For objects, try to create a meaningful summary
    if (itemType === 'object' && typeof item === 'object' && item !== null) {
      // Try common field names for summary
      const summaryFields = ['name', 'label', 'title', 'target', 'source', 'field'];
      for (const field of summaryFields) {
        if (item[field]) {
          return `${item[field]}`;
        }
      }
      // Fallback to showing first non-empty field
      const firstValue = Object.values(item).find(v => v && v !== '');
      if (firstValue) {
        return String(firstValue).substring(0, 50);
      }
    }
    return `Item ${index + 1}`;
  };

  const renderItem = (item: any, index: number) => {
    const itemProps = {
      name: `${name}[${index}]`,
      value: item,
      onChange: (val: any) => handleItemChange(index, val),
      disabled,
    };

    const isCollapsed = collapsedItems.has(index);

    let itemComponent;
    switch (itemType) {
      case 'number':
        itemComponent = (
          <NumberField
            {...itemProps}
            min={itemSchema?.minimum}
            max={itemSchema?.maximum}
          />
        );
        break;
      case 'select':
        const options = itemSchema?.enum?.map((val: any) => ({ value: val, label: val })) || [];
        itemComponent = (
          <SelectField
            {...itemProps}
            options={options}
          />
        );
        break;
      case 'checkbox':
        itemComponent = <CheckboxField {...itemProps} />;
        break;
      case 'field-select':
        itemComponent = (
          <FieldSelectField
            {...itemProps}
            availableFields={availableFields}
          />
        );
        break;
      case 'object':
        // itemSchema should already be resolved by JsonSchemaForm
        const objectProperties = itemSchema?.properties || {};


        itemComponent = (
          <ObjectField
            {...itemProps}
            properties={objectProperties}
          />
        );
        break;
      default:
        itemComponent = <TextField {...itemProps} />;
    }

    // Special layout for objects to save space
    if (itemType === 'object') {
      return (
        <div key={index} className="border rounded-md mb-2">
          <div className="flex items-center gap-2 p-2 bg-muted/30">
            <button
              type="button"
              className="cursor-move text-gray-400 hover:text-gray-600"
              disabled={disabled}
              onMouseDown={(e) => {
                e.preventDefault();
              }}
            >
              <GripVertical className="h-4 w-4" />
            </button>

            <button
              type="button"
              className="flex items-center gap-1 flex-1 text-left"
              onClick={() => toggleItemCollapse(index)}
            >
              {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              <span className="font-medium text-sm">{getItemSummary(item, index)}</span>
            </button>

            <div className="flex gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleMoveItem(index, 'up')}
                disabled={disabled || index === 0}
              >
                ↑
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleMoveItem(index, 'down')}
                disabled={disabled || index === value.length - 1}
              >
                ↓
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleRemoveItem(index)}
                disabled={disabled || value.length <= minItems}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          {!isCollapsed && (
            <div className="p-3">
              {itemComponent}
            </div>
          )}
        </div>
      );
    }

    // Default layout for simple types
    return (
      <div key={index} className="flex items-center gap-2 p-2 border rounded">
        <button
          type="button"
          className="cursor-move text-gray-400 hover:text-gray-600"
          disabled={disabled}
          onMouseDown={(e) => {
            // Placeholder for drag handle - would need DnD library for full implementation
            e.preventDefault();
          }}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <div className="flex-1">
          {itemComponent}
        </div>
        <div className="flex gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleMoveItem(index, 'up')}
            disabled={disabled || index === 0}
          >
            ↑
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleMoveItem(index, 'down')}
            disabled={disabled || index === value.length - 1}
          >
            ↓
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleRemoveItem(index)}
            disabled={disabled || value.length <= minItems}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  };

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <div className="space-y-2">
        {value.map((item, index) => renderItem(item, index))}
        {(!maxItems || value.length < maxItems) && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddItem}
            disabled={disabled}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Item
          </Button>
        )}
      </div>
      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default ArrayField;
