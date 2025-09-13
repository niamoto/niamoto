import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Database, FileSpreadsheet, FileText, Link2, X, Upload, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'
import type { Source } from './GroupManager'

interface SourceSelectorProps {
  sources: Source[]
  onSourcesChange: (sources: Source[]) => void
  groupName?: string
}

interface AvailableTable {
  name: string
  rowCount: number
  columns: string[]
  hasGeometry?: boolean
}

const availableTables: AvailableTable[] = [
  { name: 'occurrences', rowCount: 15234, columns: ['id', 'taxon_ref', 'date', 'location'], hasGeometry: true },
  { name: 'taxon', rowCount: 2456, columns: ['id', 'name', 'rank', 'parent_id'] },
  { name: 'plots', rowCount: 567, columns: ['id', 'name', 'area', 'elevation'], hasGeometry: true },
  { name: 'measurements', rowCount: 8901, columns: ['id', 'plot_id', 'dbh', 'height', 'date'] },
  { name: 'shapes', rowCount: 89, columns: ['id', 'name', 'type', 'geometry'], hasGeometry: true },
]

const relationPlugins = [
  { id: 'nested_set', name: 'Nested Set', description: 'Hierarchical tree structure' },
  { id: 'stats_loader', name: 'Statistics Loader', description: 'Load and aggregate statistics' },
  { id: 'direct_attribute', name: 'Direct Attribute', description: 'Direct field mapping' },
]

