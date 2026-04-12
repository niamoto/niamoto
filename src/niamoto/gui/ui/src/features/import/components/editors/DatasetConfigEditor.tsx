/**
 * DatasetConfigEditor - Edit dataset entity configuration
 *
 * Allows editing:
 * - Connector settings (path, format)
 * - Schema fields
 * - Links to references
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Plus,
  X,
  Link,
} from 'lucide-react'
import { apiClient } from '@/shared/lib/api/client'
import { importQueryKeys } from '@/features/import/queryKeys'
import { datasetConfigQueryOptions } from '@/features/import/queryUtils'

interface DatasetConfigEditorProps {
  datasetName: string
  onSaved?: () => void
}

interface LinkConfig {
  entity: string
  field: string
  target_field: string
}

interface DatasetConfig {
  description?: string
  connector?: {
    type?: string
    format?: string
    path?: string
  }
  schema?: {
    id_field?: string
    fields?: Record<string, string>
    geometry_field?: string
  }
  links?: LinkConfig[]
  options?: {
    mode?: string
    chunk_size?: number
  }
}

async function saveDatasetConfig(name: string, config: DatasetConfig): Promise<void> {
  await apiClient.put(`/config/datasets/${name}/config`, config)
}

export function DatasetConfigEditor({ datasetName, onSaved }: DatasetConfigEditorProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data, isLoading, error } = useQuery({
    ...datasetConfigQueryOptions(datasetName),
    select: (response) => ({
      ...response,
      config: response.config as DatasetConfig,
    }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {t('configEditor.loadError')}
        </AlertDescription>
      </Alert>
    )
  }

  if (!data?.config) return null

  return (
    <DatasetConfigEditorForm
      key={`${datasetName}:${JSON.stringify(data.config)}`}
      datasetName={datasetName}
      initialConfig={data.config}
      onSaved={onSaved}
    />
  )
}

interface DatasetConfigEditorFormProps {
  datasetName: string
  initialConfig: DatasetConfig
  onSaved?: () => void
}

function DatasetConfigEditorForm({
  datasetName,
  initialConfig,
  onSaved,
}: DatasetConfigEditorFormProps) {
  const { t } = useTranslation(['sources', 'common'])
  const queryClient = useQueryClient()
  const [localConfig, setLocalConfig] = useState<DatasetConfig>(initialConfig)
  const [hasChanges, setHasChanges] = useState(false)

  const mutation = useMutation({
    mutationFn: (config: DatasetConfig) => saveDatasetConfig(datasetName, config),
    onSuccess: async () => {
      setHasChanges(false)
      queryClient.setQueryData(importQueryKeys.config.dataset(datasetName), {
        name: datasetName,
        config: localConfig,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: importQueryKeys.entities.datasets() }),
        queryClient.invalidateQueries({ queryKey: importQueryKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: importQueryKeys.config.dataset(datasetName) }),
      ])
      onSaved?.()
    },
  })

  const updateConfig = (updates: Partial<DatasetConfig>) => {
    setLocalConfig({ ...localConfig, ...updates })
    setHasChanges(true)
  }

  const updateConnector = (updates: Partial<NonNullable<DatasetConfig['connector']>>) => {
    setLocalConfig({
      ...localConfig,
      connector: { ...localConfig.connector, ...updates },
    })
    setHasChanges(true)
  }

  const updateSchema = (updates: Partial<NonNullable<DatasetConfig['schema']>>) => {
    if (!localConfig) return
    setLocalConfig({
      ...localConfig,
      schema: { ...localConfig.schema, ...updates },
    })
    setHasChanges(true)
  }

  const addLink = () => {
    const links = localConfig.links || []
    updateConfig({ links: [...links, { entity: '', field: '', target_field: '' }] })
  }

  const updateLink = (index: number, updates: Partial<LinkConfig>) => {
    if (!localConfig.links) return
    const links = [...localConfig.links]
    links[index] = { ...links[index], ...updates }
    updateConfig({ links })
  }

  const removeLink = (index: number) => {
    if (!localConfig.links) return
    const links = localConfig.links.filter((_, i) => i !== index)
    updateConfig({ links })
  }

  const handleSave = () => {
    mutation.mutate(localConfig)
  }

  return (
    <div className="space-y-4">
      {/* Save status */}
      {mutation.isSuccess && (
        <Alert className="bg-success/10 border-success/30">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <AlertDescription className="text-success">
            {t('configEditor.savedSuccess')}
          </AlertDescription>
        </Alert>
      )}

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {t('configEditor.saveError')}
          </AlertDescription>
        </Alert>
      )}

      {/* Basic Info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t('configEditor.generalInfo')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>{t('configEditor.name')}</Label>
            <Input value={datasetName} disabled />
          </div>

          <div className="space-y-2">
            <Label>{t('configEditor.description')}</Label>
            <Input
              value={localConfig.description || ''}
              onChange={(e) => updateConfig({ description: e.target.value })}
              placeholder={t('configEditor.descriptionPlaceholder')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Connector Settings */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t('configEditor.dataSource')}</CardTitle>
          <CardDescription>{t('configEditor.connectorConfig')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('configEditor.connectorType')}</Label>
              <Select
                value={localConfig.connector?.type || 'file'}
                onValueChange={(value) => updateConnector({ type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="file">{t('configEditor.file')}</SelectItem>
                  <SelectItem value="database">{t('configEditor.database')}</SelectItem>
                  <SelectItem value="api">{t('configEditor.api')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {localConfig.connector?.type === 'file' && (
              <div className="space-y-2">
                <Label>{t('configEditor.format')}</Label>
                <Select
                  value={localConfig.connector?.format || 'csv'}
                  onValueChange={(value) => updateConnector({ format: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="excel">{t('configEditor.excel')}</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="geojson">GeoJSON</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label>{t('configEditor.filePath')}</Label>
            <Input
              value={localConfig.connector?.path || ''}
              onChange={(e) => updateConnector({ path: e.target.value })}
              placeholder={t('configEditor.filePathPlaceholder')}
              className="font-mono text-sm"
            />
          </div>
        </CardContent>
      </Card>

      {/* Schema Settings */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t('configEditor.schema')}</CardTitle>
          <CardDescription>{t('configEditor.fieldsConfig')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('configEditor.idField')}</Label>
              <Input
                value={localConfig.schema?.id_field || ''}
                onChange={(e) => updateSchema({ id_field: e.target.value })}
                placeholder="id"
              />
            </div>
            <div className="space-y-2">
              <Label>{t('configEditor.geometryField')}</Label>
              <Input
                value={localConfig.schema?.geometry_field || ''}
                onChange={(e) => updateSchema({ geometry_field: e.target.value })}
                placeholder={t('configEditor.geometryOptional')}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Links to References */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Link className="h-4 w-4" />
                {t('configEditor.linksToReferences')}
              </CardTitle>
              <CardDescription>{t('configEditor.joinsWithReferences')}</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={addLink}>
              <Plus className="h-3 w-3 mr-1" />
              {t('common:actions.add')}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {(localConfig.links || []).map((link, index) => (
              <div key={index} className="flex items-center gap-2 p-3 rounded-md border bg-muted/30">
                <div className="flex-1 grid grid-cols-3 gap-2">
                  <div>
                    <Label className="text-xs text-muted-foreground">{t('configEditor.reference')}</Label>
                    <Input
                      value={link.entity}
                      onChange={(e) => updateLink(index, { entity: e.target.value })}
                      placeholder="taxons"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">{t('configEditor.localField')}</Label>
                    <Input
                      value={link.field}
                      onChange={(e) => updateLink(index, { field: e.target.value })}
                      placeholder="taxon_id"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">{t('configEditor.targetField')}</Label>
                    <Input
                      value={link.target_field}
                      onChange={(e) => updateLink(index, { target_field: e.target.value })}
                      placeholder="id"
                      className="h-8"
                    />
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeLink(index)}
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            {(!localConfig.links || localConfig.links.length === 0) && (
              <p className="text-sm text-muted-foreground py-4 text-center">
                {t('configEditor.noLinksHint')}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="text-sm text-muted-foreground">
          {hasChanges ? (
            <span className="text-warning">{t('configEditor.unsavedChanges')}</span>
          ) : (
            <span>{t('configEditor.noChanges')}</span>
          )}
        </div>
        <Button
          onClick={handleSave}
          disabled={!hasChanges || mutation.isPending}
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('configEditor.saving')}
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              {t('configEditor.save')}
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
