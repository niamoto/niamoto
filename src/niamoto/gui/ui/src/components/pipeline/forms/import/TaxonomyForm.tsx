import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { FileUpload } from '@/components/import/FileUpload'
import { ColumnMapping } from '@/components/import/ColumnMapping'
import { BaseImportForm } from '../BaseImportForm'
import type { ImportConfig } from '../../types'

interface TaxonomyFormProps {
  config: ImportConfig
  onConfigChange: (config: ImportConfig) => void
}

export function TaxonomyForm({ config, onConfigChange }: TaxonomyFormProps) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [fields, setFields] = useState<string[]>([])
  const [mappingConfig, setMappingConfig] = useState<any>({})

  // Required fields for taxonomy
  const requiredFields = [
    { key: 'id_taxon', label: 'Taxon ID', required: true },
    { key: 'full_name', label: 'Full Name', required: true },
    { key: 'rank_name', label: 'Rank', required: true },
    { key: 'parent_id', label: 'Parent ID', required: false },
    { key: 'authors', label: 'Authors', required: false },
  ]

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile)

    // Detect fields from file
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('/api/imports/detect-fields', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setFields(data.fields || [])
      }
    } catch (error) {
      console.error('Error detecting fields:', error)
    }
  }

  const handleMappingChange = (mapping: any) => {
    setMappingConfig(mapping)
    onConfigChange({
      ...config,
      file: file?.name || '',
      mapping,
    })
  }

  return (
    <BaseImportForm
      config={config}
      onConfigChange={onConfigChange}
    >
      <div className="space-y-4">
        {/* File selection */}
        <div className="space-y-2">
          <Label>{t('pipeline.import.taxonomy.file', 'Taxonomy File')}</Label>
          {!file ? (
            <FileUpload
              onFileSelect={handleFileSelect}
              accept=".csv,.xlsx,.xls"
              maxSize={50 * 1024 * 1024} // 50MB
            />
          ) : (
            <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span className="text-sm font-medium">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setFile(null)
                  setFields([])
                  setMappingConfig({})
                }}
              >
                {t('common.change', 'Change')}
              </Button>
            </div>
          )}
        </div>

        {/* Column mapping */}
        {fields.length > 0 && (
          <div className="space-y-2">
            <Label>{t('pipeline.import.taxonomy.mapping', 'Field Mapping')}</Label>
            <ColumnMapping
              sourceColumns={fields}
              targetFields={requiredFields}
              mapping={mappingConfig}
              onMappingChange={handleMappingChange}
            />
          </div>
        )}

        {/* Advanced options */}
        <div className="space-y-2">
          <Label>{t('pipeline.import.taxonomy.options', 'Import Options')}</Label>

          <div className="flex items-center space-x-2">
            <Switch
              id="update-existing"
              checked={config.updateExisting || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, updateExisting: checked })
              }
            />
            <Label htmlFor="update-existing" className="text-sm font-normal">
              {t('pipeline.import.taxonomy.updateExisting', 'Update existing taxa')}
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="create-missing-parents"
              checked={config.createMissingParents || false}
              onCheckedChange={(checked) =>
                onConfigChange({ ...config, createMissingParents: checked })
              }
            />
            <Label htmlFor="create-missing-parents" className="text-sm font-normal">
              {t('pipeline.import.taxonomy.createParents', 'Create missing parent taxa')}
            </Label>
          </div>
        </div>

        {/* Encoding */}
        <div className="space-y-2">
          <Label htmlFor="encoding">
            {t('pipeline.import.encoding', 'File Encoding')}
          </Label>
          <Select
            value={config.encoding || 'utf-8'}
            onValueChange={(value) => onConfigChange({ ...config, encoding: value })}
          >
            <SelectTrigger id="encoding">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="utf-8">UTF-8</SelectItem>
              <SelectItem value="latin1">Latin-1</SelectItem>
              <SelectItem value="cp1252">Windows-1252</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </BaseImportForm>
  )
}
