import {
  getCanonicalStaticPageOutputFile,
  type FooterSection,
  type NavigationItem,
  type SiteConfigResponse,
  type StaticPage,
} from '@/shared/hooks/useSiteConfig'

type SiteLike = Pick<SiteConfigResponse, 'static_pages' | 'navigation' | 'footer_navigation'>

function navigationHasUrl(items: NavigationItem[], target: string): boolean {
  return items.some((item) =>
    item.url === target || navigationHasUrl(item.children ?? [], target)
  )
}

function footerHasUrl(sections: FooterSection[], target: string): boolean {
  return sections.some((section) => section.links.some((link) => link.url === target))
}

// Keep these frontend readiness rules aligned with the backend pipeline site-status
// logic in src/niamoto/gui/api/routers/pipeline.py so Site Builder and Publish
// use the same readiness semantics.
export function hasPublishableRootPage(pages: StaticPage[]): boolean {
  return pages.some((page) => getCanonicalStaticPageOutputFile(page) === 'index.html')
}

export function isLegacyPlaceholderSite(site: SiteLike): boolean {
  if (site.static_pages.length !== 1) return false

  const [page] = site.static_pages
  if (page.name.toLowerCase() !== 'home') return false
  if (page.template !== 'index.html') return false
  if (getCanonicalStaticPageOutputFile(page) !== 'index.html') return false
  if (page.context && Object.keys(page.context).length > 0) return false

  return !navigationHasUrl(site.navigation, '/index.html') &&
    !footerHasUrl(site.footer_navigation, '/index.html')
}

export function requiresSiteSetup(site: SiteLike): boolean {
  if (site.static_pages.length === 0) return true
  if (!hasPublishableRootPage(site.static_pages)) return true
  return isLegacyPlaceholderSite(site)
}
