import { renderToStaticMarkup } from "react-dom/server"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: "/" }),
}))

vi.mock("motion/react", () => ({
  motion: {
    div: (props: {
      children: ReactNode
      className?: string
      initial?: unknown
      animate?: unknown
      exit?: unknown
      transition?: unknown
    }) => (
      <div
        className={props.className}
        data-motion-initial={JSON.stringify(props.initial)}
        data-motion-animate={JSON.stringify(props.animate)}
        data-motion-exit={JSON.stringify(props.exit)}
        data-motion-transition={JSON.stringify(props.transition)}
      >
        {props.children}
      </div>
    ),
  },
}))

vi.mock("@/components/motion/useReducedMotion", () => ({
  useReducedMotion: () => false,
}))

import { PageTransition } from "./PageTransition"

describe("PageTransition", () => {
  it("keeps the initial route mount visible", () => {
    const html = renderToStaticMarkup(
      <PageTransition>
        <main>Dashboard</main>
      </PageTransition>,
    )

    expect(html).toContain('&quot;opacity&quot;:0.98')
    expect(html).not.toContain('&quot;opacity&quot;:0,&quot;')
  })

  it("uses a simple no-exit transition to avoid overlay ghosting", () => {
    const html = renderToStaticMarkup(
      <PageTransition transitionKey="/sources">
        <main>Data</main>
      </PageTransition>,
    )

    expect(html).toContain('&quot;duration&quot;:0.18')
    expect(html).toContain('&quot;opacity&quot;:1')
    expect(html).toContain('&quot;y&quot;:0')
    expect(html).not.toContain('data-motion-exit')
    expect(html).not.toContain('filter')
  })
})
