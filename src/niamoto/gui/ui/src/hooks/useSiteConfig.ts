/**
 * Hook for managing site configuration from export.yml.
 *
 * Provides functions to:
 * - Get site settings (title, logos, colors)
 * - Get/update navigation menu items
 * - Get/update static pages
 * - List available templates
 * - List project files
 * - Preview markdown content
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = '/api/site'

// =============================================================================
// TYPES
// =============================================================================

export interface SiteSettings {
  title: string
  logo_header?: string | null
  logo_footer?: string | null
  lang: string
  // Theme colors
  primary_color: string
  secondary_color?: string
  nav_color: string
  background_color?: string
  text_color?: string
  link_color?: string
  footer_bg_color?: string
  // Visual effects
  widget_header_gradient?: boolean
  border_radius?: 'none' | 'small' | 'medium' | 'large' | 'full'
  font_family?: 'system' | 'serif' | 'mono' | 'inter' | 'roboto'
  [key: string]: unknown // Allow additional fields
}

export interface NavigationItem {
  text: string
  url?: string
  children?: NavigationItem[]
}

export interface ExternalLink {
  name: string
  url: string
  icon?: string | null  // Font Awesome class or icon name
  type?: 'github' | 'twitter' | 'facebook' | 'linkedin' | 'instagram' | 'website' | 'email' | null
}

export interface StaticPageContext {
  content_markdown?: string | null
  content_source?: string | null
  title?: string | null
  [key: string]: unknown
}

export interface StaticPage {
  name: string
  template: string
  output_file: string
  context?: StaticPageContext | null
}

export interface SiteConfigResponse {
  site: SiteSettings
  navigation: NavigationItem[]
  footer_navigation: NavigationItem[]
  external_links: ExternalLink[]
  static_pages: StaticPage[]
  template_dir: string
  output_dir: string
  copy_assets_from: string[]
}

export interface SiteConfigUpdate {
  site: SiteSettings
  navigation: NavigationItem[]
  footer_navigation: NavigationItem[]
  external_links: ExternalLink[]
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

// =============================================================================
// API FUNCTIONS
// =============================================================================

async function fetchSiteConfig(): Promise<SiteConfigResponse> {
  const response = await fetch(`${API_BASE}/config`)
  if (!response.ok) {
    throw new Error(`Failed to fetch site config: ${response.statusText}`)
  }
  return response.json()
}

async function updateSiteConfig(
  config: SiteConfigUpdate
): Promise<{ success: boolean; message: string; path: string }> {
  const response = await fetch(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Update failed')
  }

  return response.json()
}

async function fetchTemplates(): Promise<TemplatesResponse> {
  const response = await fetch(`${API_BASE}/templates`)
  if (!response.ok) {
    throw new Error(`Failed to fetch templates: ${response.statusText}`)
  }
  return response.json()
}

async function fetchProjectFiles(folder: string): Promise<FilesResponse> {
  const response = await fetch(`${API_BASE}/files?folder=${encodeURIComponent(folder)}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch files: ${response.statusText}`)
  }
  return response.json()
}

async function previewMarkdown(content: string): Promise<{ html: string }> {
  const response = await fetch(`${API_BASE}/preview-markdown`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Preview failed')
  }

  return response.json()
}

/**
 * Request for template preview.
 */
export interface TemplatePreviewRequest {
  template: string
  context: Record<string, unknown>
  site?: Record<string, unknown>
  navigation?: Array<{ text: string; url?: string; children?: unknown[] }>
}

/**
 * Preview a template with the given context.
 */
async function previewTemplate(request: TemplatePreviewRequest): Promise<{ html: string; template: string }> {
  const response = await fetch(`${API_BASE}/preview-template`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Template preview failed')
  }

  return response.json()
}

async function fetchGroups(): Promise<GroupsResponse> {
  const response = await fetch(`${API_BASE}/groups`)
  if (!response.ok) {
    throw new Error(`Failed to fetch groups: ${response.statusText}`)
  }
  return response.json()
}

export interface FileContentResponse {
  content: string
  path: string
  filename: string
}

async function fetchFileContent(path: string): Promise<FileContentResponse> {
  const response = await fetch(`${API_BASE}/file-content?path=${encodeURIComponent(path)}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to fetch file content: ${response.statusText}`)
  }
  return response.json()
}

async function updateFileContent(path: string, content: string): Promise<{ success: boolean; message: string; path: string }> {
  const response = await fetch(`${API_BASE}/file-content`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, content }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Update failed')
  }

  return response.json()
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook to fetch site configuration from export.yml.
 */
