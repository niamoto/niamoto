// src/components/forms/widgets/ObjectField.tsx

import React from 'react';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import TextField from './TextField';
import NumberField from './NumberField';
import CheckboxField from './CheckboxField';
import SelectField from './SelectField';

interface ObjectFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: Record<string, any>;
  onChange?: (value: Record<string, any>) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  properties?: Record<string, any>;
}

const ObjectField: React.FC<ObjectFieldProps> = ({
  name,
  label,
  description,
  value = {},
  onChange,
  required = false,
  disabled = false,
  error,
  className = '',
  properties = {}
}) => {
  const handleFieldChange = (fieldName: string, fieldValue: any) => {
    const newValue = { ...value, [fieldName]: fieldValue };
    onChange?.(newValue);
  };

  const renderField = (fieldName: string, fieldSchema: any) => {
    const fieldType = Array.isArray(fieldSchema.type) ? fieldSchema.type[0] : fieldSchema.type;
    const fieldValue = value[fieldName];

    const commonProps = {
      name: `${name}.${fieldName}`,
      label: fieldSchema.title || fieldName,
      description: fieldSchema.description,
      value: fieldValue,
      onChange: (val: any) => handleFieldChange(fieldName, val),
      disabled,
      required: fieldSchema.required || false
    };

    switch (fieldType) {
      case 'string':
        if (fieldSchema.enum) {
          return (
            <SelectField
              {...commonProps}
              options={fieldSchema.enum.map((val: any) => ({ value: val, label: val }))}
            />
          );
        }
        return <TextField {...commonProps} />;

      case 'number':
      case 'integer':
        return (
          <NumberField
            {...commonProps}
            min={fieldSchema.minimum}
            max={fieldSchema.maximum}
          />
        );

      case 'boolean':
        return <CheckboxField {...commonProps} />;

      case 'object':
        return (
          <ObjectField
            {...commonProps}
            properties={fieldSchema.properties || {}}
          />
        );

      default:
        return <TextField {...commonProps} />;
    }
  };


  return (
    <FormItem className={className}>
      {label && (
        <Label>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <div className="space-y-3">
        {Object.entries(properties).map(([fieldName, fieldSchema]) => (
          <div key={fieldName}>
            {renderField(fieldName, fieldSchema)}
          </div>
        ))}
        {Object.keys(properties).length === 0 && (
          <div className="text-sm text-gray-500">
            No properties defined
          </div>
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

export default ObjectField;
