/**
 * ExternalLinksEditor - Editor for external links (social, GitHub, etc.)
 *
 * Allows:
 * - Adding external links with name, URL, and type
 * - Auto-detection of link type from URL
 * - Icon selection based on type
 * - Reordering via drag & drop
 */

import { useState } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  GripVertical,
  Plus,
  Trash2,
  ExternalLink as ExternalLinkIcon,
  Github,
  Twitter,
  Facebook,
  Linkedin,
  Instagram,
  Globe,
  Mail,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import type { ExternalLink } from '@/hooks/useSiteConfig'

// Link types with their icons
const LINK_TYPES = [
  { value: 'github', label: 'GitHub', icon: Github, pattern: /github\.com/i },
  { value: 'twitter', label: 'Twitter/X', icon: Twitter, pattern: /twitter\.com|x\.com/i },
  { value: 'facebook', label: 'Facebook', icon: Facebook, pattern: /facebook\.com/i },
  { value: 'linkedin', label: 'LinkedIn', icon: Linkedin, pattern: /linkedin\.com/i },
  { value: 'instagram', label: 'Instagram', icon: Instagram, pattern: /instagram\.com/i },
  { value: 'email', label: 'Email', icon: Mail, pattern: /^mailto:/i },
  { value: 'website', label: 'Site web', icon: Globe, pattern: null },
] as const

type LinkType = (typeof LINK_TYPES)[number]['value']

interface ExternalLinksEditorProps {
  links: ExternalLink[]
  onChange: (links: ExternalLink[]) => void
}

function getLinkIcon(type?: string | null) {
  const linkType = LINK_TYPES.find((t) => t.value === type)
  return linkType?.icon || Globe
}

function detectLinkType(url: string): LinkType {
  for (const type of LINK_TYPES) {
    if (type.pattern && type.pattern.test(url)) {
      return type.value
    }
  }
  return 'website'
}

interface SortableLinkItemProps {
  id: string
  link: ExternalLink
  onUpdate: (link: ExternalLink) => void
  onRemove: () => void
}

function SortableLinkItem({ id, link, onUpdate, onRemove }: SortableLinkItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const Icon = getLinkIcon(link.type)

  const handleUrlChange = (url: string) => {
    const detectedType = detectLinkType(url)
    onUpdate({
      ...link,
      url,
      type: detectedType,
    })
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-2 rounded-lg border bg-card p-2',
        isDragging && 'opacity-50 shadow-lg'
      )}
    >
      {/* Drag handle */}
      <button
        className="cursor-grab touch-none rounded p-1 hover:bg-muted active:cursor-grabbing"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </button>

      {/* Type selector with icon */}
      <Select
        value={link.type || 'website'}
        onValueChange={(v) => onUpdate({ ...link, type: v as LinkType })}
      >
        <SelectTrigger className="w-[140px]">
          <SelectValue>
            <span className="flex items-center gap-2">
              <Icon className="h-4 w-4" />
              {LINK_TYPES.find((t) => t.value === (link.type || 'website'))?.label}
            </span>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {LINK_TYPES.map((type) => (
            <SelectItem key={type.value} value={type.value}>
              <span className="flex items-center gap-2">
                <type.icon className="h-4 w-4" />
                {type.label}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Name input */}
      <Input
        value={link.name}
        onChange={(e) => onUpdate({ ...link, name: e.target.value })}
        placeholder="Nom du lien"
        className="w-32"
      />

      {/* URL input */}
      <Input
        value={link.url}
        onChange={(e) => handleUrlChange(e.target.value)}
        placeholder="https://..."
        className="flex-1 font-mono text-sm"
      />

      {/* Remove button */}
      <Button variant="ghost" size="icon" onClick={onRemove} className="h-8 w-8 shrink-0">
        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
      </Button>
    </div>
  )
}

export function ExternalLinksEditor({ links, onChange }: ExternalLinksEditorProps) {
  // Generate stable IDs for sortable items
  const [idMap] = useState(() => {
    const map = new Map<number, string>()
    links.forEach((_, index) => {
      map.set(index, `link-${index}-${Date.now()}`)
    })
    return map
  })

  const getId = (index: number): string => {
    if (!idMap.has(index)) {
      idMap.set(index, `link-${index}-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`)
    }
    return idMap.get(index)!
  }

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = links.findIndex((_, i) => getId(i) === active.id)
      const newIndex = links.findIndex((_, i) => getId(i) === over.id)

      if (oldIndex !== -1 && newIndex !== -1) {
        onChange(arrayMove(links, oldIndex, newIndex))
      }
    }
  }

  const handleAdd = () => {
    onChange([...links, { name: '', url: '', type: 'website' }])
  }

  const handleUpdate = (index: number, link: ExternalLink) => {
    const newLinks = [...links]
    newLinks[index] = link
    onChange(newLinks)
  }

  const handleRemove = (index: number) => {
    onChange(links.filter((_, i) => i !== index))
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <ExternalLinkIcon className="h-4 w-4" />
              Liens externes
            </CardTitle>
            <CardDescription>Liens vers GitHub, reseaux sociaux, partenaires</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleAdd}>
            <Plus className="mr-1 h-4 w-4" />
            Ajouter
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {links.length === 0 ? (
          <div className="flex min-h-[80px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-4 text-center">
            <ExternalLinkIcon className="mb-2 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">Aucun lien externe configure</p>
            <Button variant="link" size="sm" onClick={handleAdd} className="mt-2">
              <Plus className="mr-1 h-4 w-4" />
              Ajouter un lien
            </Button>
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext
              items={links.map((_, i) => getId(i))}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {links.map((link, index) => (
                  <SortableLinkItem
                    key={getId(index)}
                    id={getId(index)}
                    link={link}
                    onUpdate={(updated) => handleUpdate(index, updated)}
                    onRemove={() => handleRemove(index)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}

        {/* Preview */}
        {links.length > 0 && (
          <div className="mt-4 rounded-lg border bg-muted/30 p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Apercu</p>
            <div className="flex flex-wrap gap-3">
              {links.map((link, index) => {
                const Icon = getLinkIcon(link.type)
                return (
                  <a
                    key={index}
                    href={link.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary"
                  >
                    <Icon className="h-4 w-4" />
                    <span>{link.name || link.type || 'Lien'}</span>
                  </a>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
