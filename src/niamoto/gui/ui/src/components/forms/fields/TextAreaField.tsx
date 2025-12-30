// src/components/forms/widgets/TextAreaField.tsx

import React from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';

interface TextAreaFieldProps {
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
  rows?: number;
  maxLength?: number;
}

const TextAreaField: React.FC<TextAreaFieldProps> = ({
  name,
  label,
  description,
  value = '',
  onChange,
  placeholder,
  required = false,
  disabled = false,
  error,
  className = '',
  rows = 4,
  maxLength
}) => {
  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <Textarea
        id={name}
        name={name}
        value={value}
        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => onChange?.(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={error ? 'border-red-500' : ''}
        rows={rows}
        maxLength={maxLength}
      />
      <div className="flex justify-between">
        <div>
          {description && !error && (
            <FormDescription>{description}</FormDescription>
          )}
          {error && (
            <FormMessage className="text-red-500">{error}</FormMessage>
          )}
        </div>
        {maxLength && (
          <span className="text-xs text-gray-500">
            {value.length}/{maxLength}
          </span>
        )}
      </div>
    </FormItem>
  );
};

export default TextAreaField;
