/**
 * MarkdownContentField - Reusable markdown content editor with external file support
 *
 * This component allows editing markdown content that is stored in external files
 * rather than inline in the YAML configuration. It supports:
 * - Single file mode (one .md file)
 * - Multilingual mode (separate .fr.md, .en.md files)
 * - Auto-creation of files when content is first edited
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Globe, Save, Loader2, FileText, CheckCircle2 } from 'lucide-react'
import { toast } from 'sonner'
import { MarkdownEditor } from '@/components/site/MarkdownEditor'
import { MultilingualMarkdownEditor } from '@/components/site/MultilingualMarkdownEditor'
import { useFileContent, useUpdateFileContent } from '@/hooks/useSiteConfig'
import { useLanguages } from '@/contexts/LanguageContext'

type ContentMode = 'single' | 'multilingual'

interface MarkdownContentFieldProps {
  /** Base name for the file (e.g., "bibliography" -> templates/content/bibliography.md) */
  baseName: string
  /** Current content_source value from context */
  contentSource?: string | null
  /** Callback when content_source changes */
  onContentSourceChange: (source: string | null) => void
  /** Label for the field */
  label?: string
  /** Description/hint text */
  description?: string
  /** Minimum height for editor */
  minHeight?: string
  /** Placeholder text */
  placeholder?: string
}

export function MarkdownContentField({
  baseName,
  contentSource,
  onContentSourceChange,
  label,
  description,
  minHeight = '200px',
  placeholder,
}: MarkdownContentFieldProps) {
  // Get languages from context
  const { languages, defaultLang } = useLanguages()
  const { t } = useTranslation(['site', 'common'])

  // Determine initial mode from content_source
  const [contentMode, setContentMode] = useState<ContentMode>(() => {
    if (contentSource) {
      // If ends with .md, it's single file mode
      if (/\.md$/i.test(contentSource)) {
        return 'single'
      }
      // Otherwise it's multilingual (base path without extension)
      return 'multilingual'
    }
    return 'single'
  })

  // Generate default file path
  const getDefaultFilePath = useCallback(() => {
    return `templates/content/${baseName}.md`
  }, [baseName])

  const getMultilingualBasePath = useCallback(() => {
    return `templates/content/${baseName}`
  }, [baseName])

  // Current file path for single mode
  const singleFilePath = contentMode === 'single'
    ? (contentSource || getDefaultFilePath())
    : null

  // Fetch file content for single mode
  const { data: fileContentData, isLoading: fileContentLoading } = useFileContent(singleFilePath)
  const updateFileContentMutation = useUpdateFileContent()

  // Local state for editing
  const [editedContent, setEditedContent] = useState<string>('')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Sync content from file
  useEffect(() => {
    if (fileContentData?.content !== undefined) {
      setEditedContent(fileContentData.content)
      setHasUnsavedChanges(false)
    }
  }, [fileContentData?.content])

  // Handle mode change
  const handleContentModeChange = (mode: ContentMode) => {
    setContentMode(mode)
    setHasUnsavedChanges(false)

    if (mode === 'single') {
      const newPath = getDefaultFilePath()
      onContentSourceChange(newPath)
    } else {
      const basePath = getMultilingualBasePath()
      onContentSourceChange(basePath)
    }
  }

  // Handle content change in editor
  const handleContentChange = (content: string) => {
    setEditedContent(content)
    setHasUnsavedChanges(content !== (fileContentData?.content || ''))
  }

  // Save content to file
  const handleSave = async () => {
    if (!singleFilePath) return

    setIsSaving(true)
    try {
      await updateFileContentMutation.mutateAsync({
        path: singleFilePath,
        content: editedContent,
      })
      setHasUnsavedChanges(false)
      toast.success(t('site:pageEditor.fileSaved'), {
        description: singleFilePath,
      })
      // Update content_source if it wasn't set
      if (!contentSource) {
        onContentSourceChange(singleFilePath)
      }
    } catch (error) {
      toast.error(t('site:pageEditor.saveError'), {
        description: String(error),
      })
    } finally {
      setIsSaving(false)
    }
  }

  // Auto-initialize content_source if not set
  useEffect(() => {
    if (contentMode === 'single' && !contentSource) {
      onContentSourceChange(getDefaultFilePath())
    } else if (contentMode === 'multilingual' && !contentSource) {
      onContentSourceChange(getMultilingualBasePath())
    }
  }, [contentMode, contentSource, getDefaultFilePath, getMultilingualBasePath, onContentSourceChange])

  return (
    <div className="space-y-4">
      {/* Header with label and mode toggle */}
      <div className="flex items-center justify-between">
        <div>
          {label && <Label className="text-base font-medium">{label}</Label>}
          {description && (
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          )}
        </div>

        {/* Mode toggle - only show if multiple languages */}
        {languages.length > 1 && (
          <RadioGroup
            value={contentMode}
            onValueChange={(v) => handleContentModeChange(v as ContentMode)}
            className="flex gap-4"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="single" id={`mode-single-${baseName}`} />
              <Label htmlFor={`mode-single-${baseName}`} className="cursor-pointer text-sm">
                <FileText className="h-4 w-4 inline mr-1" />
                {t('site:pageEditor.singleFile')}
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="multilingual" id={`mode-multi-${baseName}`} />
              <Label htmlFor={`mode-multi-${baseName}`} className="cursor-pointer text-sm">
                <Globe className="h-4 w-4 inline mr-1" />
                {t('site:pageEditor.multilingualFiles')}
              </Label>
            </div>
          </RadioGroup>
        )}
      </div>

      {/* File path indicator */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <FileText className="h-3 w-3" />
        <span className="font-mono">
          {contentMode === 'single'
            ? singleFilePath
            : `${getMultilingualBasePath()}.{lang}.md`}
        </span>
        {hasUnsavedChanges && (
          <span className="text-amber-600 font-medium">
            ({t('common:unsavedChanges')})
          </span>
        )}
        {!hasUnsavedChanges && editedContent && (
          <span className="text-green-600 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            {t('common:saved')}
          </span>
        )}
      </div>

      {/* Single file editor */}
      {contentMode === 'single' && (
        <div className="space-y-2">
          {fileContentLoading ? (
            <div className="flex items-center justify-center p-8 border rounded-md bg-muted/30">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <MarkdownEditor
                initialContent={editedContent}
                onChange={handleContentChange}
                placeholder={placeholder || t('site:pageEditor.markdownPlaceholder')}
                className={`min-h-[${minHeight}]`}
              />
              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={!hasUnsavedChanges || isSaving}
                >
                  {isSaving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  {t('site:pageEditor.save')}
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Multilingual editor */}
      {contentMode === 'multilingual' && contentSource && (
        <MultilingualMarkdownEditor
          basePath={contentSource}
          languages={languages}
          defaultLang={defaultLang}
          className={`min-h-[${minHeight}]`}
        />
      )}
    </div>
  )
}

export default MarkdownContentField
