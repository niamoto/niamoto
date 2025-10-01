import { Editor } from '@monaco-editor/react'
import { useEffect, useState } from 'react'
import { useTheme } from '@/hooks/use-theme'
import * as yaml from 'js-yaml'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { AlertCircle, Save, Undo2, History } from 'lucide-react'

interface YamlEditorProps {
  value: string
  onChange?: (value: string) => void
  onSave?: (value: string) => Promise<void>
  readOnly?: boolean
  height?: string
  showToolbar?: boolean
  showBackupRestore?: boolean
  onRestore?: () => void
  canRestore?: boolean
  configName?: string
}

export function YamlEditor({
  value: initialValue,
  onChange,
  onSave,
  readOnly = false,
  height = '600px',
  showToolbar = true,
  showBackupRestore = false,
  onRestore,
  canRestore = false,
  configName,
}: YamlEditorProps) {
  const { theme } = useTheme()
  const [editorValue, setEditorValue] = useState(initialValue)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    setEditorValue(initialValue)
    setHasChanges(false)
  }, [initialValue])

  const validateYaml = (yamlString: string): boolean => {
    try {
      yaml.load(yamlString)
      setError(null)
      return true
    } catch (e) {
      if (e instanceof Error) {
        setError(`YAML syntax error: ${e.message}`)
      } else {
        setError('Invalid YAML syntax')
      }
      return false
    }
  }

  const handleEditorChange = (value: string | undefined) => {
    const newValue = value || ''
    setEditorValue(newValue)
    setHasChanges(newValue !== initialValue)

    // Validate YAML syntax
    if (newValue.trim()) {
      validateYaml(newValue)
    } else {
      setError(null)
    }

    // Notify parent
    if (onChange) {
      onChange(newValue)
    }
  }

  const handleSave = async () => {
    if (!onSave) return

    // Validate before saving
    if (!validateYaml(editorValue)) {
      return
    }

    setIsSaving(true)
    try {
      await onSave(editorValue)
      setHasChanges(false)
    } catch (e) {
      if (e instanceof Error) {
        setError(`Save error: ${e.message}`)
      } else {
        setError('Failed to save configuration')
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleRevert = () => {
    setEditorValue(initialValue)
    setHasChanges(false)
    setError(null)
  }

  return (
    <div className="flex flex-col gap-3">
      {showToolbar && (
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {configName && (
              <div className="text-sm font-medium text-muted-foreground">
                {configName}.yml
              </div>
            )}
            {hasChanges && (
              <span className="text-xs text-amber-600 dark:text-amber-400">
                Unsaved changes
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {showBackupRestore && onRestore && canRestore && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRestore}
                disabled={isSaving}
              >
                <History className="h-4 w-4 mr-2" />
                Restore Backup
              </Button>
            )}
            {hasChanges && !readOnly && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRevert}
                disabled={isSaving}
              >
                <Undo2 className="h-4 w-4 mr-2" />
                Revert
              </Button>
            )}
            {onSave && !readOnly && (
              <Button
                onClick={handleSave}
                disabled={isSaving || !hasChanges || !!error}
                size="sm"
              >
                <Save className="h-4 w-4 mr-2" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            )}
          </div>
        </div>
      )}

      {error && (
        <Alert variant="destructive" className="flex items-start gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5" />
          <div className="flex-1 text-sm">{error}</div>
        </Alert>
      )}

      <Card className="overflow-hidden">
        <Editor
          height={height}
          defaultLanguage="yaml"
          value={editorValue}
          onChange={handleEditorChange}
          theme={theme === 'dark' ? 'vs-dark' : 'light'}
          options={{
            readOnly,
            minimap: { enabled: true },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            wrappingIndent: 'indent',
            automaticLayout: true,
            tabSize: 2,
            insertSpaces: true,
            formatOnPaste: true,
            formatOnType: true,
          }}
        />
      </Card>
    </div>
  )
}
