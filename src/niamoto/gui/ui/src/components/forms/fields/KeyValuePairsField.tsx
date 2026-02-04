// src/components/forms/fields/KeyValuePairsField.tsx

import React, { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Plus, X } from 'lucide-react';

interface KeyValuePairsFieldProps {
  name: string;
  label?: string;
  description?: string;
  placeholder?: string;
  value?: Record<string, string>;
  onChange?: (value: Record<string, string>) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
}

const KeyValuePairsField: React.FC<KeyValuePairsFieldProps> = ({
  name: _name,
  label,
  description,
  placeholder,
  value = {},
  onChange,
  required = false,
  disabled = false,
  error,
  className = ''
}) => {
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const pairs = Object.entries(value);

  const handleAdd = () => {
    if (newKey.trim() && !value[newKey.trim()]) {
      const updated = { ...value, [newKey.trim()]: newValue };
      onChange?.(updated);
      setNewKey('');
      setNewValue('');
    }
  };

  const handleRemove = (key: string) => {
    const updated = { ...value };
    delete updated[key];
    onChange?.(updated);
  };

  const handleValueChange = (key: string, newVal: string) => {
    const updated = { ...value, [key]: newVal };
    onChange?.(updated);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
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

      <div className="space-y-2">
        {/* Existing pairs */}
        {pairs.map(([key, val]) => (
          <div key={key} className="flex items-center gap-2">
            <Input
              value={key}
              disabled
              className="flex-1 bg-muted"
            />
            <span className="text-muted-foreground">&rarr;</span>
            <Input
              value={val}
              onChange={(e) => handleValueChange(key, e.target.value)}
              disabled={disabled}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => handleRemove(key)}
              disabled={disabled}
              className="h-9 w-9 text-muted-foreground hover:text-destructive"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ))}

        {/* Add new pair */}
        {!disabled && (
          <div className="flex items-center gap-2">
            <Input
              placeholder={placeholder || "Key"}
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
            />
            <span className="text-muted-foreground">&rarr;</span>
            <Input
              placeholder="Value"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleAdd}
              disabled={!newKey.trim()}
              className="h-9 w-9"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        )}

        {pairs.length === 0 && disabled && (
          <div className="text-sm text-muted-foreground">
            No mappings defined
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

export default KeyValuePairsField;
