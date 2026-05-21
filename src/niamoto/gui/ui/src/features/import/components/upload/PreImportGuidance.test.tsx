// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PreImportGuidance } from './PreImportGuidance'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const downloadTemplateMock = vi.hoisted(() => vi.fn())
const downloadCsvTemplateMock = vi.hoisted(() => vi.fn())

const translations: Record<string, string> = {
  'preImport.title': 'Before you import',
  'preImport.badge': 'Quick check',
  'preImport.description': 'Prepare files before uploading.',
  'preImport.formats.csv.title': 'CSV tables',
  'preImport.formats.csv.description': 'Delimited attribute tables.',
  'preImport.formats.vector.title': 'Vector layers',
  'preImport.formats.vector.description': 'Spatial layers with geometry.',
  'preImport.formats.raster.title': 'Raster layers',
  'preImport.formats.raster.description': 'TIFF rasters.',
  'preImport.shapefileNote': 'For shapefiles, prefer GeoPackage for automatic detection.',
  'preImport.detectionTips.title': 'For more reliable automatic detection',
  'preImport.detectionTips.items.headers': 'Keep one clear header row in CSV files.',
  'preImport.detectionTips.items.identifiers': 'Use explicit identifier columns such as id, plot_id, or taxon_id.',
  'preImport.detectionTips.items.matchingValues': 'Reuse the same identifier values between related files.',
  'preImport.detectionTips.items.spatial': 'Prefer GeoPackage or GeoJSON for spatial data.',
  'preImport.hierarchy.title': 'Do your data have nested levels?',
  'preImport.hierarchy.summary': 'Use this for taxonomies or geographic levels.',
  'preImport.hierarchy.meaningTitle': 'What Niamoto can detect',
  'preImport.hierarchy.meaningDescription': 'A hierarchy moves from broad to precise levels.',
  'preImport.hierarchy.standardTaxonomyTitle': 'Standard case: taxonomy derived from occurrences',
  'preImport.hierarchy.standardTaxonomyDescription': 'You usually do not need a separate taxonomy file.',
  'preImport.hierarchy.separateColumns': 'One column per level',
  'preImport.hierarchy.separateColumnsDescription': 'Put at least two levels in the same CSV.',
  'preImport.hierarchy.clearNames': 'Clear level names',
  'preImport.hierarchy.clearNamesDescription': 'Use family, genus, species, country, region, locality, or plot.',
  'preImport.hierarchy.order': 'Broad to precise',
  'preImport.hierarchy.orderDescription': 'Keep broader levels less unique than deeper levels.',
  'preImport.hierarchy.identifier': 'Stable identifiers help links',
  'preImport.hierarchy.identifierDescription': 'Add taxon_id, plot_id, id_taxon, or id when possible.',
  'preImport.templates.title': 'Need a starting file?',
  'preImport.templates.description': 'Download a small CSV model.',
  'preImport.templates.occurrences': 'Occurrences',
  'preImport.templates.siteReference': 'Sites / plots',
  'preImport.classObject.title': 'Do you have values already calculated by class?',
  'preImport.classObject.summary': 'Use this when one entity has numeric values split into named classes.',
  'preImport.classObject.meaningTitle': 'What this CSV represents',
  'preImport.classObject.meaningDescription': 'Each row links one entity to one measured object, an optional class, and one numeric value.',
  'preImport.classObject.example': 'Example: plot_001 + forest_cover + forest + 8.4.',
  'preImport.classObject.requiredColumns': 'Required columns',
  'preImport.classObject.identifier': 'Entity identifier',
  'preImport.classObject.identifierDescription': 'Use entity_id, plot_id, shape_id, taxon_id, or id.',
  'preImport.classObject.numericValues': 'Numeric values',
  'preImport.classObject.numericValuesDescription': 'class_value must be numeric.',
  'preImport.classObject.downloadTemplate': 'Download CSV template',
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => translations[key] ?? key,
  }),
}))

vi.mock('./classObjectTemplate', () => ({
  downloadClassObjectTemplate: downloadTemplateMock,
  downloadCsvTemplate: downloadCsvTemplateMock,
}))

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  return {
    container,
    async render(element: ReactNode) {
      await act(async () => {
        root.render(element)
        await Promise.resolve()
      })
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('PreImportGuidance', () => {
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('summarizes supported file families without opening the class_object details', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    expect(harness.container.textContent).toContain('CSV tables')
    expect(harness.container.textContent).toContain('Vector layers')
    expect(harness.container.textContent).toContain('Raster layers')
    expect(harness.container.textContent).toContain('.csv')
    expect(harness.container.textContent).toContain('.gpkg')
    expect(harness.container.textContent).toContain('prefer GeoPackage for automatic detection')
    expect(harness.container.textContent).toContain('For more reliable automatic detection')
    expect(harness.container.textContent).toContain('Use explicit identifier columns')
    expect(harness.container.textContent).toContain('Need a starting file?')
    expect(harness.container.textContent).toContain('Occurrences')
    expect(harness.container.textContent).toContain('Sites / plots')
    expect(harness.container.textContent).not.toContain('Required columns')
    expect(harness.container.textContent).not.toContain('One column per level')

    await harness.unmount()
  })

  it('reveals hierarchy guidance only when users ask for nested level details', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    const trigger = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Do your data have nested levels?')
    )
    expect(trigger).toBeTruthy()

    await act(async () => {
      trigger?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('What Niamoto can detect')
    expect(harness.container.textContent).toContain('Standard case: taxonomy derived from occurrences')
    expect(harness.container.textContent).toContain('You usually do not need a separate taxonomy file')
    expect(harness.container.textContent).toContain('family')
    expect(harness.container.textContent).toContain('genus')
    expect(harness.container.textContent).toContain('species')
    expect(harness.container.textContent).toContain('One column per level')
    expect(harness.container.textContent).toContain('taxon_id, plot_id, id_taxon, or id')

    await harness.unmount()
  })

  it('downloads concrete CSV templates from the starting file section', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    const occurrencesTemplateButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Occurrences')
    )
    expect(occurrencesTemplateButton).toBeTruthy()

    await act(async () => {
      occurrencesTemplateButton?.click()
      await Promise.resolve()
    })

    expect(downloadCsvTemplateMock).toHaveBeenCalledWith('occurrences')

    await harness.unmount()
  })

  it('reveals class_object constraints and downloads the template on demand', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    const trigger = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Do you have values already calculated by class?')
    )
    expect(trigger).toBeTruthy()

    await act(async () => {
      trigger?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('What this CSV represents')
    expect(harness.container.textContent).toContain('plot_001 + forest_cover + forest + 8.4')
    expect(harness.container.textContent).toContain('Required columns')
    expect(harness.container.textContent).toContain('class_object')
    expect(harness.container.textContent).toContain('class_name')
    expect(harness.container.textContent).toContain('class_value')
    expect(harness.container.textContent).toContain('entity_id, plot_id, shape_id, taxon_id, or id')

    const downloadButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Download CSV template')
    )
    expect(downloadButton).toBeTruthy()

    await act(async () => {
      downloadButton?.click()
      await Promise.resolve()
    })

    expect(downloadTemplateMock).toHaveBeenCalledTimes(1)

    await harness.unmount()
  })
})
