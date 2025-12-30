// src/components/forms/widgets/SelectField.tsx

import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';

interface SelectOption {
  value: any;
  label: string;
}

interface SelectFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: any;
  onChange?: (value: any) => void;
  options: SelectOption[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
}

const SelectField: React.FC<SelectFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  options,
  placeholder = 'Select an option...',
  required = false,
  disabled = false,
  error,
  className = ''
}) => {
  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Select
        value={value?.toString()}
        onValueChange={(val) => {
          // Convert back to original type if needed
          const option = options.find(opt => opt.value?.toString() === val);
          onChange?.(option?.value);
        }}
        disabled={disabled}
      >
        <SelectTrigger id={name} className={error ? 'border-red-500' : ''}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option, index) => (
            <SelectItem
              key={`${option.value}-${index}`}
              value={option.value?.toString() || ''}
            >
              {option.label}
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

export default SelectField;
