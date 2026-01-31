import { useCallback, useState, useEffect } from 'react'
import Editor, { type OnMount, type OnChange } from '@monaco-editor/react'
import type { editor, Position } from 'monaco-editor'
import * as yaml from 'js-yaml'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { AlertCircle, CheckCircle2, Copy, FileCode2 } from 'lucide-react'

interface YamlEditorProps {
  value: string
  onChange: (value: string) => void
  onValidChange?: (parsed: unknown, valid: boolean) => void
  height?: string
  className?: string
  readOnly?: boolean
  templates?: YamlTemplate[]
}

export interface YamlTemplate {
  id: string
  label: string
  description: string
  content: string
}

interface ValidationState {
  valid: boolean
  error?: string
  parsed?: unknown
}

export function YamlEditor({
  value,
  onChange,
  onValidChange,
  height = '400px',
  className,
  readOnly = false,
  templates = [],
}: YamlEditorProps) {
  const [validation, setValidation] = useState<ValidationState>({ valid: true })
  const [copied, setCopied] = useState(false)

  // Validate YAML on change
  const validateYaml = useCallback(
    (content: string) => {
      try {
        const parsed = yaml.load(content)
        setValidation({ valid: true, parsed })
        onValidChange?.(parsed, true)
      } catch (e) {
        const error = e instanceof Error ? e.message : 'Invalid YAML'
        setValidation({ valid: false, error })
        onValidChange?.(null, false)
      }
    },
    [onValidChange]
  )

  // Validate on initial load
  useEffect(() => {
    if (value) {
      validateYaml(value)
    }
  }, [])

  const handleEditorMount: OnMount = (editor, monaco) => {
    // Configure YAML language
    monaco.languages.registerCompletionItemProvider('yaml', {
      provideCompletionItems: (model: editor.ITextModel, position: Position) => {
        const word = model.getWordUntilPosition(position)
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }

        // Plugin suggestions
        const pluginSuggestions = [
          'class_object_field_aggregator',
          'class_object_binary_aggregator',
          'class_object_series_extractor',
          'class_object_categories_extractor',
          'class_object_series_ratio_aggregator',
          'class_object_categories_mapper',
          'class_object_series_matrix_extractor',
          'class_object_series_by_axis_extractor',
          'field_aggregator',
          'geospatial_extractor',
          'top_ranking',
          'binary_counter',
          'binned_distribution',
          'statistical_summary',
          'bar_plot',
          'donut_chart',
          'info_grid',
          'radial_gauge',
          'interactive_map',
        ].map((plugin) => ({
          label: plugin,
          kind: monaco.languages.CompletionItemKind.Value,
          insertText: plugin,
          range,
        }))

        // Key suggestions
        const keySuggestions = [
          { label: 'plugin', detail: 'Plugin name' },
          { label: 'params', detail: 'Plugin parameters' },
          { label: 'source', detail: 'Data source' },
          { label: 'class_object', detail: 'Class object name' },
          { label: 'orientation', detail: 'h or v' },
          { label: 'title', detail: 'Widget title' },
          { label: 'layout', detail: 'Layout config' },
          { label: 'colspan', detail: 'Column span' },
          { label: 'order', detail: 'Display order' },
        ].map((item) => ({
          label: item.label,
          kind: monaco.languages.CompletionItemKind.Property,
          insertText: `${item.label}: `,
          detail: item.detail,
          range,
        }))

        return { suggestions: [...pluginSuggestions, ...keySuggestions] }
      },
    })

    // Set editor options
    editor.updateOptions({
      minimap: { enabled: false },
      lineNumbers: 'on',
      folding: true,
      tabSize: 2,
      insertSpaces: true,
      wordWrap: 'on',
      scrollBeyondLastLine: false,
    })
  }

  const handleChange: OnChange = (newValue) => {
    const content = newValue ?? ''
    onChange(content)
    validateYaml(content)
  }

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [value])

  const handleTemplateClick = useCallback(
    (template: YamlTemplate) => {
      onChange(template.content)
      validateYaml(template.content)
    },
    [onChange, validateYaml]
  )

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      {/* Templates bar */}
      {templates.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-muted-foreground self-center mr-2">Templates:</span>
          {templates.map((template) => (
            <Button
              key={template.id}
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => handleTemplateClick(template)}
              title={template.description}
            >
              <FileCode2 className="h-3 w-3 mr-1" />
              {template.label}
            </Button>
          ))}
        </div>
      )}

      {/* Editor */}
      <div className="relative border rounded-md overflow-hidden">
        <Editor
          height={height}
          defaultLanguage="yaml"
          value={value}
          onChange={handleChange}
          onMount={handleEditorMount}
          theme="vs-dark"
          options={{
            readOnly,
            fontSize: 13,
            fontFamily: 'JetBrains Mono, Menlo, Monaco, monospace',
          }}
        />

        {/* Copy button */}
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-7 opacity-70 hover:opacity-100"
          onClick={handleCopy}
        >
          {copied ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Validation status */}
      <div
        className={cn(
          'flex items-center gap-2 text-sm px-2 py-1 rounded',
          validation.valid
            ? 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30'
            : 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30'
        )}
      >
        {validation.valid ? (
          <>
            <CheckCircle2 className="h-4 w-4" />
            <span>YAML valide</span>
          </>
        ) : (
          <>
            <AlertCircle className="h-4 w-4" />
            <span className="truncate">{validation.error}</span>
          </>
        )}
      </div>
    </div>
  )
}
