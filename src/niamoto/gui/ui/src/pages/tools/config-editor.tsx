import { useState, useEffect } from 'react'
import { FileCode2, History, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { YamlEditor } from '@/components/editors/YamlEditor'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert } from '@/components/ui/alert'
import { useConfig } from '@/hooks/useConfig'
import type { ConfigType } from '@/hooks/useConfig'
import * as yaml from 'js-yaml'
import { toast } from 'sonner'

const CONFIG_TABS: { value: ConfigType; label: string; description: string }[] = [
  {
    value: 'config',
    label: 'Main Config',
    description: 'Project and database configuration'
  },
  {
    value: 'import',
    label: 'Import',
    description: 'Data import sources configuration'
  },
  {
    value: 'transform',
    label: 'Transform',
    description: 'Data transformation pipeline'
  },
  {
    value: 'export',
    label: 'Export',
    description: 'Static site export configuration'
  },
]

interface BackupInfo {
  filename: string
  path: string
  size: number
  modified: string
}

function ConfigTab({ configName }: { configName: ConfigType }) {
  const { config, loading, error, updateConfig, listBackups, restoreBackup } = useConfig(configName)
  const [showBackupDialog, setShowBackupDialog] = useState(false)
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [loadingBackups, setLoadingBackups] = useState(false)

  useEffect(() => {
    if (showBackupDialog) {
      setLoadingBackups(true)
      listBackups().then((data) => {
        setBackups(data.backups || [])
        setLoadingBackups(false)
      })
    }
  }, [showBackupDialog, listBackups])

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
    } catch (err) {
      if (err instanceof Error) {
        toast.error('Failed to save configuration', {
          description: err.message
        })
      }
      throw err
    }
  }

  const handleRestore = async (backupFilename: string) => {
    try {
      await restoreBackup(backupFilename)
      toast.success('Configuration restored', {
        description: `Restored from ${backupFilename}`
      })
      setShowBackupDialog(false)
    } catch (err) {
      if (err instanceof Error) {
        toast.error('Failed to restore configuration', {
          description: err.message
        })
      }
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading configuration...</div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <div className="ml-2">
          Failed to load configuration: {error}
        </div>
      </Alert>
    )
  }

  // Convert config object to YAML string
  const yamlContent = config ? yaml.dump(config, { indent: 2, lineWidth: -1 }) : ''

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">{configName}.yml</h3>
          <p className="text-sm text-muted-foreground">
            Edit your {configName} configuration. Changes are automatically backed up.
          </p>
        </div>
        <Dialog open={showBackupDialog} onOpenChange={setShowBackupDialog}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm">
              <History className="h-4 w-4 mr-2" />
              View Backups ({backups?.length || 0})
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Configuration Backups</DialogTitle>
              <DialogDescription>
                Select a backup to restore. Current configuration will be backed up automatically.
              </DialogDescription>
            </DialogHeader>
            <ScrollArea className="h-96">
              {loadingBackups ? (
                <div className="flex items-center justify-center h-32 text-muted-foreground">
                  Loading backups...
                </div>
              ) : backups && backups.length > 0 ? (
                <div className="space-y-2 pr-4">
                  {backups.map((backup: BackupInfo) => (
                    <Card key={backup.filename} className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium font-mono">{backup.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(backup.modified).toLocaleString()}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Size: {(backup.size / 1024).toFixed(2)} KB
                          </p>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => handleRestore(backup.filename)}
                        >
                          Restore
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-32 text-muted-foreground">
                  No backups available
                </div>
              )}
            </ScrollArea>
          </DialogContent>
        </Dialog>
      </div>

      <YamlEditor
        value={yamlContent}
        onSave={handleSave}
        configName={configName}
        showToolbar={true}
        height="calc(100vh - 350px)"
      />
    </div>
  )
}

export function ConfigEditor() {
  const [activeTab, setActiveTab] = useState<ConfigType>('config')

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FileCode2 className="h-8 w-8" />
            <h1 className="text-3xl font-bold tracking-tight">
              Configuration Editor
            </h1>
          </div>
          <p className="text-muted-foreground">
            Edit your Niamoto configuration files with automatic backup and restore functionality
          </p>
        </div>
      </div>

      {/* Info Alert */}
      <Alert>
        <CheckCircle2 className="h-4 w-4" />
        <div className="ml-2 space-y-1">
          <p className="font-medium">Automatic Backups</p>
          <p className="text-sm text-muted-foreground">
            Every time you save a configuration, a backup is automatically created.
            You can restore previous versions at any time from the backup list.
          </p>
        </div>
      </Alert>

      {/* Configuration Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration Files</CardTitle>
          <CardDescription>
            Select a configuration file to edit
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ConfigType)}>
            <TabsList className="grid w-full grid-cols-4">
              {CONFIG_TABS.map((tab) => (
                <TabsTrigger key={tab.value} value={tab.value}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>

            {CONFIG_TABS.map((tab) => (
              <TabsContent key={tab.value} value={tab.value} className="mt-6">
                <div className="mb-4 p-4 bg-muted/50 rounded-lg">
                  <p className="text-sm text-muted-foreground">{tab.description}</p>
                </div>
                <ConfigTab configName={tab.value} />
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
