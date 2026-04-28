// @vitest-environment jsdom

import { act, type ReactNode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TransformParamsEditor } from './TransformParamsEditor'
import type { TransformParamDef } from '@/lib/api/recipes'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const transformSchemas: Record<string, Record<string, TransformParamDef>> = {
  direct: {
    threshold: {
      type: 'number',
      default: 10,
      description: 'Minimum threshold',
    },
  },
}

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  return {
    container,
    async render(element: ReactNode) {
      await act(async () => {
        root.render(element)
        await Promise.resolve()
      })
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

describe('TransformParamsEditor', () => {
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('does not emit params back to the parent while syncing props', async () => {
    vi.useFakeTimers()
    const onChange = vi.fn()
    const harness = createHarness()

    function Harness() {
      const [params, setParams] = useState<Record<string, unknown> | undefined>({
        threshold: 10,
      })

      return (
        <TransformParamsEditor
          selectedTransform="direct"
          transformSchemas={transformSchemas}
          value={params}
          onChange={(nextParams) => {
            onChange(nextParams)
            setParams(nextParams)
          }}
        />
      )
    }

    await harness.render(<Harness />)

    await act(async () => {
      vi.runOnlyPendingTimers()
      await Promise.resolve()
    })

    expect(onChange).not.toHaveBeenCalled()

    await harness.unmount()
    vi.useRealTimers()
  })
})
