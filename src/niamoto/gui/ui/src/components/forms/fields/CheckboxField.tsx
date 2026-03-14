// src/components/forms/widgets/CheckboxField.tsx

import React from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';

interface CheckboxFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: boolean;
  onChange?: (value: boolean) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
}

const CheckboxField: React.FC<CheckboxFieldProps> = ({
  name,
  label,
  description,
  value = false,
  onChange,
  required = false,
  disabled = false,
  error,
  className = ''
}) => {
  return (
    <FormItem className={`flex flex-col space-y-2 ${className}`}>
      <div className="flex items-center space-x-2">
        <Checkbox
          id={name}
          checked={value}
          onCheckedChange={(checked: boolean) => onChange?.(checked)}
          disabled={disabled}
        />
        {label && (
          <Label
            htmlFor={name}
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </Label>
        )}
      </div>
      {description && !error && (
        <FormDescription className="ml-6">{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500 ml-6">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default CheckboxField;
