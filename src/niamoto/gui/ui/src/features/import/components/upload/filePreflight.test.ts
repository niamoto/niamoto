// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import { analyzeFilesBeforeUpload, getFilePreflightKey } from './filePreflight'

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

    expect(summaries[getFilePreflightKey(file)]).toMatchObject({
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

  it('keeps distinct summaries for different files sharing the same name', async () => {
    const validFile = new File(['id,family,genus\n1,A,B'], 'occurrences.csv', { type: 'text/csv' })
    const incompleteFile = new File(['value\n42'], 'occurrences.csv', { type: 'text/csv' })

    const summaries = await analyzeFilesBeforeUpload([validFile, incompleteFile])

    expect(getFilePreflightKey(validFile)).not.toBe(getFilePreflightKey(incompleteFile))
    expect(summaries[getFilePreflightKey(validFile)]).toMatchObject({
      status: 'ready',
    })
    expect(summaries[getFilePreflightKey(incompleteFile)]).toMatchObject({
      status: 'review',
      tips: expect.arrayContaining(['missingIdentifiers']),
    })
  })
})
