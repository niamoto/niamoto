import { useTranslation } from "react-i18next"

import type { FreshnessStatus } from "@/hooks/usePipelineStatus"
import { cn } from "@/lib/utils"

export function CollectionsSummary({
  items,
}: {
  items: Array<{ name: string; status: FreshnessStatus }>
}) {
  const { t } = useTranslation("common")
  if (!items.length) return null

  const freshCount = items.filter((item) => item.status === "fresh").length
  const total = items.length
  const allFresh = freshCount === total
  const staleCount = total - freshCount

  return (
    <p
      className={cn(
        "text-xs",
        allFresh
          ? "text-green-600 dark:text-green-400"
          : "text-amber-600 dark:text-amber-400",
      )}
    >
      {allFresh
        ? t("pipeline.summary.collections_ratio", "{{fresh}}/{{total}} up to date", {
            fresh: freshCount,
            total,
          })
        : t(
            "pipeline.summary.collections_stale_ratio",
            "{{stale}}/{{total}} need recomputing",
            { stale: staleCount, total },
          )}
    </p>
  )
}
