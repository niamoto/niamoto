/**
 * FooterSectionsEditor - Editor for footer sections with categories and links
 *
 * Each section has a title (category heading) and a list of links.
 * Links can be internal (to site pages) or external (to any URL).
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Plus,
  Trash2,
  ExternalLink as ExternalLinkIcon,
  FileText,
  Folder,
  ChevronDown,
  Globe,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { LocalizedInput } from '@/components/ui/localized-input'
import type { FooterSection, FooterLink, StaticPage, GroupInfo } from '@/hooks/useSiteConfig'

interface FooterSectionsEditorProps {
  sections: FooterSection[]
  onChange: (sections: FooterSection[]) => void
  staticPages?: StaticPage[]
  groups?: GroupInfo[]
}

interface AvailablePage {
  name: string
  url: string
  type: 'static' | 'group'
}

export function FooterSectionsEditor({
  sections,
  onChange,
  staticPages = [],
  groups = [],
}: FooterSectionsEditorProps) {
  const { t } = useTranslation(['site', 'common'])

  const availablePages: AvailablePage[] = [
    ...staticPages.map((page) => ({
      name: page.name,
      url: `/${page.output_file}`,
      type: 'static' as const,
    })),
    ...groups
      .filter((g) => g.index_output_pattern)
      .map((group) => ({
        name: `${group.name} (index)`,
        url: `/${group.index_output_pattern}`,
        type: 'group' as const,
      })),
  ]

  const handleAddSection = () => {
    onChange([...sections, { title: '', links: [] }])
  }

  const handleUpdateSection = (index: number, section: FooterSection) => {
    const newSections = [...sections]
    newSections[index] = section
    onChange(newSections)
  }

  const handleRemoveSection = (index: number) => {
    onChange(sections.filter((_, i) => i !== index))
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Globe className="h-4 w-4" />
              {t('footer.sections')}
            </CardTitle>
            <CardDescription>{t('footer.sectionsDesc')}</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleAddSection}>
            <Plus className="mr-1 h-4 w-4" />
            {t('footer.addSection')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {sections.length === 0 ? (
          <div className="flex min-h-[100px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-4 text-center">
            <Globe className="mb-2 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">{t('footer.noSections')}</p>
            <Button variant="link" size="sm" onClick={handleAddSection} className="mt-2">
              <Plus className="mr-1 h-4 w-4" />
              {t('footer.addFirstSection')}
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {sections.map((section, index) => (
              <FooterSectionItem
                key={index}
                section={section}
                availablePages={availablePages}
                onUpdate={(updated) => handleUpdateSection(index, updated)}
                onRemove={() => handleRemoveSection(index)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface FooterSectionItemProps {
  section: FooterSection
  availablePages: AvailablePage[]
  onUpdate: (section: FooterSection) => void
  onRemove: () => void
}

function FooterSectionItem({ section, availablePages, onUpdate, onRemove }: FooterSectionItemProps) {
  const { t } = useTranslation(['site', 'common'])
  const [isOpen, setIsOpen] = useState(true)

  const handleAddLink = () => {
    onUpdate({
      ...section,
      links: [...section.links, { text: '', url: '', external: false }],
    })
  }

  const handleUpdateLink = (linkIndex: number, link: FooterLink) => {
    const newLinks = [...section.links]
    newLinks[linkIndex] = link
    onUpdate({ ...section, links: newLinks })
  }

  const handleRemoveLink = (linkIndex: number) => {
    onUpdate({
      ...section,
      links: section.links.filter((_, i) => i !== linkIndex),
    })
  }

  return (
    <div className="rounded-lg border bg-card">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <div className="flex items-center gap-2 p-3">
          <CollapsibleTrigger asChild>
            <button className="p-1 hover:bg-muted rounded">
              <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', !isOpen && '-rotate-90')} />
            </button>
          </CollapsibleTrigger>

          <LocalizedInput
            value={section.title}
            onChange={(title) => onUpdate({ ...section, title: title || '' })}
            placeholder={t('footer.sectionTitle')}
            className="flex-1 min-w-0"
          />

          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {section.links.length} {section.links.length <= 1 ? t('footer.link') : t('footer.links')}
          </span>

          <Button
            variant="ghost"
            size="icon"
            onClick={handleAddLink}
            className="h-8 w-8 shrink-0"
            title={t('footer.addLink')}
          >
            <Plus className="h-4 w-4 text-muted-foreground" />
          </Button>

          <Button variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 shrink-0">
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
          </Button>
        </div>

        <CollapsibleContent>
          <div className="border-t bg-muted/30 p-3 space-y-2">
            {section.links.length === 0 ? (
              <p className="text-xs text-muted-foreground italic text-center py-2">
                {t('footer.noLinks')}
              </p>
            ) : (
              section.links.map((link, linkIndex) => (
                <FooterLinkItem
                  key={linkIndex}
                  link={link}
                  availablePages={availablePages}
                  onUpdate={(updated) => handleUpdateLink(linkIndex, updated)}
                  onRemove={() => handleRemoveLink(linkIndex)}
                />
              ))
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

interface FooterLinkItemProps {
  link: FooterLink
  availablePages: AvailablePage[]
  onUpdate: (link: FooterLink) => void
  onRemove: () => void
}

function FooterLinkItem({ link, availablePages, onUpdate, onRemove }: FooterLinkItemProps) {
  const { t } = useTranslation(['site', 'common'])
  const [popoverOpen, setPopoverOpen] = useState(false)

  const isExternal = link.external || (link.url && !link.url.startsWith('/'))

  return (
    <div className="flex items-center gap-2 ml-6">
      {/* Link text */}
      <LocalizedInput
        value={link.text}
        onChange={(text) => onUpdate({ ...link, text: text || '' })}
        placeholder={t('footer.linkText')}
        className="flex-1 min-w-0 [&_input]:h-8 [&_input]:text-sm"
      />

      {/* URL with page selector */}
      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className={cn(
              'flex-1 justify-between font-mono text-xs h-8',
              !link.url && 'text-muted-foreground'
            )}
          >
            <span className="flex items-center gap-1.5 truncate">
              {isExternal ? (
                <ExternalLinkIcon className="h-3 w-3 shrink-0" />
              ) : (
                <FileText className="h-3 w-3 shrink-0" />
              )}
              {link.url || t('footer.selectUrl')}
            </span>
            <ChevronDown className="h-3 w-3 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[280px] p-0" align="start">
          <div className="max-h-[250px] overflow-auto">
            {/* Static pages */}
            {availablePages.filter((p) => p.type === 'static').length > 0 && (
              <div className="p-2">
                <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                  Pages
                </p>
                {availablePages
                  .filter((p) => p.type === 'static')
                  .map((page) => (
                    <button
                      key={page.url}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted',
                        link.url === page.url && 'bg-muted'
                      )}
                      onClick={() => {
                        onUpdate({ ...link, url: page.url, external: false })
                        setPopoverOpen(false)
                      }}
                    >
                      <FileText className="h-3 w-3 shrink-0" />
                      <span className="flex-1 text-left truncate">{page.name}</span>
                    </button>
                  ))}
              </div>
            )}

            {/* Group pages */}
            {availablePages.filter((p) => p.type === 'group').length > 0 && (
              <div className="border-t p-2">
                <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                  Groups
                </p>
                {availablePages
                  .filter((p) => p.type === 'group')
                  .map((page) => (
                    <button
                      key={page.url}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted',
                        link.url === page.url && 'bg-muted'
                      )}
                      onClick={() => {
                        onUpdate({ ...link, url: page.url, external: false })
                        setPopoverOpen(false)
                      }}
                    >
                      <Folder className="h-3 w-3 shrink-0 text-amber-600" />
                      <span className="flex-1 text-left truncate">{page.name}</span>
                    </button>
                  ))}
              </div>
            )}

            {/* Custom URL */}
            <div className="border-t p-2">
              <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                {t('footer.customUrl')}
              </p>
              <div className="px-2 space-y-2">
                <Input
                  value={link.url || ''}
                  onChange={(e) => {
                    const url = e.target.value
                    const ext = url.startsWith('http') || url.startsWith('mailto:')
                    onUpdate({ ...link, url, external: ext })
                  }}
                  placeholder="https://... ou /page.html"
                  className="font-mono text-xs h-8"
                  onClick={(e) => e.stopPropagation()}
                />
                <div className="flex items-center gap-2">
                  <Switch
                    id="external-toggle"
                    checked={link.external || false}
                    onCheckedChange={(checked) => onUpdate({ ...link, external: checked })}
                  />
                  <Label htmlFor="external-toggle" className="text-xs text-muted-foreground">
                    {t('footer.externalLink')}
                  </Label>
                </div>
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {/* Remove button */}
      <Button variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 shrink-0">
        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
      </Button>
    </div>
  )
}
