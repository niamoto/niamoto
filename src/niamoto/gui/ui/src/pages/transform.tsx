import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Settings, Play, Save, AlertCircle } from 'lucide-react'
import { GroupManager, type Group } from '@/components/transform/GroupManager'
import { SourceSelector } from '@/components/transform/SourceSelector'
import { PluginCatalog } from '@/components/transform/PluginCatalog'
import { PipelineCanvas } from '@/components/transform/PipelineCanvas'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export function TransformPage() {
  const { t } = useTranslation()
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null)
  const [activeTab, setActiveTab] = useState('groups')

  const handleGroupSelect = (group: Group) => {
    setSelectedGroup(group)
    setActiveTab('sources')
  }

  const handleSourcesChange = (sources: any[]) => {
    if (selectedGroup) {
      setSelectedGroup({
        ...selectedGroup,
        sources,
      })
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('transform.title', 'Data Transformation')}
          </h1>
          <p className="text-muted-foreground">
            {t('transform.description', 'Configure how your data is aggregated and transformed for analysis')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Save className="mr-2 h-4 w-4" />
            {t('common.save', 'Save')}
          </Button>
          <Button>
            <Play className="mr-2 h-4 w-4" />
            {t('transform.run', 'Run Transform')}
          </Button>
        </div>
      </div>

      {/* Alert for selected group */}
      {selectedGroup && (
        <Alert>
          <Settings className="h-4 w-4" />
          <AlertTitle>{t('transform.working_on', 'Working on')}: {selectedGroup.displayName}</AlertTitle>
          <AlertDescription>
            {t('transform.group_description', 'Configure sources and transformations for this analysis group')}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="groups">
            {t('transform.tabs.groups', 'Groups')}
            {selectedGroup && <span className="ml-2 text-xs">✓</span>}
          </TabsTrigger>
          <TabsTrigger value="sources" disabled={!selectedGroup}>
            {t('transform.tabs.sources', 'Sources')}
            {selectedGroup && selectedGroup.sources.length > 0 && (
              <span className="ml-2 text-xs">({selectedGroup.sources.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="pipeline" disabled={!selectedGroup}>
            {t('transform.tabs.pipeline', 'Pipeline')}
          </TabsTrigger>
          <TabsTrigger value="preview" disabled={!selectedGroup}>
            {t('transform.tabs.preview', 'Preview')}
          </TabsTrigger>
        </TabsList>

        {/* Groups Tab */}
        <TabsContent value="groups" className="mt-6">
          <GroupManager
            onGroupSelect={handleGroupSelect}
            selectedGroupId={selectedGroup?.id}
          />
        </TabsContent>

        {/* Sources Tab */}
        <TabsContent value="sources" className="mt-6">
          {selectedGroup ? (
            <div className="space-y-6">
              <div className="rounded-lg bg-muted/50 p-4">
                <h3 className="font-medium">
                  {t('transform.sources.group_context', 'Configuring sources for')}: {selectedGroup.displayName}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedGroup.description}
                </p>
              </div>
              <SourceSelector
                sources={selectedGroup.sources}
                onSourcesChange={handleSourcesChange}
                groupName={selectedGroup.name}
              />
            </div>
          ) : (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{t('transform.no_group', 'No group selected')}</AlertTitle>
              <AlertDescription>
                {t('transform.select_group_first', 'Please select a group from the Groups tab first')}
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        {/* Pipeline Tab */}
        <TabsContent value="pipeline" className="mt-6">
          {selectedGroup ? (
            <div className="space-y-4">
              <div className="rounded-lg bg-muted/50 p-4">
                <h3 className="font-medium">
                  {t('transform.pipeline.group_context', 'Building pipeline for')}: {selectedGroup.displayName}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {t('transform.pipeline.instructions', 'Drag plugins from the catalog to build your transformation pipeline')}
                </p>
              </div>
              <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
                <PluginCatalog compact onPluginDragStart={(plugin) => console.log('Dragging:', plugin)} />
                <PipelineCanvas
                  sources={selectedGroup.sources}
                  onPipelineChange={(nodes, edges) => console.log('Pipeline changed:', { nodes, edges })}
                />
              </div>
            </div>
          ) : (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{t('transform.no_group', 'No group selected')}</AlertTitle>
              <AlertDescription>
                {t('transform.select_group_first', 'Please select a group from the Groups tab first')}
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        {/* Preview Tab (Placeholder) */}
        <TabsContent value="preview" className="mt-6">
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4" />
              <p className="text-lg font-medium">
                {t('transform.preview.coming_soon', 'Preview Coming Soon')}
              </p>
              <p className="text-sm mt-2">
                {t('transform.preview.description', 'Preview transformed data before saving')}
              </p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
