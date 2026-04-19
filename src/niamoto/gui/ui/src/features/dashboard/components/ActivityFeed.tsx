import { useTranslation } from "react-i18next"
import { formatDistanceToNow } from "date-fns"
import { enUS, fr } from "date-fns/locale"
import {
  AlertCircle,
  CheckCircle2,
  Database,
  Layers,
  Loader2,
  Send,
  XCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { JobHistoryEntry } from "@/hooks/usePipelineHistory"
import { usePipelineHistory } from "@/hooks/usePipelineHistory"

function jobIcon(type: string) {
  switch (type) {
    case "import":
      return <Database className="h-3.5 w-3.5" />
    case "transform":
      return <Layers className="h-3.5 w-3.5" />
    case "export":
      return <Send className="h-3.5 w-3.5" />
    default:
      return <AlertCircle className="h-3.5 w-3.5" />
  }
}

function statusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-3 w-3 text-green-500" />
    case "failed":
      return <XCircle className="h-3 w-3 text-red-500" />
    case "running":
      return <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
    default:
      return <AlertCircle className="h-3 w-3 text-muted-foreground" />
  }
}

const JOB_TYPE_LABELS: Record<string, string> = {
  import: "Import",
  transform: "Recalculer",
  export: "Export",
}

function ActivityEntry({ entry }: { entry: JobHistoryEntry }) {
  const { i18n } = useTranslation()
  const dateLocale = i18n.language === "fr" ? fr : enUS

  const refDate = entry.completed_at ?? entry.started_at
  const timeAgo = refDate
    ? formatDistanceToNow(new Date(refDate), {
        addSuffix: true,
        locale: dateLocale,
      })
    : null

  const isCompleted = entry.status === "completed"
  const isFailed = entry.status === "failed"

  return (
    <div className="flex items-start gap-2.5 py-2">
      <div
        className={cn(
          "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
          isCompleted && "bg-green-50 text-green-600 dark:bg-green-950/40 dark:text-green-400",
          isFailed && "bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400",
          !isCompleted &&
            !isFailed &&
            "bg-muted text-muted-foreground",
        )}
      >
        {jobIcon(entry.type)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium">
            {JOB_TYPE_LABELS[entry.type] ?? entry.type}
          </span>
          {entry.group_by && (
            <span className="max-w-[100px] truncate text-[11px] text-muted-foreground">
              · {entry.group_by}
            </span>
          )}
          {statusIcon(entry.status)}
        </div>
        {timeAgo && (
          <p className="text-[11px] text-muted-foreground">{timeAgo}</p>
        )}
      </div>
    </div>
  )
}

export function ActivityFeed() {
  const { t } = useTranslation("common")
  const { data: history, isLoading } = usePipelineHistory(8)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>{t("common.loading", "Chargement...")}</span>
      </div>
    )
  }

  if (!history || history.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        {t("pipeline.no_activity", "Aucune activité récente")}
      </p>
    )
  }

  return (
    <div className="divide-y divide-border/50">
      {history.map((entry) => (
        <ActivityEntry key={entry.id} entry={entry} />
      ))}
    </div>
  )
}
