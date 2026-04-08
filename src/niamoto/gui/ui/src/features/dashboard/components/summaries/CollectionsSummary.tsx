import { useTranslation } from "react-i18next"
import { CheckCircle2, Circle } from "lucide-react"

import type { FreshnessStatus } from "@/hooks/usePipelineStatus"
import { cn } from "@/lib/utils"

export function CollectionsSummary({
  items,
  status,
  groups,
}: {
  items: Array<{ name: string; status: FreshnessStatus }>
  status?: FreshnessStatus
  groups?: Array<{ name: string }>
}) {
  const { t } = useTranslation("common")
  const availableGroups = groups?.map((group) => group.name) ?? []
  const configuredGroups = new Set(items.map((item) => item.name))

  if (status === 'unconfigured') {
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          {t(
            'pipeline.summary.collections_unconfigured',
            'No collection configured',
          )}
        </p>
        {availableGroups.length > 0 && (
          <div className="space-y-1">
            {availableGroups.map((groupName) => {
              const isConfigured = configuredGroups.has(groupName)

              return (
                <div
                  key={groupName}
                  className="flex items-center gap-2 text-xs text-muted-foreground"
                >
                  {isConfigured ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <Circle className="h-3.5 w-3.5 text-muted-foreground/50" />
                  )}
                  <span>{groupName}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  if (!items.length) return null

  const freshCount = items.filter((item) => item.status === "fresh").length
  const neverRunCount = items.filter((item) => item.status === "never_run").length
  const total = items.length
  const allFresh = freshCount === total
  const staleCount = items.filter((item) => item.status === "stale").length

  return (
    <p
      className={cn(
        "text-xs",
        allFresh
          ? "text-green-600 dark:text-green-400"
          : neverRunCount === total
            ? "text-muted-foreground"
            : "text-amber-600 dark:text-amber-400",
      )}
    >
      {allFresh
        ? t("pipeline.summary.collections_ratio", "{{fresh}}/{{total}} up to date", {
            fresh: freshCount,
            total,
          })
        : neverRunCount === total
          ? t(
              "pipeline.summary.collections_never_run_ratio",
              "{{count}}/{{total}} not yet calculated",
              { count: neverRunCount, total },
            )
        : t(
            "pipeline.summary.collections_stale_ratio",
            "{{stale}}/{{total}} need recomputing",
            { stale: staleCount, total },
          )}
    </p>
  )
}
