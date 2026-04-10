import {
  BookOpen,
  Download,
  FileText,
  Home,
  List,
  Mail,
  Newspaper,
  ScrollText,
  Users,
  type LucideIcon,
} from 'lucide-react'

import type { NavigationItem } from '@/shared/hooks/useSiteConfig'

export const TEMPLATE_ICONS: Record<string, LucideIcon> = {
  'index.html': Home,
  'page.html': FileText,
  'article.html': Newspaper,
  'documentation.html': ScrollText,
  'team.html': Users,
  'contact.html': Mail,
  'resources.html': Download,
  'bibliography.html': BookOpen,
  'glossary.html': List,
}

export function getTemplateIcon(template?: string): LucideIcon {
  return template ? TEMPLATE_ICONS[template] || FileText : FileText
}

export function isPageInNavigation(
  pageUrl: string,
  items: NavigationItem[]
): 'direct' | 'parent' | null {
  for (const item of items) {
    if (item.url === pageUrl) return 'direct'
    if (item.children && item.children.length > 0) {
      if (!item.url && item.children.some((child) => child.url === pageUrl)) {
        return 'parent'
      }
      const childResult = isPageInNavigation(pageUrl, item.children)
      if (childResult) return childResult
    }
  }
  return null
}
