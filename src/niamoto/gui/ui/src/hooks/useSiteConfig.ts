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
  primary_color: string
  nav_color: string
  github_url?: string | null
  [key: string]: unknown // Allow additional fields
}

export interface NavigationItem {
  text: string
  url: string
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
  static_pages: StaticPage[]
  template_dir: string
  output_dir: string
  copy_assets_from: string[]
}

export interface SiteConfigUpdate {
  site: SiteSettings
  navigation: NavigationItem[]
  static_pages: StaticPage[]
  template_dir?: string | null
  output_dir?: string | null
  copy_assets_from?: string[] | null
}

export interface TemplatesResponse {
  templates: string[]
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
  primary_color: '#228b22',
  nav_color: '#228b22',
  github_url: null,
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
  template: 'static_page.html',
  output_file: 'new-page.html',
  context: null,
}
