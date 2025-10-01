import { useState } from 'react'
import { FileCode2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { YamlEditor } from '@/components/editors/YamlEditor'
import { useConfig } from '@/hooks/useConfig'
import type { ConfigType } from '@/hooks/useConfig'
import * as yaml from 'js-yaml'
import { toast } from 'sonner'

const CONFIG_TABS: { value: ConfigType; label: string }[] = [
  { value: 'import', label: 'Import' },
  { value: 'transform', label: 'Transform' },
  { value: 'export', label: 'Export' },
]

export function YamlConfigDialog() {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<ConfigType>('import')

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <FileCode2 className="mr-2 h-4 w-4" />
          Edit YAML
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[90vw] h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Configuration Files</DialogTitle>
          <DialogDescription>
            Edit your pipeline configuration files directly. Changes will be validated before saving.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as ConfigType)}
          className="flex-1 flex flex-col overflow-hidden"
        >
          <TabsList className="w-full grid grid-cols-3">
            {CONFIG_TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {CONFIG_TABS.map((tab) => (
            <TabsContent
              key={tab.value}
              value={tab.value}
              className="flex-1 overflow-hidden mt-4"
            >
              <ConfigTabContent configName={tab.value} />
            </TabsContent>
          ))}
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

function ConfigTabContent({ configName }: { configName: ConfigType }) {
  const { config, loading, updateConfig } = useConfig(configName)

  const handleSave = async (yamlContent: string) => {
    try {
      // Parse YAML to validate and convert to JSON
      const content = yaml.load(yamlContent) as Record<string, any>

      const result = await updateConfig({ content, backup: true })
      toast.success('Configuration saved', {
        description: result.backup_path
          ? `Backup created: ${result.backup_path.split('/').pop()}`
          : 'Configuration saved successfully'
      })
    } catch (error) {
      if (error instanceof Error) {
        toast.error('Failed to save configuration', {
          description: error.message
        })
      }
      throw error
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  // Convert config object to YAML string
  const yamlContent = config ? yaml.dump(config, { indent: 2, lineWidth: -1 }) : ''

  return (
    <YamlEditor
      value={yamlContent}
      onSave={handleSave}
      configName={configName}
      showToolbar={true}
      height="calc(90vh - 250px)"
    />
  )
}
