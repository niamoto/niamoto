/**
 * TemplateList - Inline template selector for creating new pages
 *
 * Displays templates grouped by category as a simple list
 * Used in the editor panel instead of a modal
 */

import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  Home,
  FileText,
  BookOpen,
  Users,
  Mail,
  Download,
  List,
  Newspaper,
  ScrollText,
  type LucideIcon,
} from 'lucide-react'

// =============================================================================
// Types & Configuration
// =============================================================================

type TemplateCategory = 'landing' | 'content' | 'project' | 'reference'

const CATEGORY_INFO: Record<TemplateCategory, { label: string; order: number }> = {
  landing: { label: 'Accueil', order: 0 },
  content: { label: 'Contenu', order: 1 },
  project: { label: 'Projet', order: 2 },
  reference: { label: 'Reference', order: 3 },
}

const CATEGORY_PALETTES: Record<TemplateCategory, string[]> = {
  landing: ['blue'],
  content: ['gray', 'orange', 'emerald'],
  project: ['green', 'amber'],
  reference: ['cyan', 'teal', 'slate'],
}

interface TemplateDefinition {
  icon: LucideIcon
  description: string
  category: TemplateCategory
  colorIndex: number
}

const TEMPLATES: Record<string, TemplateDefinition> = {
  'index.html': {
    icon: Home,
    description: "Page d'accueil avec hero, statistiques et fonctionnalites",
    category: 'landing',
    colorIndex: 0,
  },
  'page.html': {
    icon: FileText,
    description: 'Page de contenu simple avec titre et texte markdown',
    category: 'content',
    colorIndex: 0,
  },
  'article.html': {
    icon: Newspaper,
    description: 'Article avec auteur, date et contenu enrichi',
    category: 'content',
    colorIndex: 1,
  },
  'documentation.html': {
    icon: ScrollText,
    description: 'Documentation technique avec sommaire et sections',
    category: 'content',
    colorIndex: 2,
  },
  'team.html': {
    icon: Users,
    description: 'Equipe, partenaires et financeurs avec photos et logos',
    category: 'project',
    colorIndex: 0,
  },
  'contact.html': {
    icon: Mail,
    description: 'Page de contact avec email, adresse et reseaux sociaux',
    category: 'project',
    colorIndex: 1,
  },
  'resources.html': {
    icon: Download,
    description: 'Liste de ressources telechargeables avec fichiers et liens',
    category: 'reference',
    colorIndex: 0,
  },
  'bibliography.html': {
    icon: BookOpen,
    description: 'Liste de references bibliographiques formatees',
    category: 'reference',
    colorIndex: 1,
  },
  'glossary.html': {
    icon: List,
    description: 'Glossaire de termes avec definitions et categories',
    category: 'reference',
    colorIndex: 2,
  },
}

// =============================================================================
// Helper Functions
// =============================================================================

function getTemplateConfig(templateName: string) {
  const template = TEMPLATES[templateName]
  if (!template) {
    return {
      icon: FileText,
      description: 'Template personnalise',
      category: 'content' as TemplateCategory,
      colorClass: 'text-gray-600',
    }
  }

  const palette = CATEGORY_PALETTES[template.category]
  const color = palette[template.colorIndex % palette.length]

  return {
    icon: template.icon,
    description: template.description,
    category: template.category,
    colorClass: `text-${color}-600`,
  }
}

function groupTemplatesByCategory(
  templates: Array<{ name: string }>
): Map<TemplateCategory, Array<{ name: string; config: ReturnType<typeof getTemplateConfig> }>> {
  const groups = new Map<TemplateCategory, Array<{ name: string; config: ReturnType<typeof getTemplateConfig> }>>()

  const orderedCategories = Object.entries(CATEGORY_INFO)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([cat]) => cat as TemplateCategory)

  for (const cat of orderedCategories) {
    groups.set(cat, [])
  }

  for (const template of templates) {
    const config = getTemplateConfig(template.name)
    groups.get(config.category)?.push({ name: template.name, config })
  }

  for (const [cat, items] of groups) {
    if (items.length === 0) {
      groups.delete(cat)
    }
  }

  return groups
}

// =============================================================================
// Component
// =============================================================================

interface TemplateListProps {
  templates: Array<{ name: string; description: string; icon: string }>
  onSelect: (templateName: string) => void
  onBack: () => void
}

export function TemplateList({ templates, onSelect, onBack }: TemplateListProps) {
  const groupedTemplates = groupTemplatesByCategory(templates)

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h2 className="text-lg font-semibold">Nouvelle page</h2>
            <p className="text-sm text-muted-foreground">
              Choisissez un template pour commencer
            </p>
          </div>
        </div>
      </div>

      {/* Template list */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {Array.from(groupedTemplates.entries()).map(([category, items]) => (
            <div key={category}>
              {/* Category header */}
              <h3 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide px-2">
                {CATEGORY_INFO[category].label}
              </h3>

              {/* Templates */}
              <div className="space-y-1">
                {items.map(({ name, config }) => {
                  const Icon = config.icon

                  return (
                    <button
                      key={name}
                      onClick={() => onSelect(name)}
                      className={cn(
                        'flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors',
                        'hover:bg-muted/80 active:bg-muted'
                      )}
                    >
                      <div className={cn('p-2 rounded-md bg-muted', config.colorClass)}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">
                          {name.replace('.html', '')}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {config.description}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

export default TemplateList
