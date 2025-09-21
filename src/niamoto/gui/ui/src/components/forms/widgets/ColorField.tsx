// src/components/forms/widgets/ColorField.tsx

import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Palette } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ColorFieldProps {
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
  presets?: string[];
}

const ColorField: React.FC<ColorFieldProps> = ({
  name,
  label,
  description,
  value = '#000000',
  onChange,
  placeholder = '#000000',
  required = false,
  disabled = false,
  error,
  className = '',
  presets = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
    '#DDA0DD', '#98D8C8', '#6C5CE7', '#FDCB6E', '#FD79A8'
  ]
}) => {
  const [showPresets, setShowPresets] = useState(false);

  const handleColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(e.target.value);
  };

  const handlePresetClick = (color: string) => {
    onChange?.(color);
    setShowPresets(false);
  };

  return (
    <FormItem className={className}>
      {label && (
        <Label htmlFor={name}>
          <Palette className="inline-block h-3 w-3 mr-1" />
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Input
            id={name}
            name={name}
            type="text"
            value={value}
            onChange={handleColorChange}
            placeholder={placeholder}
            disabled={disabled}
            className={`pr-12 ${error ? 'border-red-500' : ''}`}
          />
          <input
            type="color"
            value={value}
            onChange={handleColorChange}
            disabled={disabled}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 border rounded cursor-pointer"
            style={{ backgroundColor: value }}
          />
        </div>
        {!disabled && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowPresets(!showPresets)}
          >
            Presets
          </Button>
        )}
      </div>
      {showPresets && !disabled && (
        <div className="flex flex-wrap gap-2 p-2 border rounded bg-gray-50">
          {presets.map((color) => (
            <button
              key={color}
              type="button"
              className="w-8 h-8 rounded border-2 border-gray-300 hover:border-gray-500 transition-colors"
              style={{ backgroundColor: color }}
              onClick={() => handlePresetClick(color)}
              title={color}
            />
          ))}
        </div>
      )}
      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}
    </FormItem>
  );
};

export default ColorField;
