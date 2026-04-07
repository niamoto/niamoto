// src/components/forms/JsonSchemaForm.tsx

import React, { useState, useEffect, useMemo } from 'react';
import type { UseFormReturn } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Info } from 'lucide-react';

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

interface JsonSchemaFormProps {
  pluginId: string;
  pluginType?: string;
  groupBy?: string;
  form?: UseFormReturn<any>;
  onSubmit?: (data: any) => void;
  onChange?: (data: any) => void;
  readOnly?: boolean;
  className?: string;
  showTitle?: boolean;
  availableFields?: string[]; // For field-select widgets
  initialValues?: Record<string, any>; // Initial values to populate the form
  hiddenFields?: string[];
}

interface PluginSchema {
  plugin_id: string;
  plugin_type: string;
  has_params: boolean;
  schema?: {
    title?: string;
    description?: string;
    type: string;
    properties: Record<string, any>;
    required?: string[];
    json_schema_extra?: Record<string, any>;
    $defs?: Record<string, any>;
  };
  message?: string;
}

interface FieldSchema {
  type: string | string[];
  title?: string;
  description?: string;
  default?: any;
  enum?: any[];
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
  items?: any;
  properties?: Record<string, any>;
  additionalProperties?: { type?: string };
  json_schema_extra?: Record<string, any>;
  anyOf?: any[];
  allOf?: any[];
}

