// src/components/forms/widgets/ObjectField.tsx

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Label } from '@/components/ui/label';
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form';
import { evaluateUiCondition, getUiSchemaValue, humanizeFieldName } from '../formSchemaUtils';
import TextField from './TextField';
import NumberField from './NumberField';
import CheckboxField from './CheckboxField';
import SelectField from './SelectField';
import TextAreaField from './TextAreaField';
import JsonField from './JsonField';
import KeyValuePairsField from './KeyValuePairsField';
import TagsField from './TagsField';
import type {
  FieldSchema,
  FormValue,
  FormValues,
  SelectOption,
  SelectOptionValue,
} from '../formSchemaTypes';
import {
  isFormValues,
  isSelectOptionValue,
  isStringArray,
} from '../formSchemaTypes';

interface ObjectFieldProps {
  name: string;
  label?: string;
  description?: string;
  value?: FormValues;
  onChange?: (value: FormValues) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  className?: string;
  properties?: Record<string, FieldSchema>;
}

const ObjectField: React.FC<ObjectFieldProps> = ({
  name,
  label,
  description,
  value = {},
  onChange,
  required = false,
  disabled = false,
  error,
  className = '',
  properties = {}
}) => {
  const { t } = useTranslation(['common', 'widgets']);

  const handleFieldChange = (fieldName: string, fieldValue: FormValue | undefined) => {
    const newValue = { ...value, [fieldName]: fieldValue };
    onChange?.(newValue);
  };

  const renderField = (fieldName: string, fieldSchema: FieldSchema) => {
    const fieldType = Array.isArray(fieldSchema.type) ? fieldSchema.type[0] : fieldSchema.type;
    const fieldValue = value[fieldName];
    const uiCondition = getUiSchemaValue<string>(fieldSchema, 'ui:condition');

    if (!evaluateUiCondition(uiCondition, value)) {
      return null;
    }

    // Check for ui:widget hint (Pydantic places it directly in schema)
    const uiWidget = getUiSchemaValue<string>(fieldSchema, 'ui:widget');
    const uiPlaceholder = getUiSchemaValue<string>(fieldSchema, 'ui:placeholder');
    const uiHelp = getUiSchemaValue<string>(fieldSchema, 'ui:help');
    const uiOptions = getUiSchemaValue<Array<string | SelectOption>>(fieldSchema, 'ui:options');
    const autoTitle = humanizeFieldName(fieldName);
    const resolvedLabel =
      fieldSchema.title && fieldSchema.title !== autoTitle
        ? fieldSchema.title
        : t(`widgets:form.fieldLabels.${fieldName}`, { defaultValue: autoTitle });

    const translateOptionLabel = (optionValue: SelectOptionValue, fallbackLabel: string) =>
      t(`widgets:form.fieldOptions.${fieldName}.${String(optionValue)}`, {
        defaultValue: fallbackLabel,
      });

    const commonProps = {
      name: `${name}.${fieldName}`,
      label: resolvedLabel,
      description: uiHelp || fieldSchema.description,
      placeholder: uiPlaceholder,
      disabled,
      required: fieldSchema.required || false
    };

    // First check ui:widget hint
    if (uiWidget) {
      switch (uiWidget) {
        case 'textarea':
          return <TextAreaField {...commonProps} />;

        case 'select':
          {
            const selectOptions = uiOptions?.map((opt) => {
              if (typeof opt === 'string') {
                return { value: opt, label: translateOptionLabel(opt, opt) };
              }
              return {
                value: opt.value,
                label: translateOptionLabel(opt.value, opt.label),
              };
            }) ||
              fieldSchema.enum?.map((val) => ({
                value: val,
                label: translateOptionLabel(val, String(val)),
              })) || [];
            return (
              <SelectField
                {...commonProps}
                value={isSelectOptionValue(fieldValue) ? fieldValue : undefined}
                onChange={(val) => handleFieldChange(fieldName, val)}
                options={selectOptions}
              />
            );
          }

        case 'checkbox':
          return (
            <CheckboxField
              {...commonProps}
              value={typeof fieldValue === 'boolean' ? fieldValue : false}
              onChange={(val) => handleFieldChange(fieldName, val)}
            />
          );

        case 'json':
          return (
            <JsonField
              {...commonProps}
              value={fieldValue}
              onChange={(val) => handleFieldChange(fieldName, val as FormValue | undefined)}
            />
          );

        case 'key-value-pairs':
          return (
            <KeyValuePairsField
              {...commonProps}
              value={isFormValues(fieldValue) ? Object.fromEntries(
                Object.entries(fieldValue).filter(([, val]) => typeof val === 'string')
              ) as Record<string, string> : undefined}
              onChange={(val) => handleFieldChange(fieldName, val)}
            />
          );

        case 'tags':
          return (
            <TagsField
              {...commonProps}
              value={isStringArray(fieldValue) ? fieldValue : []}
              onChange={(val) => handleFieldChange(fieldName, val)}
            />
          );

        case 'number':
          return (
            <NumberField
              {...commonProps}
              value={typeof fieldValue === 'number' ? fieldValue : undefined}
              onChange={(val) => handleFieldChange(fieldName, val)}
              min={fieldSchema.minimum}
              max={fieldSchema.maximum}
            />
          );

        // Fall through for unknown widgets
        default:
          break;
      }
    }

    // Fallback based on JSON schema type
    switch (fieldType) {
      case 'string':
        if (fieldSchema.enum) {
          return (
            <SelectField
              {...commonProps}
              value={isSelectOptionValue(fieldValue) ? fieldValue : undefined}
              onChange={(val) => handleFieldChange(fieldName, val)}
              options={fieldSchema.enum.map((val) => ({
                value: val,
                label: translateOptionLabel(val, String(val)),
              }))}
            />
          );
        }
        return (
          <TextField
            {...commonProps}
            value={typeof fieldValue === 'string' ? fieldValue : ''}
            onChange={(val) => handleFieldChange(fieldName, val)}
          />
        );

      case 'number':
      case 'integer':
        return (
          <NumberField
            {...commonProps}
            value={typeof fieldValue === 'number' ? fieldValue : undefined}
            onChange={(val) => handleFieldChange(fieldName, val)}
            min={fieldSchema.minimum}
            max={fieldSchema.maximum}
          />
        );

      case 'boolean':
        return (
          <CheckboxField
            {...commonProps}
            value={typeof fieldValue === 'boolean' ? fieldValue : false}
            onChange={(val) => handleFieldChange(fieldName, val)}
          />
        );

      case 'object':
        // Check if it's a Dict[str, str] (additionalProperties with string type)
        if (fieldSchema.additionalProperties?.type === 'string') {
          return (
            <KeyValuePairsField
              {...commonProps}
              value={isFormValues(fieldValue) ? Object.fromEntries(
                Object.entries(fieldValue).filter(([, val]) => typeof val === 'string')
              ) as Record<string, string> : undefined}
              onChange={(val) => handleFieldChange(fieldName, val)}
            />
          );
        }
        return (
          <ObjectField
            {...commonProps}
            value={isFormValues(fieldValue) ? fieldValue : {}}
            onChange={(val) => handleFieldChange(fieldName, val)}
            properties={fieldSchema.properties || {}}
          />
        );

      case 'array':
        // Check if it's a simple string array (tags)
        if (fieldSchema.items?.type === 'string') {
          return (
            <TagsField
              {...commonProps}
              value={isStringArray(fieldValue) ? fieldValue : []}
              onChange={(val) => handleFieldChange(fieldName, val)}
            />
          );
        }
        return (
          <JsonField
            {...commonProps}
            value={fieldValue}
            onChange={(val) => handleFieldChange(fieldName, val as FormValue | undefined)}
          />
        );

      default:
        return (
          <TextField
            {...commonProps}
            value={typeof fieldValue === 'string' ? fieldValue : ''}
            onChange={(val) => handleFieldChange(fieldName, val)}
          />
        );
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
      <div className="space-y-3">
        {Object.entries(properties)
          .map(([fieldName, fieldSchema]) => {
            const renderedField = renderField(fieldName, fieldSchema);
            if (!renderedField) {
              return null;
            }

            return <div key={fieldName}>{renderedField}</div>;
          })
          .filter(Boolean)}
        {Object.keys(properties).length === 0 && (
          <div className="text-sm text-gray-500">
            {t('messages.noPropertiesDefined')}
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

export default ObjectField;
