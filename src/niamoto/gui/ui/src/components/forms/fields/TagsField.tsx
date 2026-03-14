// src/components/forms/fields/TagsField.tsx

import React, { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { X } from 'lucide-react';

interface TagsFieldProps {
  name: string;
  label?: string;
  description?: string;
  placeholder?: string;
  value?: string[];
  onChange?: (value: string[]) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
}

const TagsField: React.FC<TagsFieldProps> = ({
  name: _name,
  label,
  description,
  placeholder,
  value = [],
  onChange,
  required = false,
  disabled = false,
  error,
  className = ''
}) => {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = (tag: string) => {
    const trimmed = tag.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange?.([...value, trimmed]);
    }
    setInputValue('');
  };

  const handleRemove = (tagToRemove: string) => {
    onChange?.(value.filter(tag => tag !== tagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd(inputValue);
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      // Remove last tag on backspace when input is empty
      handleRemove(value[value.length - 1]);
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

      <div className="flex flex-wrap gap-2 p-2 border rounded-md min-h-[42px] bg-background">
        {/* Tags */}
        {value.map((tag) => (
          <Badge
            key={tag}
            variant="secondary"
            className="flex items-center gap-1 px-2 py-1"
          >
            {tag}
            {!disabled && (
              <button
                type="button"
                onClick={() => handleRemove(tag)}
                className="ml-1 hover:text-destructive focus:outline-none"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </Badge>
        ))}

        {/* Input for new tags */}
        {!disabled && (
          <Input
            type="text"
            placeholder={value.length === 0 ? (placeholder || "Add tag...") : ""}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              if (inputValue.trim()) {
                handleAdd(inputValue);
              }
            }}
            className="flex-1 min-w-[120px] border-0 shadow-none focus-visible:ring-0 p-0 h-6"
          />
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

export default TagsField;
