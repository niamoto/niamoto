import { describe, expect, it } from 'vitest'
import {
  hasPublishableRootPage,
  isLegacyPlaceholderSite,
  requiresSiteSetup,
} from './siteReadiness'

describe('siteReadiness', () => {
  it('requires setup when static pages are empty', () => {
    expect(
      requiresSiteSetup({
        static_pages: [],
        navigation: [],
        footer_navigation: [],
      })
    ).toBe(true)
  })

  it('treats the legacy placeholder home as unconfigured', () => {
    expect(
      isLegacyPlaceholderSite({
        static_pages: [
          { name: 'home', template: 'index.html', output_file: 'index.html' },
        ],
        navigation: [],
        footer_navigation: [],
      })
    ).toBe(true)
  })

  it('recognizes a real configured root page when the home is linked', () => {
    expect(
      hasPublishableRootPage([
        { name: 'home', template: 'index.html', output_file: 'index.html' },
      ])
    ).toBe(true)

    expect(
      requiresSiteSetup({
        static_pages: [
          { name: 'home', template: 'index.html', output_file: 'index.html' },
        ],
        navigation: [{ text: 'Home', url: '/index.html' }],
        footer_navigation: [],
      })
    ).toBe(false)
  })

  it('treats a footer-linked home as configured even for the legacy placeholder page', () => {
    expect(
      isLegacyPlaceholderSite({
        static_pages: [
          { name: 'home', template: 'index.html', output_file: 'index.html' },
        ],
        navigation: [],
        footer_navigation: [
          {
            title: 'Explore',
            links: [{ text: 'Home', url: '/index.html' }],
          },
        ],
      })
    ).toBe(false)

    expect(
      requiresSiteSetup({
        static_pages: [
          { name: 'home', template: 'index.html', output_file: 'index.html' },
        ],
        navigation: [],
        footer_navigation: [
          {
            title: 'Explore',
            links: [{ text: 'Home', url: '/index.html' }],
          },
        ],
      })
    ).toBe(false)
  })
})
