// src/components/forms/JsonSchemaForm.tsx

import React, { useState, useEffect, useMemo } from 'react';
import type { UseFormReturn } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Info } from 'lucide-react';
import { useSourceColumns } from '@/lib/api/recipes';
import { evaluateUiCondition, flattenColumnTree, getUiSchemaValue, humanizeFieldName } from './formSchemaUtils';

// Import our specialized fields
import TextField from './fields/TextField';
import NumberField from './fields/NumberField';
import SelectField from './fields/SelectField';
import CheckboxField from './fields/CheckboxField';
import FieldSelectField from './fields/FieldSelectField';
import EntitySelectField from './fields/EntitySelectField';
import TransformSourceSelectField from './fields/TransformSourceSelectField';
import ArrayField from './fields/ArrayField';
import JsonField from './fields/JsonField';
import ColorField from './fields/ColorField';
import DirectorySelectField from './fields/DirectorySelectField';
import TextAreaField from './fields/TextAreaField';
import ObjectField from './fields/ObjectField';
import KeyValuePairsField from './fields/KeyValuePairsField';
import TagsField from './fields/TagsField';
import ClassObjectSelectField from './fields/ClassObjectSelectField';
import FilePickerField from './fields/FilePickerField';
import FieldListEditor from './fields/FieldListEditor';
import LayerSelectField from './fields/LayerSelectField';
import TransformParamsField from './fields/TransformParamsField';
import type {
  FieldSchema,
  FormValue,
  FormValues,
  PluginSchemaResponse,
  SelectOption,
} from './formSchemaTypes';
import {
  isFormValues,
  isSelectOptionValue,
  isStringArray,
} from './formSchemaTypes';

interface JsonSchemaFormProps {
  pluginId: string;
  pluginType?: string;
  groupBy?: string;
  form?: UseFormReturn<Record<string, unknown>>;
  onSubmit?: (data: FormValues) => void;
  onChange?: (data: FormValues) => void;
  readOnly?: boolean;
  className?: string;
  showTitle?: boolean;
  availableFields?: string[]; // For field-select widgets
  initialValues?: FormValues; // Initial values to populate the form
  hiddenFields?: string[];
}

function addCompatibilityFields(
  pluginId: string,
  properties: Record<string, FieldSchema>,
): Record<string, FieldSchema> {
  if (pluginId !== 'donut_chart' || properties.show_legend) {
    return properties;
  }

  const injectedField = {
    type: 'boolean',
    title: 'Show Legend',
    description: 'Display legend',
    default: false,
    'ui:widget': 'checkbox',
    'ui:group': 'display',
    'ui:order': 0,
  };

  const entries = Object.entries(properties);
  const legendOrientationIndex = entries.findIndex(([fieldName]) => fieldName === 'legend_orientation');

  if (legendOrientationIndex === -1) {
    return { ...properties, show_legend: injectedField };
  }

  return Object.fromEntries([
    ...entries.slice(0, legendOrientationIndex + 1),
    ['show_legend', injectedField],
    ...entries.slice(legendOrientationIndex + 1),
  ]);
}

const pluginSchemaCache = new Map<string, PluginSchemaResponse>();
const pluginSchemaRequests = new Map<string, Promise<PluginSchemaResponse>>();

