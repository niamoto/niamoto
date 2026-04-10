import type { LocalizedString } from '@/components/ui/localized-input'

export interface SiteSettings {
  title: string
  logo_header?: string | null
  logo_footer?: string | null
  lang: string
  languages?: string[]
  language_switcher?: boolean
  primary_color: string
  secondary_color?: string
  nav_color: string
  background_color?: string
  text_color?: string
  link_color?: string
  footer_bg_color?: string
  widget_header_gradient?: boolean
  border_radius?: 'none' | 'small' | 'medium' | 'large' | 'full'
  font_family?: 'system' | 'serif' | 'mono' | 'inter' | 'roboto'
  [key: string]: unknown
}

export interface NavigationItem {
  text: LocalizedString
  url?: string
  children?: NavigationItem[]
}

export interface ExternalLink {
  name: string
  url: string
  type?: string | null
}

export interface FooterLink {
  text: LocalizedString
  url: string
  external?: boolean
}

export interface FooterSection {
  title: LocalizedString
  links: FooterLink[]
}

export interface StaticPageContext {
  content_source?: string | null
  title?: LocalizedString | null
  introduction?: LocalizedString | null
  subtitle?: LocalizedString | null
  [key: string]: unknown
}

export interface StaticPage {
  name: string
  template: string
  output_file: string
  context?: StaticPageContext | null
}

export const ROOT_INDEX_TEMPLATE = 'index.html'
export const ROOT_INDEX_OUTPUT_FILE = 'index.html'

export function isRootIndexTemplate(template?: string | null): boolean {
  return template === ROOT_INDEX_TEMPLATE
}

export function isRootIndexPage(page: Pick<StaticPage, 'template' | 'output_file'>): boolean {
  return isRootIndexTemplate(page.template) || page.output_file === ROOT_INDEX_OUTPUT_FILE
}

export function getCanonicalStaticPageOutputFile(
  page: Pick<StaticPage, 'template' | 'output_file'>
): string {
  return isRootIndexTemplate(page.template) ? ROOT_INDEX_OUTPUT_FILE : page.output_file
}

export function hasRootIndexPage(
  pages: Array<Pick<StaticPage, 'template' | 'output_file'>>
): boolean {
  return pages.some((page) => isRootIndexTemplate(page.template))
}

export interface SiteConfigResponse {
  site: SiteSettings
  navigation: NavigationItem[]
  footer_navigation: FooterSection[]
  static_pages: StaticPage[]
  template_dir: string
  output_dir: string
  copy_assets_from: string[]
}

export interface SiteConfigUpdate {
  site: SiteSettings
  navigation: NavigationItem[]
  footer_navigation: FooterSection[]
  static_pages: StaticPage[]
  template_dir?: string | null
  output_dir?: string | null
  copy_assets_from?: string[] | null
}

export interface GroupIndexConfig {
  enabled: boolean
  template: string
  page_config: {
    title?: string
    description?: string
    items_per_page?: number
  }
  filters: Array<{
    field: string
    values: string[]
    operator: string
  }>
  display_fields: Array<{
    name: string
    source: string
    type: string
    label?: string
    searchable?: boolean
    format?: string
  }>
  views: Array<{
    type: string
    default: boolean
  }>
}

export interface GroupInfo {
  name: string
  output_pattern: string
  index_output_pattern?: string | null
  index_generator?: GroupIndexConfig | null
  widgets_count: number
}

export interface GroupsResponse {
  groups: GroupInfo[]
}

export interface TemplateInfo {
  name: string
  description: string
  icon: string
  category: string
}

export interface TemplatesResponse {
  templates: TemplateInfo[]
  default_templates: string[]
  project_templates: string[]
}

export interface ProjectFile {
  name: string
  path: string
  size: number
  extension: string
  modified: string
}

export interface FilesResponse {
  files: ProjectFile[]
  folder: string
}

export interface TemplatePreviewRequest {
  template: string
  context: Record<string, unknown>
  site?: Record<string, unknown>
  navigation?: Array<{
    text: LocalizedString
    url?: string
    children?: unknown[]
  }>
  footer_navigation?: Array<{
    title: LocalizedString
    links: Array<{
      text: LocalizedString
      url: string
      external?: boolean
    }>
  }>
  output_file?: string
  gui_lang?: string
}

export interface GroupIndexPreviewRequest {
  site?: Record<string, unknown>
  navigation?: Array<{ text: string; url?: string; children?: unknown[] }>
  gui_lang?: string
}

export interface FileContentResponse {
  content: string
  path: string
  filename: string
}

export interface DataContentResponse {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  path: string
  count: number
}

export interface ImportResponse {
  success: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  count: number
  errors: string[]
}

export const DEFAULT_SITE_SETTINGS: SiteSettings = {
  title: 'Niamoto',
  logo_header: null,
  logo_footer: null,
  lang: 'fr',
  primary_color: '#228b22',
  secondary_color: '#4caf50',
  nav_color: '#228b22',
  background_color: '#f9fafb',
  text_color: '#111827',
  link_color: '#228b22',
  footer_bg_color: '#1f2937',
  widget_header_gradient: true,
  border_radius: 'medium',
  font_family: 'system',
}

export const DEFAULT_NAVIGATION_ITEM: NavigationItem = {
  text: 'Nouvelle page',
  url: '/page.html',
}

export const DEFAULT_STATIC_PAGE: StaticPage = {
  name: 'new-page',
  template: 'page.html',
  output_file: 'new-page.html',
  context: null,
}