export function SourceSelector({ sources, onSourcesChange }: SourceSelectorProps) {
  const { t } = useTranslation()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [sourceType, setSourceType] = useState<'table' | 'csv' | 'excel'>('table')
  const [selectedTable, setSelectedTable] = useState('')
  const [groupingField, setGroupingField] = useState('')
  const [relationPlugin, setRelationPlugin] = useState('')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [expandedSources, setExpandedSources] = useState<string[]>([])

  const handleAddSource = () => {
    const newSource: Source = {
      id: String(Date.now()),
      name: sourceType === 'table' ? selectedTable : uploadedFile?.name || '',
      type: sourceType,
      groupingField: groupingField || undefined,
      relation: relationPlugin && relationPlugin !== 'none' ? { plugin: relationPlugin } : undefined,
    }
    onSourcesChange([...sources, newSource])
    setIsDialogOpen(false)
    resetForm()
  }

  const handleRemoveSource = (sourceId: string) => {
    onSourcesChange(sources.filter(s => s.id !== sourceId))
  }

  const resetForm = () => {
    setSelectedTable('')
    setGroupingField('')
    setRelationPlugin('')
    setUploadedFile(null)
    setSourceType('table')
  }

  const toggleSourceExpanded = (sourceId: string) => {
    setExpandedSources(prev =>
      prev.includes(sourceId)
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    )
  }

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'table': return Database
      case 'csv': return FileText
      case 'excel': return FileSpreadsheet
      default: return FileText
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-base font-medium">
            {t('transform.sources.title', 'Data Sources')}
          </h4>
          <p className="text-sm text-muted-foreground">
            {t('transform.sources.description', 'Select tables and files to include in this group')}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setIsDialogOpen(true)}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t('transform.sources.add', 'Add Source')}
        </Button>
      </div>

      {/* Sources List */}
      <div className="space-y-2">
        {sources.map((source) => {
          const Icon = getSourceIcon(source.type)
          const isExpanded = expandedSources.includes(source.id)

          return (
            <Collapsible
              key={source.id}
              open={isExpanded}
              onOpenChange={() => toggleSourceExpanded(source.id)}
            >
              <Card>
                <CollapsibleTrigger className="w-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-muted p-2">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="text-left">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{source.name}</span>
                            <Badge variant="secondary" className="text-xs">
                              {source.type}
                            </Badge>
                          </div>
                          {source.groupingField && (
                            <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                              <span>Grouped by:</span>
                              <code className="rounded bg-muted px-1">{source.groupingField}</code>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <ChevronDown className={cn(
                          'h-4 w-4 transition-transform',
                          isExpanded && 'rotate-180'
                        )} />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRemoveSource(source.id)
                          }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="pt-0">
                    <div className="space-y-2 rounded-lg bg-muted/50 p-3">
                      {source.relation && (
                        <div className="flex items-center gap-2 text-sm">
                          <Link2 className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Relation:</span>
                          <Badge variant="outline">
                            {relationPlugins.find(p => p.id === source.relation?.plugin)?.name}
                          </Badge>
                        </div>
                      )}
                      {source.type === 'table' && (
                        <div className="text-sm">
                          <span className="text-muted-foreground">Table info:</span>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {availableTables.find(t => t.name === source.name)?.rowCount.toLocaleString()} rows
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )
        })}

        {sources.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-6">
              <Database className="h-8 w-8 text-muted-foreground/50" />
              <p className="mt-2 text-sm text-muted-foreground">
                {t('transform.sources.empty', 'No sources added yet')}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Add Source Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('transform.sources.add_title', 'Add Data Source')}</DialogTitle>
            <DialogDescription>
              {t('transform.sources.add_description', 'Select a table or upload a file to use as a data source')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Source Type */}
            <div className="space-y-2">
              <Label>{t('transform.sources.type_label', 'Source Type')}</Label>
              <Select value={sourceType} onValueChange={(v: any) => setSourceType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="table">
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      <span>Database Table</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="csv">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span>CSV File</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="excel">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className="h-4 w-4" />
                      <span>Excel File</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Table Selection */}
            {sourceType === 'table' && (
              <>
                <div className="space-y-2">
                  <Label>{t('transform.sources.table_label', 'Select Table')}</Label>
                  <Select value={selectedTable} onValueChange={setSelectedTable}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a table..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableTables.map((table) => (
                        <SelectItem key={table.name} value={table.name}>
                          <div className="flex items-center justify-between w-full">
                            <div className="flex items-center gap-2">
                              <span>{table.name}</span>
                              {table.hasGeometry && (
                                <Badge variant="secondary" className="text-xs">Spatial</Badge>
                              )}
                            </div>
                            <span className="text-xs text-muted-foreground ml-4">
                              {table.rowCount.toLocaleString()} rows
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Grouping Field */}
                {selectedTable && (
                  <div className="space-y-2">
                    <Label>{t('transform.sources.grouping_label', 'Grouping Field')}</Label>
                    <Select value={groupingField} onValueChange={setGroupingField}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select field to group by..." />
                      </SelectTrigger>
                      <SelectContent>
                        {availableTables
                          .find(t => t.name === selectedTable)
                          ?.columns.map((col) => (
                            <SelectItem key={col} value={col}>
                              {col}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </>
            )}

            {/* File Upload */}
            {(sourceType === 'csv' || sourceType === 'excel') && (
              <div className="space-y-2">
                <Label>{t('transform.sources.file_label', 'Upload File')}</Label>
                <div className="rounded-lg border-2 border-dashed p-4 text-center">
                  <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-2 text-sm text-muted-foreground">
                    {uploadedFile
                      ? uploadedFile.name
                      : t('transform.sources.upload_prompt', 'Click to upload or drag and drop')
                    }
                  </p>
                  <Input
                    type="file"
                    accept={sourceType === 'csv' ? '.csv' : '.xlsx,.xls'}
                    className="mt-2"
                    onChange={(e) => setUploadedFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>
            )}

            {/* Relation Plugin */}
            <div className="space-y-2">
              <Label>{t('transform.sources.relation_label', 'Relation Plugin (Optional)')}</Label>
              <Select value={relationPlugin} onValueChange={setRelationPlugin}>
                <SelectTrigger>
                  <SelectValue placeholder="Select relation type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {relationPlugins.map((plugin) => (
                    <SelectItem key={plugin.id} value={plugin.id}>
                      <div>
                        <div>{plugin.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {plugin.description}
                        </div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button
              onClick={handleAddSource}
              disabled={
                (sourceType === 'table' && !selectedTable) ||
                ((sourceType === 'csv' || sourceType === 'excel') && !uploadedFile)
              }
            >
              {t('common.add', 'Add')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
