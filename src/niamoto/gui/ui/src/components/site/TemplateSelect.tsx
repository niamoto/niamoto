/**
 * TemplateSelect - Enhanced template selector for forms
 *
 * Displays templates grouped by category in a popover
 * More compact than TemplateList, designed for form integration
 */

import { useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
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
// Types & Configuration (shared with TemplateList)
// =============================================================================

type TemplateCategory = 'landing' | 'content' | 'project' | 'reference'

const CATEGORY_INFO: Record<TemplateCategory, { label: string; order: number }> = {
  landing: { label: 'Landing', order: 0 },
  content: { label: 'Content', order: 1 },
  project: { label: 'Project', order: 2 },
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
  label: string
  category: TemplateCategory
  colorIndex: number
}

const TEMPLATES: Record<string, TemplateDefinition> = {
  'index.html': {
    icon: Home,
    label: 'Index',
    category: 'landing',
    colorIndex: 0,
  },
  'page.html': {
    icon: FileText,
    label: 'Page',
    category: 'content',
    colorIndex: 0,
  },
  'article.html': {
    icon: Newspaper,
    label: 'Article',
    category: 'content',
    colorIndex: 1,
  },
  'documentation.html': {
    icon: ScrollText,
    label: 'Documentation',
    category: 'content',
    colorIndex: 2,
  },
  'team.html': {
    icon: Users,
    label: 'Equipe',
    category: 'project',
    colorIndex: 0,
  },
  'contact.html': {
    icon: Mail,
    label: 'Contact',
    category: 'project',
    colorIndex: 1,
  },
  'resources.html': {
    icon: Download,
    label: 'Ressources',
    category: 'reference',
    colorIndex: 0,
  },
  'bibliography.html': {
    icon: BookOpen,
    label: 'Bibliographie',
    category: 'reference',
    colorIndex: 1,
  },
  'glossary.html': {
    icon: List,
    label: 'Glossaire',
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
      label: templateName.replace('.html', ''),
      category: 'content' as TemplateCategory,
      colorClass: 'text-gray-600 bg-gray-100',
    }
  }

  const palette = CATEGORY_PALETTES[template.category]
  const color = palette[template.colorIndex % palette.length]

  return {
    icon: template.icon,
    label: template.label,
    category: template.category,
    colorClass: `text-${color}-600 bg-${color}-100`,
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

interface TemplateSelectProps {
  value: string
  onChange: (templateName: string) => void
  templates: Array<{ name: string; description: string; icon: string }>
  disabled?: boolean
}

export function TemplateSelect({ value, onChange, templates, disabled }: TemplateSelectProps) {
  const [open, setOpen] = useState(false)
  const groupedTemplates = groupTemplatesByCategory(templates)
  const selectedConfig = getTemplateConfig(value)
  const SelectedIcon = selectedConfig.icon

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <div className="flex items-center gap-2">
            <div className={cn('p-1 rounded', selectedConfig.colorClass)}>
              <SelectedIcon className="h-4 w-4" />
            </div>
            <span>{selectedConfig.label}</span>
          </div>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        <ScrollArea className="h-[300px]">
          <div className="p-2">
            {Array.from(groupedTemplates.entries()).map(([category, items]) => (
              <div key={category} className="mb-3 last:mb-0">
                {/* Category header */}
                <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {CATEGORY_INFO[category].label}
                </div>

                {/* Templates */}
                <div className="space-y-0.5">
                  {items.map(({ name, config }) => {
                    const Icon = config.icon
                    const isSelected = value === name

                    return (
                      <button
                        key={name}
                        onClick={() => {
                          onChange(name)
                          setOpen(false)
                        }}
                        className={cn(
                          'flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm transition-colors',
                          isSelected
                            ? 'bg-primary/10 text-primary'
                            : 'hover:bg-muted'
                        )}
                      >
                        <div className={cn('p-1 rounded', config.colorClass)}>
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <span className="flex-1 text-left">{config.label}</span>
                        {isSelected && (
                          <Check className="h-4 w-4 text-primary" />
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}

export default TemplateSelect
