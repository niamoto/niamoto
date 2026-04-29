import { describe, expect, it } from 'vitest'

import type {
  ApiExportAutoConfigProposal,
  ApiExportGroupConfig,
} from '@/features/collections/hooks/useApiExportConfigs'

import {
  applyApiExportAutoConfigProposal,
  isJsonArray,
  isJsonObject,
  normalizeApiExportGroupConfig,
  parseJsonConfigDraft,
} from './apiExportConfigUtils'

function buildProposal(
  proposal: ApiExportGroupConfig,
  sections: ApiExportAutoConfigProposal['sections']
): ApiExportAutoConfigProposal {
  return {
    export_name: 'json_api',
    group_by: 'taxons',
    total_entities: 12,
    proposal,
    sections,
  }
}

describe('apiExportConfigUtils', () => {
  it('normalizes sparse group configs without dropping unknown values', () => {
    const normalized = normalizeApiExportGroupConfig({
      enabled: true,
      group_by: 'taxons',
      data_source: 'taxons_data',
    })

    expect(normalized).toEqual({
      enabled: true,
      group_by: 'taxons',
      data_source: 'taxons_data',
      detail: { pass_through: true },
      index: { fields: [] },
    })
  })

  it('applies only selected proposal sections to the local draft', () => {
    const current: ApiExportGroupConfig = {
      enabled: true,
      group_by: 'taxons',
      detail: {
        pass_through: false,
        fields: [{ custom_name: 'general_info.name.value' }],
      },
      index: { fields: [{ custom_id: 'id' }] },
      json_options: { indent: 2 },
    }
    const proposal = buildProposal(
      {
        enabled: true,
        group_by: 'taxons',
        detail: {
          pass_through: true,
          fields: [{ name: 'general_info.name.value' }],
        },
        index: { fields: [{ name: 'general_info.name.value' }] },
      },
      {
        index: {
          confidence: 'high',
          config: { fields: [{ name: 'general_info.name.value' }] },
          notes: [],
          unresolved: [],
        },
      }
    )

    expect(applyApiExportAutoConfigProposal(current, proposal, ['index'])).toEqual({
      ...current,
      index: { fields: [{ name: 'general_info.name.value' }] },
    })
  })

  it('turns off pass-through when applying proposed detail fields', () => {
    const current: ApiExportGroupConfig = {
      enabled: true,
      group_by: 'taxons',
      detail: { pass_through: true },
      index: { fields: [] },
    }
    const proposal = buildProposal(
      {
        enabled: true,
        group_by: 'taxons',
        detail: {
          pass_through: true,
          fields: [{ name: 'general_info.name.value' }],
        },
        index: { fields: [] },
      },
      {
        detail: {
          confidence: 'medium',
          config: {
            pass_through: true,
            fields: [{ name: 'general_info.name.value' }],
          },
          notes: [],
          unresolved: [],
        },
      }
    )

    const next = applyApiExportAutoConfigProposal(current, proposal, ['detail'])

    expect(next.detail?.pass_through).toBe(false)
    expect(next.detail?.fields).toEqual([{ name: 'general_info.name.value' }])
  })

  it('merges Darwin Core transformer params without dropping existing params', () => {
    const current: ApiExportGroupConfig = {
      enabled: true,
      group_by: 'taxons',
      transformer_plugin: 'niamoto_to_dwc_occurrence',
      transformer_params: {
        occurrence_table: 'custom_occurrences',
        mapping: { scientificName: '@taxon.name' },
      },
    }
    const proposal = buildProposal(
      {
        enabled: true,
        group_by: 'taxons',
        transformer_plugin: 'niamoto_to_dwc_occurrence',
        transformer_params: {
          mapping: { occurrenceID: { generator: 'unique_occurrence_id' } },
        },
      },
      {
        dwc_mapping: {
          confidence: 'medium',
          config: { occurrenceID: { generator: 'unique_occurrence_id' } },
          notes: [],
          unresolved: [],
        },
      }
    )

    const next = applyApiExportAutoConfigProposal(current, proposal, ['dwc_mapping'])

    expect(next.transformer_params).toEqual({
      occurrence_table: 'custom_occurrences',
      mapping: { occurrenceID: { generator: 'unique_occurrence_id' } },
    })
  })

  it('keeps the previous JSON value when draft JSON is invalid', () => {
    const lastValid = { fields: [{ name: 'general_info.name.value' }] }
    const result = parseJsonConfigDraft('{', lastValid, isJsonObject)

    expect(result.ok).toBe(false)
    expect(result.value).toBe(lastValid)
    expect(result.error).toContain('Expected')
  })

  it('returns a validation error when JSON shape does not match the section', () => {
    const lastValid = [{ name: 'general_info.name.value' }]
    const result = parseJsonConfigDraft('{"name":"taxon"}', lastValid, isJsonArray)

    expect(result).toEqual({
      ok: false,
      value: lastValid,
      error: 'JSON shape does not match this section.',
    })
  })
})
