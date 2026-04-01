/**
 * TemplateList - Inline template selector for creating new pages
 *
 * Displays templates grouped by category as a simple list
 * Used in the editor panel instead of a modal
 */

import { useTranslation } from 'react-i18next'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

// Template thumbnail imports (static SVGs for offline support)
import indexThumb from '../assets/templates/index-thumbnail.svg'
import pageThumb from '../assets/templates/page-thumbnail.svg'
import teamThumb from '../assets/templates/team-thumbnail.svg'
import contactThumb from '../assets/templates/contact-thumbnail.svg'
import bibliographyThumb from '../assets/templates/bibliography-thumbnail.svg'
import resourcesThumb from '../assets/templates/resources-thumbnail.svg'
import glossaryThumb from '../assets/templates/glossary-thumbnail.svg'

const TEMPLATE_THUMBNAILS: Record<string, string> = {
  'index.html': indexThumb,
  'page.html': pageThumb,
  'article.html': pageThumb, // reuse page wireframe
  'documentation.html': pageThumb,
  'team.html': teamThumb,
  'contact.html': contactThumb,
  'resources.html': resourcesThumb,
  'bibliography.html': bibliographyThumb,
  'glossary.html': glossaryThumb,
}

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

// Category order - labels are i18n keys
const CATEGORY_ORDER: Record<TemplateCategory, number> = {
  landing: 0,
  content: 1,
  project: 2,
  reference: 3,
}

const CATEGORY_PALETTES: Record<TemplateCategory, string[]> = {
  landing: ['blue'],
  content: ['gray', 'orange', 'emerald'],
  project: ['green', 'amber'],
  reference: ['cyan', 'teal', 'slate'],
}

interface TemplateDefinition {
  icon: LucideIcon
  descriptionKey: string // i18n key for description
  category: TemplateCategory
  colorIndex: number
}

const TEMPLATES: Record<string, TemplateDefinition> = {
  'index.html': {
    icon: Home,
    descriptionKey: 'index',
    category: 'landing',
    colorIndex: 0,
  },
  'page.html': {
    icon: FileText,
    descriptionKey: 'page',
    category: 'content',
    colorIndex: 0,
  },
  'article.html': {
    icon: Newspaper,
    descriptionKey: 'article',
    category: 'content',
    colorIndex: 1,
  },
  'documentation.html': {
    icon: ScrollText,
    descriptionKey: 'documentation',
    category: 'content',
    colorIndex: 2,
  },
  'team.html': {
    icon: Users,
    descriptionKey: 'team',
    category: 'project',
    colorIndex: 0,
  },
  'contact.html': {
    icon: Mail,
    descriptionKey: 'contact',
    category: 'project',
    colorIndex: 1,
  },
  'resources.html': {
    icon: Download,
    descriptionKey: 'resources',
    category: 'reference',
    colorIndex: 0,
  },
  'bibliography.html': {
    icon: BookOpen,
    descriptionKey: 'bibliography',
    category: 'reference',
    colorIndex: 1,
  },
  'glossary.html': {
    icon: List,
    descriptionKey: 'glossary',
    category: 'reference',
    colorIndex: 2,
  },
}

// =============================================================================
// Helper Functions
// =============================================================================

interface TemplateConfig {
  icon: LucideIcon
  descriptionKey: string
  category: TemplateCategory
  colorClass: string
}

function getTemplateConfig(templateName: string): TemplateConfig {
  const template = TEMPLATES[templateName]
  if (!template) {
    return {
      icon: FileText,
      descriptionKey: 'custom',
      category: 'content' as TemplateCategory,
      colorClass: 'text-gray-600',
    }
  }

  const palette = CATEGORY_PALETTES[template.category]
  const color = palette[template.colorIndex % palette.length]

  return {
    icon: template.icon,
    descriptionKey: template.descriptionKey,
    category: template.category,
    colorClass: `text-${color}-600`,
  }
}

function groupTemplatesByCategory(
  templates: Array<{ name: string }>
): Map<TemplateCategory, Array<{ name: string; config: TemplateConfig }>> {
  const groups = new Map<TemplateCategory, Array<{ name: string; config: TemplateConfig }>>()

  const orderedCategories = Object.entries(CATEGORY_ORDER)
    .sort(([, a], [, b]) => a - b)
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
  const { t } = useTranslation('site')
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
            <h2 className="text-lg font-semibold">{t('templates.newPage')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('templates.chooseTemplate')}
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
                {t(`templates.categories.${category}`)}
              </h3>

              {/* Templates */}
              <div className="space-y-1">
                {items.map(({ name, config }) => {
                  const Icon = config.icon

                  const thumbnail = TEMPLATE_THUMBNAILS[name]

                  return (
                    <button
                      key={name}
                      onClick={() => onSelect(name)}
                      className={cn(
                        'flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors',
                        'hover:bg-muted/80 active:bg-muted'
                      )}
                    >
                      {thumbnail ? (
                        <img
                          src={thumbnail}
                          alt=""
                          className="h-10 w-14 rounded border bg-white object-contain shrink-0"
                        />
                      ) : (
                        <div className={cn('p-2 rounded-md bg-muted', config.colorClass)}>
                          <Icon className="h-4 w-4" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">
                          {name.replace('.html', '')}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {t(`templates.descriptions.${config.descriptionKey}`)}
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
