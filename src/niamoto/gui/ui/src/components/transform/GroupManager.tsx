import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Edit2, Trash2, Database, ChevronRight, Users, Map, TreePine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

export interface Group {
  id: string
  name: string
  displayName: string
  description?: string
  sources: Source[]
  transformations: number
  lastModified: string
  icon?: 'taxon' | 'plot' | 'shape' | 'custom'
}

export interface Source {
  id: string
  name: string
  type: 'table' | 'csv' | 'excel'
  groupingField?: string
  relation?: {
    plugin: string
    config?: any
  }
}

interface GroupManagerProps {
  onGroupSelect?: (group: Group) => void
  selectedGroupId?: string
}

const iconMap = {
  taxon: TreePine,
  plot: Map,
  shape: Database,
  custom: Users,
}

export function GroupManager({ onGroupSelect, selectedGroupId }: GroupManagerProps) {
  const { t } = useTranslation()
  const [groups, setGroups] = useState<Group[]>([
    {
      id: '1',
      name: 'taxon',
      displayName: 'Espèces',
      description: 'Groupement par taxonomie',
      icon: 'taxon',
      sources: [
        { id: '1', name: 'occurrences', type: 'table', groupingField: 'taxon_ref' },
        { id: '2', name: 'taxon_stats.csv', type: 'csv', relation: { plugin: 'nested_set' } },
      ],
      transformations: 12,
      lastModified: '2024-12-13T10:30:00',
    },
    {
      id: '2',
      name: 'plot',
      displayName: 'Parcelles',
      description: 'Groupement par parcelles d’étude',
      icon: 'plot',
      sources: [
        { id: '3', name: 'plots', type: 'table', groupingField: 'plot_id' },
        { id: '4', name: 'measurements', type: 'table', relation: { plugin: 'stats_loader' } },
      ],
      transformations: 8,
      lastModified: '2024-12-12T14:20:00',
    },
  ])

  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingGroup, setEditingGroup] = useState<Group | null>(null)
  const [formData, setFormData] = useState<{
    name: string
    displayName: string
    description: string
    icon: 'taxon' | 'plot' | 'shape' | 'custom'
  }>({
    name: '',
    displayName: '',
    description: '',
    icon: 'custom',
  })

  const handleCreateGroup = () => {
    setEditingGroup(null)
    setFormData({ name: '', displayName: '', description: '', icon: 'custom' })
    setIsDialogOpen(true)
  }

  const handleEditGroup = (group: Group) => {
    setEditingGroup(group)
    setFormData({
      name: group.name,
      displayName: group.displayName,
      description: group.description || '',
      icon: (group.icon || 'custom') as 'taxon' | 'plot' | 'shape' | 'custom',
    })
    setIsDialogOpen(true)
  }

  const handleSaveGroup = () => {
    if (editingGroup) {
      setGroups(groups.map(g =>
        g.id === editingGroup.id
          ? { ...g, ...formData }
          : g
      ))
    } else {
      const newGroup: Group = {
        id: String(Date.now()),
        ...formData,
        sources: [],
        transformations: 0,
        lastModified: new Date().toISOString(),
      }
      setGroups([...groups, newGroup])
    }
    setIsDialogOpen(false)
  }

  const handleDeleteGroup = (groupId: string) => {
    setGroups(groups.filter(g => g.id !== groupId))
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

    if (diffHours < 1) return t('transform.groups.just_now', 'Just now')
    if (diffHours < 24) return t('transform.groups.hours_ago', '{{count}} hours ago', { count: diffHours })
    const diffDays = Math.floor(diffHours / 24)
    return t('transform.groups.days_ago', '{{count}} days ago', { count: diffDays })
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">
            {t('transform.groups.title', 'Analysis Groups')}
          </h3>
          <p className="text-sm text-muted-foreground">
            {t('transform.groups.description', 'Define how your data should be grouped for analysis')}
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={handleCreateGroup}>
              <Plus className="mr-2 h-4 w-4" />
              {t('transform.groups.create', 'Create Group')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingGroup
                  ? t('transform.groups.edit_title', 'Edit Group')
                  : t('transform.groups.create_title', 'Create New Group')
                }
              </DialogTitle>
              <DialogDescription>
                {t('transform.groups.dialog_description', 'Configure your analysis group settings')}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">
                  {t('transform.groups.name_label', 'Technical Name')}
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., taxon, plot, shape"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="displayName">
                  {t('transform.groups.display_name_label', 'Display Name')}
                </Label>
                <Input
                  id="displayName"
                  value={formData.displayName}
                  onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                  placeholder="e.g., Species, Plots, Regions"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="description">
                  {t('transform.groups.description_label', 'Description')}
                </Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of the grouping"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="icon">
                  {t('transform.groups.icon_label', 'Icon')}
                </Label>
                <Select
                  value={formData.icon}
                  onValueChange={(value: any) => setFormData({ ...formData, icon: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="taxon">🌳 Taxonomy</SelectItem>
                    <SelectItem value="plot">📍 Plot</SelectItem>
                    <SelectItem value="shape">🗺️ Geographic</SelectItem>
                    <SelectItem value="custom">👥 Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                {t('common.cancel', 'Cancel')}
              </Button>
              <Button onClick={handleSaveGroup}>
                {editingGroup ? t('common.save', 'Save') : t('common.create', 'Create')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Groups Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {groups.map((group) => {
          const Icon = iconMap[group.icon || 'custom']
          const isSelected = selectedGroupId === group.id

          return (
            <Card
              key={group.id}
              className={cn(
                'cursor-pointer transition-all hover:shadow-md',
                isSelected && 'ring-2 ring-primary'
              )}
              onClick={() => onGroupSelect?.(group)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-primary/10 p-2">
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{group.displayName}</CardTitle>
                      <Badge variant="outline" className="mt-1">
                        {group.name}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleEditGroup(group)
                      }}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteGroup(group.id)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {group.description && (
                  <CardDescription className="mt-2">
                    {group.description}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {/* Sources */}
                  <div className="flex items-center gap-2 text-sm">
                    <Database className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">
                      {t('transform.groups.sources', '{{count}} sources', { count: group.sources.length })}
                    </span>
                  </div>

                  {/* Source List */}
                  {group.sources.length > 0 && (
                    <div className="ml-6 space-y-1">
                      {group.sources.slice(0, 2).map((source) => (
                        <div key={source.id} className="flex items-center gap-2 text-xs text-muted-foreground">
                          <ChevronRight className="h-3 w-3" />
                          <span>{source.name}</span>
                          <Badge variant="secondary" className="h-4 px-1 text-[10px]">
                            {source.type}
                          </Badge>
                        </div>
                      ))}
                      {group.sources.length > 2 && (
                        <div className="text-xs text-muted-foreground">
                          {t('transform.groups.more_sources', '+{{count}} more', { count: group.sources.length - 2 })}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Stats */}
                  <div className="flex items-center justify-between pt-2 text-sm">
                    <span className="text-muted-foreground">
                      {t('transform.groups.transformations', '{{count}} transformations', { count: group.transformations })}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(group.lastModified)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}

        {/* Empty State Card */}
        {groups.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-8">
              <Database className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-2 text-sm font-medium">
                {t('transform.groups.empty_title', 'No groups yet')}
              </p>
              <p className="text-xs text-muted-foreground">
                {t('transform.groups.empty_description', 'Create your first analysis group')}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
