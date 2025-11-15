// src/components/forms/widgets/JsonField.tsx

import React, { useState, useEffect } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { Code2, Check, X } from 'lucide-react';

interface JsonFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: any;
  onChange?: (value: any) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  schema?: any; // JSON schema for validation
}

const JsonField: React.FC<JsonFieldProps> = ({
  name,
  label,
  description,
  value,
  onChange,
  placeholder = '{}',
  required = false,
  disabled = false,
  error,
  className = '',
  schema: _schema
}) => {
  const [textValue, setTextValue] = useState<string>('');
  const [parseError, setParseError] = useState<string | null>(null);
  const [isFormatted, setIsFormatted] = useState(false);

  // Initialize text value from prop value
  useEffect(() => {
    try {
      const formatted = value ? JSON.stringify(value, null, 2) : '';
      setTextValue(formatted);
      setIsFormatted(true);
    } catch (err) {
      setTextValue(String(value || ''));
      setIsFormatted(false);
    }
  }, [value]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    setTextValue(newText);
    setIsFormatted(false);

    // Try to parse and update the value
    if (newText.trim() === '') {
      setParseError(null);
      onChange?.(undefined);
      return;
    }

    try {
      const parsed = JSON.parse(newText);
      setParseError(null);
      onChange?.(parsed);
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(textValue);
      const formatted = JSON.stringify(parsed, null, 2);
      setTextValue(formatted);
      setIsFormatted(true);
      setParseError(null);
      onChange?.(parsed);
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  const handleClear = () => {
    setTextValue('');
    setParseError(null);
    onChange?.(undefined);
  };

  const displayError = parseError || error;

  return (
    <FormItem className={className}>
      {label && (
        <div className="flex items-center justify-between">
          <Label htmlFor={name}>
            <Code2 className="inline-block h-3 w-3 mr-1" />
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          <div className="flex gap-1">
            {!disabled && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleFormat}
                  disabled={!textValue || isFormatted}
                  title="Format JSON"
                >
                  <Check className="h-3 w-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  disabled={!textValue}
                  title="Clear"
                >
                  <X className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        </div>
      )}
      <Textarea
        id={name}
        name={name}
        value={textValue}
        onChange={handleTextChange}
        placeholder={placeholder}
        disabled={disabled}
        className={`font-mono text-sm ${displayError ? 'border-red-500' : ''}`}
        rows={8}
      />
      {description && !displayError && (
        <FormDescription>{description}</FormDescription>
      )}
      {displayError && (
        <FormMessage className="text-red-500">{displayError}</FormMessage>
      )}
    </FormItem>
  );
};

export default JsonField;
