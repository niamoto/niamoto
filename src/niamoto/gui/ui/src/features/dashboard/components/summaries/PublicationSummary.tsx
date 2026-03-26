import { useTranslation } from "react-i18next"
import { Package } from "lucide-react"

import type { StageSummary } from "@/hooks/usePipelineStatus"

export function PublicationSummary({
  summary,
}: {
  summary: StageSummary | null
}) {
  const { t } = useTranslation("common")
  if (!summary?.html_page_count) return null

  const parts: string[] = [
    t("pipeline.summary.html_pages", "{{count}} pages HTML", {
      count: summary.html_page_count,
    }),
  ]
  if ((summary.total_size_mb ?? 0) > 0) {
    parts.push(`${summary.total_size_mb} MB`)
  }

  return (
    <p className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <Package className="h-3 w-3" />
      {parts.join(" · ")}
    </p>
  )
}
