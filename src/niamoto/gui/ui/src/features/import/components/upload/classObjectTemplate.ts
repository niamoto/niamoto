import { invoke, isTauri } from '@tauri-apps/api/core'

export const CLASS_OBJECT_TEMPLATE_FILENAME = 'class_object-template.csv'

export const CLASS_OBJECT_TEMPLATE_CONTENT = [
  'entity_id,class_object,class_name,class_value',
  'plot_001,total_area_ha,,12.5',
  'plot_001,forest_cover,forest,8.4',
  'plot_001,forest_cover,non_forest,4.1',
  'plot_001,elevation_band,0-100m,3',
  'plot_001,elevation_band,100-200m,9.5',
].join('\n')

export function downloadClassObjectTemplate() {
  return downloadCsvTemplate('classObject')
}

export const CSV_TEMPLATES = {
  reference: {
    filename: 'reference-table-template.csv',
    content: [
      'id,name,description',
      'plot_001,Plot 001,Main monitoring plot',
      'plot_002,Plot 002,Secondary monitoring plot',
    ].join('\n'),
  },
  occurrences: {
    filename: 'occurrences-template.csv',
    content: [
      'id,id_taxonref,plot_name,taxaname,taxonref,family,genus,species,infra,geo_pt',
      'obs_001,2283,Plot 001,Burretiokentia vieillardii,Burretiokentia vieillardii (Brongn. & Gris) Pic.Serm.,Arecaceae,Burretiokentia,Burretiokentia vieillardii,,POINT (165.7683 -21.6461)',
      'obs_002,3467,Plot 001,Geissois polyphylla,Geissois polyphylla Lecard ex Guillaumin,Cunoniaceae,Geissois,Geissois polyphylla,,POINT (165.7683 -21.6461)',
    ].join('\n'),
  },
  siteReference: {
    filename: 'sites-plots-template.csv',
    content: [
      'id_plot,plot,locality,elevation,rainfall,geo_pt',
      '10,Plot 001,Blue River,507,1830,POINT (165.12036133 -21.14814186)',
      '6,Plot 002,Mount Panie,42,1570,POINT (164.35525513 -20.53927231)',
    ].join('\n'),
  },
  classObject: {
    filename: CLASS_OBJECT_TEMPLATE_FILENAME,
    content: CLASS_OBJECT_TEMPLATE_CONTENT,
  },
} as const

export type CsvTemplateId = keyof typeof CSV_TEMPLATES

function downloadWithBrowser(filename: string, content: string) {
  const blob = new Blob([`${content}\n`], {
    type: 'text/csv;charset=utf-8;',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()

  window.setTimeout(() => {
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }, 1000)
}

export async function downloadCsvTemplate(templateId: CsvTemplateId) {
  const template = CSV_TEMPLATES[templateId]

  if (isTauri()) {
    try {
      await invoke('save_text_file', {
        filename: template.filename,
        contents: `${template.content}\n`,
      })
      return
    } catch (error) {
      console.warn('Native file save failed, falling back to browser download.', error)
    }
  }

  downloadWithBrowser(template.filename, template.content)
}
