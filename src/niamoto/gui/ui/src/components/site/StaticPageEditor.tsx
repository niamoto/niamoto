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

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  FileText,
  Trash2,
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
import { TemplateSelect } from './TemplateSelect'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import {
  useTemplates,
  type StaticPage,
  type NavigationItem,
} from '@/features/site/hooks/useSiteConfig'
import {
  hasTemplateForm,
  MarkdownContentField,
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
  onUpdateNavigation?: (nav: NavigationItem[]) => void
}

export function StaticPageEditor({
  page,
  onChange,
  onDelete,
  onBack,
  navigation = [],
  onUpdateNavigation,
}: StaticPageEditorProps) {
  const { t } = useTranslation(['site', 'common'])

  // Local state for editing (initialized from prop, component remounts on page change via key)
  const [editedPage, setEditedPage] = useState<StaticPage>(page)

  // Fetch templates
  const { data: templatesData, isLoading: templatesLoading } = useTemplates()

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
              {onUpdateNavigation && (
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
                        {onUpdateNavigation != null && (
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
                    ) : onUpdateNavigation != null && (
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

                    {/* No links indicator */}
                    {!inMainNav && !onUpdateNavigation && (
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
                    pageName={editedPage.name}
                  />
                )}
                {editedPage.template === 'bibliography.html' && (
                  <BibliographyForm
                    context={(editedPage.context as BibliographyPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                    pageName={editedPage.name}
                  />
                )}
                {editedPage.template === 'team.html' && (
                  <TeamForm
                    context={(editedPage.context as TeamPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                    pageName={editedPage.name}
                  />
                )}
                {editedPage.template === 'resources.html' && (
                  <ResourcesForm
                    context={(editedPage.context as ResourcesPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                    pageName={editedPage.name}
                  />
                )}
                {editedPage.template === 'contact.html' && (
                  <ContactForm
                    context={(editedPage.context as ContactPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                    pageName={editedPage.name}
                  />
                )}
                {editedPage.template === 'glossary.html' && (
                  <GlossaryForm
                    context={(editedPage.context as GlossaryPageContext) || {}}
                    onChange={(ctx) =>
                      setEditedPage((prev) => ({ ...prev, context: ctx }))
                    }
                    pageName={editedPage.name}
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
                <CardContent>
                  <MarkdownContentField
                    baseName={editedPage.name}
                    contentSource={editedPage.context?.content_source}
                    onContentSourceChange={(source) => updateContext('content_source', source)}
                    minHeight="300px"
                  />
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
                    <LocalizedInput
                      value={editedPage.context?.title as LocalizedString | undefined}
                      onChange={(title) => updateContext('title', title || null)}
                      placeholder={t('pageEditor.pageTitleHint')}
                      label={t('pageEditor.pageTitle')}
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
