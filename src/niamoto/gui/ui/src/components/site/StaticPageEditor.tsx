/**
 * StaticPageEditor - Full-page editor for static pages
 *
 * Features:
 * - Page name and output file configuration
 * - Template selection
 * - Content source toggle (inline markdown or file)
 * - WYSIWYG markdown editor
 * - Real-time updates (no save button - changes sync to parent state)
 */

import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  FileText,
  Trash2,
  Upload,
  Loader2,
  Edit3,
  Save,
  Code,
  FileType,
  Plus,
  X,
  Navigation,
  Menu,
} from 'lucide-react'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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
import { MarkdownEditor } from './MarkdownEditor'
import { TemplateSelect } from './TemplateSelect'
import { useTemplates, useProjectFiles, useUploadFile, useFileContent, useUpdateFileContent, type StaticPage, type NavigationItem } from '@/hooks/useSiteConfig'
import {
  hasTemplateForm,
  IndexPageForm,
  BibliographyForm,
  TeamForm,
  ResourcesForm,
  ContactForm,
  GlossaryForm,
  type IndexPageContext,
  type BibliographyPageContext,
  type TeamPageContext,
  type ResourcesPageContext,
  type ContactPageContext,
  type GlossaryPageContext,
} from './forms'

interface StaticPageEditorProps {
  page: StaticPage
  onChange: (page: StaticPage) => void
  onDelete?: () => void
  onBack: () => void
  // Navigation linking
  navigation?: NavigationItem[]
  footerNavigation?: NavigationItem[]
  onUpdateNavigation?: (nav: NavigationItem[]) => void
  onUpdateFooterNavigation?: (nav: NavigationItem[]) => void
}

type ContentMode = 'inline' | 'file'

