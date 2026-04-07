import { describe, expect, it } from 'vitest'
import {
  evaluateUiCondition,
  flattenColumnTree,
  mergeOptionValue,
} from '../formSchemaUtils'

describe('formSchemaUtils', () => {
  it('flattens nested source columns into field paths', () => {
    const fields = flattenColumnTree([
      {
        name: 'id_taxonref',
        path: 'id_taxonref',
        type: 'number',
        children: [],
      },
      {
        name: 'extra_data',
        path: 'extra_data',
        type: 'object',
        children: [
          {
            name: 'rank_name',
            path: 'extra_data.rank_name',
            type: 'string',
            children: [],
          },
        ],
      },
    ])

    expect(fields).toEqual(['id_taxonref', 'extra_data', 'extra_data.rank_name'])
  })

  it('evaluates JS-like ui:condition expressions', () => {
    expect(
      evaluateUiCondition("mode !== 'direct'", { mode: 'hierarchical' })
    ).toBe(true)
    expect(
      evaluateUiCondition("!fields || Object.keys(fields).length === 0", {
        fields: { flowers: 'has_flowers' },
      })
    ).toBe(false)
  })

  it('supports custom "in [...]" ui:condition syntax', () => {
    expect(
      evaluateUiCondition("operation in ['normalize_array', 'conformity_index']", {
        operation: 'normalize_array',
      })
    ).toBe(true)
    expect(
      evaluateUiCondition("operation in ['normalize_array', 'conformity_index']", {
        operation: 'weighted_sum',
      })
    ).toBe(false)
  })

  it('keeps the persisted select value visible when missing from options', () => {
    expect(mergeOptionValue(['height', 'dbh'], 'id_taxonref')).toEqual([
      'id_taxonref',
      'height',
      'dbh',
    ])
    expect(mergeOptionValue(['height', 'dbh'], 'dbh')).toEqual(['height', 'dbh'])
  })
})
