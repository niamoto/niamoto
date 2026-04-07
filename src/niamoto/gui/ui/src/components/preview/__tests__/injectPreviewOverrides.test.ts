import { describe, expect, it } from 'vitest'

import { injectPreviewOverrides } from '../injectPreviewOverrides'

describe('injectPreviewOverrides', () => {
  const baseHtml = '<html><head><title>Preview</title></head><body><div>Chart</div></body></html>'

  it('keeps preview static while enabling full-size charts', () => {
    const html = injectPreviewOverrides(baseHtml, { fullSize: true })

    expect(html).toContain('layout.autosize=true;')
    expect(html).toContain('delete layout.width;')
    expect(html).toContain('delete layout.height;')
    expect(html).toContain('p.Plots.resize(gd)')
    expect(html).not.toContain('config.responsive=true')
    expect(html).not.toContain('config.staticPlot=false')
  })

  it('adds Leaflet control overrides without injecting Plotly script', () => {
    const html = injectPreviewOverrides(baseHtml, { hideLeafletControls: true })

    expect(html).toContain('.leaflet-control{display:none!important}')
    expect(html).not.toContain('Object.defineProperty(window,\'Plotly\'')
  })
})