export function StaticPageEditor({
  page,
  onChange,
  onDelete,
  onBack,
  navigation = [],
  footerNavigation = [],
  onUpdateNavigation,
  onUpdateFooterNavigation,
}: StaticPageEditorProps) {
  const { t } = useTranslation(['site', 'common'])

  // Local state for editing (initialized from prop, component remounts on page change via key)
  const [editedPage, setEditedPage] = useState<StaticPage>(page)
  const [contentMode, setContentMode] = useState<ContentMode>(() => {
    if (page.context?.content_source) return 'file'
    return 'inline'
  })

  // File content editing state
  const [isEditingFile, setIsEditingFile] = useState(false)
  const [editedFileContent, setEditedFileContent] = useState<string>('')
  const [showRawContent, setShowRawContent] = useState(false) // false = formatted, true = raw

  // File upload ref
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch templates and markdown files from templates/content/ folder
  const { data: templatesData, isLoading: templatesLoading } = useTemplates()
  const { data: filesData, isLoading: filesLoading, refetch: refetchFiles } = useProjectFiles('templates/content')
  const uploadMutation = useUploadFile()

  // Fetch file content when a file is selected
  const selectedFilePath = contentMode === 'file' ? editedPage.context?.content_source : null
  const { data: fileContentData, isLoading: fileContentLoading } = useFileContent(selectedFilePath)
  const updateFileContentMutation = useUpdateFileContent()

  // Sync file content to edit state when loaded
  useEffect(() => {
    if (fileContentData?.content) {
      setEditedFileContent(fileContentData.content)
    }
  }, [fileContentData?.content])

  // Filter markdown files
  const markdownFiles =
    filesData?.files.filter((f) => ['.md', '.markdown', '.txt'].includes(f.extension)) ?? []

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const result = await uploadMutation.mutateAsync({ file, folder: 'templates/content' })
      // Refresh file list and select the uploaded file
      await refetchFiles()
      updateContext('content_source', result.path)
      toast.success(t('pageEditor.fileUploaded'), {
        description: result.filename,
      })
    } catch (err) {
      toast.error(t('pageEditor.uploadError'), {
        description: err instanceof Error ? err.message : t('pageEditor.uploadFailed'),
      })
    }
    // Reset input
    e.target.value = ''
  }

  // All templates (default + project)
  const allTemplates = templatesData?.templates ?? []

  // Navigation linking helpers
  const pageUrl = `/${editedPage.output_file}`

  // Check if page is in a navigation list (recursive for children)
  const isInNavigation = (items: NavigationItem[]): boolean => {
    for (const item of items) {
      if (item.url === pageUrl) return true
      if (item.children && isInNavigation(item.children)) return true
    }
    return false
  }

  const inMainNav = isInNavigation(navigation)
  const inFooterNav = isInNavigation(footerNavigation)

  // Add page to main navigation
  const handleAddToMainNav = () => {
    if (!onUpdateNavigation || inMainNav) return
    onUpdateNavigation([
      ...navigation,
      { text: editedPage.name, url: pageUrl },
    ])
    toast.success(t('navigation.linkAdded'), {
      description: t('navigation.addedToMain'),
    })
  }

  // Add page to footer navigation
  const handleAddToFooterNav = () => {
    if (!onUpdateFooterNavigation || inFooterNav) return
    onUpdateFooterNavigation([
      ...footerNavigation,
      { text: editedPage.name, url: pageUrl },
    ])
    toast.success(t('navigation.linkAdded'), {
      description: t('navigation.addedToFooter'),
    })
  }

  // Remove page from main navigation (recursive)
  const removeFromNav = (items: NavigationItem[], url: string): NavigationItem[] => {
    return items
      .filter((item) => item.url !== url)
      .map((item) => ({
        ...item,
        children: item.children ? removeFromNav(item.children, url) : undefined,
      }))
  }

  const handleRemoveFromMainNav = () => {
    if (!onUpdateNavigation) return
    onUpdateNavigation(removeFromNav(navigation, pageUrl))
    toast.success(t('navigation.linkRemoved'), {
      description: t('navigation.removedFromMain'),
    })
  }

  const handleRemoveFromFooterNav = () => {
    if (!onUpdateFooterNavigation) return
    onUpdateFooterNavigation(removeFromNav(footerNavigation, pageUrl))
    toast.success(t('navigation.linkRemoved'), {
      description: t('navigation.removedFromFooter'),
    })
  }

  // Sync changes to parent on every edit
  useEffect(() => {
    // Only notify parent if there are actual changes
    if (JSON.stringify(page) !== JSON.stringify(editedPage)) {
      onChange(editedPage)
    }
  }, [editedPage, page, onChange])

  // Update field helper
  const updateField = <K extends keyof StaticPage>(field: K, value: StaticPage[K]) => {
    setEditedPage((prev) => ({ ...prev, [field]: value }))
  }

  // Update context helper
  const updateContext = (key: string, value: unknown) => {
    setEditedPage((prev) => ({
      ...prev,
      context: {
        ...prev.context,
        [key]: value,
      },
    }))
  }

  // Handle content mode change
  const handleContentModeChange = (mode: ContentMode) => {
    setContentMode(mode)
    setIsEditingFile(false) // Reset edit mode when switching
    if (mode === 'inline') {
      // Clear file source, keep markdown
      setEditedPage((prev) => ({
        ...prev,
        context: {
          ...prev.context,
          content_source: null,
        },
      }))
    } else {
      // Clear inline markdown when switching to file
      setEditedPage((prev) => ({
        ...prev,
        context: {
          ...prev.context,
          content_markdown: null,
        },
      }))
    }
  }

  // Handle saving file content
  const handleSaveFileContent = async () => {
    if (!selectedFilePath) return

    try {
      await updateFileContentMutation.mutateAsync({
        path: selectedFilePath,
        content: editedFileContent,
      })
      setIsEditingFile(false)
      toast.success(t('pageEditor.fileSaved'), {
        description: fileContentData?.filename || selectedFilePath,
      })
    } catch (err) {
      toast.error(t('pageEditor.saveError'), {
        description: err instanceof Error ? err.message : t('pageEditor.saveFailed'),
      })
    }
  }

  // Cancel file editing
  const handleCancelEdit = () => {
    setEditedFileContent(fileContentData?.content || '')
    setIsEditingFile(false)
  }

  // Auto-generate output file from name
  const handleNameChange = (name: string) => {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
    setEditedPage((prev) => ({
      ...prev,
      name,
      output_file: `${slug || 'page'}.html`,
    }))
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-6 py-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold">
              <FileText className="h-5 w-5" />
              {editedPage.name || t('pageEditor.newPage')}
            </h1>
            <p className="text-sm text-muted-foreground">
              {editedPage.output_file}
            </p>
          </div>
        </div>
        {onDelete && (
          <Button
            variant="outline"
            size="sm"
            onClick={onDelete}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {t('pageEditor.delete')}
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Basic Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('pageEditor.pageSettings')}</CardTitle>
              <CardDescription>{t('pageEditor.pageSettingsDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                {/* Page name */}
                <div className="space-y-2">
                  <Label htmlFor="page-name">{t('pageEditor.pageName')}</Label>
                  <Input
                    id="page-name"
                    value={editedPage.name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    placeholder="methodology"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('pageEditor.pageNameHint')}
                  </p>
                </div>

                {/* Output file */}
                <div className="space-y-2">
                  <Label htmlFor="output-file">{t('pageEditor.outputFile')}</Label>
                  <Input
                    id="output-file"
                    value={editedPage.output_file}
                    onChange={(e) => updateField('output_file', e.target.value)}
                    placeholder="methodology.html"
                    className="font-mono"
                  />
                </div>
              </div>

              {/* Template selection */}
              <div className="space-y-2">
                <Label>{t('groupViewer.template')}</Label>
                <TemplateSelect
                  value={editedPage.template}
                  onChange={(v) => updateField('template', v)}
                  templates={allTemplates}
                  disabled={templatesLoading}
                />
              </div>

              {/* Navigation linking */}
              {(onUpdateNavigation || onUpdateFooterNavigation) && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Menu className="h-4 w-4" />
                    {t('navigation.menuLinks')}
                  </Label>
                  <div className="flex flex-wrap gap-2">
                    {/* Main navigation status/action */}
                    {inMainNav ? (
                      <div className="flex items-center gap-1 rounded-full bg-primary/10 pl-3 pr-1 py-1 text-sm">
                        <Navigation className="h-3 w-3 text-primary" />
                        <span className="text-primary">{t('navigation.mainMenu')}</span>
                        {onUpdateNavigation && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 rounded-full hover:bg-destructive/20"
                            onClick={handleRemoveFromMainNav}
                          >
                            <X className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                          </Button>
                        )}
                      </div>
                    ) : onUpdateNavigation && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 gap-1"
                        onClick={handleAddToMainNav}
                      >
                        <Plus className="h-3 w-3" />
                        {t('navigation.addToMainMenu')}
                      </Button>
                    )}

                    {/* Footer navigation status/action */}
                    {inFooterNav ? (
                      <div className="flex items-center gap-1 rounded-full bg-muted pl-3 pr-1 py-1 text-sm">
                        <Navigation className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{t('navigation.footerMenu')}</span>
                        {onUpdateFooterNavigation && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 rounded-full hover:bg-destructive/20"
                            onClick={handleRemoveFromFooterNav}
                          >
                            <X className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                          </Button>
                        )}
                      </div>
                    ) : onUpdateFooterNavigation && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 gap-1"
                        onClick={handleAddToFooterNav}
                      >
                        <Plus className="h-3 w-3" />
                        {t('navigation.addToFooterMenu')}
                      </Button>
                    )}

                    {/* No links indicator */}
                    {!inMainNav && !inFooterNav && !onUpdateNavigation && !onUpdateFooterNavigation && (
                      <span className="text-sm text-muted-foreground italic">
                        {t('navigation.notLinked')}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Content Section - Template-specific form or Markdown editor */}
          {hasTemplateForm(editedPage.template) ? (
            /* Dedicated form for specific templates */
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('pageEditor.pageConfig')}</CardTitle>
                <CardDescription>
                  {t('pageEditor.templateFormDesc', { template: editedPage.template })}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {editedPage.template === 'index.html' && (
                  <IndexPageForm
                    context={(editedPage.context as IndexPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                  />
                )}
                {editedPage.template === 'bibliography.html' && (
                  <BibliographyForm
                    context={(editedPage.context as BibliographyPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                  />
                )}
                {editedPage.template === 'team.html' && (
                  <TeamForm
                    context={(editedPage.context as TeamPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                  />
                )}
                {editedPage.template === 'resources.html' && (
                  <ResourcesForm
                    context={(editedPage.context as ResourcesPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                  />
                )}
                {editedPage.template === 'contact.html' && (
                  <ContactForm
                    context={(editedPage.context as ContactPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                  />
                )}
                {editedPage.template === 'glossary.html' && (
                  <GlossaryForm
                    context={(editedPage.context as GlossaryPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                  />
                )}
              </CardContent>
            </Card>
          ) : (
            /* Standard markdown editor for other templates */
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t('pageEditor.content')}</CardTitle>
                  <CardDescription>{t('pageEditor.markdownContent')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Content mode toggle */}
                  <RadioGroup
                    value={contentMode}
                    onValueChange={(v) => handleContentModeChange(v as ContentMode)}
                    className="flex gap-4"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="inline" id="mode-inline" />
                      <Label htmlFor="mode-inline" className="cursor-pointer">
                        {t('pageEditor.editDirectly')}
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="file" id="mode-file" />
                      <Label htmlFor="mode-file" className="cursor-pointer">
                        {t('pageEditor.fromFile')}
                      </Label>
                    </div>
                  </RadioGroup>

                  {/* File selector */}
                  {contentMode === 'file' && (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="content-source">{t('pageEditor.sourceFile')}</Label>
                        <div className="flex gap-2">
                          {markdownFiles.length === 0 ? (
                            <div className="flex-1 flex items-center">
                              <p className="text-sm text-muted-foreground">
                                {t('pageEditor.noFilesIn')}
                              </p>
                            </div>
                          ) : (
                            <Select
                              value={editedPage.context?.content_source || ''}
                              onValueChange={(v) => {
                                updateContext('content_source', v || null)
                                setIsEditingFile(false) // Reset edit mode when changing file
                              }}
                              disabled={filesLoading}
                            >
                              <SelectTrigger id="content-source" className="flex-1">
                                <SelectValue placeholder={t('pageEditor.selectFile')} />
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
                            title={t('pageEditor.uploadMarkdown')}
                          >
                            {uploadMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Upload className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {t('pageEditor.mdFileIn')}
                        </p>
                      </div>

                      {/* File content preview/edit */}
                      {selectedFilePath && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label>{t('pageEditor.fileContent')}</Label>
                            <div className="flex gap-2">
                              {isEditingFile ? (
                                <>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCancelEdit}
                                  >
                                    {t('pageEditor.cancel')}
                                  </Button>
                                  <Button
                                    size="sm"
                                    onClick={handleSaveFileContent}
                                    disabled={updateFileContentMutation.isPending}
                                  >
                                    {updateFileContentMutation.isPending ? (
                                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                      <Save className="mr-2 h-4 w-4" />
                                    )}
                                    {t('pageEditor.save')}
                                  </Button>
                                </>
                              ) : (
                                <>
                                  {/* Toggle formatted/raw view */}
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
                                    onClick={() => setIsEditingFile(true)}
                                    disabled={fileContentLoading}
                                  >
                                    <Edit3 className="mr-2 h-4 w-4" />
                                    {t('pageEditor.edit')}
                                  </Button>
                                </>
                              )}
                            </div>
                          </div>

                          {fileContentLoading ? (
                            <div className="flex items-center justify-center p-8 border rounded-md bg-muted/30">
                              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                            </div>
                          ) : isEditingFile ? (
                            <MarkdownEditor
                              initialContent={editedFileContent}
                              onChange={setEditedFileContent}
                              placeholder={t('pageEditor.markdownPlaceholder')}
                              className="min-h-[300px]"
                            />
                          ) : showRawContent ? (
                            <div className="border rounded-md bg-muted/30 p-4 max-h-[400px] overflow-auto">
                              <pre className="text-sm whitespace-pre-wrap font-mono text-muted-foreground">
                                {fileContentData?.content || t('pageEditor.noContent')}
                              </pre>
                            </div>
                          ) : (
                            <div className="max-h-[400px] overflow-auto">
                              <MarkdownEditor
                                initialContent={fileContentData?.content || ''}
                                readOnly
                                className="border-muted/50"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Markdown editor */}
                  {contentMode === 'inline' && (
                    <div className="space-y-2">
                      <Label>{t('pageEditor.editor')}</Label>
                      <MarkdownEditor
                        initialContent={editedPage.context?.content_markdown || ''}
                        onChange={(md) => updateContext('content_markdown', md)}
                        placeholder={t('pageEditor.markdownPlaceholder')}
                        className="min-h-[400px]"
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('pageEditor.editorHint')}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Additional context - only for non-form templates */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t('pageEditor.additionalContext')}</CardTitle>
                  <CardDescription>{t('pageEditor.additionalContextDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Label htmlFor="page-title">{t('pageEditor.pageTitle')}</Label>
                    <Input
                      id="page-title"
                      value={(editedPage.context?.title as string) || ''}
                      onChange={(e) => updateContext('title', e.target.value || null)}
                      placeholder={t('pageEditor.pageTitleHint')}
                    />
                    <p className="text-xs text-muted-foreground">
                      {t('pageEditor.pageTitleHint')}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default StaticPageEditor
