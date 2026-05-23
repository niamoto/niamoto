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

export type WidgetImpactStatus =
  | 'still_valid'
  | 'degraded'
  | 'broken'
  | 'newly_available'
  | 'unknown'

export interface WidgetImpact {
  widget_id: string
  collection: string
  status: WidgetImpactStatus
  detail: string
  affected_columns: string[]
  transformer_plugin?: string | null
  widget_plugin?: string | null
}

export type WidgetImpactSummary = Record<WidgetImpactStatus, number>

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
  widget_impacts: WidgetImpact[]
  widget_impact_summary: Partial<WidgetImpactSummary>
  widget_repair_context: Record<string, unknown>
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
