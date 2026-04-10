export type SelectOptionValue = string | number | boolean;

export interface SelectOption<T extends SelectOptionValue = SelectOptionValue> {
  value: T;
  label: string;
}

export type FormPrimitive = string | number | boolean | null;

export interface FormValues {
  [key: string]: FormValue | undefined;
}

export type FormValue = FormPrimitive | FormValue[] | FormValues;

export interface AdditionalPropertiesSchema {
  type?: string;
}

export interface FieldSchema {
  $ref?: string;
  type?: string | string[];
  title?: string;
  description?: string;
  default?: FormValue;
  enum?: SelectOptionValue[];
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
  items?: FieldSchema;
  properties?: Record<string, FieldSchema>;
  additionalProperties?: AdditionalPropertiesSchema;
  json_schema_extra?: Record<string, unknown>;
  anyOf?: FieldSchema[];
  allOf?: FieldSchema[];
  required?: string[];
  ui_component?: string;
  examples?: unknown[];
  [key: string]: unknown;
}

export interface PluginSchemaDefinition {
  title?: string;
  description?: string;
  type: string;
  properties: Record<string, FieldSchema>;
  required?: string[];
  json_schema_extra?: Record<string, unknown>;
  $defs?: Record<string, FieldSchema>;
}

export interface PluginSchemaResponse {
  plugin_id: string;
  plugin_type: string;
  has_params: boolean;
  schema?: PluginSchemaDefinition;
  message?: string;
}

export function isFormValues(value: unknown): value is FormValues {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

export function isSelectOptionValue(value: unknown): value is SelectOptionValue {
  return (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  );
}
