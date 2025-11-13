/**
 * Import Configuration API Client
 *
 * Client-side API functions for EntityRegistry v2 import configuration.
 * Handles validation, saving, and schema retrieval for import.yml files.
 */

/**
 * Validation error/warning structure
 */
export interface ValidationIssue {
  field: string
  message: string
  severity: 'error' | 'warning'
}

/**
 * Validation response from backend
 */
export interface ValidationResponse {
  valid: boolean
  errors: Record<string, string[]>
  warnings: Record<string, string[]>
}

/**
 * Save configuration response
 */
export interface SaveConfigResponse {
  success: boolean
  message: string
  path: string
  backup_path?: string
}

/**
 * Validate import configuration without saving
 *
 * Sends YAML config to backend for validation against EntityRegistry v2 spec.
 * Returns validation results with errors and warnings per entity.
 *
 * @param yamlConfig - YAML string to validate
 * @returns Validation result
 * @throws Error if request fails
 */
export async function validateImportConfig(yamlConfig: string): Promise<ValidationResponse> {
  const response = await fetch('/api/config/import/v2/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ config: yamlConfig })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Validation request failed')
  }

  return response.json()
}

/**
 * Save import configuration to import.yml
 *
 * Validates and saves the configuration. Creates a backup of existing file.
 *
 * @param yamlConfig - YAML string to save
 * @returns Save result with paths
 * @throws Error if save fails
 */
export async function saveImportConfig(yamlConfig: string): Promise<SaveConfigResponse> {
  const response = await fetch('/api/config/import/v2', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ config: yamlConfig })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Save request failed')
  }

  return response.json()
}

/**
 * Get JSON Schema for EntityRegistry v2 import configuration
 *
 * Retrieves the JSON Schema that defines the structure of import.yml.
 * Useful for validation, autocompletion, and documentation.
 *
 * @returns JSON Schema object
 * @throws Error if request fails
 */
export async function getImportConfigSchema(): Promise<any> {
  const response = await fetch('/api/config/import/v2/schema', {
    method: 'GET',
    headers: {
      'Accept': 'application/json'
    }
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Schema request failed')
  }

  return response.json()
}

/**
 * Get current import configuration
 *
 * Retrieves the existing import.yml file content.
 * Falls back to default structure if file doesn't exist.
 *
 * @returns Import configuration object
 * @throws Error if request fails
 */
export async function getImportConfig(): Promise<any> {
  const response = await fetch('/api/config/import', {
    method: 'GET',
    headers: {
      'Accept': 'application/json'
    }
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to retrieve import configuration')
  }

  return response.json()
}

/**
 * Convert validation response to structured issues
 *
 * Transforms backend validation response into a flat list of issues
 * with entity context.
 *
 * @param validation - Validation response from backend
 * @returns Array of validation issues
 */
export function flattenValidationIssues(validation: ValidationResponse): Array<{
  entityId: string
  issues: ValidationIssue[]
}> {
  const result: Array<{ entityId: string; issues: ValidationIssue[] }> = []

  // Process errors
  Object.entries(validation.errors).forEach(([entityId, messages]) => {
    const issues: ValidationIssue[] = messages.map((message) => ({
      field: entityId,
      message,
      severity: 'error' as const
    }))
    result.push({ entityId, issues })
  })

  // Process warnings
  Object.entries(validation.warnings).forEach(([entityId, messages]) => {
    const existingEntry = result.find((r) => r.entityId === entityId)
    const issues: ValidationIssue[] = messages.map((message) => ({
      field: entityId,
      message,
      severity: 'warning' as const
    }))

    if (existingEntry) {
      existingEntry.issues.push(...issues)
    } else {
      result.push({ entityId, issues })
    }
  })

  return result
}

/**
 * Get validation summary text
 *
 * Generates a human-readable summary of validation results.
 *
 * @param validation - Validation response
 * @returns Summary string (e.g., "2 errors, 1 warning" or "Configuration is valid")
 */
export function getValidationSummary(validation: ValidationResponse): string {
  const errorCount = Object.values(validation.errors).reduce(
    (sum, errs) => sum + errs.length,
    0
  )
  const warningCount = Object.values(validation.warnings).reduce(
    (sum, warns) => sum + warns.length,
    0
  )

  if (errorCount === 0 && warningCount === 0) {
    return 'Configuration is valid'
  }

  const parts: string[] = []
  if (errorCount > 0) {
    parts.push(`${errorCount} error${errorCount > 1 ? 's' : ''}`)
  }
  if (warningCount > 0) {
    parts.push(`${warningCount} warning${warningCount > 1 ? 's' : ''}`)
  }

  return parts.join(', ')
}

/**
 * Check if validation passed
 *
 * @param validation - Validation response
 * @returns True if configuration is valid (no errors)
 */
export function isValidationPassed(validation: ValidationResponse): boolean {
  return validation.valid && Object.keys(validation.errors).length === 0
}

/**
 * Get errors for specific entity
 *
 * @param validation - Validation response
 * @param entityId - Entity identifier (e.g., "dataset.occurrences" or "reference.taxonomy")
 * @returns Array of error messages for the entity
 */
export function getEntityErrors(validation: ValidationResponse, entityId: string): string[] {
  return validation.errors[entityId] || []
}

/**
 * Get warnings for specific entity
 *
 * @param validation - Validation response
 * @param entityId - Entity identifier
 * @returns Array of warning messages for the entity
 */
export function getEntityWarnings(validation: ValidationResponse, entityId: string): string[] {
  return validation.warnings[entityId] || []
}

/**
 * Check if entity has issues
 *
 * @param validation - Validation response
 * @param entityId - Entity identifier
 * @returns True if entity has errors or warnings
 */
export function hasEntityIssues(validation: ValidationResponse, entityId: string): boolean {
  const hasErrors = (validation.errors[entityId] || []).length > 0
  const hasWarnings = (validation.warnings[entityId] || []).length > 0
  return hasErrors || hasWarnings
}
