/**
 * Site Panel - Site Structure Configuration
 *
 * Three sub-sections:
 * - Structure: Site config + Navigation (drag & drop)
 * - Pages: Static pages with WYSIWYG editor
 * - Theme: Colors (coming soon)
 */

import { useState, useEffect } from 'react'
import { Palette, Loader2, Save, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { toast } from 'sonner'
import {
  useSiteConfig,
  useUpdateSiteConfig,
  type SiteSettings,
  type NavigationItem,
  type StaticPage,
  type SiteConfigUpdate,
  DEFAULT_SITE_SETTINGS,
  DEFAULT_STATIC_PAGE,
} from '@/hooks/useSiteConfig'
import {
  SiteConfigForm,
  NavigationBuilder,
  StaticPagesList,
  StaticPageEditor,
} from '@/components/site'

interface SitePanelProps {
  subSection: 'structure' | 'pages' | 'theme'
}

export function SitePanel({ subSection }: SitePanelProps) {
  // Fetch site config
  const { data: siteConfig, isLoading, error, refetch } = useSiteConfig()
  const updateMutation = useUpdateSiteConfig()

  // Local state for editing
  const [editedSite, setEditedSite] = useState<SiteSettings>(DEFAULT_SITE_SETTINGS)
  const [editedNavigation, setEditedNavigation] = useState<NavigationItem[]>([])
  const [editedPages, setEditedPages] = useState<StaticPage[]>([])
  const [selectedPageName, setSelectedPageName] = useState<string | null>(null)

  // Sync local state with fetched data
  useEffect(() => {
    if (siteConfig) {
      setEditedSite(siteConfig.site)
      setEditedNavigation(siteConfig.navigation)
      setEditedPages(siteConfig.static_pages)
    }
  }, [siteConfig])

  // Check if there are unsaved changes
  const hasChanges =
    siteConfig &&
    (JSON.stringify(editedSite) !== JSON.stringify(siteConfig.site) ||
      JSON.stringify(editedNavigation) !== JSON.stringify(siteConfig.navigation) ||
      JSON.stringify(editedPages) !== JSON.stringify(siteConfig.static_pages))

  // Save all changes
  const handleSave = async () => {
    if (!siteConfig) return

    const update: SiteConfigUpdate = {
      site: editedSite,
      navigation: editedNavigation,
      static_pages: editedPages,
      template_dir: siteConfig.template_dir,
      output_dir: siteConfig.output_dir,
      copy_assets_from: siteConfig.copy_assets_from,
    }

    try {
      await updateMutation.mutateAsync(update)
      toast.success('Configuration sauvegardee', {
        description: 'Les modifications ont ete appliquees a export.yml',
      })
    } catch (err) {
      toast.error('Erreur', {
        description: err instanceof Error ? err.message : 'Echec de la sauvegarde',
      })
    }
  }

  // Add new page
  const handleAddPage = () => {
    const newPage: StaticPage = {
      ...DEFAULT_STATIC_PAGE,
      name: `page-${editedPages.length + 1}`,
      output_file: `page-${editedPages.length + 1}.html`,
    }
    setEditedPages([...editedPages, newPage])
    setSelectedPageName(newPage.name)
  }

  // Delete page
  const handleDeletePage = (pageName: string) => {
    setEditedPages(editedPages.filter((p) => p.name !== pageName))
  }

  // Save page from editor
  const handleSavePage = (updatedPage: StaticPage) => {
    setEditedPages((pages) =>
      pages.map((p) => (p.name === selectedPageName ? updatedPage : p))
    )
    setSelectedPageName(null)
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Chargement de la configuration...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Erreur lors du chargement: {error instanceof Error ? error.message : 'Erreur inconnue'}
          </AlertDescription>
        </Alert>
        <Button onClick={() => refetch()} className="mt-4">
          Reessayer
        </Button>
      </div>
    )
  }

  // Page editor view (full screen)
  if (selectedPageName) {
    const selectedPage = editedPages.find((p) => p.name === selectedPageName)
    if (selectedPage) {
      return (
        <StaticPageEditor
          page={selectedPage}
          onSave={handleSavePage}
          onBack={() => setSelectedPageName(null)}
          isSaving={updateMutation.isPending}
        />
      )
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header with save button */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-6 py-4">
        <div>
          <h1 className="text-2xl font-bold">Site</h1>
          <p className="text-muted-foreground">
            Configurez la structure et le contenu de votre site.
          </p>
        </div>
        {hasChanges && (
          <Button onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Sauvegarder
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {subSection === 'structure' && (
          <StructureSection
            site={editedSite}
            navigation={editedNavigation}
            onSiteChange={setEditedSite}
            onNavigationChange={setEditedNavigation}
          />
        )}
        {subSection === 'pages' && (
          <PagesSection
            pages={editedPages}
            onEdit={setSelectedPageName}
            onAdd={handleAddPage}
            onDelete={handleDeletePage}
          />
        )}
        {subSection === 'theme' && <ThemeSection />}
      </div>
    </div>
  )
}

// Structure section: Site config + Navigation
interface StructureSectionProps {
  site: SiteSettings
  navigation: NavigationItem[]
  onSiteChange: (site: SiteSettings) => void
  onNavigationChange: (nav: NavigationItem[]) => void
}

function StructureSection({
  site,
  navigation,
  onSiteChange,
  onNavigationChange,
}: StructureSectionProps) {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <SiteConfigForm config={site} onChange={onSiteChange} />
      <NavigationBuilder items={navigation} onChange={onNavigationChange} />
    </div>
  )
}

// Pages section: List of static pages
interface PagesSectionProps {
  pages: StaticPage[]
  onEdit: (pageName: string) => void
  onAdd: () => void
  onDelete: (pageName: string) => void
}

function PagesSection({ pages, onEdit, onAdd, onDelete }: PagesSectionProps) {
  return (
    <div className="mx-auto max-w-4xl">
      <StaticPagesList pages={pages} onEdit={onEdit} onAdd={onAdd} onDelete={onDelete} />
    </div>
  )
}

// Theme section: Coming soon
function ThemeSection() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Theme
          </CardTitle>
          <CardDescription>
            Personnalisez les couleurs et les polices de votre site
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8">
            <Palette className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 font-medium">Configuration du theme</h3>
            <p className="max-w-md text-center text-sm text-muted-foreground">
              Configurez les couleurs, polices et elements de branding.
              <br />
              Les options de personnalisation seront disponibles prochainement.
            </p>
            <Button variant="outline" className="mt-4" disabled>
              Bientot disponible
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
