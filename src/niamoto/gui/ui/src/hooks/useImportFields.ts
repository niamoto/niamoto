import { useState, useEffect } from 'react'
import axios from 'axios'

export interface RequiredField {
  key: string
  label: string
  description: string
  required: boolean
}

export interface ImportFieldsInfo {
  fields: RequiredField[]
  method_params: Record<string, any>
}

export function useImportFields(importType: string) {
  const [fields, setFields] = useState<RequiredField[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchFields = async () => {
      if (!importType) {
        setFields([])
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const response = await axios.get<ImportFieldsInfo>(
          `/api/imports/required-fields/${importType}`
        )
        setFields(response.data.fields || [])
      } catch (err) {
        console.error('Failed to fetch import fields:', err)
        setError('Failed to load field definitions')

        // Fallback to static definitions if API fails
        setFields(getFallbackFields(importType))
      } finally {
        setLoading(false)
      }
    }

    fetchFields()
  }, [importType])

  return { fields, loading, error }
}

// Fallback field definitions in case the API is unavailable
function getFallbackFields(importType: string): RequiredField[] {
  const fallbackFields: Record<string, RequiredField[]> = {
    taxonomy: [
      { key: 'taxon_id', label: 'Taxon ID', description: 'Unique identifier for each taxon', required: true },
      { key: 'family', label: 'Family', description: 'Family rank column', required: true },
      { key: 'genus', label: 'Genus', description: 'Genus rank column', required: true },
      { key: 'species', label: 'Species', description: 'Species rank column', required: true },
      { key: 'infra', label: 'Infra', description: 'Infraspecific rank', required: false },
      { key: 'authors', label: 'Authors', description: 'Taxonomic authority', required: false },
    ],
    plots: [
      { key: 'identifier', label: 'Plot Identifier', description: 'Unique identifier for each plot', required: true },
      { key: 'location', label: 'Location', description: 'Geometry field (WKT or coordinates)', required: true },
      { key: 'locality', label: 'Locality', description: 'Plot locality name', required: true },
      { key: 'link_field', label: 'Link Field', description: 'Field for linking with occurrences', required: false },
      { key: 'occurrence_link_field', label: 'Occurrence Link Field', description: 'Corresponding field in occurrences', required: false },
    ],
    occurrences: [
      { key: 'taxon_id', label: 'Taxon ID', description: 'Reference to taxonomy', required: true },
      { key: 'location', label: 'Location', description: 'Occurrence coordinates (WKT format)', required: true },
      { key: 'plot_name', label: 'Plot Name', description: 'Link to plot', required: false },
    ],
    shapes: [
      { key: 'name', label: 'Name', description: 'Shape name field', required: true },
      { key: 'type', label: 'Type', description: 'Shape type', required: false },
    ],
  }

  return fallbackFields[importType] || []
}
