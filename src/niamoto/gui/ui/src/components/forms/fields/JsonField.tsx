// src/components/forms/widgets/JsonField.tsx

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { Code2, Check, X } from 'lucide-react';

interface JsonFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: unknown;
  onChange?: (value: unknown) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  schema?: unknown; // JSON schema for validation
}

function formatJsonValue(value: unknown): {
  sourceKey: string;
  textValue: string;
  isFormatted: boolean;
} {
  try {
    const textValue =
      value !== undefined && value !== null ? JSON.stringify(value, null, 2) : '';
    return {
      sourceKey: textValue,
      textValue,
      isFormatted: true,
    };
  } catch {
    const textValue = value !== undefined && value !== null ? String(value) : '';
    return {
      sourceKey: textValue,
      textValue,
      isFormatted: false,
    };
  }
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
  const { t } = useTranslation('common');
  const formattedValue = formatJsonValue(value);
  const [editorState, setEditorState] = useState<{
    sourceKey: string;
    textValue: string;
    parseError: string | null;
    isFormatted: boolean;
  }>(() => ({
    ...formattedValue,
    parseError: null,
  }));

  const isCurrentValue = editorState.sourceKey === formattedValue.sourceKey;
  const textValue = isCurrentValue ? editorState.textValue : formattedValue.textValue;
  const parseError = isCurrentValue ? editorState.parseError : null;
  const isFormatted = isCurrentValue ? editorState.isFormatted : formattedValue.isFormatted;

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;

    // Try to parse and update the value
    if (newText.trim() === '') {
      setEditorState({
        sourceKey: formattedValue.sourceKey,
        textValue: newText,
        parseError: null,
        isFormatted: false,
      });
      onChange?.(undefined);
      return;
    }

    try {
      const parsed = JSON.parse(newText);
      setEditorState({
        sourceKey: formattedValue.sourceKey,
        textValue: newText,
        parseError: null,
        isFormatted: false,
      });
      onChange?.(parsed);
    } catch (err) {
      setEditorState({
        sourceKey: formattedValue.sourceKey,
        textValue: newText,
        parseError: err instanceof Error ? err.message : 'Invalid JSON',
        isFormatted: false,
      });
    }
  };

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(textValue);
      const formatted = JSON.stringify(parsed, null, 2);
      setEditorState({
        sourceKey: formattedValue.sourceKey,
        textValue: formatted,
        parseError: null,
        isFormatted: true,
      });
      onChange?.(parsed);
    } catch (err) {
      setEditorState({
        sourceKey: formattedValue.sourceKey,
        textValue,
        parseError: err instanceof Error ? err.message : 'Invalid JSON',
        isFormatted: false,
      });
    }
  };

  const handleClear = () => {
    setEditorState({
      sourceKey: formattedValue.sourceKey,
      textValue: '',
      parseError: null,
      isFormatted: false,
    });
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
                  title={t('actions.formatJson')}
                >
                  <Check className="h-3 w-3" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  disabled={!textValue}
                  title={t('actions.clear')}
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
