// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import { analyzeFilesBeforeUpload } from './filePreflight'

describe('analyzeFilesBeforeUpload', () => {
  it('recognizes taxonomy embedded in an occurrences CSV', async () => {
    const file = new File(
      [
        [
          'id,id_taxonref,plot_name,taxaname,taxonref,family,genus,species,infra,geo_pt',
          '29105,2283,Plot 001,Burretiokentia vieillardii,Burretiokentia vieillardii,Arecaceae,Burretiokentia,Burretiokentia vieillardii,,POINT (165.7683 -21.6461)',
        ].join('\n'),
      ],
      'occurrences.csv',
      { type: 'text/csv' }
    )

    const summaries = await analyzeFilesBeforeUpload([file])

    expect(summaries['occurrences.csv']).toMatchObject({
      status: 'ready',
      badges: expect.arrayContaining([
        'headers',
        'identifiers',
        'hierarchy',
        'taxonomyFromOccurrences',
      ]),
      tips: [],
    })
  })
})
