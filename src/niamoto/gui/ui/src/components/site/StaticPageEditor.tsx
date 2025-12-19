/**
 * StaticPageEditor - Full-page editor for static pages
 *
 * Features:
 * - Page name and output file configuration
 * - Template selection
 * - Content source toggle (inline markdown or file)
 * - WYSIWYG markdown editor
 */

import { useState } from 'react'
import { ArrowLeft, Save, FileText, FileCode, Loader2 } from 'lucide-react'
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
import { useTemplates, useProjectFiles, type StaticPage } from '@/hooks/useSiteConfig'

interface StaticPageEditorProps {
  page: StaticPage
  onSave: (page: StaticPage) => void
  onBack: () => void
  isSaving?: boolean
}

type ContentMode = 'inline' | 'file'

export function StaticPageEditor({ page, onSave, onBack, isSaving = false }: StaticPageEditorProps) {
  // Local state for editing
  const [editedPage, setEditedPage] = useState<StaticPage>(page)
  const [contentMode, setContentMode] = useState<ContentMode>(() => {
    if (page.context?.content_source) return 'file'
    return 'inline'
  })

  // Fetch templates and markdown files
  const { data: templatesData, isLoading: templatesLoading } = useTemplates()
  const { data: filesData, isLoading: filesLoading } = useProjectFiles('files')

  // Filter markdown files
  const markdownFiles =
    filesData?.files.filter((f) => ['.md', '.markdown', '.txt'].includes(f.extension)) ?? []

  // All templates (default + project)
  const allTemplates = templatesData?.templates ?? []

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

  // Auto-generate output file from name
  const handleNameChange = (name: string) => {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
    updateField('name', name)
    updateField('output_file', `${slug || 'page'}.html`)
  }

  const handleSave = () => {
    onSave(editedPage)
  }

  const hasChanges = JSON.stringify(page) !== JSON.stringify(editedPage)

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
        <Button onClick={handleSave} disabled={isSaving || !hasChanges}>
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Sauvegarder
        </Button>
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
                <Label htmlFor="template">Template</Label>
                <Select
                  value={editedPage.template}
                  onValueChange={(v) => updateField('template', v)}
                  disabled={templatesLoading}
                >
                  <SelectTrigger id="template">
                    <SelectValue placeholder="Selectionner un template" />
                  </SelectTrigger>
                  <SelectContent>
                    {allTemplates.map((t) => (
                      <SelectItem key={t} value={t}>
                        <div className="flex items-center gap-2">
                          <FileCode className="h-4 w-4 text-muted-foreground" />
                          {t}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Template Jinja2 utilise pour generer la page
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Content Section */}
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
                    Editer directement
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
                <div className="space-y-2">
                  <Label htmlFor="content-source">Fichier source</Label>
                  <Select
                    value={editedPage.context?.content_source || ''}
                    onValueChange={(v) => updateContext('content_source', v || null)}
                    disabled={filesLoading}
                  >
                    <SelectTrigger id="content-source">
                      <SelectValue placeholder="Selectionner un fichier markdown" />
                    </SelectTrigger>
                    <SelectContent>
                      {markdownFiles.length === 0 ? (
                        <SelectItem value="" disabled>
                          Aucun fichier markdown trouve
                        </SelectItem>
                      ) : (
                        markdownFiles.map((f) => (
                          <SelectItem key={f.path} value={f.path}>
                            {f.name}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Fichier markdown dans le dossier files/
                  </p>
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

          {/* Additional context */}
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
        </div>
      </div>
    </div>
  )
}

export default StaticPageEditor
