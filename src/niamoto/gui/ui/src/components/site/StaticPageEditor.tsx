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
import { useTemplates, useProjectFiles, useUploadFile, useFileContent, useUpdateFileContent, type StaticPage } from '@/hooks/useSiteConfig'
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
}

type ContentMode = 'inline' | 'file'

export function StaticPageEditor({ page, onChange, onDelete, onBack }: StaticPageEditorProps) {
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
      toast.success('Fichier uploade', {
        description: result.filename,
      })
    } catch (err) {
      toast.error('Erreur upload', {
        description: err instanceof Error ? err.message : 'Echec de l\'upload',
      })
    }
    // Reset input
    e.target.value = ''
  }

  // All templates (default + project)
  const allTemplates = templatesData?.templates ?? []

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
      toast.success('Fichier sauvegarde', {
        description: fileContentData?.filename || selectedFilePath,
      })
    } catch (err) {
      toast.error('Erreur de sauvegarde', {
        description: err instanceof Error ? err.message : 'Echec de la sauvegarde',
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
              {editedPage.name || 'Nouvelle page'}
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
            Supprimer
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Basic Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Parametres de la page</CardTitle>
              <CardDescription>Configuration de base de la page statique</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                {/* Page name */}
                <div className="space-y-2">
                  <Label htmlFor="page-name">Nom de la page</Label>
                  <Input
                    id="page-name"
                    value={editedPage.name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    placeholder="methodology"
                  />
                  <p className="text-xs text-muted-foreground">
                    Identifiant interne (sans espaces)
                  </p>
                </div>

                {/* Output file */}
                <div className="space-y-2">
                  <Label htmlFor="output-file">Fichier de sortie</Label>
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
                <Label>Template</Label>
                <TemplateSelect
                  value={editedPage.template}
                  onChange={(v) => updateField('template', v)}
                  templates={allTemplates}
                  disabled={templatesLoading}
                />
              </div>
            </CardContent>
          </Card>

          {/* Content Section - Template-specific form or Markdown editor */}
          {hasTemplateForm(editedPage.template) ? (
            /* Dedicated form for specific templates */
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Configuration de la page</CardTitle>
                <CardDescription>
                  Formulaire dedie pour le template {editedPage.template}
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
                  <CardTitle className="text-base">Contenu</CardTitle>
                  <CardDescription>Contenu markdown de la page</CardDescription>
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
                        Éditer directement
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="file" id="mode-file" />
                      <Label htmlFor="mode-file" className="cursor-pointer">
                        Depuis un fichier
                      </Label>
                    </div>
                  </RadioGroup>

                  {/* File selector */}
                  {contentMode === 'file' && (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="content-source">Fichier source</Label>
                        <div className="flex gap-2">
                          {markdownFiles.length === 0 ? (
                            <div className="flex-1 flex items-center">
                              <p className="text-sm text-muted-foreground">
                                Aucun fichier dans templates/content/
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
                                <SelectValue placeholder="Selectionner un fichier" />
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
                            title="Uploader un fichier markdown"
                          >
                            {uploadMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Upload className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Fichier markdown dans templates/content/
                        </p>
                      </div>

                      {/* File content preview/edit */}
                      {selectedFilePath && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label>Contenu du fichier</Label>
                            <div className="flex gap-2">
                              {isEditingFile ? (
                                <>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCancelEdit}
                                  >
                                    Annuler
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
                                    Sauvegarder
                                  </Button>
                                </>
                              ) : (
                                <>
                                  {/* Toggle formatted/raw view */}
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setShowRawContent(!showRawContent)}
                                    title={showRawContent ? 'Voir formaté' : 'Voir le code'}
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
                                    Éditer
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
                              placeholder="Contenu markdown..."
                              className="min-h-[300px]"
                            />
                          ) : showRawContent ? (
                            <div className="border rounded-md bg-muted/30 p-4 max-h-[400px] overflow-auto">
                              <pre className="text-sm whitespace-pre-wrap font-mono text-muted-foreground">
                                {fileContentData?.content || 'Aucun contenu'}
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
                      <Label>Editeur</Label>
                      <MarkdownEditor
                        initialContent={editedPage.context?.content_markdown || ''}
                        onChange={(md) => updateContext('content_markdown', md)}
                        placeholder="Tapez / pour voir les commandes..."
                        className="min-h-[400px]"
                      />
                      <p className="text-xs text-muted-foreground">
                        Utilisez / pour inserer des titres, listes, citations, etc.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Additional context - only for non-form templates */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Contexte supplementaire</CardTitle>
                  <CardDescription>Variables additionnelles passees au template</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Label htmlFor="page-title">Titre de la page</Label>
                    <Input
                      id="page-title"
                      value={(editedPage.context?.title as string) || ''}
                      onChange={(e) => updateContext('title', e.target.value || null)}
                      placeholder="Titre affiche dans la page"
                    />
                    <p className="text-xs text-muted-foreground">
                      Titre utilise dans le template (optionnel)
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