async function loadPluginSchema(pluginId: string): Promise<PluginSchemaResponse> {
  const cachedSchema = pluginSchemaCache.get(pluginId);
  if (cachedSchema) {
    return cachedSchema;
  }

  const inFlightRequest = pluginSchemaRequests.get(pluginId);
  if (inFlightRequest) {
    return inFlightRequest;
  }

  const request = fetch(`/api/plugins/${pluginId}/schema`, {
    cache: 'no-store',
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Failed to fetch schema: ${response.statusText}`);
      }

      const data: PluginSchemaResponse = await response.json();
      pluginSchemaCache.set(pluginId, data);
      return data;
    })
    .finally(() => {
      pluginSchemaRequests.delete(pluginId);
    });

  pluginSchemaRequests.set(pluginId, request);
  return request;
}

function toStringRecord(value: FormValue | undefined): Record<string, string> | undefined {
  if (!isFormValues(value)) {
    return undefined;
  }

  const entries = Object.entries(value).filter(
    (entry): entry is [string, string] => typeof entry[1] === 'string'
  );
  return Object.fromEntries(entries);
}

const JsonSchemaForm: React.FC<JsonSchemaFormProps> = ({
  pluginId,
  pluginType: _pluginType, // unused but kept for interface compatibility
  groupBy,
  form,
  onSubmit: _onSubmit, // unused but kept for interface compatibility
  onChange,
  readOnly = false,
  className = '',
  showTitle = true,
  availableFields = [],
  initialValues = {},
  hiddenFields = []
}) => {
  const { t } = useTranslation(['common', 'widgets']);
  const [schema, setSchema] = useState<PluginSchemaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormValues>({});
  const hiddenFieldSet = useMemo(() => new Set(hiddenFields), [hiddenFields]);
  const lastSyncedValuesRef = React.useRef<string>('');

  // Track if we've initialized with initialValues
  const initializedRef = React.useRef(false);

  const filterHiddenValues = React.useCallback(
    (values: FormValues) =>
      Object.fromEntries(
        Object.entries(values).filter(([key]) => !hiddenFieldSet.has(key))
      ) as FormValues,
    [hiddenFieldSet]
  );

  // Fetch schema from API (only when pluginId changes)
  useEffect(() => {
    const fetchSchema = async () => {
      try {
        setLoading(true);
        setError(null);
        initializedRef.current = false;

        const data = await loadPluginSchema(pluginId);
        setSchema(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plugin schema');
      } finally {
        setLoading(false);
      }
    };

    if (pluginId) {
      void fetchSchema();
    }
  }, [pluginId]);

  useEffect(() => {
    if (!schema || loading || initializedRef.current) {
      return;
    }

    if (schema.schema?.properties) {
      const defaults: FormValues = {};
      Object.entries(schema.schema.properties).forEach(([key, field]) => {
        if (hiddenFieldSet.has(key)) {
          return;
        }
        if (field.default !== undefined) {
          defaults[key] = field.default;
        }
      });

      const initialData = { ...defaults, ...filterHiddenValues(initialValues) };
      setFormData(initialData);
      lastSyncedValuesRef.current = JSON.stringify(filterHiddenValues(initialData));
      initializedRef.current = true;
      return;
    }

    if (Object.keys(initialValues).length > 0) {
      const initialData = filterHiddenValues(initialValues);
      setFormData(initialData);
      lastSyncedValuesRef.current = JSON.stringify(initialData);
      initializedRef.current = true;
    }
  }, [filterHiddenValues, hiddenFieldSet, initialValues, loading, schema]);

  // Update form data when initialValues change (after initial load)
  useEffect(() => {
    const visibleInitialValues = filterHiddenValues(initialValues);
    if (schema && !loading && Object.keys(visibleInitialValues).length > 0) {
      const nextValuesKey = JSON.stringify(visibleInitialValues);
      if (nextValuesKey !== lastSyncedValuesRef.current) {
        setFormData(prev => ({ ...prev, ...visibleInitialValues }));
        lastSyncedValuesRef.current = nextValuesKey;
        initializedRef.current = true;
      }
    }
  }, [filterHiddenValues, initialValues, loading, schema]);

  const sourceFieldName = useMemo(() => {
    if (!schema?.schema?.properties) {
      return null;
    }

    if (schema.schema.properties.source) {
      return 'source';
    }

    return null;
  }, [schema]);

  const sourceValue = sourceFieldName ? formData[sourceFieldName] : undefined;
  const selectedSource = typeof sourceValue === 'string' && sourceValue.trim() !== '' ? sourceValue : null;
  const { columns: sourceColumns } = useSourceColumns(groupBy ?? '', selectedSource);
  const pluginSchemaType = schema?.plugin_type;

  const resolvedAvailableFields = useMemo(() => {
    const fromSource = flattenColumnTree(sourceColumns);
    const merged = new Set<string>([...fromSource, ...availableFields]);
    return Array.from(merged).sort();
  }, [availableFields, sourceColumns]);

  const resolveFieldLabel = React.useCallback((fieldName: string, title?: string) => {
    const autoTitle = humanizeFieldName(fieldName);
    if (!title || title === autoTitle) {
      return t(`widgets:form.fieldLabels.${fieldName}`, { defaultValue: autoTitle });
    }
    return title;
  }, [t]);

  const resolveFieldDescription = React.useCallback((fieldName: string, description?: string) => {
    return t(`widgets:form.fieldDescriptions.${fieldName}`, {
      defaultValue: description ?? '',
    });
  }, [t]);

  const translateOptionLabel = React.useCallback((fieldName: string, option: SelectOption) => {
    if (option.value === undefined || option.value === null) {
      return option.label;
    }

    return t(`widgets:form.fieldOptions.${fieldName}.${String(option.value)}`, {
      defaultValue: option.label,
    });
  }, [t]);

  // Handle field changes
  const handleFieldChange = React.useCallback((fieldName: string, value: FormValue | undefined) => {
    const newData = { ...formData, [fieldName]: value };
    setFormData(newData);
    lastSyncedValuesRef.current = JSON.stringify(filterHiddenValues(newData));

    if (onChange) {
      onChange(newData);
    }

    if (form) {
      form.setValue(fieldName as never, value as never);
    }
  }, [filterHiddenValues, form, formData, onChange]);

  // Helper function to resolve $ref in schema
  const resolveRef = React.useCallback((ref: string): FieldSchema | null => {
    if (!schema?.schema?.$defs) return null;
    const refName = ref.split('/').pop();
    return refName ? schema.schema.$defs[refName] : null;
  }, [schema]);

  const resolveFieldSchema = React.useCallback((fieldSchema: FieldSchema): FieldSchema => {
    const schemaWithRef = fieldSchema as FieldSchema & { $ref?: string };

    if (schemaWithRef.$ref) {
      const resolved = resolveRef(schemaWithRef.$ref);
      if (resolved) {
        const { $ref: _ignoredRef, ...rest } = schemaWithRef;
        return { ...resolved, ...rest };
      }
    }

    if (fieldSchema.allOf?.length === 1 && fieldSchema.allOf[0]?.$ref) {
      const resolved = resolveRef(fieldSchema.allOf[0].$ref);
      if (resolved) {
        return {
          ...resolved,
          ...fieldSchema,
          allOf: undefined,
        };
      }
    }

    return fieldSchema;
  }, [resolveRef]);

  // Render a single field based on its schema
  const renderField = React.useCallback((fieldName: string, fieldSchema: FieldSchema, required: boolean = false) => {
    const resolvedFieldSchema = resolveFieldSchema(fieldSchema);
    const fieldCondition = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:condition');
    if (!evaluateUiCondition(fieldCondition, formData)) {
      return null;
    }

    // Get UI widget type from json_schema_extra or directly from fieldSchema
    // Pydantic places ui:widget directly in the schema, not nested in json_schema_extra
    const uiWidget =
      getUiSchemaValue<string>(resolvedFieldSchema, 'ui:widget');
    const dependsOn = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:depends');
    const fieldValue = form
      ? (form.watch(fieldName as never) as FormValue | undefined)
      : formData[fieldName];
    const dependsValue = dependsOn ? formData[dependsOn] : undefined;
    const hasSelectableFields = resolvedAvailableFields.length > 0;
    const hasExistingFieldValue = Array.isArray(fieldValue)
      ? fieldValue.length > 0
      : fieldValue !== undefined && fieldValue !== null && fieldValue !== '';

    // Common props for all fields
    const commonProps = {
      name: fieldName,
      label: resolveFieldLabel(fieldName, resolvedFieldSchema.title),
      description: resolveFieldDescription(fieldName, resolvedFieldSchema.description),
      required,
      disabled: readOnly || (!!dependsOn && (dependsValue === undefined || dependsValue === null || dependsValue === '')),
      error: (form?.formState.errors[fieldName]?.message || undefined) as string | undefined
    };

    // Determine field type and render appropriate widget
    if (uiWidget) {
      switch (uiWidget) {
        case 'text':
          return (
            <TextField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'string' ? fieldValue : ''}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'textarea':
          return (
            <TextAreaField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'string' ? fieldValue : ''}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'number':
          return (
            <NumberField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'number' ? fieldValue : undefined}
              onChange={(value) => handleFieldChange(fieldName, value)}
              min={resolvedFieldSchema.minimum}
              max={resolvedFieldSchema.maximum}
            />
          );

        case 'select':
          {
            // Options can be in json_schema_extra['ui:options'] or directly in fieldSchema['ui:options']
            const rawOptions =
              getUiSchemaValue<Array<string | SelectOption>>(resolvedFieldSchema, 'ui:options') ||
              resolvedFieldSchema.enum?.map((val) => ({ value: val, label: String(val) })) ||
              [];
            const options: SelectOption[] = rawOptions
              .map((option) =>
                typeof option === 'string'
                  ? { value: option, label: option }
                  : option
              )
              .filter((option): option is SelectOption => isSelectOptionValue(option.value))
              .map((option) => ({
                ...option,
                label: translateOptionLabel(fieldName, option),
              }));
            return (
              <SelectField
                key={fieldName}
                {...commonProps}
                value={isSelectOptionValue(fieldValue) ? fieldValue : undefined}
                onChange={(value) => handleFieldChange(fieldName, value)}
                options={options}
              />
            );
          }

        case 'checkbox':
          return (
            <CheckboxField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'boolean' ? fieldValue : false}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'field-select':
          if (!hasSelectableFields && !hasExistingFieldValue) {
            return null;
          }
          return (
            <FieldSelectField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'string' ? fieldValue : undefined}
              onChange={(value) => handleFieldChange(fieldName, value)}
              availableFields={resolvedAvailableFields}
            />
          );

        case 'entity-select':
          {
            const entityKind = getUiSchemaValue<{ kind?: 'dataset' | 'reference' }>(
              resolvedFieldSchema,
              'ui:entity-filter'
            )?.kind;
            if (pluginSchemaType === 'transformer' && fieldName === 'source' && groupBy) {
              return (
                <TransformSourceSelectField
                  key={fieldName}
                  {...commonProps}
                  value={typeof fieldValue === 'string' ? fieldValue : undefined}
                  onChange={(value) => handleFieldChange(fieldName, value)}
                  groupBy={groupBy}
                  kind={entityKind}
                />
              );
            }
            return (
              <EntitySelectField
                key={fieldName}
                {...commonProps}
                value={typeof fieldValue === 'string' ? fieldValue : undefined}
                onChange={(value) => handleFieldChange(fieldName, value)}
                kind={entityKind}
                groupBy={groupBy}
              />
            );
          }

        case 'class-object-select':
          {
            const coSource = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:source');
            const coMultiple = getUiSchemaValue<boolean>(resolvedFieldSchema, 'ui:multiple');
            return (
              <ClassObjectSelectField
                key={fieldName}
                {...commonProps}
                value={
                  typeof fieldValue === 'string' || isStringArray(fieldValue)
                    ? fieldValue
                    : undefined
                }
                onChange={(value) => handleFieldChange(fieldName, value)}
                groupBy={groupBy}
                source={coSource}
                multiple={coMultiple}
              />
            );
          }

        case 'transform-source-select':
          {
            const sourceGroupBy = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:groupBy');
            return (
              <TransformSourceSelectField
                key={fieldName}
                {...commonProps}
                value={typeof fieldValue === 'string' ? fieldValue : undefined}
                onChange={(value) => handleFieldChange(fieldName, value)}
                groupBy={sourceGroupBy || groupBy}
              />
            );
          }

        case 'multi-field-select':
          if (!hasSelectableFields && !hasExistingFieldValue) {
            return null;
          }
          return (
            <ArrayField
              key={fieldName}
              {...commonProps}
              value={Array.isArray(fieldValue) ? fieldValue : []}
              onChange={(value) => handleFieldChange(fieldName, value)}
              itemType="field-select"
              availableFields={resolvedAvailableFields}
              minItems={resolvedFieldSchema.minItems}
              maxItems={resolvedFieldSchema.maxItems}
            />
          );

        case 'field-list':
        case 'field-list-editor':
          return (
            <FieldListEditor
              key={fieldName}
              {...commonProps}
              value={Array.isArray(fieldValue) ? fieldValue as Array<{
                source?: string | null;
                class_object: string | string[];
                target: string;
                units?: string | null;
                format?: 'range' | 'number' | 'text' | null;
              }> : []}
              onChange={(value) => handleFieldChange(fieldName, value)}
              groupBy={groupBy}
              minItems={resolvedFieldSchema.minItems}
              maxItems={resolvedFieldSchema.maxItems}
            />
          );

        case 'array':
          {
            const itemWidget = resolvedFieldSchema.json_schema_extra?.['ui:item-widget'];

            // Determine the item type based on the items schema
            let itemType = itemWidget || 'text';
            let resolvedItemSchema = resolvedFieldSchema.items;

            if (!itemWidget && resolvedFieldSchema.items) {
              // Check if items reference a $def (object type)
              if (resolvedFieldSchema.items.$ref) {
                itemType = 'object';
                const resolved = resolveRef(resolvedFieldSchema.items.$ref);
                if (resolved) {
                  resolvedItemSchema = resolved;
                }
              } else if (resolvedFieldSchema.items.type === 'object' || resolvedFieldSchema.items.properties) {
                itemType = 'object';
              } else if (resolvedFieldSchema.items.type) {
                itemType = resolvedFieldSchema.items.type;
              }
            }

            return (
              <ArrayField
                key={fieldName}
                {...commonProps}
                value={Array.isArray(fieldValue) ? fieldValue : []}
                onChange={(value) => handleFieldChange(fieldName, value)}
                itemType={itemType}
                itemSchema={resolvedItemSchema}
                minItems={resolvedFieldSchema.minItems}
                maxItems={resolvedFieldSchema.maxItems}
                availableFields={itemWidget === 'field-select' ? resolvedAvailableFields : undefined}
              />
            );
          }

        case 'json':
          {
            const transformSchemas = getUiSchemaValue<Record<string, Record<string, { type: string; default?: unknown; description?: string }>>>(
              resolvedFieldSchema,
              'ui:transform_schemas'
            );
            if (transformSchemas) {
              return (
                <TransformParamsField
                  key={fieldName}
                  {...commonProps}
                  value={isFormValues(fieldValue) ? fieldValue : undefined}
                  onChange={(value) => handleFieldChange(fieldName, value)}
                  selectedTransform={typeof formData.transform === 'string' ? formData.transform : undefined}
                  transformSchemas={transformSchemas}
                />
              );
            }
            if (fieldName === 'field_mapping' || resolvedFieldSchema.additionalProperties?.type === 'string') {
              return (
                <KeyValuePairsField
                  key={fieldName}
                  {...commonProps}
                  value={toStringRecord(fieldValue)}
                  onChange={(value) => handleFieldChange(fieldName, value)}
                />
              );
            }
            return (
              <JsonField
                key={fieldName}
                {...commonProps}
                value={fieldValue}
                onChange={(value) => handleFieldChange(fieldName, value as FormValue | undefined)}
              />
            );
          }

        case 'key-value-pairs':
          return (
            <KeyValuePairsField
              key={fieldName}
              {...commonProps}
              value={toStringRecord(fieldValue)}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'tags':
          return (
            <TagsField
              key={fieldName}
              {...commonProps}
              value={isStringArray(fieldValue) ? fieldValue : []}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'object':
          return (
            <ObjectField
              key={fieldName}
              {...commonProps}
              value={isFormValues(fieldValue) ? fieldValue : {}}
              onChange={(value) => handleFieldChange(fieldName, value)}
              properties={resolvedFieldSchema.properties || {}}
            />
          );

        case 'color':
          return (
            <ColorField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'string' ? fieldValue : undefined}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'directory-select':
          return (
            <DirectorySelectField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'string' ? fieldValue : undefined}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );

        case 'file-select':
        case 'file-picker':
          {
            const fileAccept = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:accept') || 'all';
            const fileBasePath = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:basePath') || 'imports/';
            return (
              <FilePickerField
                key={fieldName}
                {...commonProps}
                value={typeof fieldValue === 'string' ? fieldValue : undefined}
                onChange={(value) => handleFieldChange(fieldName, value)}
                accept={fileAccept}
                basePath={fileBasePath}
              />
            );
          }

        case 'layer-select':
          {
            const layerAccept = getUiSchemaValue<string>(resolvedFieldSchema, 'ui:accept') || 'all';
            return (
              <LayerSelectField
                key={fieldName}
                {...commonProps}
                value={typeof fieldValue === 'string' ? fieldValue : undefined}
                onChange={(value) => handleFieldChange(fieldName, value)}
                accept={layerAccept}
              />
            );
          }

        case 'hidden':
          return null; // Don't render hidden fields

        default:
          // Fallback to text field for unknown widgets
          return <TextField key={fieldName} {...commonProps} />;
      }
    }

    // Fallback based on JSON schema type
    const fieldType = Array.isArray(resolvedFieldSchema.type)
      ? resolvedFieldSchema.type[0]
      : resolvedFieldSchema.type;

    switch (fieldType) {
      case 'string':
        if (resolvedFieldSchema.enum) {
          return (
            <SelectField
              key={fieldName}
              {...commonProps}
              value={isSelectOptionValue(fieldValue) ? fieldValue : undefined}
              onChange={(value) => handleFieldChange(fieldName, value)}
              options={resolvedFieldSchema.enum.map(val => ({
                value: val,
                label: translateOptionLabel(fieldName, { value: val, label: String(val) }),
              }))}
            />
          );
        }
        return (
          <TextField
            key={fieldName}
            {...commonProps}
            value={typeof fieldValue === 'string' ? fieldValue : ''}
            onChange={(value) => handleFieldChange(fieldName, value)}
          />
        );

      case 'number':
      case 'integer':
        return (
            <NumberField
              key={fieldName}
              {...commonProps}
              value={typeof fieldValue === 'number' ? fieldValue : undefined}
              onChange={(value) => handleFieldChange(fieldName, value)}
              min={resolvedFieldSchema.minimum}
              max={resolvedFieldSchema.maximum}
            />
        );

      case 'boolean':
        return (
          <CheckboxField
            key={fieldName}
            {...commonProps}
            value={typeof fieldValue === 'boolean' ? fieldValue : false}
            onChange={(value) => handleFieldChange(fieldName, value)}
          />
        );

      case 'array':
        {
          if (resolvedFieldSchema.items?.type === 'string' && !resolvedFieldSchema.items.enum) {
            return (
              <TagsField
                key={fieldName}
                {...commonProps}
                value={isStringArray(fieldValue) ? fieldValue : []}
                onChange={(value) => handleFieldChange(fieldName, value)}
              />
            );
          }

          let itemType = 'text';
          let resolvedItemSchema = resolvedFieldSchema.items;

          if (resolvedFieldSchema.items) {
            if (resolvedFieldSchema.items.$ref) {
              itemType = 'object';
              const resolved = resolveRef(resolvedFieldSchema.items.$ref);
              if (resolved) {
                resolvedItemSchema = resolved;
              }
            } else if (resolvedFieldSchema.items.type === 'object' || resolvedFieldSchema.items.properties) {
              itemType = 'object';
            } else if (resolvedFieldSchema.items.type) {
              itemType = resolvedFieldSchema.items.type;
            }
          }

          return (
            <ArrayField
              key={fieldName}
              {...commonProps}
              value={Array.isArray(fieldValue) ? fieldValue : []}
              onChange={(value) => handleFieldChange(fieldName, value)}
              itemType={itemType}
              itemSchema={resolvedItemSchema}
              minItems={resolvedFieldSchema.minItems}
              maxItems={resolvedFieldSchema.maxItems}
            />
          );
        }

      case 'object':
        // Check if it's a Dict[str, str] (additionalProperties with string type)
        if (resolvedFieldSchema.additionalProperties?.type === 'string') {
          return (
            <KeyValuePairsField
              key={fieldName}
              {...commonProps}
              value={toStringRecord(fieldValue)}
              onChange={(value) => handleFieldChange(fieldName, value)}
            />
          );
        }
        return (
          <ObjectField
            key={fieldName}
            {...commonProps}
            value={isFormValues(fieldValue) ? fieldValue : {}}
            onChange={(value) => handleFieldChange(fieldName, value)}
            properties={resolvedFieldSchema.properties || {}}
          />
        );

      default:
        return (
          <TextField
            key={fieldName}
            {...commonProps}
            value={typeof fieldValue === 'string' ? fieldValue : ''}
            onChange={(value) => handleFieldChange(fieldName, value)}
          />
        );
    }
  }, [
    form,
    formData,
    groupBy,
    handleFieldChange,
    readOnly,
    resolveFieldDescription,
    resolveFieldLabel,
    resolveRef,
    resolveFieldSchema,
    resolvedAvailableFields,
    pluginSchemaType,
    translateOptionLabel,
  ]);

  // Render all fields from schema
  const renderFields = useMemo(() => {
    if (!schema?.schema) {
      return null;
    }

    // Store the original schema for reference resolution
    const originalSchema = schema.schema;

    // Extract the actual properties to render
    let properties = originalSchema.properties;
    let required = originalSchema.required || [];

    // Check if this is a schema with $defs
    // If the main properties only contain plugin/source/params, look for the real schema
    if (properties && originalSchema.$defs) {
      const hasWrapperProps = properties.plugin || properties.params;

      if (hasWrapperProps) {
        // This is a wrapper schema, find the actual params schema
        // Look for params field
        if (properties.params) {
          const paramsField = properties.params;

          // Check if params has allOf with $ref
          if (paramsField.allOf && paramsField.allOf[0].$ref) {
            const refName = paramsField.allOf[0].$ref.split('/').pop();
            if (originalSchema.$defs[refName]) {
              // Use the referenced schema
              properties = originalSchema.$defs[refName].properties;
              required = originalSchema.$defs[refName].required || [];
            }
          }
          // Check if params has direct $ref
          else if (paramsField.$ref) {
            const refName = paramsField.$ref.split('/').pop();
            if (originalSchema.$defs[refName]) {
              properties = originalSchema.$defs[refName].properties;
              required = originalSchema.$defs[refName].required || [];
            }
          }
        }
      }
      // If there's only one $def and main properties seem like a wrapper, use the $def
      else {
        const defKeys = Object.keys(originalSchema.$defs);
        if (defKeys.length === 1 && defKeys[0].includes('Params')) {
          // Use the params definition
          const paramsSchema = originalSchema.$defs[defKeys[0]];
          if (paramsSchema.properties) {
            properties = paramsSchema.properties;
            required = paramsSchema.required || [];
          }
        }
      }
    }

    if (!properties) {
      return null;
    }

    properties = addCompatibilityFields(pluginId, properties);

    const fields = Object.entries(properties)
      .filter(([fieldName]) => !hiddenFieldSet.has(fieldName))
      .map(([fieldName, fieldSchema]) => {
      const field = fieldSchema as FieldSchema;
      const isRequired = required.includes(fieldName);
      const renderedField = renderField(fieldName, field, isRequired);

      if (!renderedField) {
        return null;
      }

      return (
        <div key={fieldName} className="space-y-2">
          {renderedField}
        </div>
      );
      })
      .filter(Boolean);

    return <div className="space-y-4">{fields}</div>;
  }, [hiddenFieldSet, pluginId, renderField, schema]);

  // Loading state
  if (loading) {
    // Minimal skeleton when showTitle is false (embedded mode)
    if (!showTitle) {
      return (
        <div className={className}>
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-3/4" />
          </div>
        </div>
      );
    }
    // Full skeleton with card header
    return (
      <Card className={className}>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  // No params message
  if (!schema?.has_params) {
    return (
      <Alert className={className}>
        <Info className="h-4 w-4" />
          <AlertDescription>
          {schema?.message || t('widgets:form.noConfigurableParameters', 'This plugin does not have configurable parameters')}
        </AlertDescription>
      </Alert>
    );
  }

  // Main form render
  return (
    <Card className={className}>
      {showTitle && schema?.schema && (
        <CardHeader>
          <CardTitle>{schema.schema.title || pluginId}</CardTitle>
          {schema.schema.description && (
            <CardDescription>{schema.schema.description}</CardDescription>
          )}
        </CardHeader>
      )}
      <CardContent className={showTitle ? undefined : 'py-4'}>
        {renderFields}
      </CardContent>
    </Card>
  );
};

export default JsonSchemaForm;
