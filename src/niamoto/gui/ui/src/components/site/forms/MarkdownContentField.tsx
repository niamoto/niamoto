/**
 * MarkdownContentField - Reusable markdown content editor with external file support
 *
 * This component allows editing markdown content that is stored in external files
 * rather than inline in the YAML configuration. It supports:
 * - File selector (dropdown of .md files in templates/content/)
 * - Upload button for importing .md files
 * - View modes: preview (readOnly), raw code, edit (full WYSIWYG editor)
 * - Single file mode (one .md file)
 * - Multilingual mode (separate .fr.md, .en.md files)
 * - Auto-creation of files when content is first edited
 */

import { lazy, Suspense, useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Globe, Save, Loader2, FileText, Upload, Edit3, Code, FileType, X } from 'lucide-react'
import { toast } from 'sonner'
import { useFileContent, useUpdateFileContent, useProjectFiles, useUploadFile } from '@/hooks/useSiteConfig'
import { useLanguages } from '@/contexts/LanguageContext'

const MarkdownEditor = lazy(() =>
  import('@/components/site/MarkdownEditor').then((module) => ({
    default: module.MarkdownEditor,
  }))
)
const MultilingualMarkdownEditor = lazy(() =>
  import('@/components/site/MultilingualMarkdownEditor').then((module) => ({
    default: module.MultilingualMarkdownEditor,
  }))
)

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
      if (/\.md$/i.test(contentSource)) {
        return 'single'
      }
      return 'multilingual'
    }
    return 'single'
  })

  // View mode state
  const [isEditing, setIsEditing] = useState(false)
  const [showRawContent, setShowRawContent] = useState(false)

  // File upload ref
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Generate default file path
  const getDefaultFilePath = useCallback(() => {
    return `templates/content/${baseName}.md`
  }, [baseName])

  const getMultilingualBasePath = useCallback(() => {
    return `templates/content/${baseName}`
  }, [baseName])

  // Current file path for single mode — only fetch if contentSource is explicitly set
  const singleFilePath = contentMode === 'single' && contentSource
    ? contentSource
    : null

  // Fetch file content for single mode
  const { data: fileContentData, isLoading: fileContentLoading } = useFileContent(singleFilePath)
  const updateFileContentMutation = useUpdateFileContent()

  // Fetch markdown files from templates/content/ folder
  const { data: filesData, isLoading: filesLoading, refetch: refetchFiles } = useProjectFiles('templates/content')
  const uploadMutation = useUploadFile()

  // Filter markdown files
  const markdownFiles =
    filesData?.files.filter((f) => ['.md', '.markdown', '.txt'].includes(f.extension)) ?? []

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
    setIsEditing(false)

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
      setIsEditing(false)
      toast.success(t('site:pageEditor.fileSaved'), {
        description: singleFilePath,
      })
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

  // Cancel editing
  const handleCancelEdit = () => {
    setEditedContent(fileContentData?.content || '')
    setIsEditing(false)
    setHasUnsavedChanges(false)
  }

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await uploadMutation.mutateAsync({ file, folder: 'templates/content' })
      await refetchFiles()
      onContentSourceChange(result.path)
      setIsEditing(false)
      toast.success(t('site:pageEditor.fileUploaded'), {
        description: result.filename,
      })
    } catch (err) {
      toast.error(t('site:pageEditor.uploadError'), {
        description: err instanceof Error ? err.message : t('site:pageEditor.uploadFailed'),
      })
    }
    e.target.value = ''
  }

  // Note: we no longer auto-initialize content_source.
  // It stays null until the user explicitly selects or creates a file.
  const editorFallback = (
    <div className="flex items-center justify-center p-8 border rounded-md bg-muted/30">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )

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

      {/* Single file mode */}
      {contentMode === 'single' && (
        <div className="space-y-4">
          {/* Source file selector */}
          <div className="space-y-2">
            <Label>{t('site:pageEditor.sourceFile')}</Label>
            <div className="flex gap-2">
              {markdownFiles.length === 0 && !filesLoading ? (
                <div className="flex-1 flex items-center">
                  <p className="text-sm text-muted-foreground">
                    {t('site:pageEditor.noFilesIn')}
                  </p>
                </div>
              ) : (
                <Select
                  value={contentSource || ''}
                  onValueChange={(v) => {
                    onContentSourceChange(v || null)
                    setIsEditing(false)
                  }}
                  disabled={filesLoading}
                >
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder={t('site:pageEditor.selectFile')} />
                  </SelectTrigger>
                  <SelectContent>
                    {markdownFiles.map((f) => (
                      <SelectItem key={f.path} value={f.path}>
                        {f.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".md,.markdown,.txt"
                onChange={handleFileUpload}
                className="hidden"
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMutation.isPending}
                title={t('site:pageEditor.uploadMarkdown')}
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
              </Button>
              {contentSource && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    onContentSourceChange(null)
                    setIsEditing(false)
                    setEditedContent('')
                    setHasUnsavedChanges(false)
                  }}
                  title={t('site:pageEditor.clearFile')}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {t('site:pageEditor.mdFileIn')}
            </p>
          </div>

          {/* File content preview/edit */}
          {singleFilePath && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{t('site:pageEditor.fileContent')}</Label>
                <div className="flex gap-2">
                  {isEditing ? (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleCancelEdit}
                      >
                        {t('site:pageEditor.cancel')}
                      </Button>
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
                    </>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowRawContent(!showRawContent)}
                        title={showRawContent ? t('site:pageEditor.viewFormatted') : t('site:pageEditor.viewCode')}
                      >
                        {showRawContent ? (
                          <FileType className="h-4 w-4" />
                        ) : (
                          <Code className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsEditing(true)}
                        disabled={fileContentLoading}
                      >
                        <Edit3 className="mr-2 h-4 w-4" />
                        {t('site:pageEditor.edit')}
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {fileContentLoading ? (
                <div className="flex items-center justify-center p-8 border rounded-md bg-muted/30">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : isEditing ? (
                <Suspense fallback={editorFallback}>
                  <MarkdownEditor
                    initialContent={fileContentData?.content ?? editedContent}
                    onChange={handleContentChange}
                    placeholder={placeholder || t('site:pageEditor.markdownPlaceholder')}
                    className={`min-h-[${minHeight}]`}
                  />
                </Suspense>
              ) : showRawContent ? (
                <div className="border rounded-md bg-muted/30 p-4 max-h-[400px] overflow-auto">
                  <pre className="text-sm whitespace-pre-wrap font-mono text-muted-foreground">
                    {editedContent || fileContentData?.content || t('site:pageEditor.noContent')}
                  </pre>
                </div>
              ) : (
                <div className="max-h-[400px] overflow-auto">
                  <Suspense fallback={editorFallback}>
                    <MarkdownEditor
                      key={editedContent}
                      initialContent={editedContent || fileContentData?.content || ''}
                      readOnly
                      className="border-muted/50"
                    />
                  </Suspense>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Multilingual editor */}
      {contentMode === 'multilingual' && contentSource && (
        <Suspense fallback={editorFallback}>
          <MultilingualMarkdownEditor
            basePath={contentSource}
            languages={languages}
            defaultLang={defaultLang}
            className={`min-h-[${minHeight}]`}
          />
        </Suspense>
      )}
    </div>
  )
}

export default MarkdownContentField
