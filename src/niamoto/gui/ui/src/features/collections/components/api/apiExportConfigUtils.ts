import type {
  ApiExportAutoConfigProposal,
  ApiExportGroupConfig,
} from '@/features/collections/hooks/useApiExportConfigs'

const SECTION_INDEX = 'index'
const SECTION_DETAIL = 'detail'
const SECTION_JSON_OPTIONS = 'json_options'
const SECTION_DWC_MAPPING = 'dwc_mapping'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasOwn(value: Record<string, unknown>, key: string) {
  return Object.prototype.hasOwnProperty.call(value, key)
}

export function normalizeApiExportGroupConfig(
  config: ApiExportGroupConfig
): ApiExportGroupConfig {
  return {
    ...config,
    enabled: config.enabled ?? true,
    detail: {
      pass_through: config.detail?.pass_through ?? true,
      ...(config.detail?.fields ? { fields: config.detail.fields } : {}),
    },
    index: {
      fields: config.index?.fields ?? [],
    },
  }
}

export function applyApiExportAutoConfigProposal(
  current: ApiExportGroupConfig,
  proposal: ApiExportAutoConfigProposal,
  sectionKeys = Object.keys(proposal.sections)
): ApiExportGroupConfig {
  const selected = new Set(sectionKeys)
  const currentConfig = normalizeApiExportGroupConfig(current)
  const proposalConfig = normalizeApiExportGroupConfig(proposal.proposal)
  const next: ApiExportGroupConfig = { ...currentConfig, enabled: true }

  if (selected.has(SECTION_INDEX)) {
    next.index = proposalConfig.index
  }

  if (selected.has(SECTION_DETAIL)) {
    next.detail = {
      ...proposalConfig.detail,
      pass_through:
        proposalConfig.detail?.fields && proposalConfig.detail.fields.length > 0
          ? false
          : proposalConfig.detail?.pass_through,
    }
  }

  if (
    selected.has(SECTION_JSON_OPTIONS) &&
    hasOwn(proposal.proposal as unknown as Record<string, unknown>, 'json_options')
  ) {
    next.json_options = proposalConfig.json_options
  }

  if (selected.has(SECTION_DWC_MAPPING)) {
    if (proposalConfig.transformer_plugin) {
      next.transformer_plugin = proposalConfig.transformer_plugin
    }

    const proposalMapping = proposalConfig.transformer_params?.mapping
    next.transformer_params = {
      ...(currentConfig.transformer_params ?? {}),
      ...(proposalMapping !== undefined ? { mapping: proposalMapping } : {}),
    }
  }

  return next
}

export type JsonConfigDraftResult<T> =
  | { ok: true; value: T; error: null }
  | { ok: false; value: T; error: string }

export function parseJsonConfigDraft<T>(
  text: string,
  lastValidValue: T,
  validate?: (value: unknown) => value is T
): JsonConfigDraftResult<T> {
  try {
    const parsed = text.trim() ? JSON.parse(text) : undefined
    if (validate && !validate(parsed)) {
      return {
        ok: false,
        value: lastValidValue,
        error: 'JSON shape does not match this section.',
      }
    }

    return {
      ok: true,
      value: parsed as T,
      error: null,
    }
  } catch (error) {
    return {
      ok: false,
      value: lastValidValue,
      error: error instanceof Error ? error.message : 'Invalid JSON',
    }
  }
}

export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return isRecord(value)
}

export function isJsonArray(value: unknown): value is unknown[] {
  return Array.isArray(value)
}
