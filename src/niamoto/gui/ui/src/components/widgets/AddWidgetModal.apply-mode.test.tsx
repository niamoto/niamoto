// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import type { WidgetCandidate } from '@/features/collections/api/widget-candidates'
import { candidateMatchesSuggestion } from './addWidgetCandidateMatching'
import { shouldUseCandidateApplyPath } from './addWidgetApplyMode'
import type { TemplateSuggestion } from './types'

function makeWidgetCandidate(
  overrides: Partial<WidgetCandidate> = {},
): WidgetCandidate {
  return {
    id: 'candidate-1',
    collection: 'plots',
    title: 'Class object metrics',
    subtitle: null,
    origin: 'class_object',
    category: 'chart',
    status: 'recommended',
    applyability: 'applicable',
    default_selected: true,
    recommendation: null,
    source_fields: ['nbe_stem', 'richness'],
    source_name: 'plot_stats',
    transformer_plugin: 'class_object_field_aggregator',
    widget_plugin: 'info_grid',
    preview_descriptor: null,
    detail: {
      shape: {},
      warnings: [],
      skip_reasons: [],
      score: {},
      provenance: {},
      recipe_summary: {},
    },
    recipe_summary: {},
    fingerprint: null,
    ...overrides,
  }
}

function makeTemplateSuggestion(
  overrides: Partial<TemplateSuggestion> = {},
): TemplateSuggestion {
  return {
    template_id: 'nbe_stem_field_aggregator_radial_gauge',
    name: 'Nbe stem',
    description: 'Nbe stem (source: plot_stats)',
    plugin: 'class_object_field_aggregator',
    widget_plugin: 'radial_gauge',
    category: 'gauge',
    icon: 'gauge',
    confidence: 0.95,
    source: 'class_object',
    source_name: 'plot_stats',
    matched_column: 'nbe_stem',
    match_reason: 'Source: plot_stats',
    is_recommended: true,
    config: {},
    widget_params: {},
    alternatives: [],
    ...overrides,
  }
}

describe('shouldUseCandidateApplyPath', () => {
  it('uses the candidate apply path only when every selected suggestion is candidate-backed', () => {
    const candidateSuggestionIds = new Set(['nav', 'info'])

    expect(shouldUseCandidateApplyPath([], candidateSuggestionIds)).toBe(false)
    expect(shouldUseCandidateApplyPath(['nav'], candidateSuggestionIds)).toBe(true)
    expect(shouldUseCandidateApplyPath(['nav', 'info'], candidateSuggestionIds)).toBe(
      true,
    )
    expect(shouldUseCandidateApplyPath(['nav', 'legacy'], candidateSuggestionIds)).toBe(
      false,
    )
  })

  it('falls back to the editable suggestion flow when a candidate-backed suggestion was customized', () => {
    const candidateSuggestionIds = new Set(['nav', 'info'])
    const customizedSuggestionIds = new Set(['nav'])

    expect(
      shouldUseCandidateApplyPath(
        ['nav'],
        candidateSuggestionIds,
        customizedSuggestionIds,
      ),
    ).toBe(false)
    expect(
      shouldUseCandidateApplyPath(
        ['info'],
        candidateSuggestionIds,
        customizedSuggestionIds,
      ),
    ).toBe(true)
  })
})

describe('candidateMatchesSuggestion', () => {
  it('matches class object recipes from the same source and field when the recommended widget differs', () => {
    expect(
      candidateMatchesSuggestion(
        makeWidgetCandidate(),
        makeTemplateSuggestion(),
      ),
    ).toBe(true)
  })

  it('does not match class object recipes from another auxiliary source when the widget differs', () => {
    expect(
      candidateMatchesSuggestion(
        makeWidgetCandidate({ source_name: 'taxa_stats' }),
        makeTemplateSuggestion(),
      ),
    ).toBe(false)
  })

  it('keeps strict widget matching for non class object recipes', () => {
    expect(
      candidateMatchesSuggestion(
        makeWidgetCandidate({
          origin: 'raw_field',
          source_name: 'occurrences',
          source_fields: ['locality'],
          transformer_plugin: 'categorical_distribution',
          widget_plugin: 'bar_plot',
        }),
        makeTemplateSuggestion({
          plugin: 'categorical_distribution',
          widget_plugin: 'donut_chart',
          source: 'auto',
          source_name: 'occurrences',
          matched_column: 'locality',
        }),
      ),
    ).toBe(false)
  })

  it('does not match equal titles across different class object sources', () => {
    expect(
      candidateMatchesSuggestion(
        makeWidgetCandidate({
          title: 'Nbe stem',
          origin: 'raw_field',
          source_name: 'plots_source',
          source_fields: ['nbe_stem'],
          transformer_plugin: 'binned_distribution',
          widget_plugin: 'bar_plot',
        }),
        makeTemplateSuggestion({
          name: 'Nbe stem',
          source: 'class_object',
          source_name: 'plot_stats',
          matched_column: 'nbe_stem',
        }),
      ),
    ).toBe(false)
  })
})
