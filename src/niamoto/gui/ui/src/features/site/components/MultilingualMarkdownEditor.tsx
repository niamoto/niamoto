/**
 * MultilingualMarkdownEditor - Editor for language-specific markdown files
 *
 * Supports the convention: {basePath}.{lang}.md
 * Example: pages/about.fr.md, pages/about.en.md
 *
 * Features:
 * - Tabs for each configured language
 * - Load/save individual language files
 * - Create new language file if missing
 * - Visual indicators for existing vs missing translations
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Loader2,
  Save,
  Plus,
  FileText,
  AlertCircle,
  Check,
  Globe,
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MarkdownEditor } from './MarkdownEditor'
import { useUpdateFileContent } from '@/shared/hooks/useSiteConfig'
import { useLanguages } from '@/shared/contexts/LanguageContext'

interface LanguageFileState {
  content: string
  exists: boolean
  loading: boolean
  modified: boolean
  error?: string
}

interface MultilingualMarkdownEditorProps {
  /** Base path without extension (e.g., "templates/content/about") */
  basePath: string
  /** Available languages (optional, uses context if not provided) */
  languages?: string[]
  /** Default language (optional, uses context if not provided) */
  defaultLang?: string
  /** Called when any file is saved */
  onSave?: () => void
  /** Additional class name */
  className?: string
}

