/**
 * WidgetConfigYamlEditor - YAML editor for widget configurations
 *
 * Wraps the base YamlEditor with:
 * - Class object suggestions sidebar
 * - Validation feedback
 * - Preview integration
 */
import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Editor } from '@monaco-editor/react'
import { useTheme } from '@/hooks/use-theme'
import * as yaml from 'js-yaml'
import { cn } from '@/lib/utils'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  AlertCircle,
  Save,
  Undo2,
  Copy,
  Check,
  FileCode,
  Sparkles,
} from 'lucide-react'
import type { ClassObjectSuggestion } from '@/lib/api/widget-suggestions'
import { CATEGORY_INFO } from '@/lib/api/widget-suggestions'

interface WidgetConfigYamlEditorProps {
  value: string
  onChange?: (value: string) => void
  onSave?: (value: string) => Promise<void>
  classObjects?: ClassObjectSuggestion[]
  widgetName?: string
  readOnly?: boolean
  height?: string
}

export function WidgetConfigYamlEditor({
  value: initialValue,
  onChange,
  onSave,
  classObjects = [],
  widgetName,
  readOnly = false,
  height = '400px',
}: WidgetConfigYamlEditorProps) {
  const { t } = useTranslation('common')
  const { theme } = useTheme()
  const [editorValue, setEditorValue] = useState(initialValue)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [copiedName, setCopiedName] = useState<string | null>(null)

  // Group class_objects by category for quick reference
  const groupedClassObjects = useMemo(() => {
    const groups: Record<string, ClassObjectSuggestion[]> = {}
    classObjects.forEach((co) => {
      if (!groups[co.category]) {
        groups[co.category] = []
      }
      groups[co.category].push(co)
    })
    return groups
  }, [classObjects])

  const validateYaml = (yamlString: string): boolean => {
    try {
      yaml.load(yamlString)
      setError(null)
      return true
    } catch (e) {
      if (e instanceof Error) {
        setError(`Erreur YAML: ${e.message}`)
      } else {
        setError('Syntaxe YAML invalide')
      }
      return false
    }
  }

  const handleEditorChange = (value: string | undefined) => {
    const newValue = value || ''
    setEditorValue(newValue)
    setHasChanges(newValue !== initialValue)

    if (newValue.trim()) {
      validateYaml(newValue)
    } else {
      setError(null)
    }

    if (onChange) {
      onChange(newValue)
    }
  }

  const handleSave = async () => {
    if (!onSave) return
    if (!validateYaml(editorValue)) return

    setIsSaving(true)
    try {
      await onSave(editorValue)
      setHasChanges(false)
    } catch (e) {
      if (e instanceof Error) {
        setError(`Erreur: ${e.message}`)
      } else {
        setError('Echec de la sauvegarde')
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

  const copyToClipboard = (name: string) => {
    navigator.clipboard.writeText(name)
    setCopiedName(name)
    setTimeout(() => setCopiedName(null), 1500)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 p-2 border-b">
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4 text-muted-foreground" />
          {widgetName && (
            <span className="text-sm font-medium">{widgetName}</span>
          )}
          {hasChanges && (
            <Badge variant="outline" className="text-amber-600">
              Modifie
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && !readOnly && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRevert}
              disabled={isSaving}
            >
              <Undo2 className="h-3.5 w-3.5 mr-1" />
              Annuler
            </Button>
          )}
          {onSave && !readOnly && (
            <Button
              onClick={handleSave}
              disabled={isSaving || !hasChanges || !!error}
              size="sm"
            >
              <Save className="h-3.5 w-3.5 mr-1" />
              {isSaving ? t('status.saving') : t('actions.save')}
            </Button>
          )}
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <Alert variant="destructive" className="m-2 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5" />
          <div className="flex-1 text-sm">{error}</div>
        </Alert>
      )}

      {/* Main content */}
      <div className="flex-1 flex min-h-0">
        {/* Editor */}
        <div className="flex-1 min-w-0">
          <Editor
            height={height}
            defaultLanguage="yaml"
            value={editorValue}
            onChange={handleEditorChange}
            theme={theme === 'dark' ? 'vs-dark' : 'light'}
            options={{
              readOnly,
              minimap: { enabled: false },
              fontSize: 12,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              wrappingIndent: 'indent',
              automaticLayout: true,
              tabSize: 2,
              insertSpaces: true,
            }}
          />
        </div>

        {/* Class objects sidebar */}
        {classObjects.length > 0 && (
          <div className="w-56 border-l flex flex-col bg-muted/20">
            <div className="p-2 border-b">
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Sparkles className="h-3 w-3" />
                Class objects
              </div>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-3">
                {Object.entries(groupedClassObjects).map(([category, items]) => {
                  const info = CATEGORY_INFO[category as keyof typeof CATEGORY_INFO]
                  return (
                    <div key={category}>
                      <div className="text-[10px] font-medium text-muted-foreground mb-1 uppercase tracking-wider">
                        {info?.label || category}
                      </div>
                      <div className="space-y-0.5">
                        {items.slice(0, 10).map((co) => (
                          <button
                            key={co.name}
                            onClick={() => copyToClipboard(co.name)}
                            className={cn(
                              'w-full flex items-center gap-1.5 px-1.5 py-1 rounded text-left',
                              'hover:bg-muted/50 transition-colors',
                              'text-xs font-mono truncate'
                            )}
                            title={co.name}
                          >
                            {copiedName === co.name ? (
                              <Check className="h-3 w-3 text-emerald-500 flex-shrink-0" />
                            ) : (
                              <Copy className="h-3 w-3 text-muted-foreground/50 flex-shrink-0" />
                            )}
                            <span className="truncate">{co.name}</span>
                          </button>
                        ))}
                        {items.length > 10 && (
                          <div className="text-[10px] text-muted-foreground pl-5">
                            +{items.length - 10} autres
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  )
}

export default WidgetConfigYamlEditor
