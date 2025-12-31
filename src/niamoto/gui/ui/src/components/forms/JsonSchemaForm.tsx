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
  json_schema_extra?: Record<string, any>;
  anyOf?: any[];
  allOf?: any[];
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
  initialValues = {}
}) => {
  const [schema, setSchema] = useState<PluginSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});

  // Track if we've initialized with initialValues
  const initializedRef = React.useRef(false);

  // Fetch schema from API (only when pluginId changes)
  useEffect(() => {
    const fetchSchema = async () => {
      try {
        setLoading(true);
        setError(null);
        initializedRef.current = false;

        const response = await fetch(`/api/plugins/${pluginId}/schema`);
        if (!response.ok) {
          throw new Error(`Failed to fetch schema: ${response.statusText}`);
        }

        const data: PluginSchema = await response.json();
        setSchema(data);

        // Initialize form data with defaults
        if (data.schema?.properties) {
          const defaults: Record<string, any> = {};
          Object.entries(data.schema.properties).forEach(([key, field]) => {
            const fieldSchema = field as FieldSchema;
            if (fieldSchema.default !== undefined) {
              defaults[key] = fieldSchema.default;
            }
          });
          // Merge: defaults first, then initialValues override
          setFormData({ ...defaults, ...initialValues });
          initializedRef.current = true;
        } else if (Object.keys(initialValues).length > 0) {
          setFormData(initialValues);
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
    if (schema && !loading && Object.keys(initialValues).length > 0) {
      // Only update if values are different to avoid loops
      const hasNewValues = Object.keys(initialValues).some(
        key => initialValues[key] !== formData[key]
      );
      if (hasNewValues && !initializedRef.current) {
        setFormData(prev => ({ ...prev, ...initialValues }));
        initializedRef.current = true;
      }
    }
  }, [initialValues, schema, loading]);

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

  // Render a single field based on its schema
  const renderField = (fieldName: string, fieldSchema: FieldSchema, required: boolean = false) => {

    // Get UI widget type from json_schema_extra
    const uiWidget = fieldSchema.json_schema_extra?.['ui:widget'];
    const fieldValue = form ? form.watch(fieldName) : formData[fieldName];

    // Common props for all fields
    const commonProps = {
      name: fieldName,
      label: fieldSchema.title || fieldName,
      description: fieldSchema.description,
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
              min={fieldSchema.minimum}
              max={fieldSchema.maximum}
            />
          );

        case 'select':
          const options = fieldSchema.json_schema_extra?.['ui:options'] ||
                         fieldSchema.enum?.map(val => ({ value: val, label: val })) || [];
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
          const entityKind = fieldSchema.json_schema_extra?.['ui:entity-filter']?.kind;
          return (
            <EntitySelectField
              key={fieldName}
              {...commonProps}
              kind={entityKind}
              groupBy={groupBy}
            />
          );

        case 'transform-source-select':
          const sourceGroupBy = fieldSchema.json_schema_extra?.['ui:groupBy'];
          return (
            <TransformSourceSelectField
              key={fieldName}
              {...commonProps}
              groupBy={sourceGroupBy || groupBy}
            />
          );

        case 'array':
          const itemWidget = fieldSchema.json_schema_extra?.['ui:item-widget'];

          // Determine the item type based on the items schema
          let itemType = itemWidget || 'text';
          let resolvedItemSchema = fieldSchema.items;


          if (!itemWidget && fieldSchema.items) {
            // Check if items reference a $def (object type)
            if (fieldSchema.items.$ref) {
              itemType = 'object';
              // Resolve the reference
              const resolved = resolveRef(fieldSchema.items.$ref);
              if (resolved) {
                resolvedItemSchema = resolved;
              }
            } else if (fieldSchema.items.type === 'object' || fieldSchema.items.properties) {
              itemType = 'object';
            } else if (fieldSchema.items.type) {
              itemType = fieldSchema.items.type;
            }
          }


          return (
            <ArrayField
              key={fieldName}
              {...commonProps}
              itemType={itemType}
              itemSchema={resolvedItemSchema}
              minItems={fieldSchema.minItems}
              maxItems={fieldSchema.maxItems}
              availableFields={itemWidget === 'field-select' ? availableFields : undefined}
            />
          );

        case 'json':
          return <JsonField key={fieldName} {...commonProps} />;

        case 'object':
          return (
            <ObjectField
              key={fieldName}
              {...commonProps}
              properties={fieldSchema.properties || {}}
            />
          );

        case 'color':
          return <ColorField key={fieldName} {...commonProps} />;

        case 'directory-select':
        case 'file-select':
          return <DirectorySelectField key={fieldName} {...commonProps} />;

        case 'hidden':
          return null; // Don't render hidden fields

        default:
          // Fallback to text field for unknown widgets
          return <TextField key={fieldName} {...commonProps} />;
      }
    }

    // Fallback based on JSON schema type
    const fieldType = Array.isArray(fieldSchema.type) ? fieldSchema.type[0] : fieldSchema.type;

    switch (fieldType) {
      case 'string':
        if (fieldSchema.enum) {
          return (
            <SelectField
              key={fieldName}
              {...commonProps}
              options={fieldSchema.enum.map(val => ({ value: val, label: val }))}
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
            min={fieldSchema.minimum}
            max={fieldSchema.maximum}
          />
        );

      case 'boolean':
        return <CheckboxField key={fieldName} {...commonProps} />;

      case 'array':
        // Determine the item type based on the items schema
        let itemType = 'text';
        let resolvedItemSchema = fieldSchema.items;


        if (fieldSchema.items) {
          // Check if items reference a $def (object type)
          if (fieldSchema.items.$ref) {
            itemType = 'object';
            // Resolve the reference
            const resolved = resolveRef(fieldSchema.items.$ref);
            if (resolved) {
              resolvedItemSchema = resolved;
            }
          } else if (fieldSchema.items.type === 'object' || fieldSchema.items.properties) {
            itemType = 'object';
          } else if (fieldSchema.items.type) {
            itemType = fieldSchema.items.type;
          }
        }


        return (
          <ArrayField
            key={fieldName}
            {...commonProps}
            itemType={itemType}
            itemSchema={resolvedItemSchema}
            minItems={fieldSchema.minItems}
            maxItems={fieldSchema.maxItems}
          />
        );

      case 'object':
        return (
          <ObjectField
            key={fieldName}
            {...commonProps}
            properties={fieldSchema.properties || {}}
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

    const fields = Object.entries(properties).map(([fieldName, fieldSchema]) => {
      const field = fieldSchema as FieldSchema;
      const isRequired = required.includes(fieldName);

      return (
        <div key={fieldName} className="space-y-2">
          {renderField(fieldName, field, isRequired)}
        </div>
      );
    });

    return <div className="space-y-4">{fields}</div>;
  }, [schema, formData, form, readOnly, availableFields]);

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
      <CardContent>
        {renderFields}
      </CardContent>
    </Card>
  );
};

export default JsonSchemaForm;
