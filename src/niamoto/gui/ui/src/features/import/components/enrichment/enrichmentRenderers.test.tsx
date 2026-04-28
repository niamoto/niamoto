import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { renderMappedPreview, renderValue } from './enrichmentRenderers'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

describe('enrichmentRenderers', () => {
  it('renders mapped image arrays as a gallery', () => {
    const html = renderToStaticMarkup(
      <>
        {renderValue([
          {
            url: 'http://api.endemia.nc/ressources/images/flore/media/photo/a/example.jpg',
            small_thumb:
              'http://api.endemia.nc/media/cache/small_thumb/ressources/images/flore/media/photo/a/example.jpg',
            auteur: 'Bernard Suprin',
            datmaj: '2012-04-16 15:54:00',
          },
          {
            url: 'http://api.endemia.nc/ressources/images/flore/media/photo/b/example.jpg',
            small_thumb:
              'http://api.endemia.nc/media/cache/small_thumb/ressources/images/flore/media/photo/b/example.jpg',
            auteur: 'Benoît Henry',
            datmaj: '2013-01-08 14:10:45',
          },
        ])}
      </>
    )

    expect(html).toContain('<img')
    expect(html).toContain('small_thumb')
    expect(html).toContain('Bernard Suprin')
    expect(html).toContain('Benoît Henry')
    expect(html).not.toContain('&quot;small_thumb&quot;')
  })

  it('does not add an internal scroll container to mapped previews', () => {
    const html = renderToStaticMarkup(
      <>
        {renderMappedPreview({
          images: [
            {
              url: 'http://api.endemia.nc/ressources/images/flore/media/photo/a/example.jpg',
              small_thumb:
                'http://api.endemia.nc/media/cache/small_thumb/ressources/images/flore/media/photo/a/example.jpg',
            },
          ],
        })}
      </>
    )

    expect(html).not.toContain('max-h-')
    expect(html).not.toContain('overflow-auto')
  })
})
