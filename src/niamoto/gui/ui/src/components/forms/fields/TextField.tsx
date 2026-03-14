// src/components/forms/widgets/TextField.tsx

import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';

interface TextFieldProps {
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
}

const TextField: React.FC<TextFieldProps> = ({
  name,
  label,
  description,
  value = '',
  onChange,
  placeholder,
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
      <Input
        id={name}
        name={name}
        type="text"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
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

export default TextField;
