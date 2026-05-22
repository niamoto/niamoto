import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'

import { AboutPartnersSection } from './AboutPartnersSection'

vi.mock('@/shared/desktop/openExternalUrl', () => ({
  openExternalUrl: vi.fn(),
}))

describe('AboutPartnersSection', () => {
  it('renders partner logo tiles with a themed support surface', () => {
    const html = renderToStaticMarkup(
      <AboutPartnersSection
        title="Partners"
        intro="Institutional support"
        organizations={[
          {
            id: 'province-nord',
            name: 'Province Nord',
            url: 'https://province-nord.nc',
            logoAlt: 'Province Nord',
            logoSrc: 'https://example.com/logo.png',
            categories: ['partner'],
          },
        ]}
      />
    )

    expect(html).toContain('bg-gradient-to-br')
    expect(html).toContain('bg-card/45')
    expect(html).toContain('Province Nord')
    expect(html).toContain('province-nord.nc')
  })
})
