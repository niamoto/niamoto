/**
 * ResourcesForm - Dedicated form for resources.html template
 *
 * Manages:
 * - Title and introduction
 * - Resources list (title, description, type, url, size, format, license)
 */

import { useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RepeatableField } from './RepeatableField'
import { renderLucideIcon } from './LucideIconPicker'
import { FilePickerField } from './FilePickerField'

// Types for resources.html context
interface ResourceItem {
  title: string
  description: string
  type: string
  url: string
  license?: string
}

export interface ResourcesPageContext {
  title?: string
  introduction?: string
  resources?: ResourceItem[]
  [key: string]: unknown
}

interface ResourcesFormProps {
  context: ResourcesPageContext
  onChange: (context: ResourcesPageContext) => void
}

const RESOURCE_TYPES = [
  { value: 'dataset', label: 'Dataset', icon: 'database' },
  { value: 'document', label: 'Document', icon: 'file-text' },
  { value: 'tool', label: 'Outil', icon: 'settings' },
  { value: 'api', label: 'API', icon: 'zap' },
  { value: 'code', label: 'Code source', icon: 'files' },
  { value: 'image', label: 'Image/Media', icon: 'eye' },
  { value: 'other', label: 'Autre', icon: 'folder' },
]

const COMMON_LICENSES = ['CC-BY-4.0', 'CC-BY-SA-4.0', 'CC-BY-NC-4.0', 'CC0', 'MIT', 'GPL-3.0', 'Proprietary']

export function ResourcesForm({ context, onChange }: ResourcesFormProps) {
  const updateField = useCallback(
    <K extends keyof ResourcesPageContext>(field: K, value: ResourcesPageContext[K]) => {
      onChange({ ...context, [field]: value })
    },
    [context, onChange]
  )

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">En-tete</h3>

        <div className="space-y-2">
          <Label htmlFor="title">Titre de la page</Label>
          <Input
            id="title"
            value={context.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="Ressources"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="introduction">Introduction</Label>
          <Textarea
            id="introduction"
            value={context.introduction || ''}
            onChange={(e) => updateField('introduction', e.target.value)}
            placeholder="Telechargez nos datasets, outils et documentation..."
            rows={3}
          />
        </div>
      </div>

      <Separator />

      {/* Resources Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Ressources</h3>
        <p className="text-sm text-muted-foreground">
          {context.resources?.length || 0} ressource(s)
        </p>

        <RepeatableField<ResourceItem>
          items={context.resources || []}
          onChange={(resources) => updateField('resources', resources)}
          createItem={() => ({
            title: '',
            description: '',
            type: 'dataset',
            url: '',
            license: 'CC-BY-4.0',
          })}
          addLabel="Ajouter une ressource"
          renderItem={(item, _index, onItemChange) => (
            <div className="space-y-3">
              {/* Row 1: Title, Type */}
              <div className="grid grid-cols-[1fr_150px] gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">Titre</Label>
                  <Input
                    value={item.title}
                    onChange={(e) => onItemChange({ ...item, title: e.target.value })}
                    placeholder="Dataset Occurrences 2023"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Type</Label>
                  <Select
                    value={item.type}
                    onValueChange={(value) => onItemChange({ ...item, type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RESOURCE_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          <span className="flex items-center gap-2">
                            {renderLucideIcon(type.icon, 'h-4 w-4')}
                            <span>{type.label}</span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Row 2: Description */}
              <div className="space-y-1">
                <Label className="text-xs">Description</Label>
                <Textarea
                  value={item.description}
                  onChange={(e) => onItemChange({ ...item, description: e.target.value })}
                  placeholder="Donnees d'occurrences de plantes en Nouvelle-Caledonie..."
                  rows={2}
                />
              </div>

              {/* Row 3: File/URL */}
              <div className="space-y-1">
                <Label className="text-xs">Fichier ou URL</Label>
                <FilePickerField
                  value={item.url}
                  onChange={(url) => onItemChange({ ...item, url })}
                  folder="files/data"
                  placeholder="Selectionner ou uploader un fichier"
                />
              </div>

              {/* Row 4: License */}
              <div className="space-y-1">
                <Label className="text-xs">Licence</Label>
                <Select
                  value={item.license || ''}
                  onValueChange={(value) => onItemChange({ ...item, license: value })}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Licence" />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_LICENSES.map((license) => (
                      <SelectItem key={license} value={license}>
                        {license}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        />
      </div>
    </div>
  )
}

export default ResourcesForm
