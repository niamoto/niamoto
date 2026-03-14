// src/components/forms/widgets/NumberField.tsx

import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';

interface NumberFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: number;
  onChange?: (value: number | undefined) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  min?: number;
  max?: number;
  step?: number;
  className?: string;
}

const NumberField: React.FC<NumberFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder,
  required = false,
  disabled = false,
  error,
  min,
  max,
  step = 1,
  className = ''
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      onChange?.(undefined);
    } else {
      const num = parseFloat(val);
      if (!isNaN(num)) {
        onChange?.(num);
      }
    }
  };

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Input
        id={name}
        name={name}
        type="number"
        value={value ?? ''}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        className={error ? 'border-red-500' : ''}
      />
      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default NumberField;
