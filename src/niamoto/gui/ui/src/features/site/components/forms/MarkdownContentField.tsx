/**
 * MarkdownContentField - Reusable markdown content editor with external file support
 *
 * This component allows editing markdown content that is stored in external files
 * rather than inline in the YAML configuration.
 */

import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronDown,
  Code,
  FileText,
  Globe,
  Loader2,
  Save,
  Settings2,
  Upload,
  X,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { cn } from '@/lib/utils'
import {
  useFileContent,
  useProjectFiles,
  useUpdateFileContent,
  useUploadFile,
} from '@/shared/hooks/useSiteConfig'
import { useLanguages } from '@/shared/contexts/useLanguages'

const MarkdownEditor = lazy(() =>
  import('@/features/site/components/MarkdownEditor').then((module) => ({
    default: module.MarkdownEditor,
  }))
)

const MultilingualMarkdownEditor = lazy(() =>
  import('@/features/site/components/MultilingualMarkdownEditor').then((module) => ({
    default: module.MultilingualMarkdownEditor,
  }))
)

type ContentMode = 'single' | 'multilingual'
type ViewMode = 'write' | 'source'
type MarkdownContentFieldVariant = 'default' | 'authoring'

interface MarkdownContentFieldProps {
  baseName: string
  contentSource?: string | null
  onContentSourceChange: (source: string | null) => void
  label?: string
  description?: string
  minHeight?: string
  placeholder?: string
  variant?: MarkdownContentFieldVariant
}

function getInitialContentMode(contentSource?: string | null): ContentMode {
  if (!contentSource) {
    return 'single'
  }
  return /\.md$/i.test(contentSource) ? 'single' : 'multilingual'
}

function getSourceSummary(contentMode: ContentMode, contentSource?: string | null): string | null {
  if (!contentSource) {
    return null
  }

  const lastSegment = contentSource.split('/').pop() ?? contentSource
  if (contentMode === 'multilingual') {
    return `${lastSegment}.[lang].md`
  }
  return lastSegment
}

