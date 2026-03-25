import { useTranslation } from "react-i18next"

import type { StageSummary } from "@/hooks/usePipelineStatus"

export function SiteSummary({ summary }: { summary: StageSummary | null }) {
  const { t } = useTranslation("common")
  if (!summary) return null

  const parts: string[] = []
  if ((summary.page_count ?? 0) > 0) {
    parts.push(
      t("pipeline.summary.pages", "{{count}} pages", {
        count: summary.page_count,
      }),
    )
  }
  if ((summary.language_count ?? 0) > 1 && summary.languages) {
    parts.push(summary.languages.join(", "))
  }

  return (
    <div className="space-y-1">
      {summary.title && <p className="text-sm font-medium">{summary.title}</p>}
      {parts.length > 0 && (
        <p className="text-xs text-muted-foreground">{parts.join(" · ")}</p>
      )}
    </div>
  )
}