function addCompatibilityFields(
  pluginId: string,
  properties: Record<string, any>,
): Record<string, any> {
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

const pluginSchemaCache = new Map<string, PluginSchema>();
const pluginSchemaRequests = new Map<string, Promise<PluginSchema>>();

async function loadPluginSchema(pluginId: string): Promise<PluginSchema> {
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

      const data: PluginSchema = await response.json();
      return data;
    })
    .finally(() => {
      pluginSchemaRequests.delete(pluginId);
    });

  pluginSchemaRequests.set(pluginId, request);
  return request;
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
  const [schema, setSchema] = useState<PluginSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const hiddenFieldSet = useMemo(() => new Set(hiddenFields), [hiddenFields]);

  // Track if we've initialized with initialValues
  const initializedRef = React.useRef(false);

  const filterHiddenValues = React.useCallback(
    (values: Record<string, any>) =>
      Object.fromEntries(
        Object.entries(values).filter(([key]) => !hiddenFieldSet.has(key))
      ),
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

        // Initialize form data with defaults
        if (data.schema?.properties) {
          const defaults: Record<string, any> = {};
          Object.entries(data.schema.properties).forEach(([key, field]) => {
            if (hiddenFieldSet.has(key)) {
              return;
            }
            const fieldSchema = field as FieldSchema;
            if (fieldSchema.default !== undefined) {
              defaults[key] = fieldSchema.default;
            }
          });
          // Merge: defaults first, then initialValues override
          setFormData({ ...defaults, ...filterHiddenValues(initialValues) });
          initializedRef.current = true;
        } else if (Object.keys(initialValues).length > 0) {
          setFormData(filterHiddenValues(initialValues));
          initializedRef.current = true;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plugin schema');
      } finally {
        setLoading(false);
      }
    };

    if (pluginId) {
      fetchSchema();
    }
  }, [pluginId]);

  // Update form data when initialValues change (after initial load)
  useEffect(() => {
    const visibleInitialValues = filterHiddenValues(initialValues);
    if (schema && !loading && Object.keys(visibleInitialValues).length > 0) {
      // Only update if values are different to avoid loops
      const hasNewValues = Object.keys(visibleInitialValues).some(
        key => visibleInitialValues[key] !== formData[key]
      );
      if (hasNewValues && !initializedRef.current) {
        setFormData(prev => ({ ...prev, ...visibleInitialValues }));
        initializedRef.current = true;
      }
    }
  }, [filterHiddenValues, formData, initialValues, loading, schema]);

  // Handle field changes
  const handleFieldChange = (fieldName: string, value: any) => {
    const newData = { ...formData, [fieldName]: value };
    setFormData(newData);

    if (onChange) {
      onChange(newData);
    }

    if (form) {
      form.setValue(fieldName, value);
    }
  };

  // Helper function to resolve $ref in schema
  const resolveRef = (ref: string): any => {
    if (!schema?.schema?.$defs) return null;
    const refName = ref.split('/').pop();
    return refName ? schema.schema.$defs[refName] : null;
  };

  const resolveFieldSchema = (fieldSchema: FieldSchema): FieldSchema => {
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
  };

  // Render a single field based on its schema
  const renderField = (fieldName: string, fieldSchema: FieldSchema, required: boolean = false) => {
    const resolvedFieldSchema = resolveFieldSchema(fieldSchema);

    // Get UI widget type from json_schema_extra or directly from fieldSchema
    // Pydantic places ui:widget directly in the schema, not nested in json_schema_extra
    const uiWidget =
      resolvedFieldSchema.json_schema_extra?.['ui:widget'] ||
      (resolvedFieldSchema as any)['ui:widget'];
    const fieldValue = form ? form.watch(fieldName) : formData[fieldName];

    // Common props for all fields
    const commonProps = {
      name: fieldName,
      label: resolvedFieldSchema.title || fieldName,
      description: resolvedFieldSchema.description,
      value: fieldValue,
      onChange: (value: any) => handleFieldChange(fieldName, value),
      required,
      disabled: readOnly,
      error: (form?.formState.errors[fieldName]?.message || undefined) as string | undefined
    };

    // Determine field type and render appropriate widget
    if (uiWidget) {
      switch (uiWidget) {
        case 'text':
          return <TextField key={fieldName} {...commonProps} />;

        case 'textarea':
          return <TextAreaField key={fieldName} {...commonProps} />;

        case 'number':
          return (
            <NumberField
              key={fieldName}
              {...commonProps}
              min={resolvedFieldSchema.minimum}
              max={resolvedFieldSchema.maximum}
            />
          );

        case 'select':
          // Options can be in json_schema_extra['ui:options'] or directly in fieldSchema['ui:options']
          const options = resolvedFieldSchema.json_schema_extra?.['ui:options'] ||
                         (resolvedFieldSchema as any)['ui:options'] ||
                         resolvedFieldSchema.enum?.map(val => ({ value: val, label: val })) || [];
          return (
            <SelectField
              key={fieldName}
              {...commonProps}
              options={options}
            />
          );

        case 'checkbox':
          return <CheckboxField key={fieldName} {...commonProps} />;

        case 'field-select':
          return (
            <FieldSelectField
              key={fieldName}
              {...commonProps}
              availableFields={availableFields}
            />
          );

        case 'entity-select':
          const entityKind = resolvedFieldSchema.json_schema_extra?.['ui:entity-filter']?.kind;
          return (
            <EntitySelectField
              key={fieldName}
              {...commonProps}
              kind={entityKind}
              groupBy={groupBy}
            />
          );

        case 'class-object-select':
          const coSource = resolvedFieldSchema.json_schema_extra?.['ui:source'] || (resolvedFieldSchema as any)['ui:source'];
          const coMultiple = resolvedFieldSchema.json_schema_extra?.['ui:multiple'] || (resolvedFieldSchema as any)['ui:multiple'];
          return (
            <ClassObjectSelectField
              key={fieldName}
              {...commonProps}
              groupBy={groupBy}
              source={coSource}
              multiple={coMultiple}
            />
          );

        case 'transform-source-select':
          const sourceGroupBy = resolvedFieldSchema.json_schema_extra?.['ui:groupBy'];
          return (
            <TransformSourceSelectField
              key={fieldName}
              {...commonProps}
              groupBy={sourceGroupBy || groupBy}
            />
          );

        case 'field-list':
        case 'field-list-editor':
          return (
            <FieldListEditor
              key={fieldName}
              {...commonProps}
              groupBy={groupBy}
              minItems={resolvedFieldSchema.minItems}
              maxItems={resolvedFieldSchema.maxItems}
            />
          );

        case 'array':
          const itemWidget = resolvedFieldSchema.json_schema_extra?.['ui:item-widget'];

          // Determine the item type based on the items schema
          let itemType = itemWidget || 'text';
          let resolvedItemSchema = resolvedFieldSchema.items;


          if (!itemWidget && resolvedFieldSchema.items) {
            // Check if items reference a $def (object type)
            if (resolvedFieldSchema.items.$ref) {
              itemType = 'object';
              // Resolve the reference
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
              itemType={itemType}
              itemSchema={resolvedItemSchema}
              minItems={resolvedFieldSchema.minItems}
              maxItems={resolvedFieldSchema.maxItems}
              availableFields={itemWidget === 'field-select' ? availableFields : undefined}
            />
          );

        case 'json':
          return <JsonField key={fieldName} {...commonProps} />;

        case 'key-value-pairs':
          return <KeyValuePairsField key={fieldName} {...commonProps} />;

        case 'tags':
          return <TagsField key={fieldName} {...commonProps} />;

        case 'object':
          return (
            <ObjectField
              key={fieldName}
              {...commonProps}
              properties={resolvedFieldSchema.properties || {}}
            />
          );

        case 'color':
          return <ColorField key={fieldName} {...commonProps} />;

        case 'directory-select':
          return <DirectorySelectField key={fieldName} {...commonProps} />;

        case 'file-select':
        case 'file-picker':
          const fileAccept = resolvedFieldSchema.json_schema_extra?.['ui:accept'] || (resolvedFieldSchema as any)['ui:accept'] || 'all';
          const fileBasePath = resolvedFieldSchema.json_schema_extra?.['ui:basePath'] || (resolvedFieldSchema as any)['ui:basePath'] || 'imports/';
          return (
            <FilePickerField
              key={fieldName}
              {...commonProps}
              accept={fileAccept}
              basePath={fileBasePath}
            />
          );

        case 'layer-select':
          const layerAccept = resolvedFieldSchema.json_schema_extra?.['ui:accept'] || (resolvedFieldSchema as any)['ui:accept'] || 'all';
          return (
            <LayerSelectField
              key={fieldName}
              {...commonProps}
              accept={layerAccept}
            />
          );

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
              options={resolvedFieldSchema.enum.map(val => ({ value: val, label: val }))}
            />
          );
        }
        return <TextField key={fieldName} {...commonProps} />;

      case 'number':
      case 'integer':
        return (
            <NumberField
              key={fieldName}
              {...commonProps}
              min={resolvedFieldSchema.minimum}
              max={resolvedFieldSchema.maximum}
            />
        );

      case 'boolean':
        return <CheckboxField key={fieldName} {...commonProps} />;

      case 'array':
        // Check if it's a simple string array (tags)
        if (resolvedFieldSchema.items?.type === 'string' && !resolvedFieldSchema.items.enum) {
          return <TagsField key={fieldName} {...commonProps} />;
        }

        // Determine the item type based on the items schema
        let itemType = 'text';
        let resolvedItemSchema = resolvedFieldSchema.items;


        if (resolvedFieldSchema.items) {
          // Check if items reference a $def (object type)
          if (resolvedFieldSchema.items.$ref) {
            itemType = 'object';
            // Resolve the reference
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
            itemType={itemType}
            itemSchema={resolvedItemSchema}
            minItems={resolvedFieldSchema.minItems}
            maxItems={resolvedFieldSchema.maxItems}
          />
        );

      case 'object':
        // Check if it's a Dict[str, str] (additionalProperties with string type)
        if (resolvedFieldSchema.additionalProperties?.type === 'string') {
          return <KeyValuePairsField key={fieldName} {...commonProps} />;
        }
        return (
          <ObjectField
            key={fieldName}
            {...commonProps}
            properties={resolvedFieldSchema.properties || {}}
          />
        );

      default:
        return <TextField key={fieldName} {...commonProps} />;
    }
  };

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

      return (
        <div key={fieldName} className="space-y-2">
          {renderField(fieldName, field, isRequired)}
        </div>
      );
      });

    return <div className="space-y-4">{fields}</div>;
  }, [schema, formData, form, readOnly, availableFields, hiddenFieldSet]);

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
          {schema?.message || 'This plugin does not have configurable parameters'}
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