export function MarkdownContentField({
  baseName,
  contentSource,
  onContentSourceChange,
  label,
  description,
  minHeight = '200px',
  placeholder,
  variant = 'default',
}: MarkdownContentFieldProps) {
  const { languages, defaultLang } = useLanguages()
  const { t } = useTranslation(['site', 'common'])

  const [contentMode, setContentMode] = useState<ContentMode>(() =>
    getInitialContentMode(contentSource)
  )
  const [viewMode, setViewMode] = useState<ViewMode>('write')
  const [sourceControlsOpen, setSourceControlsOpen] = useState(!contentSource)
  const [editedContent, setEditedContent] = useState('')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const previousSingleFilePathRef = useRef<string | null>(null)
  const hasUnsavedChangesRef = useRef(false)

  const getDefaultFilePath = useCallback(() => `templates/content/${baseName}.md`, [baseName])
  const getMultilingualBasePath = useCallback(() => `templates/content/${baseName}`, [baseName])

  const singleFilePath = contentMode === 'single' && contentSource ? contentSource : null
  const sourceSummary = useMemo(
    () => getSourceSummary(contentMode, contentSource),
    [contentMode, contentSource]
  )

  const {
    data: fileContentData,
    error: fileContentError,
    isLoading: fileContentLoading,
  } = useFileContent(singleFilePath)
  const updateFileContentMutation = useUpdateFileContent()
  const { data: filesData, isLoading: filesLoading, refetch: refetchFiles } =
    useProjectFiles('templates/content')
  const uploadMutation = useUploadFile()

  const markdownFiles =
    filesData?.files.filter((file) => ['.md', '.markdown', '.txt'].includes(file.extension)) ?? []

  useEffect(() => {
    if (contentSource) {
      setContentMode(getInitialContentMode(contentSource))
    }
  }, [contentSource])

  const resetSingleFileDraft = useCallback((content = '') => {
    setEditedContent(content)
    setHasUnsavedChanges(false)
    setIsSaving(false)
  }, [])

  useEffect(() => {
    hasUnsavedChangesRef.current = hasUnsavedChanges
  }, [hasUnsavedChanges])

  useEffect(() => {
    const previousPath = previousSingleFilePathRef.current
    const pathChanged = previousPath !== singleFilePath
    previousSingleFilePathRef.current = singleFilePath

    if (!singleFilePath) {
      resetSingleFileDraft()
      return
    }

    if (pathChanged) {
      resetSingleFileDraft(fileContentData?.content ?? '')
      setViewMode('write')
      return
    }

    if (!hasUnsavedChangesRef.current && fileContentData?.content !== undefined) {
      setEditedContent(fileContentData.content)
    }
  }, [
    fileContentData?.content,
    resetSingleFileDraft,
    singleFilePath,
  ])

  useEffect(() => {
    if (!contentSource) {
      setSourceControlsOpen(true)
    }
  }, [contentSource])

  const handleContentModeChange = (mode: ContentMode) => {
    setContentMode(mode)
    setViewMode('write')
    resetSingleFileDraft()
    setSourceControlsOpen(false)

    if (mode === 'single') {
      onContentSourceChange(getDefaultFilePath())
      return
    }

    onContentSourceChange(getMultilingualBasePath())
  }

  const handleContentChange = (content: string) => {
    setEditedContent(content)
    setHasUnsavedChanges(content !== (fileContentData?.content || ''))
  }

  const handleSave = async () => {
    if (!singleFilePath) {
      return
    }

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
    } catch (error) {
      toast.error(t('site:pageEditor.saveError'), {
        description: String(error),
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancelEdit = () => {
    setEditedContent(fileContentData?.content || '')
    setHasUnsavedChanges(false)
    setViewMode('write')
  }

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    try {
      const result = await uploadMutation.mutateAsync({ file, folder: 'templates/content' })
      await refetchFiles()
      resetSingleFileDraft()
      onContentSourceChange(result.path)
      setViewMode('write')
      setSourceControlsOpen(false)
      toast.success(t('site:pageEditor.fileUploaded'), {
        description: result.filename,
      })
    } catch (error) {
      toast.error(t('site:pageEditor.uploadError'), {
        description: error instanceof Error ? error.message : t('site:pageEditor.uploadFailed'),
      })
    }

    event.target.value = ''
  }

  const handleFileSelection = (path: string) => {
    resetSingleFileDraft()
    onContentSourceChange(path || null)
    setViewMode('write')
    setSourceControlsOpen(false)
  }

  const handleClearFile = () => {
    onContentSourceChange(null)
    resetSingleFileDraft()
    setViewMode('write')
    setSourceControlsOpen(true)
  }

  const editorFallback = (
    <div
      className="flex items-center justify-center rounded-lg border bg-muted/30 p-8"
      style={{ minHeight }}
    >
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )

  const sourceControls = (
    <div className="space-y-4 border-t border-border/70 px-4 py-4">
      {languages.length > 1 ? (
        <div className="space-y-2">
          <Label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t('site:pageEditor.manageContentSource')}
          </Label>
          <RadioGroup
            value={contentMode}
            onValueChange={(value) => handleContentModeChange(value as ContentMode)}
            className="flex flex-wrap gap-4"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="single" id={`mode-single-${baseName}`} />
              <Label htmlFor={`mode-single-${baseName}`} className="cursor-pointer text-sm">
                <FileText className="mr-1 inline h-4 w-4" />
                {t('site:pageEditor.singleFile')}
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="multilingual" id={`mode-multi-${baseName}`} />
              <Label htmlFor={`mode-multi-${baseName}`} className="cursor-pointer text-sm">
                <Globe className="mr-1 inline h-4 w-4" />
                {t('site:pageEditor.multilingualFiles')}
              </Label>
            </div>
          </RadioGroup>
        </div>
      ) : null}

      {contentMode === 'single' ? (
        <div className="space-y-2">
          <Label>{t('site:pageEditor.sourceFile')}</Label>
          <div className="flex gap-2">
            {markdownFiles.length === 0 && !filesLoading ? (
              <div className="flex flex-1 items-center">
                <p className="text-sm text-muted-foreground">
                  {t('site:pageEditor.noFilesIn')}
                </p>
              </div>
            ) : (
              <Select
                value={contentSource || ''}
                onValueChange={handleFileSelection}
                disabled={filesLoading}
              >
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder={t('site:pageEditor.selectFile')} />
                </SelectTrigger>
                <SelectContent>
                  {markdownFiles.map((file) => (
                    <SelectItem key={file.path} value={file.path}>
                      {file.name}
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
            {contentSource ? (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClearFile}
                title={t('site:pageEditor.clearFile')}
              >
                <X className="h-4 w-4" />
              </Button>
            ) : null}
          </div>
          <p className="text-xs text-muted-foreground">
            {t('site:pageEditor.sourceDetailsHint')}
          </p>
          {fileContentError instanceof Error ? (
            <p className="text-xs text-destructive">{fileContentError.message}</p>
          ) : null}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border/70 bg-muted/20 px-3 py-3">
          <p className="text-sm font-medium">{t('site:pageEditor.basePath')}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {contentSource || getMultilingualBasePath()}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {t('site:pageEditor.basePathHint')}
          </p>
        </div>
      )}
    </div>
  )

  const renderSingleFileSurface = () => {
    if (!singleFilePath) {
      return (
        <div
          className={cn(
            'flex flex-col items-center justify-center rounded-lg border border-dashed border-border/70 bg-muted/20 px-6 py-8 text-center',
            variant === 'authoring' ? 'min-h-[320px]' : 'min-h-[220px]'
          )}
          style={variant === 'default' ? { minHeight } : undefined}
        >
          <FileText className="mb-3 h-8 w-8 text-muted-foreground/70" />
          <p className="text-sm font-medium">{t('site:pageEditor.noSourceSelected')}</p>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            {t('site:pageEditor.selectOrUploadFile')}
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => setSourceControlsOpen(true)}
          >
            <Settings2 className="mr-2 h-4 w-4" />
            {t('site:pageEditor.manageContentSource')}
          </Button>
        </div>
      )
    }

    if (fileContentLoading) {
      return editorFallback
    }

    if (viewMode === 'source') {
      return (
        <div
          className="max-h-[480px] overflow-auto rounded-lg border bg-muted/30 p-4"
          style={{ minHeight }}
        >
          <pre className="whitespace-pre-wrap font-mono text-sm text-muted-foreground">
            {editedContent || t('site:pageEditor.noContent')}
          </pre>
        </div>
      )
    }

    return (
      <div style={{ minHeight }}>
        <Suspense fallback={editorFallback}>
          <MarkdownEditor
            key={singleFilePath}
            initialContent={editedContent}
            onChange={handleContentChange}
            placeholder={placeholder || t('site:pageEditor.markdownPlaceholder')}
            className={variant === 'authoring' ? 'border-border/70 shadow-none' : undefined}
          />
        </Suspense>
      </div>
    )
  }

  return (
    <div
      data-markdown-field-variant={variant}
      className={cn(
        'space-y-4',
        variant === 'authoring' && 'rounded-xl border border-border/70 bg-background/70 p-4 shadow-sm'
      )}
    >
      {(label || description) ? (
        <div>
          {label ? <Label className="text-base font-medium">{label}</Label> : null}
          {description ? (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          ) : null}
        </div>
      ) : null}

      {contentMode === 'single' ? (
        <>
          <div className="flex flex-col gap-3 rounded-lg border border-border/70 bg-background/70 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                {t('site:pageEditor.currentFile')}
              </div>
              <div className="mt-1 flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="truncate text-sm font-medium">
                  {sourceSummary || t('site:pageEditor.noSourceSelected')}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:items-end">
              <ToggleGroup
                type="single"
                value={viewMode}
                onValueChange={(value) => value && setViewMode(value as ViewMode)}
                variant="outline"
                size="sm"
                spacing={1}
              >
                <ToggleGroupItem value="write" aria-label={t('site:pageEditor.writeMode')}>
                  {t('site:pageEditor.writeMode')}
                </ToggleGroupItem>
                <ToggleGroupItem value="source" aria-label={t('site:pageEditor.sourceMode')}>
                  <Code className="mr-1 h-4 w-4" />
                  {t('site:pageEditor.sourceMode')}
                </ToggleGroupItem>
              </ToggleGroup>

              <div className="flex flex-wrap items-center justify-end gap-2">
                {hasUnsavedChanges ? (
                  <Button variant="outline" size="sm" onClick={handleCancelEdit}>
                    {t('site:pageEditor.cancel')}
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={!hasUnsavedChanges || isSaving || fileContentLoading}
                >
                  {isSaving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  {t('site:pageEditor.save')}
                </Button>
              </div>
            </div>
          </div>

          <Collapsible open={sourceControlsOpen} onOpenChange={setSourceControlsOpen}>
            <div className="rounded-lg border border-border/70 bg-background/60">
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex h-auto w-full items-center justify-between rounded-lg px-4 py-3"
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Settings2 className="h-4 w-4 text-muted-foreground" />
                    {t('site:pageEditor.manageContentSource')}
                  </span>
                  <ChevronDown
                    className={cn(
                      'h-4 w-4 text-muted-foreground transition-transform',
                      sourceControlsOpen && 'rotate-180'
                    )}
                  />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>{sourceControls}</CollapsibleContent>
            </div>
          </Collapsible>

          {renderSingleFileSurface()}
        </>
      ) : (
        <>
          <Collapsible open={sourceControlsOpen} onOpenChange={setSourceControlsOpen}>
            <div className="rounded-lg border border-border/70 bg-background/60">
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex h-auto w-full items-center justify-between rounded-lg px-4 py-3"
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    {sourceSummary || t('site:pageEditor.multilingualContent')}
                  </span>
                  <ChevronDown
                    className={cn(
                      'h-4 w-4 text-muted-foreground transition-transform',
                      sourceControlsOpen && 'rotate-180'
                    )}
                  />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>{sourceControls}</CollapsibleContent>
            </div>
          </Collapsible>

          {contentSource ? (
            <div style={{ minHeight }}>
              <Suspense fallback={editorFallback}>
                <MultilingualMarkdownEditor
                  basePath={contentSource}
                  languages={languages}
                  defaultLang={defaultLang}
                  className={variant === 'authoring' ? 'rounded-xl border-border/70 bg-transparent shadow-none' : undefined}
                />
              </Suspense>
            </div>
          ) : (
            <div
              className="flex min-h-[220px] flex-col items-center justify-center rounded-lg border border-dashed border-border/70 bg-muted/20 px-6 py-8 text-center"
              style={{ minHeight }}
            >
              <Globe className="mb-3 h-8 w-8 text-muted-foreground/70" />
              <p className="text-sm font-medium">{t('site:pageEditor.selectFileFirst')}</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default MarkdownContentField
