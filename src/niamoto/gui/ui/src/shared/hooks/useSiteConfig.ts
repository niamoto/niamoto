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
import { isAxiosError } from 'axios'
import type { LocalizedString } from '@/components/ui/localized-input'
import { apiClient } from '@/shared/lib/api/client'

const API_BASE = '/site'

function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.length > 0) {
      return detail
    }
    if (typeof error.message === 'string' && error.message.length > 0) {
      return error.message
    }
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}

// =============================================================================
// TYPES
// =============================================================================

export interface SiteSettings {
  title: string
  logo_header?: string | null
  logo_footer?: string | null
  lang: string
  // i18n settings
  languages?: string[]
  language_switcher?: boolean
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

// =============================================================================
// API FUNCTIONS
// =============================================================================

async function fetchSiteConfig(): Promise<SiteConfigResponse> {
  const response = await apiClient.get<SiteConfigResponse>(`${API_BASE}/config`)
  return response.data
}

async function updateSiteConfig(
  config: SiteConfigUpdate
): Promise<{ success: boolean; message: string; path: string }> {
  try {
    const response = await apiClient.put<{ success: boolean; message: string; path: string }>(
      `${API_BASE}/config`,
      config
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Update failed'))
  }
}

async function fetchTemplates(): Promise<TemplatesResponse> {
  const response = await apiClient.get<TemplatesResponse>(`${API_BASE}/templates`)
  return response.data
}

async function fetchProjectFiles(folder: string): Promise<FilesResponse> {
  const response = await apiClient.get<FilesResponse>(`${API_BASE}/files`, {
    params: { folder },
  })
  return response.data
}

async function previewMarkdown(content: string): Promise<{ html: string }> {
  try {
    const response = await apiClient.post<{ html: string }>(
      `${API_BASE}/preview-markdown`,
      { content }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Preview failed'))
  }
}

/**
 * Request for template preview.
 */
export interface TemplatePreviewRequest {
  template: string
  context: Record<string, unknown>
  site?: Record<string, unknown>
  navigation?: Array<{ text: LocalizedString; url?: string; children?: unknown[] }>
  footer_navigation?: Array<{ title: LocalizedString; links: Array<{ text: LocalizedString; url: string; external?: boolean }> }>
  output_file?: string
  gui_lang?: string
}

/**
 * Preview a template with the given context.
 */
async function previewTemplate(request: TemplatePreviewRequest): Promise<{ html: string; template: string }> {
  try {
    const response = await apiClient.post<{ html: string; template: string }>(
      `${API_BASE}/preview-template`,
      request
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Template preview failed'))
  }
}

async function fetchGroups(): Promise<GroupsResponse> {
  const response = await apiClient.get<GroupsResponse>(`${API_BASE}/groups`)
  return response.data
}

async function updateGroupIndexConfig(
  groupName: string,
  config: GroupIndexConfig
): Promise<GroupIndexConfig> {
  try {
    const response = await apiClient.put<GroupIndexConfig>(
      `/config/export/${encodeURIComponent(groupName)}/index-generator`,
      config
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Update failed'))
  }
}

export interface FileContentResponse {
  content: string
  path: string
  filename: string
}

async function fetchFileContent(path: string): Promise<FileContentResponse> {
  try {
    const response = await apiClient.get<FileContentResponse>(
      `${API_BASE}/file-content`,
      { params: { path } }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch file content'))
  }
}

async function updateFileContent(path: string, content: string): Promise<{ success: boolean; message: string; path: string }> {
  try {
    const response = await apiClient.put<{ success: boolean; message: string; path: string }>(
      `${API_BASE}/file-content`,
      { path, content }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Update failed'))
  }
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

export function useUpdateGroupIndexConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ groupName, config }: { groupName: string; config: GroupIndexConfig }) =>
      updateGroupIndexConfig(groupName, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['site-groups'] })
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
  gui_lang?: string
}

/**
 * Preview a group index page with mock data.
 */
async function previewGroupIndex(
  groupName: string,
  request?: GroupIndexPreviewRequest
): Promise<{ html: string; template: string }> {
  try {
    const response = await apiClient.post<{ html: string; template: string }>(
      `${API_BASE}/preview-group-index/${encodeURIComponent(groupName)}`,
      request || {}
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Group index preview failed'))
  }
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

  try {
    const response = await apiClient.post<{ success: boolean; path: string; filename: string }>(
      `${API_BASE}/upload`,
      formData,
      {
        params: { folder },
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Upload failed'))
  }
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
// DATA FILE HOOKS (JSON for externalized lists)
// =============================================================================

export interface DataContentResponse {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  path: string
  count: number
}

async function fetchDataContent(path: string): Promise<DataContentResponse> {
  try {
    const response = await apiClient.get<DataContentResponse>(
      `${API_BASE}/data-content`,
      { params: { path } }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch data content'))
  }
}

async function updateDataContent(
  path: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
): Promise<{ success: boolean; message: string; path: string; count: number }> {
  try {
    const response = await apiClient.put<{
      success: boolean
      message: string
      path: string
      count: number
    }>(`${API_BASE}/data-content`, { path, data })
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Update failed'))
  }
}

/**
 * Hook to fetch JSON data content for externalized lists.
 */
export function useDataContent(path: string | null | undefined) {
  return useQuery({
    queryKey: ['data-content', path],
    queryFn: () => fetchDataContent(path!),
    enabled: !!path,
    staleTime: 10000,
  })
}

/**
 * Hook to update JSON data content for externalized lists.
 */
export function useUpdateDataContent() {
  const queryClient = useQueryClient()

  return useMutation({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mutationFn: ({ path, data }: { path: string; data: any[] }) =>
      updateDataContent(path, data),
    onSuccess: (_, variables) => {
      // Invalidate the data content query to refresh
      queryClient.invalidateQueries({ queryKey: ['data-content', variables.path] })
    },
  })
}

// =============================================================================
// IMPORT HOOKS (BibTeX, CSV)
// =============================================================================

export interface ImportResponse {
  success: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  count: number
  errors: string[]
}

async function importBibtex(file: File): Promise<ImportResponse> {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await apiClient.post<ImportResponse>(
      `${API_BASE}/import-bibtex`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Import failed'))
  }
}

async function importCsv(file: File, delimiter = ',', hasHeader = true): Promise<ImportResponse> {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await apiClient.post<ImportResponse>(
      `${API_BASE}/import-csv`,
      formData,
      {
        params: {
          delimiter,
          has_header: hasHeader,
        },
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Import failed'))
  }
}

/**
 * Hook to import BibTeX files.
 */
export function useImportBibtex() {
  return useMutation({
    mutationFn: (file: File) => importBibtex(file),
  })
}

/**
 * Export references as a downloadable BibTeX file.
 */
export async function exportBibtex(references: Record<string, unknown>[]): Promise<void> {
  let blob: Blob
  try {
    const response = await apiClient.post<Blob>(`${API_BASE}/export-bibtex`, references, {
      responseType: 'blob',
    })
    blob = response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Export failed'))
  }

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'references.bib'
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Hook to import CSV files.
 */
export function useImportCsv() {
  return useMutation({
    mutationFn: ({ file, delimiter, hasHeader }: { file: File; delimiter?: string; hasHeader?: boolean }) =>
      importCsv(file, delimiter, hasHeader),
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