export function useSiteConfig() {
  return useQuery({
    queryKey: ['site-config'],
    queryFn: fetchSiteConfig,
    staleTime: 30000,
  })
}

/**
 * Hook to fetch groups from export.yml.
 * Returns groups with their index_generator configuration and widget count.
 */
export function useGroups() {
  return useQuery({
    queryKey: ['site-groups'],
    queryFn: fetchGroups,
    staleTime: 30000,
  })
}

/**
 * Hook to update site configuration in export.yml.
 */
export function useUpdateSiteConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: updateSiteConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['site-config'] })
    },
  })
}

/**
 * Hook to fetch available templates.
 */
export function useTemplates() {
  return useQuery({
    queryKey: ['site-templates'],
    queryFn: fetchTemplates,
    staleTime: 60000, // Templates don't change often
  })
}

/**
 * Hook to fetch project files from a specific folder.
 */
export function useProjectFiles(folder: string) {
  return useQuery({
    queryKey: ['project-files', folder],
    queryFn: () => fetchProjectFiles(folder),
    staleTime: 30000,
    enabled: !!folder,
  })
}

/**
 * Hook to preview markdown as HTML.
 */
export function useMarkdownPreview() {
  return useMutation({
    mutationFn: previewMarkdown,
  })
}

/**
 * Hook to preview a template with context.
 */
export function useTemplatePreview() {
  return useMutation({
    mutationFn: previewTemplate,
  })
}

/**
 * Request for group index preview.
 */
export interface GroupIndexPreviewRequest {
  site?: Record<string, unknown>
  navigation?: Array<{ text: string; url?: string; children?: unknown[] }>
}

/**
 * Preview a group index page with mock data.
 */
async function previewGroupIndex(
  groupName: string,
  request?: GroupIndexPreviewRequest
): Promise<{ html: string; template: string }> {
  const response = await fetch(`${API_BASE}/preview-group-index/${encodeURIComponent(groupName)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request || {}),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Group index preview failed')
  }

  return response.json()
}

/**
 * Hook to preview a group index page.
 */
export function useGroupIndexPreview() {
  return useMutation({
    mutationFn: ({ groupName, request }: { groupName: string; request?: GroupIndexPreviewRequest }) =>
      previewGroupIndex(groupName, request),
  })
}

/**
 * Upload a file to the project.
 */
async function uploadFile(file: File, folder: string = 'files'): Promise<{ success: boolean; path: string; filename: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/upload?folder=${encodeURIComponent(folder)}`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

/**
 * Hook to upload files.
 */
export function useUploadFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, folder }: { file: File; folder?: string }) => uploadFile(file, folder),
    onSuccess: (_, variables) => {
      // Invalidate the files query to refresh the list
      queryClient.invalidateQueries({ queryKey: ['project-files', variables.folder || 'files'] })
    },
  })
}

/**
 * Hook to fetch file content.
 */
export function useFileContent(path: string | null | undefined) {
  return useQuery({
    queryKey: ['file-content', path],
    queryFn: () => fetchFileContent(path!),
    enabled: !!path,
    staleTime: 10000, // Refresh more often for file content
  })
}

/**
 * Hook to update file content.
 */
export function useUpdateFileContent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) => updateFileContent(path, content),
    onSuccess: (_, variables) => {
      // Invalidate the file content query to refresh
      queryClient.invalidateQueries({ queryKey: ['file-content', variables.path] })
    },
  })
}

// =============================================================================
// HELPER TYPES
// =============================================================================

/**
 * Default site settings for new configurations.
 */
export const DEFAULT_SITE_SETTINGS: SiteSettings = {
  title: 'Niamoto',
  logo_header: null,
  logo_footer: null,
  lang: 'fr',
  // Theme colors
  primary_color: '#228b22',
  secondary_color: '#4caf50',
  nav_color: '#228b22',
  background_color: '#f9fafb',
  text_color: '#111827',
  link_color: '#228b22',
  footer_bg_color: '#1f2937',
  // Visual effects
  widget_header_gradient: true,
  border_radius: 'medium',
  font_family: 'system',
}

/**
 * Default navigation item.
 */
export const DEFAULT_NAVIGATION_ITEM: NavigationItem = {
  text: 'Nouvelle page',
  url: '/page.html',
}

/**
 * Default static page.
 */
export const DEFAULT_STATIC_PAGE: StaticPage = {
  name: 'new-page',
  template: 'page.html',
  output_file: 'new-page.html',
  context: null,
}
