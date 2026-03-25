/**
 * ReferenceConfigEditor - Edit reference entity configuration
 *
 * Allows editing:
 * - Kind (hierarchical, generic, spatial)
 * - Connector settings (path, format)
 * - Hierarchy configuration (levels, id_column, name_column)
 * - Schema fields
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
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
  FileText,
  Leaf,
  Map,
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface ReferenceConfigEditorProps {
  referenceName: string
  onSaved?: () => void
}

interface ReferenceConfig {
  kind?: string
  description?: string
  connector?: {
    type?: string
    format?: string
    path?: string
    sources?: Array<{ name: string; path: string; name_field: string }>
  }
  hierarchy?: {
    strategy?: string
    levels?: string[]
    incomplete_rows?: string
    id_strategy?: string
    id_column?: string
    name_column?: string
  }
  schema?: {
    id_field?: string
    fields?: Record<string, string>
  }
}

async function fetchReferenceConfig(name: string): Promise<{ name: string; config: ReferenceConfig }> {
  const response = await apiClient.get(`/config/references/${name}/config`)
  return response.data
}

async function saveReferenceConfig(name: string, config: ReferenceConfig): Promise<void> {
  await apiClient.put(`/config/references/${name}/config`, config)
}

export function ReferenceConfigEditor({
  referenceName,
  onSaved,
}: ReferenceConfigEditorProps) {
  const { t } = useTranslation(['sources', 'common'])
  const queryClient = useQueryClient()
  const [localConfig, setLocalConfig] = useState<ReferenceConfig | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['reference-config', referenceName],
    queryFn: () => fetchReferenceConfig(referenceName),
  })

  const mutation = useMutation({
    mutationFn: (config: ReferenceConfig) => saveReferenceConfig(referenceName, config),
    onSuccess: () => {
      setHasChanges(false)
      queryClient.invalidateQueries({ queryKey: ['references'] })
      queryClient.invalidateQueries({ queryKey: ['reference-config', referenceName] })
      onSaved?.()
    },
  })

  useEffect(() => {
    if (data?.config) {
      setLocalConfig(data.config)
      setHasChanges(false)
    }
  }, [data])

  const updateConfig = (updates: Partial<ReferenceConfig>) => {
    if (!localConfig) return
    setLocalConfig({ ...localConfig, ...updates })
    setHasChanges(true)
  }

  const updateHierarchy = (updates: Partial<NonNullable<ReferenceConfig['hierarchy']>>) => {
    if (!localConfig) return
    setLocalConfig({
      ...localConfig,
      hierarchy: { ...localConfig.hierarchy, ...updates },
    })
    setHasChanges(true)
  }

  const updateConnector = (updates: Partial<NonNullable<ReferenceConfig['connector']>>) => {
    if (!localConfig) return
    setLocalConfig({
      ...localConfig,
      connector: { ...localConfig.connector, ...updates },
    })
    setHasChanges(true)
  }

  const addHierarchyLevel = () => {
    if (!localConfig?.hierarchy) return
    const levels = localConfig.hierarchy.levels || []
    updateHierarchy({ levels: [...levels, ''] })
  }

  const updateHierarchyLevel = (index: number, value: string) => {
    if (!localConfig?.hierarchy?.levels) return
    const levels = [...localConfig.hierarchy.levels]
    levels[index] = value
    updateHierarchy({ levels })
  }

  const removeHierarchyLevel = (index: number) => {
    if (!localConfig?.hierarchy?.levels) return
    const levels = localConfig.hierarchy.levels.filter((_, i) => i !== index)
    updateHierarchy({ levels })
  }

  const handleSave = () => {
    if (localConfig) {
      mutation.mutate(localConfig)
    }
  }

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

  if (!localConfig) return null

  const isHierarchical = localConfig.kind === 'hierarchical'
  return (
    <div className="space-y-6">
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
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>{t('configEditor.name')}</Label>
              <Input value={referenceName} disabled />
            </div>
            <div className="space-y-2">
              <Label>{t('configEditor.type')}</Label>
              <Select
                value={localConfig.kind || 'generic'}
                onValueChange={(value) => updateConfig({ kind: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="generic">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      {t('configEditor.flatSimple')}
                    </div>
                  </SelectItem>
                  <SelectItem value="hierarchical">
                    <div className="flex items-center gap-2">
                      <Leaf className="h-4 w-4" />
                      {t('configEditor.hierarchical')}
                    </div>
                  </SelectItem>
                  <SelectItem value="spatial">
                    <div className="flex items-center gap-2">
                      <Map className="h-4 w-4" />
                      {t('configEditor.spatial')}
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
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
                  <SelectItem value="derived">{t('configEditor.derived')}</SelectItem>
                  <SelectItem value="file_multi_feature">{t('configEditor.multiFeature')}</SelectItem>
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
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          {localConfig.connector?.type !== 'derived' && (
            <div className="space-y-2">
              <Label>{t('configEditor.filePath')}</Label>
              <Input
                value={localConfig.connector?.path || ''}
                onChange={(e) => updateConnector({ path: e.target.value })}
                placeholder={t('configEditor.filePathPlaceholder')}
                className="font-mono text-sm"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Hierarchy Settings (only for hierarchical) */}
      {isHierarchical && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Leaf className="h-4 w-4" />
              {t('configEditor.hierarchyConfig')}
            </CardTitle>
            <CardDescription>{t('configEditor.hierarchyLevelsConfig')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t('configEditor.strategy')}</Label>
                <Select
                  value={localConfig.hierarchy?.strategy || 'adjacency_list'}
                  onValueChange={(value) => updateHierarchy({ strategy: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="adjacency_list">{t('configEditor.adjacencyList')}</SelectItem>
                    <SelectItem value="nested_set">{t('configEditor.nestedSet')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{t('configEditor.incompleteRows')}</Label>
                <Select
                  value={localConfig.hierarchy?.incomplete_rows || 'skip'}
                  onValueChange={(value) => updateHierarchy({ incomplete_rows: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="skip">{t('configEditor.skip')}</SelectItem>
                    <SelectItem value="keep">{t('configEditor.keep')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{t('configEditor.hierarchyLevels')}</Label>
                <Button variant="outline" size="sm" onClick={addHierarchyLevel}>
                  <Plus className="h-3 w-3 mr-1" />
                  {t('common:actions.add')}
                </Button>
              </div>
              <div className="space-y-2">
                {(localConfig.hierarchy?.levels || []).map((level, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Badge variant="outline" className="w-8 justify-center">
                      {index + 1}
                    </Badge>
                    <Input
                      value={level}
                      onChange={(e) => updateHierarchyLevel(index, e.target.value)}
                      placeholder={t('configEditor.levelN', { n: index + 1 })}
                      className="flex-1"
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeHierarchyLevel(index)}
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {(!localConfig.hierarchy?.levels || localConfig.hierarchy.levels.length === 0) && (
                  <p className="text-sm text-muted-foreground py-2">
                    {t('configEditor.noLevelsHint')}
                  </p>
                )}
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t('configEditor.idColumn')}</Label>
                <Input
                  value={localConfig.hierarchy?.id_column || ''}
                  onChange={(e) => updateHierarchy({ id_column: e.target.value })}
                  placeholder="id_taxonref"
                />
              </div>
              <div className="space-y-2">
                <Label>{t('configEditor.nameColumn')}</Label>
                <Input
                  value={localConfig.hierarchy?.name_column || ''}
                  onChange={(e) => updateHierarchy({ name_column: e.target.value })}
                  placeholder="taxaname"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