export function MultilingualMarkdownEditor({
  basePath,
  languages: languagesProp,
  defaultLang: defaultLangProp,
  onSave,
  className,
}: MultilingualMarkdownEditorProps) {
  const { t } = useTranslation(['site', 'common'])
  const languageContext = useLanguages()
  const languages = languagesProp ?? languageContext.languages
  const defaultLang = defaultLangProp ?? languageContext.defaultLang
  const [activeLang, setActiveLang] = useState(defaultLang)
  const [fileStates, setFileStates] = useState<Record<string, LanguageFileState>>({})
  const updateFileMutation = useUpdateFileContent()

  // Generate file path for a language
  const getFilePath = useCallback((lang: string) => {
    // Remove any existing extension from basePath
    const cleanBase = basePath.replace(/\.(md|markdown)$/i, '')
    return `${cleanBase}.${lang}.md`
  }, [basePath])

  // Load file content for a specific language
  const loadLanguageFile = useCallback(async (lang: string) => {
    const filePath = getFilePath(lang)

    setFileStates(prev => ({
      ...prev,
      [lang]: { ...prev[lang], loading: true, error: undefined }
    }))

    try {
      const response = await fetch(`/api/site/file-content?path=${encodeURIComponent(filePath)}`)

      if (response.ok) {
        const data = await response.json()
        setFileStates(prev => ({
          ...prev,
          [lang]: {
            content: data.content || '',
            exists: true,
            loading: false,
            modified: false,
          }
        }))
      } else if (response.status === 404) {
        // File doesn't exist yet
        setFileStates(prev => ({
          ...prev,
          [lang]: {
            content: '',
            exists: false,
            loading: false,
            modified: false,
          }
        }))
      } else {
        throw new Error(`Failed to load file: ${response.statusText}`)
      }
    } catch (err) {
      setFileStates(prev => ({
        ...prev,
        [lang]: {
          content: '',
          exists: false,
          loading: false,
          modified: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        }
      }))
    }
  }, [getFilePath])

  // Load all language files on mount or when basePath changes
  useEffect(() => {
    if (!basePath) return

    languages.forEach(lang => {
      loadLanguageFile(lang)
    })
  }, [basePath, languages, loadLanguageFile])

  // Update content for a language
  const handleContentChange = useCallback((lang: string, content: string) => {
    setFileStates(prev => ({
      ...prev,
      [lang]: {
        ...prev[lang],
        content,
        modified: true,
      }
    }))
  }, [])

  // Save file for a specific language
  const handleSave = useCallback(async (lang: string) => {
    const state = fileStates[lang]
    if (!state) return

    const filePath = getFilePath(lang)

    try {
      await updateFileMutation.mutateAsync({
        path: filePath,
        content: state.content,
      })

      setFileStates(prev => ({
        ...prev,
        [lang]: {
          ...prev[lang],
          exists: true,
          modified: false,
        }
      }))

      toast.success(t('pageEditor.fileSaved'), {
        description: `${lang.toUpperCase()}: ${filePath.split('/').pop()}`,
      })

      onSave?.()
    } catch (err) {
      toast.error(t('pageEditor.saveError'), {
        description: err instanceof Error ? err.message : t('pageEditor.saveFailed'),
      })
    }
  }, [fileStates, getFilePath, updateFileMutation, t, onSave])

  // Create new file for a language
  const handleCreateFile = useCallback(async (lang: string) => {
    // Initialize with empty content and mark as modified
    setFileStates(prev => ({
      ...prev,
      [lang]: {
        content: `# ${t('pageEditor.newContent')} (${lang.toUpperCase()})\n\n`,
        exists: false,
        loading: false,
        modified: true,
      }
    }))
    setActiveLang(lang)
  }, [t])

  // Check if any file has unsaved changes
  const hasUnsavedChanges = Object.values(fileStates).some(s => s.modified)

  // Get language display name
  const getLanguageName = (code: string) => {
    const names: Record<string, string> = {
      fr: 'Francais',
      en: 'English',
      es: 'Espanol',
      de: 'Deutsch',
      pt: 'Portugues',
      it: 'Italiano',
    }
    return names[code] || code.toUpperCase()
  }

  if (!basePath) {
    return (
      <div className={cn('rounded-lg border border-dashed p-6 text-center', className)}>
        <Globe className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">
          {t('pageEditor.selectFileFirst')}
        </p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header with info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">{t('pageEditor.multilingualContent')}</span>
          {hasUnsavedChanges && (
            <Badge variant="outline" className="text-xs text-amber-600 border-amber-300">
              {t('common:status.unsaved')}
            </Badge>
          )}
        </div>
        <span className="text-xs text-muted-foreground font-mono">
          {basePath.split('/').pop()}.[lang].md
        </span>
      </div>

      {/* Language tabs */}
      <Tabs value={activeLang} onValueChange={setActiveLang} className="w-full">
        <TabsList className="w-full justify-start">
          {languages.map(lang => {
            const state = fileStates[lang]
            const isLoading = state?.loading
            const exists = state?.exists
            const isModified = state?.modified

            return (
              <TabsTrigger
                key={lang}
                value={lang}
                className="relative gap-1.5"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : exists ? (
                  <FileText className="h-3 w-3" />
                ) : (
                  <Plus className="h-3 w-3 text-muted-foreground" />
                )}
                <span>{lang.toUpperCase()}</span>
                {isModified && (
                  <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-amber-500" />
                )}
                {lang === defaultLang && (
                  <Badge variant="secondary" className="h-4 px-1 text-[10px] ml-1">
                    {t('siteConfig.default')}
                  </Badge>
                )}
              </TabsTrigger>
            )
          })}
        </TabsList>

        {languages.map(lang => {
          const state = fileStates[lang]
          const isLoading = state?.loading
          const exists = state?.exists
          const hasError = state?.error

          return (
            <TabsContent key={lang} value={lang} className="mt-3">
              {isLoading ? (
                <div className="flex items-center justify-center p-12 border rounded-lg bg-muted/30">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : hasError ? (
                <div className="flex flex-col items-center justify-center p-8 border rounded-lg bg-destructive/5">
                  <AlertCircle className="h-8 w-8 text-destructive mb-2" />
                  <p className="text-sm text-destructive">{state.error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => loadLanguageFile(lang)}
                  >
                    {t('common:actions.retry')}
                  </Button>
                </div>
              ) : !exists && !state?.modified ? (
                <div className="flex flex-col items-center justify-center p-8 border rounded-lg border-dashed bg-muted/30">
                  <FileText className="h-8 w-8 text-muted-foreground/50 mb-2" />
                  <p className="text-sm text-muted-foreground mb-1">
                    {t('pageEditor.noTranslation', { lang: getLanguageName(lang) })}
                  </p>
                  <p className="text-xs text-muted-foreground mb-3">
                    {getFilePath(lang).split('/').pop()}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCreateFile(lang)}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {t('pageEditor.createTranslation')}
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Editor */}
                  <MarkdownEditor
                    initialContent={state?.content || ''}
                    onChange={(content) => handleContentChange(lang, content)}
                    placeholder={t('pageEditor.markdownPlaceholder')}
                    className="min-h-[350px]"
                  />

                  {/* Save button */}
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-muted-foreground">
                      {exists ? (
                        <span className="flex items-center gap-1">
                          <Check className="h-3 w-3 text-green-600" />
                          {t('pageEditor.fileExists')}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <Plus className="h-3 w-3" />
                          {t('pageEditor.newFile')}
                        </span>
                      )}
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleSave(lang)}
                      disabled={!state?.modified || updateFileMutation.isPending}
                    >
                      {updateFileMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4 mr-1" />
                      )}
                      {t('pageEditor.save')} ({lang.toUpperCase()})
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}

export default MultilingualMarkdownEditor
