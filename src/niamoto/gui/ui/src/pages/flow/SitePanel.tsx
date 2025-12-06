/**
 * Site Panel - Site Structure Configuration
 *
 * Three sub-sections:
 * - Structure: Navigation tree from export.yml
 * - Pages: Static pages (markdown)
 * - Theme: Colors, fonts, branding
 */

import { Globe, FileText, Palette, FolderTree, Plus } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface SitePanelProps {
  subSection: 'structure' | 'pages' | 'theme'
}

export function SitePanel({ subSection }: SitePanelProps) {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Site</h1>
        <p className="text-muted-foreground">
          Configurez la structure et le contenu de votre site.
        </p>
      </div>

      {subSection === 'structure' && <StructureSection />}
      {subSection === 'pages' && <PagesSection />}
      {subSection === 'theme' && <ThemeSection />}
    </div>
  )
}

function StructureSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderTree className="h-5 w-5" />
            Structure du site
          </CardTitle>
          <CardDescription>
            Configuration basée sur export.yml - menus, pages statiques, groupes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8">
            <Globe className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 font-medium">Éditeur de structure</h3>
            <p className="text-center text-sm text-muted-foreground max-w-md">
              Visualisez et modifiez la structure de navigation de votre site.
              <br />
              Les groupes configurés seront automatiquement intégrés.
            </p>
            <Button variant="outline" className="mt-4" disabled>
              <Plus className="mr-2 h-4 w-4" />
              Bientôt disponible
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function PagesSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Pages Markdown
          </CardTitle>
          <CardDescription>
            Créez des pages de contenu personnalisées à intégrer au site
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8">
            <FileText className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 font-medium">Éditeur de pages</h3>
            <p className="text-center text-sm text-muted-foreground max-w-md">
              Créez et éditez des pages statiques en Markdown.
              <br />
              Idéal pour la page d'accueil, à propos, méthodologie, etc.
            </p>
            <Button variant="outline" className="mt-4" disabled>
              <Plus className="mr-2 h-4 w-4" />
              Nouvelle page
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ThemeSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Thème
          </CardTitle>
          <CardDescription>
            Personnalisez les couleurs et les polices de votre site
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex min-h-[300px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8">
            <Palette className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 font-medium">Configuration du thème</h3>
            <p className="text-center text-sm text-muted-foreground max-w-md">
              Configurez les couleurs, polices et éléments de branding.
              <br />
              Les options de personnalisation seront disponibles prochainement.
            </p>
            <Button variant="outline" className="mt-4" disabled>
              Bientôt disponible
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
