import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { DashboardView } from "./DashboardView"
import { QuickActions } from "./QuickActions"
import { ActivityFeed } from "./ActivityFeed"
import type { PipelineStatus } from "@/hooks/usePipelineStatus"

const pipelineStatusState = vi.hoisted(() => ({
  value: {
    data: null,
    isLoading: false,
    isFetching: false,
  },
}))

const pipelineHistoryState = vi.hoisted(() => ({
  value: {
    data: [],
  },
}))

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>(
    "react-i18next",
  )
  return {
    ...actual,
    useTranslation: () => ({
      t: (
        key: string,
        defaultValue?: string | Record<string, unknown>,
        options?: Record<string, unknown>,
      ) => {
        if (typeof defaultValue === "string") {
          return defaultValue.replace(/\{\{(\w+)\}\}/g, (_match, token: string) =>
            String(options?.[token] ?? ""),
          )
        }
        return key
      },
      i18n: {
        language: "fr",
        resolvedLanguage: "fr",
      },
    }),
  }
})

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("date-fns", () => ({
  formatDistanceToNow: () => "il y a un instant",
}))

vi.mock("@/hooks/usePipelineStatus", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/usePipelineStatus")>(
    "@/hooks/usePipelineStatus",
  )
  return {
    ...actual,
    usePipelineStatus: () => pipelineStatusState.value,
  }
})

vi.mock("@/hooks/usePipelineHistory", () => ({
  usePipelineHistory: () => pipelineHistoryState.value,
}))

function buildPipelineStatus(
  overrides: Partial<PipelineStatus> = {},
): PipelineStatus {
  return {
    data: {
      status: "fresh",
      last_run_at: "2026-04-19T10:00:00",
      items: [],
      summary: {
        entities: [{ name: "taxons", row_count: 12 }],
      },
      last_job_duration_s: 4,
    },
    groups: {
      status: "fresh",
      last_run_at: "2026-04-19T10:05:00",
      items: [],
      summary: {
        groups: [{ name: "plots", entity_count: 3 }],
      },
      last_job_duration_s: 9,
    },
    site: {
      status: "fresh",
      last_run_at: null,
      items: [],
      summary: {
        page_count: 8,
      },
      last_job_duration_s: null,
    },
    publication: {
      status: "fresh",
      last_run_at: "2026-04-19T10:10:00",
      items: [],
      summary: {
        html_page_count: 8,
        total_size_mb: 2.4,
      },
      last_job_duration_s: 7,
    },
    running_job: null,
    ...overrides,
  }
}

describe("dashboard redesign regressions", () => {
  it("keeps the dashboard in pending state until the first build exists", () => {
    pipelineStatusState.value = {
      data: buildPipelineStatus({
        publication: {
          status: "never_run",
          last_run_at: null,
          items: [],
          summary: {
            html_page_count: 0,
            total_size_mb: 0,
          },
          last_job_duration_s: null,
        },
      }),
      isLoading: false,
      isFetching: false,
    }
    pipelineHistoryState.value = { data: [] }

    const html = renderToStaticMarkup(<DashboardView />)

    expect(html).toContain("Étapes initiales en attente")
    expect(html).not.toContain("Tout est à jour")
  })

  it("surfaces site configuration and keeps publish disabled until a build exists", () => {
    const html = renderToStaticMarkup(
      <QuickActions
        dataStatus="fresh"
        groupsStatus="fresh"
        siteStatus="unconfigured"
        publicationStatus="never_run"
        isRunning={false}
        hasEntities
      />,
    )

    expect(html).toContain("Configurer")
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>[\s\S]*Publier/)
  })

  it("renders the recent job history instead of synthesizing only one row per stage", () => {
    pipelineHistoryState.value = {
      data: [
        {
          id: "job-failed-transform",
          type: "transform",
          status: "failed",
          started_at: "2026-04-19T10:08:00",
          completed_at: "2026-04-19T10:09:00",
          message: "Échec sur la collection plots",
        },
        {
          id: "job-completed-transform",
          type: "transform",
          status: "completed",
          started_at: "2026-04-19T10:05:00",
          completed_at: "2026-04-19T10:06:30",
          message: "Recalcul terminé",
        },
      ],
    }

    const html = renderToStaticMarkup(<ActivityFeed />)

    expect(html).toContain("Échec sur la collection plots")
    expect(html).toContain("Recalcul terminé")
  })
})
