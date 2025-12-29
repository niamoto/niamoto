/**
 * DatasetConfigEditor - Edit dataset entity configuration
 *
 * Allows editing:
 * - Connector settings (path, format)
 * - Schema fields
 * - Links to references
 */

import { useState, useEffect } from 'react'
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
import { apiClient } from '@/lib/api/client'

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

async function fetchDatasetConfig(name: string): Promise<{ name: string; config: DatasetConfig }> {
  const response = await apiClient.get(`/config/datasets/${name}/config`)
  return response.data
}

async function saveDatasetConfig(name: string, config: DatasetConfig): Promise<void> {
  await apiClient.put(`/config/datasets/${name}/config`, config)
}

export function DatasetConfigEditor({ datasetName, onSaved }: DatasetConfigEditorProps) {
  const queryClient = useQueryClient()
  const [localConfig, setLocalConfig] = useState<DatasetConfig | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['dataset-config', datasetName],
    queryFn: () => fetchDatasetConfig(datasetName),
  })

  const mutation = useMutation({
    mutationFn: (config: DatasetConfig) => saveDatasetConfig(datasetName, config),
    onSuccess: () => {
      setHasChanges(false)
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
      queryClient.invalidateQueries({ queryKey: ['dataset-config', datasetName] })
      onSaved?.()
    },
  })

  useEffect(() => {
    if (data?.config) {
      setLocalConfig(data.config)
      setHasChanges(false)
    }
  }, [data])

  const updateConfig = (updates: Partial<DatasetConfig>) => {
    if (!localConfig) return
    setLocalConfig({ ...localConfig, ...updates })
    setHasChanges(true)
  }

  const updateConnector = (updates: Partial<NonNullable<DatasetConfig['connector']>>) => {
    if (!localConfig) return
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
    const links = localConfig?.links || []
    updateConfig({ links: [...links, { entity: '', field: '', target_field: '' }] })
  }

  const updateLink = (index: number, updates: Partial<LinkConfig>) => {
    if (!localConfig?.links) return
    const links = [...localConfig.links]
    links[index] = { ...links[index], ...updates }
    updateConfig({ links })
  }

  const removeLink = (index: number) => {
    if (!localConfig?.links) return
    const links = localConfig.links.filter((_, i) => i !== index)
    updateConfig({ links })
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
          Erreur lors du chargement de la configuration
        </AlertDescription>
      </Alert>
    )
  }

  if (!localConfig) return null

  return (
    <div className="space-y-6">
      {/* Save status */}
      {mutation.isSuccess && (
        <Alert className="bg-success/10 border-success/30">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <AlertDescription className="text-success">
            Configuration sauvegardee avec succes
          </AlertDescription>
        </Alert>
      )}

      {mutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Erreur lors de la sauvegarde
          </AlertDescription>
        </Alert>
      )}

      {/* Basic Info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Informations generales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Nom</Label>
            <Input value={datasetName} disabled />
          </div>

          <div className="space-y-2">
            <Label>Description</Label>
            <Input
              value={localConfig.description || ''}
              onChange={(e) => updateConfig({ description: e.target.value })}
              placeholder="Description du dataset..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Connector Settings */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Source de donnees</CardTitle>
          <CardDescription>Configuration du connecteur</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Type de connecteur</Label>
              <Select
                value={localConfig.connector?.type || 'file'}
                onValueChange={(value) => updateConnector({ type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="file">Fichier</SelectItem>
                  <SelectItem value="database">Base de donnees</SelectItem>
                  <SelectItem value="api">API</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {localConfig.connector?.type === 'file' && (
              <div className="space-y-2">
                <Label>Format</Label>
                <Select
                  value={localConfig.connector?.format || 'csv'}
                  onValueChange={(value) => updateConnector({ format: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="excel">Excel</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="geojson">GeoJSON</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label>Chemin du fichier</Label>
            <Input
              value={localConfig.connector?.path || ''}
              onChange={(e) => updateConnector({ path: e.target.value })}
              placeholder="data/fichier.csv"
              className="font-mono text-sm"
            />
          </div>
        </CardContent>
      </Card>

      {/* Schema Settings */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Schema</CardTitle>
          <CardDescription>Configuration des champs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Champ ID</Label>
              <Input
                value={localConfig.schema?.id_field || ''}
                onChange={(e) => updateSchema({ id_field: e.target.value })}
                placeholder="id"
              />
            </div>
            <div className="space-y-2">
              <Label>Champ geometrie</Label>
              <Input
                value={localConfig.schema?.geometry_field || ''}
                onChange={(e) => updateSchema({ geometry_field: e.target.value })}
                placeholder="geometry (optionnel)"
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
                Liens vers les references
              </CardTitle>
              <CardDescription>Jointures avec les entites de reference</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={addLink}>
              <Plus className="h-3 w-3 mr-1" />
              Ajouter
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {(localConfig.links || []).map((link, index) => (
              <div key={index} className="flex items-center gap-2 p-3 rounded-md border bg-muted/30">
                <div className="flex-1 grid grid-cols-3 gap-2">
                  <div>
                    <Label className="text-xs text-muted-foreground">Reference</Label>
                    <Input
                      value={link.entity}
                      onChange={(e) => updateLink(index, { entity: e.target.value })}
                      placeholder="taxons"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Champ local</Label>
                    <Input
                      value={link.field}
                      onChange={(e) => updateLink(index, { field: e.target.value })}
                      placeholder="taxon_id"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Champ cible</Label>
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
                Aucun lien defini. Les liens permettent de joindre ce dataset aux references.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="text-sm text-muted-foreground">
          {hasChanges ? (
            <span className="text-warning">Modifications non sauvegardees</span>
          ) : (
            <span>Aucune modification</span>
          )}
        </div>
        <Button
          onClick={handleSave}
          disabled={!hasChanges || mutation.isPending}
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Sauvegarder
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
