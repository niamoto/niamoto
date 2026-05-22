import { describe, expect, it } from 'vitest'
import { hoverClassName, variantClassName } from './MetricCard.styles'

describe('MetricCard', () => {
  it('uses dark-safe success tones for enrichment cards', () => {
    expect(variantClassName('success')).toContain('dark:bg-emerald-500/10')
    expect(hoverClassName('success')).toContain('dark:hover:bg-emerald-500/14')
  })
})
