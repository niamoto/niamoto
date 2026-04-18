import type {
  HelpManifest,
  HelpPageSummary,
  HelpSearchEntry,
  HelpSection,
} from './api'

export interface HelpSelection {
  slug: string | null
  section?: HelpSection
  page?: HelpPageSummary
}

export interface RankedHelpSearchEntry extends HelpSearchEntry {
  score: number
}

export function buildHelpPath(slug?: string | null) {
  return slug ? `/help/${slug}` : '/help'
}

export function normalizeHelpPathname(pathname: string) {
  if (!pathname.startsWith('/help')) {
    return '/help'
  }

  const trimmed = pathname.replace(/\/+$/, '')
  return trimmed || '/help'
}

export function helpSlugFromPathname(pathname: string) {
  const normalized = normalizeHelpPathname(pathname)

  if (normalized === '/help') {
    return null
  }

  return decodeURIComponent(normalized.slice('/help/'.length))
}

export function findHelpSelection(
  manifest: HelpManifest | undefined,
  pathname: string,
): HelpSelection {
  const slug = helpSlugFromPathname(pathname)

  if (!manifest || !slug) {
    return { slug }
  }

  for (const section of manifest.sections) {
    if (section.slug === slug) {
      return {
        slug,
        section,
        page: section.pages.find((page) => page.slug === slug) ?? section.pages[0],
      }
    }

    const page = section.pages.find((candidate) => candidate.slug === slug)
    if (page) {
      return { slug, section, page }
    }
  }

  return { slug }
}

function scoreHelpSearchEntry(entry: HelpSearchEntry, query: string) {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) {
    return 0
  }

  const tokens = normalizedQuery.split(/\s+/).filter(Boolean)
  const title = entry.title.toLowerCase()
  const sectionTitle = entry.section_title.toLowerCase()
  const description = entry.description.toLowerCase()
  const headings = entry.headings.map((heading) => heading.toLowerCase())
  const keywordBlob = entry.keywords.join(' ').toLowerCase()
  const haystacks = [title, sectionTitle, description, ...headings, keywordBlob]

  if (!tokens.every((token) => haystacks.some((value) => value.includes(token)))) {
    return 0
  }

  let score = 0

  if (title.includes(normalizedQuery)) {
    score += 120
  }

  if (sectionTitle.includes(normalizedQuery)) {
    score += 80
  }

  if (description.includes(normalizedQuery)) {
    score += 48
  }

  for (const heading of headings) {
    if (heading.includes(normalizedQuery)) {
      score += 36
    }
  }

  for (const token of tokens) {
    if (title.includes(token)) {
      score += 24
    }
    if (sectionTitle.includes(token)) {
      score += 18
    }
    if (description.includes(token)) {
      score += 10
    }
    if (headings.some((heading) => heading.includes(token))) {
      score += 12
    }
  }

  if (entry.is_section_index) {
    score += 4
  }

  return score
}

export function rankHelpSearchEntries(
  entries: HelpSearchEntry[],
  query: string,
  limit = 8,
): RankedHelpSearchEntry[] {
  return entries
    .map((entry) => ({
      ...entry,
      score: scoreHelpSearchEntry(entry, query),
    }))
    .filter((entry) => entry.score > 0)
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score
      }

      return left.title.localeCompare(right.title)
    })
    .slice(0, limit)
}
