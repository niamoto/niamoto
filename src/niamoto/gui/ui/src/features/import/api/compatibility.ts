/**
 * API client for pre-import impact check
 */

import { apiClient } from '@/shared/lib/api/client'

export interface ImpactItem {
  column: string
  level: 'blocks_import' | 'breaks_transform' | 'warning' | 'opportunity'
  detail: string
  referenced_in: string[]
  old_type?: string
  new_type?: string
}

export interface ColumnMatch {
  name: string
  old_type: string
  new_type: string
}

export interface ImpactCheckResult {
  entity_name: string | null
  matched_columns: ColumnMatch[]
  impacts: ImpactItem[]
  error?: string
  skipped_reason?: string
  info_message?: string
  has_blockers: boolean
  has_warnings: boolean
  has_opportunities: boolean
}

/**
 * Run a pre-import impact check for a single file.
 * The backend resolves the entity from the filename and runs the check.
 */
export async function impactCheck(filePath: string): Promise<ImpactCheckResult> {
  const { data } = await apiClient.post<ImpactCheckResult>('/imports/impact-check', {
    file_path: filePath,
  })
  return data
}
