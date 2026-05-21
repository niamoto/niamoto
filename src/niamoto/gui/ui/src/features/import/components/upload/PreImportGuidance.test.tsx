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
  'preImport.acceptedFormatsTitle': 'Accepted formats',
  'preImport.shapefileNote': 'For shapefiles, prefer GeoPackage for automatic detection.',
  'preImport.assistant.nav.overview.title': 'Before you import',
  'preImport.assistant.nav.overview.description': 'The minimum to start',
  'preImport.assistant.nav.files.title': 'Files and models',
  'preImport.assistant.nav.files.description': 'Occurrences and sites',
  'preImport.assistant.nav.checks.title': 'Key checks',
  'preImport.assistant.nav.checks.description': 'What Niamoto looks at',
  'preImport.assistant.nav.advanced.title': 'Advanced details',
  'preImport.assistant.nav.advanced.description': 'Hierarchies and class_object',
  'preImport.assistant.overview.title': 'One occurrences CSV is enough to start.',
  'preImport.assistant.overview.description': 'Import your records first.',
  'preImport.assistant.overview.steps.read.title': '1. Read your columns',
  'preImport.assistant.overview.steps.read.description': 'Niamoto inspects headers.',
  'preImport.assistant.overview.steps.derive.title': '2. Derive taxonomy',
  'preImport.assistant.overview.steps.derive.description': 'Taxonomy can be extracted.',
  'preImport.assistant.overview.steps.review.title': '3. Review before import',
  'preImport.assistant.overview.steps.review.description': 'You keep control.',
  'preImport.assistant.files.title': 'Choose the model that matches your data',
  'preImport.assistant.files.description': 'Templates are starting points.',
  'preImport.assistant.files.occurrences.title': 'Occurrences',
  'preImport.assistant.files.occurrences.description': 'The main file.',
  'preImport.assistant.files.occurrences.download': 'Occurrences template',
  'preImport.assistant.files.sites.title': 'Sites / plots',
  'preImport.assistant.files.sites.description': 'A complementary file.',
  'preImport.assistant.files.sites.download': 'Sites / plots template',
  'preImport.assistant.checks.title': 'A few checks prevent errors',
  'preImport.assistant.checks.description': 'These points improve automatic detection.',
  'preImport.assistant.checks.items.headers.title': 'Headers',
  'preImport.assistant.checks.items.headers.description': 'One clear header row.',
  'preImport.assistant.checks.items.headers.status': 'OK',
  'preImport.assistant.checks.items.identifiers.title': 'Identifiers',
  'preImport.assistant.checks.items.identifiers.description': 'One unique identifier.',
  'preImport.assistant.checks.items.identifiers.status': 'OK',
  'preImport.assistant.checks.items.matchingValues.title': 'Matching values',
  'preImport.assistant.checks.items.matchingValues.description': 'Related files reuse identifiers.',
  'preImport.assistant.checks.items.matchingValues.status': 'Check',
  'preImport.assistant.checks.items.spatial.title': 'Spatial formats',
  'preImport.assistant.checks.items.spatial.description': 'GeoPackage or GeoJSON is more reliable.',
  'preImport.assistant.checks.items.spatial.status': 'Check',
  'preImport.assistant.advanced.title': 'Open these details only if this sounds like your case',
  'preImport.assistant.advanced.description': 'More constrained than the standard path.',
  'preImport.assistant.advanced.hierarchy.title': 'Hierarchies',
  'preImport.assistant.advanced.hierarchy.description': 'For nested levels.',
  'preImport.assistant.advanced.classObject.title': 'Values already calculated by class',
  'preImport.assistant.advanced.classObject.description': 'Attach one entity to one value.',
  'preImport.assistant.advanced.classObject.download': 'Class values template',
  'preImport.assistant.resources.title': 'Resources',
  'preImport.assistant.resources.description': 'Download a template.',
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

  it('opens on a lightweight overview with navigation and resources', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    expect(harness.container.textContent).toContain('One occurrences CSV is enough to start.')
    expect(harness.container.textContent).toContain('Files and models')
    expect(harness.container.textContent).toContain('Key checks')
    expect(harness.container.textContent).toContain('Advanced details')
    expect(harness.container.textContent).toContain('Resources')
    expect(harness.container.textContent).toContain('.csv')
    expect(harness.container.textContent).toContain('.gpkg')
    expect(harness.container.textContent).toContain('prefer GeoPackage')

    await harness.unmount()
  })

  it('switches to file models and downloads both starter templates', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    const filesButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Files and models')
    )
    expect(filesButton).toBeTruthy()

    await act(async () => {
      filesButton?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('Choose the model that matches your data')
    expect(harness.container.textContent).toContain('id_taxonref')
    expect(harness.container.textContent).toContain('id_plot')

    const occurrencesButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Occurrences template')
    )
    expect(occurrencesButton).toBeTruthy()

    await act(async () => {
      occurrencesButton?.click()
      await Promise.resolve()
    })

    expect(downloadCsvTemplateMock).toHaveBeenCalledWith('occurrences')

    const sitesButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Sites / plots template')
    )
    expect(sitesButton).toBeTruthy()

    await act(async () => {
      sitesButton?.click()
      await Promise.resolve()
    })

    expect(downloadCsvTemplateMock).toHaveBeenCalledWith('siteReference')

    await harness.unmount()
  })

  it('shows key checks as a focused preparation list', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    const checksButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Key checks')
    )
    expect(checksButton).toBeTruthy()

    await act(async () => {
      checksButton?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('Headers')
    expect(harness.container.textContent).toContain('Identifiers')
    expect(harness.container.textContent).toContain('Matching values')
    expect(harness.container.textContent).toContain('Spatial formats')

    await harness.unmount()
  })

  it('keeps advanced formats separate and downloads class-value template there', async () => {
    const harness = createHarness()

    await harness.render(<PreImportGuidance />)

    const advancedButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Advanced details')
    )
    expect(advancedButton).toBeTruthy()

    await act(async () => {
      advancedButton?.click()
      await Promise.resolve()
    })

    expect(harness.container.textContent).toContain('Hierarchies')
    expect(harness.container.textContent).toContain('class_object')
    expect(harness.container.textContent).toContain('class_name')
    expect(harness.container.textContent).toContain('class_value')

    const classValuesButton = Array.from(harness.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Class values template')
    )
    expect(classValuesButton).toBeTruthy()

    await act(async () => {
      classValuesButton?.click()
      await Promise.resolve()
    })

    expect(downloadTemplateMock).toHaveBeenCalledTimes(1)

    await harness.unmount()
  })
})
