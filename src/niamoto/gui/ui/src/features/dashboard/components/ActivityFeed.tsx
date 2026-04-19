import { useTranslation } from "react-i18next"
import type { TFunction } from "i18next"
import { formatDistanceToNow } from "date-fns"
import { enUS, fr } from "date-fns/locale"
import { AlertTriangle, CheckCircle2, Database, Layers, Send } from "lucide-react"
import { usePipelineHistory, type JobHistoryEntry } from "@/hooks/usePipelineHistory"

interface ActivityItem {
  id: string
  type: "import" | "transform" | "export"
  last_run_at: string
  status: string
  message: string | null
  duration_s: number | null
}

function isTrackedHistoryEntry(
  entry: JobHistoryEntry,
): entry is JobHistoryEntry & {
  type: ActivityItem["type"]
  completed_at: string
} {
  return (
    !!entry.completed_at &&
    (entry.type === "import" ||
      entry.type === "transform" ||
      entry.type === "export")
  )
}

function buildActivity(entries: JobHistoryEntry[] | undefined): ActivityItem[] {
  if (!entries) {
    return []
  }

  return entries
    .filter(isTrackedHistoryEntry)
    .map((entry) => ({
      id: entry.id,
      type: entry.type,
      last_run_at: entry.completed_at,
      status: entry.status,
      message: entry.message ?? null,
      duration_s:
        entry.started_at && entry.completed_at
          ? Math.max(
              0,
              Math.round(
                (new Date(entry.completed_at).getTime() -
                  new Date(entry.started_at).getTime()) /
                  1000,
              ),
            )
          : null,
    }))
    .sort(
      (a, b) =>
        new Date(b.last_run_at).getTime() - new Date(a.last_run_at).getTime(),
    )
}

type ActivityType = "import" | "transform" | "export"

function typeConfig(type: ActivityType, t: TFunction) {
  switch (type) {
    case "import":
      return {
        icon: <Database className="h-3.5 w-3.5" />,
        label: t("pipeline.activity.type_import", "Import"),
        bg: "bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400",
      }
    case "transform":
      return {
        icon: <Layers className="h-3.5 w-3.5" />,
        label: t("pipeline.activity.type_transform", "Recalcul"),
        bg: "bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400",
      }
    case "export":
      return {
        icon: <Send className="h-3.5 w-3.5" />,
        label: t("pipeline.activity.type_export", "Export"),
        bg: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400",
      }
  }
}

interface ActivityFeedProps {
  limit?: number
}

function statusMeta(status: string, t: TFunction) {
  if (status === "completed") {
    return {
      icon: <CheckCircle2 className="h-3 w-3 text-green-500" />,
      label: t("pipeline.activity.status_completed", "Terminé"),
    }
  }

  if (status === "failed") {
    return {
      icon: <AlertTriangle className="h-3 w-3 text-red-500" />,
      label: t("pipeline.activity.status_failed", "Échec"),
    }
  }

  return {
    icon: <AlertTriangle className="h-3 w-3 text-amber-500" />,
    label: t("pipeline.activity.status_interrupted", "Interrompu"),
  }
}

export function ActivityFeed({ limit = 10 }: ActivityFeedProps) {
  const { t, i18n } = useTranslation("common")
  const dateLocale = i18n.language === "fr" ? fr : enUS
  const { data: history } = usePipelineHistory(limit)

  const items = buildActivity(history)

  if (items.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        {t("pipeline.no_activity", "Aucune activité récente")}
      </p>
    )
  }

  return (
    <div className="divide-y divide-border/50">
      {items.map((item) => {
        const cfg = typeConfig(item.type, t)
        const status = statusMeta(item.status, t)
        const timeAgo = formatDistanceToNow(new Date(item.last_run_at), {
          addSuffix: true,
          locale: dateLocale,
        })

        return (
          <div key={item.id} className="flex items-start gap-2.5 py-2">
            <div
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md ${cfg.bg}`}
            >
              {cfg.icon}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium">{cfg.label}</span>
                {status.icon}
                <span className="text-[11px] text-muted-foreground">{status.label}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {timeAgo}
                {item.duration_s != null && (
                  <span className="ml-1.5 opacity-70">· {item.duration_s}s</span>
                )}
              </p>
              {item.message && (
                <p className="truncate text-[11px] text-muted-foreground">
                  {item.message}
                </p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
