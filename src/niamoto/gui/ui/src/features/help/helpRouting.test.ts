import { describe, expect, it } from 'vitest'
import type { HelpManifest } from './api'
import {
  findHelpSelection,
  helpSlugFromPathname,
  normalizeHelpPathname,
  rankHelpSearchEntries,
} from './routing'

const manifest: HelpManifest = {
  generated_at: '2026-04-18T00:00:00Z',
  sections: [
    {
      slug: '02-user-guide',
      title: 'Desktop App Tour',
      description: 'UI walkthrough',
      path: '/help/02-user-guide',
      article_count: 2,
      pages: [
        {
          slug: '02-user-guide',
          path: '/help/02-user-guide',
          title: 'Desktop App Tour',
          description: 'Section overview',
          is_section_index: true,
          headings: [],
        },
        {
          slug: '02-user-guide/collections',
          path: '/help/02-user-guide/collections',
          title: 'Collections',
          description: 'Manage grouped outputs',
          is_section_index: false,
          headings: [
            {
              title: 'Configure collection content',
              level: 2,
              id: 'configure-collection-content',
            },
          ],
        },
      ],
    },
  ],
}

describe('help routing helpers', () => {
  it('normalizes help pathnames and extracts page slugs', () => {
    expect(normalizeHelpPathname('/help/02-user-guide/')).toBe(
      '/help/02-user-guide',
    )
    expect(normalizeHelpPathname('/groups')).toBe('/help')
    expect(helpSlugFromPathname('/help')).toBeNull()
    expect(helpSlugFromPathname('/help/02-user-guide/collections')).toBe(
      '02-user-guide/collections',
    )
  })

  it('finds sections and pages from the manifest', () => {
    expect(findHelpSelection(manifest, '/help')).toEqual({ slug: null })

    expect(findHelpSelection(manifest, '/help/02-user-guide')).toEqual({
      slug: '02-user-guide',
      section: manifest.sections[0],
      page: manifest.sections[0].pages[0],
    })

    expect(findHelpSelection(manifest, '/help/02-user-guide/collections')).toEqual({
      slug: '02-user-guide/collections',
      section: manifest.sections[0],
      page: manifest.sections[0].pages[1],
    })
  })

  it('ranks documentation search entries on titles and headings', () => {
    const results = rankHelpSearchEntries(
      [
        {
          slug: '02-user-guide',
          path: '/help/02-user-guide',
          section_slug: '02-user-guide',
          section_title: 'Desktop App Tour',
          title: 'Desktop App Tour',
          description: 'Overview',
          is_section_index: true,
          headings: ['Main path'],
          keywords: ['Desktop App Tour', 'Main path'],
        },
        {
          slug: '02-user-guide/collections',
          path: '/help/02-user-guide/collections',
          section_slug: '02-user-guide',
          section_title: 'Desktop App Tour',
          title: 'Collections',
          description: 'Manage grouped outputs',
          is_section_index: false,
          headings: ['Configure collection content'],
          keywords: ['Collections', 'Configure collection content'],
        },
      ],
      'collection content',
    )

    expect(results).toHaveLength(1)
    expect(results[0]?.slug).toBe('02-user-guide/collections')
  })
})
