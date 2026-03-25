import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { AlertTriangle } from "lucide-react"

import type { StageSummary } from "@/hooks/usePipelineStatus"
import { useImportSummary } from "@/hooks/useImportSummary"

export function DataSummary({ summary }: { summary: StageSummary | null }) {
  const { t } = useTranslation("common")
  const navigate = useNavigate()
  const { data: importSummary } = useImportSummary()

  if (!summary?.entities?.length) return null

  const alertCount = importSummary?.alert_count ?? 0
  const datasetCount = importSummary?.dataset_count ?? 0
  const referenceCount = importSummary?.reference_count ?? 0
  const layerCount = importSummary?.layer_count ?? 0

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {summary.entities.map((entity) => (
          <span
            key={entity.name}
            className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-0.5 text-xs"
          >
            <span className="font-medium">{entity.name}</span>
            <span className="text-muted-foreground">
              {entity.row_count.toLocaleString()}
            </span>
          </span>
        ))}
      </div>

      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>
            {t("pipeline.summary.datasets", "{{count}} datasets", {
              count: datasetCount,
            })}
          </span>
          <span>•</span>
          <span>
            {t("pipeline.summary.references", "{{count}} references", {
              count: referenceCount,
            })}
          </span>
          {layerCount > 0 && (
            <>
              <span>•</span>
              <span>
                {t("pipeline.summary.layers", "{{count}} spatial layers", {
                  count: layerCount,
                })}
              </span>
            </>
          )}
        </div>
        {alertCount > 0 && (
          <div>
            <button
              className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-400 dark:hover:bg-amber-950"
              onClick={(e) => {
                e.stopPropagation()
                navigate("/sources")
              }}
            >
              <AlertTriangle className="h-3 w-3" />
              {alertCount === 1
                ? t("pipeline.summary.alert", "1 alert")
                : t("pipeline.summary.alerts", "{{count}} alerts", {
                    count: alertCount,
                  })}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
