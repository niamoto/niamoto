export type PreflightStatus = 'ready' | 'review' | 'info'

export interface FilePreflightSummary {
  fileName: string
  status: PreflightStatus
  badges: string[]
  tips: string[]
}

const HIERARCHY_COLUMNS = new Set([
  'kingdom',
  'phylum',
  'class',
  'order',
  'family',
  'genus',
  'species',
  'subspecies',
  'country',
  'region',
  'locality',
  'sublocality',
  'plot',
])

const CLASS_OBJECT_COLUMNS = new Set(['class_object', 'class_name', 'class_value'])
const ENTITY_COLUMNS = new Set(['entity_id', 'plot_id', 'shape_id', 'taxon_id', 'id'])
const TAXON_ID_COLUMNS = new Set(['taxon_id', 'id_taxon', 'id_taxonref'])

function detectDelimiter(firstLine: string) {
  const delimiters = [',', ';', '\t'] as const
  return delimiters.reduce((best, delimiter) =>
    firstLine.split(delimiter).length > firstLine.split(best).length ? delimiter : best
  )
}

function splitRow(row: string, delimiter: string) {
  return row.split(delimiter).map((value) => value.trim().replace(/^"|"$/g, ''))
}

function normalizeColumn(column: string) {
  return column.trim().replace(/^\ufeff/, '').toLowerCase()
}

async function analyzeCsv(file: File): Promise<FilePreflightSummary> {
  const text = await file.slice(0, 128 * 1024).text()
  const rows = text.split(/\r?\n/).filter((row) => row.trim().length > 0)
  const firstLine = rows[0] || ''
  const delimiter = detectDelimiter(firstLine)
  const columns = splitRow(firstLine, delimiter)
  const normalizedColumns = columns.map(normalizeColumn)
  const columnSet = new Set(normalizedColumns)
  const badges: string[] = []
  const tips: string[] = []

  if (columns.length > 1 && normalizedColumns.every(Boolean)) {
    badges.push('headers')
  } else {
    tips.push('missingHeaders')
  }

  const idColumns = normalizedColumns.filter((column) =>
    column === 'id' || column.endsWith('_id') || column.startsWith('id_') || column.endsWith('_code')
  )
  if (idColumns.length > 0) {
    badges.push('identifiers')
  } else {
    tips.push('missingIdentifiers')
  }

  const hierarchyColumns = normalizedColumns.filter((column) => HIERARCHY_COLUMNS.has(column))
  if (hierarchyColumns.length >= 2) {
    badges.push('hierarchy')
  }
  const hasTaxonomyLevels = ['family', 'genus', 'species'].filter((column) => columnSet.has(column))
    .length >= 2
  const hasTaxonIdentifier = [...TAXON_ID_COLUMNS].some((column) => columnSet.has(column))
  if (hasTaxonomyLevels && hasTaxonIdentifier) {
    badges.push('taxonomyFromOccurrences')
  }

  const looksLikeClassObject = [...CLASS_OBJECT_COLUMNS].every((column) => columnSet.has(column))
  if (looksLikeClassObject) {
    badges.push('classObject')
    if (![...ENTITY_COLUMNS].some((column) => columnSet.has(column))) {
      tips.push('classObjectIdentifier')
    }

    const valueIndex = normalizedColumns.indexOf('class_value')
    const sampleValues = rows.slice(1, 12).map((row) => splitRow(row, delimiter)[valueIndex])
    const hasNonNumericValue = sampleValues.some((value) => value && Number.isNaN(Number(value)))
    if (hasNonNumericValue) {
      tips.push('classObjectNumeric')
    }
  }

  return {
    fileName: file.name,
    status: tips.length > 0 ? 'review' : 'ready',
    badges,
    tips,
  }
}

function analyzeByExtension(file: File): FilePreflightSummary {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext === 'gpkg' || ext === 'geojson') {
    return {
      fileName: file.name,
      status: 'ready',
      badges: ['spatial'],
      tips: [],
    }
  }
  if (ext === 'tif' || ext === 'tiff') {
    return {
      fileName: file.name,
      status: 'info',
      badges: ['raster'],
      tips: [],
    }
  }
  if (ext === 'zip') {
    return {
      fileName: file.name,
      status: 'review',
      badges: ['zip'],
      tips: ['zipShapefile'],
    }
  }
  return {
    fileName: file.name,
    status: 'info',
    badges: [],
    tips: ['unsupported'],
  }
}

export async function analyzeFilesBeforeUpload(files: File[]) {
  const summaries = await Promise.all(
    files.map(async (file) => {
      const ext = file.name.split('.').pop()?.toLowerCase()
      if (ext === 'csv') {
        try {
          return await analyzeCsv(file)
        } catch {
          return {
            fileName: file.name,
            status: 'review' as const,
            badges: [],
            tips: ['unreadableCsv'],
          }
        }
      }
      return analyzeByExtension(file)
    })
  )

  return Object.fromEntries(summaries.map((summary) => [summary.fileName, summary]))
}
