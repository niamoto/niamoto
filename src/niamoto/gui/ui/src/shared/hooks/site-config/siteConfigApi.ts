import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'
import {
  getCanonicalStaticPageOutputFile,
  type DataContentResponse,
  type FileContentResponse,
  type FilesResponse,
  type GroupIndexConfig,
  type GroupIndexPreviewRequest,
  type GroupsResponse,
  type ImportResponse,
  type SiteConfigResponse,
  type SiteConfigUpdate,
  type TemplatePreviewRequest,
  type TemplatesResponse,
} from './types'

const API_BASE = '/site'

function normalizePageUrl(
  url: string | undefined,
  aliases: Map<string, string>
): string | undefined {
  if (!url) {
    return url
  }

  const normalized = url.replace(/^\/+/, '')
  const replacement = aliases.get(normalized)
  if (!replacement) {
    return url
  }

  return url.startsWith('/') ? `/${replacement}` : replacement
}

function normalizeSiteConfig(config: SiteConfigResponse): SiteConfigResponse {
  const aliases = new Map<string, string>()
  const staticPages = config.static_pages.map((page) => {
    const normalizedOutputFile = getCanonicalStaticPageOutputFile(page)
    if (page.output_file !== normalizedOutputFile) {
      aliases.set(page.output_file.replace(/^\/+/, ''), normalizedOutputFile)
    }

    return {
      ...page,
      output_file: normalizedOutputFile,
    }
  })

  const navigation = config.navigation.map((item) => ({
    ...item,
    url: normalizePageUrl(item.url, aliases),
    children: item.children?.map((child) => ({
      ...child,
      url: normalizePageUrl(child.url, aliases),
    })),
  }))

  const footerNavigation = config.footer_navigation.map((section) => ({
    ...section,
    links: section.links.map((link) => ({
      ...link,
      url: normalizePageUrl(link.url, aliases) || link.url,
    })),
  }))

  return {
    ...config,
    navigation,
    footer_navigation: footerNavigation,
    static_pages: staticPages,
  }
}

export async function fetchSiteConfig(): Promise<SiteConfigResponse> {
  const response = await apiClient.get<SiteConfigResponse>(`${API_BASE}/config`)
  return normalizeSiteConfig(response.data)
}

export async function updateSiteConfig(
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

export async function fetchTemplates(): Promise<TemplatesResponse> {
  const response = await apiClient.get<TemplatesResponse>(`${API_BASE}/templates`)
  return response.data
}

export async function fetchProjectFiles(folder: string): Promise<FilesResponse> {
  const response = await apiClient.get<FilesResponse>(`${API_BASE}/files`, {
    params: { folder },
  })
  return response.data
}

export async function previewMarkdown(content: string): Promise<{ html: string }> {
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

export async function previewTemplate(
  request: TemplatePreviewRequest
): Promise<{ html: string; template: string }> {
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

export async function fetchGroups(): Promise<GroupsResponse> {
  const response = await apiClient.get<GroupsResponse>(`${API_BASE}/groups`)
  return response.data
}

export async function updateGroupIndexConfig(
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

export async function previewGroupIndex(
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

export async function uploadFile(
  file: File,
  folder = 'files'
): Promise<{ success: boolean; path: string; filename: string }> {
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

export async function fetchFileContent(path: string): Promise<FileContentResponse> {
  try {
    const response = await apiClient.get<FileContentResponse>(`${API_BASE}/file-content`, {
      params: { path },
    })
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch file content'))
  }
}

export async function updateFileContent(
  path: string,
  content: string
): Promise<{ success: boolean; message: string; path: string }> {
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

export async function fetchDataContent(path: string): Promise<DataContentResponse> {
  try {
    const response = await apiClient.get<DataContentResponse>(`${API_BASE}/data-content`, {
      params: { path },
    })
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch data content'))
  }
}

export async function updateDataContent(
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

export async function importBibtex(file: File): Promise<ImportResponse> {
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

export async function importCsv(
  file: File,
  delimiter = ',',
  hasHeader = true
): Promise<ImportResponse> {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await apiClient.post<ImportResponse>(`${API_BASE}/import-csv`, formData, {
      params: {
        delimiter,
        has_header: hasHeader,
      },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Import failed'))
  }
}

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
