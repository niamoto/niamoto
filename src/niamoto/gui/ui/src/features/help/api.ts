import apiClient from '@/shared/lib/api/client'

export interface HelpHeading {
  title: string
  level: number
  id: string
}

export interface HelpPageSummary {
  slug: string
  path: string
  title: string
  description: string
  is_section_index: boolean
  headings: HelpHeading[]
}

export interface HelpSection {
  slug: string
  title: string
  description: string
  path: string
  article_count: number
  pages: HelpPageSummary[]
}

export interface HelpManifest {
  generated_at: string
  sections: HelpSection[]
}

export interface HelpPage extends HelpPageSummary {
  html: string
  section_slug: string
  source_path: string
}

export interface HelpSearchEntry {
  slug: string
  path: string
  section_slug: string
  section_title: string
  title: string
  description: string
  is_section_index: boolean
  headings: string[]
  keywords: string[]
}

export interface HelpSearchIndex {
  generated_at: string
  entries: HelpSearchEntry[]
}

export async function fetchHelpManifest() {
  const response = await apiClient.get<HelpManifest>('/help/manifest')
  return response.data
}

export async function fetchHelpSearchIndex() {
  const response = await apiClient.get<HelpSearchIndex>('/help/search-index')
  return response.data
}

export async function fetchHelpPage(slug: string) {
  const response = await apiClient.get<HelpPage>(`/help/pages/${slug}`)
  return response.data
}
